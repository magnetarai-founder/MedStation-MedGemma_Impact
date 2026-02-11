"""
MedGemma inference service.

Loads google/medgemma-1.5-4b-it from a local snapshot and runs inference
on Apple Silicon (MPS) or CPU. Supports both text-only and multimodal
(text + image) queries.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator

import torch

logger = logging.getLogger(__name__)

# Default local model path (downloaded via huggingface_hub.snapshot_download)
_DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[4] / ".models" / "medgemma-1.5-4b-it"


class MedGemmaService:
    """Singleton service for MedGemma inference."""

    _instance: Optional["MedGemmaService"] = None

    def __init__(self):
        self.model = None
        self.processor = None
        self.device: str = "cpu"
        self.loaded = False
        self._loading = False

    @classmethod
    def get(cls) -> "MedGemmaService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def load(self, model_dir: Optional[str] = None) -> bool:
        """Load model and processor. Safe to call multiple times."""
        if self.loaded:
            return True
        if self._loading:
            # Another coroutine is already loading
            while self._loading:
                await asyncio.sleep(0.5)
            return self.loaded

        self._loading = True
        try:
            model_path = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR

            if not model_path.exists():
                logger.error(f"Model directory not found: {model_path}")
                logger.error("Download with: huggingface-cli download google/medgemma-1.5-4b-it --local-dir .models/medgemma-1.5-4b-it")
                return False

            logger.info(f"Loading MedGemma from {model_path}...")

            # Import here to avoid slow startup if not used
            from transformers import AutoProcessor, AutoModelForImageTextToText

            # Determine device
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            logger.info(f"Using device: {self.device}")

            # Load in a thread to avoid blocking the event loop
            def _load():
                self.processor = AutoProcessor.from_pretrained(str(model_path))
                self.model = AutoModelForImageTextToText.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.bfloat16 if self.device != "cpu" else torch.float32,
                    device_map=self.device,
                )

            await asyncio.to_thread(_load)

            self.loaded = True
            logger.info(f"MedGemma loaded on {self.device}")
            return True

        except Exception as e:
            logger.error(f"Failed to load MedGemma: {e}", exc_info=True)
            return False
        finally:
            self._loading = False

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are an expert medical AI assistant.",
        image=None,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate a response from MedGemma.

        Args:
            prompt: User's medical query
            system_prompt: System instruction
            image: Optional PIL Image for multimodal queries
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 = greedy)
        """
        if not self.loaded:
            ok = await self.load()
            if not ok:
                return "Error: MedGemma model not loaded. Please check the model directory."

        # Build messages in chat format
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        ]

        user_content = []
        if image is not None:
            user_content.append({"type": "image", "image": image})
        user_content.append({"type": "text", "text": prompt})

        messages.append({"role": "user", "content": user_content})

        def _infer():
            inputs = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self.model.device, dtype=self.model.dtype)

            input_len = inputs["input_ids"].shape[-1]

            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=temperature > 0,
                    temperature=temperature if temperature > 0 else None,
                )

            generated = output[0][input_len:]
            return self.processor.decode(generated, skip_special_tokens=True)

        return await asyncio.to_thread(_infer)

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "You are an expert medical AI assistant.",
        image=None,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from MedGemma using TextIteratorStreamer.
        """
        if not self.loaded:
            ok = await self.load()
            if not ok:
                yield "Error: MedGemma model not loaded."
                return

        from transformers import TextIteratorStreamer
        import threading

        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        ]
        user_content = []
        if image is not None:
            user_content.append({"type": "image", "image": image})
        user_content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": user_content})

        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device, dtype=self.model.dtype)

        streamer = TextIteratorStreamer(
            self.processor.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        gen_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0,
            "streamer": streamer,
        }
        if temperature > 0:
            gen_kwargs["temperature"] = temperature

        thread = threading.Thread(
            target=lambda: self.model.generate(**gen_kwargs),
            daemon=True,
        )
        thread.start()

        for token in streamer:
            yield token

        thread.join(timeout=5)


def get_medgemma() -> MedGemmaService:
    """Get the MedGemma singleton."""
    return MedGemmaService.get()
