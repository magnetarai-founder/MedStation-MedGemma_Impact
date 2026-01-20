"""
Hardware Detection for llama.cpp

Detects available GPU memory and validates model compatibility.
Optimized for Apple Silicon (Metal) with fallback for other platforms.
"""

import logging
import platform
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    """System hardware information"""
    platform: str  # "darwin", "linux", "windows"
    architecture: str  # "arm64", "x86_64"
    is_apple_silicon: bool

    # Memory
    total_memory_gb: float
    available_memory_gb: float

    # GPU
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None  # Dedicated VRAM (or unified for Apple Silicon)
    has_metal: bool = False
    has_cuda: bool = False
    metal_gpu_family: Optional[str] = None  # e.g., "Apple M2 Pro"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "architecture": self.architecture,
            "is_apple_silicon": self.is_apple_silicon,
            "total_memory_gb": round(self.total_memory_gb, 1),
            "available_memory_gb": round(self.available_memory_gb, 1),
            "gpu_name": self.gpu_name,
            "gpu_vram_gb": round(self.gpu_vram_gb, 1) if self.gpu_vram_gb else None,
            "has_metal": self.has_metal,
            "has_cuda": self.has_cuda,
            "metal_gpu_family": self.metal_gpu_family,
        }


def _get_macos_memory() -> tuple[float, float]:
    """Get total and available memory on macOS"""
    try:
        # Get total memory via sysctl
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True
        )
        total_bytes = int(result.stdout.strip())
        total_gb = total_bytes / (1024**3)

        # Get memory pressure / available via vm_stat
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True
        )

        # Parse vm_stat output
        page_size = 16384  # Default Apple Silicon page size
        free_pages = 0
        inactive_pages = 0

        for line in result.stdout.split("\n"):
            if "page size" in line.lower():
                try:
                    page_size = int(line.split()[-2])
                except (ValueError, IndexError):
                    pass
            elif "Pages free:" in line:
                try:
                    free_pages = int(line.split(":")[1].strip().rstrip("."))
                except (ValueError, IndexError):
                    pass
            elif "Pages inactive:" in line:
                try:
                    inactive_pages = int(line.split(":")[1].strip().rstrip("."))
                except (ValueError, IndexError):
                    pass

        # Available = free + inactive (can be reclaimed)
        available_bytes = (free_pages + inactive_pages) * page_size
        available_gb = available_bytes / (1024**3)

        return total_gb, available_gb

    except Exception as e:
        logger.warning(f"Failed to get macOS memory: {e}")
        return 8.0, 4.0  # Conservative defaults


def _get_apple_silicon_info() -> tuple[str, str]:
    """Get Apple Silicon chip name and GPU family"""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True
        )
        chip_name = result.stdout.strip()

        # Map to GPU family
        if "M3" in chip_name:
            gpu_family = "Apple M3 GPU"
        elif "M2" in chip_name:
            gpu_family = "Apple M2 GPU"
        elif "M1" in chip_name:
            gpu_family = "Apple M1 GPU"
        else:
            gpu_family = "Apple GPU"

        return chip_name, gpu_family

    except Exception as e:
        logger.warning(f"Failed to get Apple Silicon info: {e}")
        return "Apple Silicon", "Apple GPU"


def _check_metal_support() -> bool:
    """Check if Metal GPU is available"""
    if platform.system() != "Darwin":
        return False

    try:
        # Try to use system_profiler for GPU info
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=5
        )

        import json
        data = json.loads(result.stdout)
        displays = data.get("SPDisplaysDataType", [])

        for display in displays:
            # Check for Metal support indicator
            metal_support = display.get("spdisplays_metal_support")
            if metal_support and "supported" in metal_support.lower():
                return True
            # Apple Silicon GPUs always support Metal
            vendor = display.get("spdisplays_vendor", "").lower()
            if "apple" in vendor:
                return True

        return False

    except Exception as e:
        logger.debug(f"Metal check failed: {e}")
        # Assume Metal on macOS ARM64
        return platform.machine() == "arm64"


def _check_cuda_support() -> bool:
    """Check if CUDA is available"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_nvidia_vram() -> Optional[float]:
    """Get NVIDIA GPU VRAM in GB"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            vram_mb = int(result.stdout.strip().split("\n")[0])
            return vram_mb / 1024
    except Exception:
        pass
    return None


def detect_hardware() -> HardwareInfo:
    """
    Detect system hardware for model compatibility

    Returns:
        HardwareInfo with detected hardware capabilities
    """
    system = platform.system().lower()
    arch = platform.machine()
    is_apple_silicon = system == "darwin" and arch == "arm64"

    # Get memory
    if system == "darwin":
        total_mem, avail_mem = _get_macos_memory()
    else:
        # Linux/Windows fallback
        try:
            import psutil
            mem = psutil.virtual_memory()
            total_mem = mem.total / (1024**3)
            avail_mem = mem.available / (1024**3)
        except ImportError:
            total_mem = 8.0
            avail_mem = 4.0

    # GPU detection
    gpu_name = None
    gpu_vram = None
    has_metal = False
    has_cuda = False
    metal_family = None

    if is_apple_silicon:
        chip_name, metal_family = _get_apple_silicon_info()
        gpu_name = chip_name
        # Apple Silicon uses unified memory - GPU can use most of system RAM
        # Leave some headroom for OS and apps
        gpu_vram = total_mem * 0.75  # 75% of total as usable VRAM
        has_metal = True
    else:
        has_metal = _check_metal_support()
        has_cuda = _check_cuda_support()

        if has_cuda:
            gpu_vram = _get_nvidia_vram()
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    gpu_name = result.stdout.strip().split("\n")[0]
            except Exception:
                pass

    return HardwareInfo(
        platform=system,
        architecture=arch,
        is_apple_silicon=is_apple_silicon,
        total_memory_gb=total_mem,
        available_memory_gb=avail_mem,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram,
        has_metal=has_metal,
        has_cuda=has_cuda,
        metal_gpu_family=metal_family,
    )


def validate_model_fits(
    model_size_gb: float,
    min_vram_gb: float,
    hardware: Optional[HardwareInfo] = None
) -> tuple[bool, str]:
    """
    Validate if a model will fit in available VRAM

    Args:
        model_size_gb: Model file size in GB
        min_vram_gb: Minimum VRAM required by the model
        hardware: Hardware info (auto-detected if not provided)

    Returns:
        Tuple of (fits: bool, message: str)
    """
    if hardware is None:
        hardware = detect_hardware()

    # Get effective VRAM
    effective_vram = hardware.gpu_vram_gb
    if effective_vram is None:
        # CPU-only inference
        effective_vram = hardware.available_memory_gb * 0.8

    # Check if model fits
    if effective_vram >= min_vram_gb:
        return True, f"Model fits ({model_size_gb:.1f}GB requires {min_vram_gb:.1f}GB VRAM, {effective_vram:.1f}GB available)"

    return False, f"Insufficient VRAM: model needs {min_vram_gb:.1f}GB but only {effective_vram:.1f}GB available"


def recommend_quantization(
    hardware: Optional[HardwareInfo] = None
) -> str:
    """
    Recommend a quantization level based on available hardware

    Returns:
        Recommended quantization level string (e.g., "Q4_K_M", "Q8_0")
    """
    if hardware is None:
        hardware = detect_hardware()

    effective_vram = hardware.gpu_vram_gb or (hardware.available_memory_gb * 0.8)

    if effective_vram >= 24:
        return "Q8_0"  # High quality, lots of VRAM
    elif effective_vram >= 16:
        return "Q6_K"  # Very good quality
    elif effective_vram >= 10:
        return "Q5_K_M"  # Good quality/size balance
    elif effective_vram >= 6:
        return "Q4_K_M"  # Best balance for most users
    else:
        return "Q3_K_M"  # Lower quality for constrained hardware


# Cache hardware info
_hardware_cache: Optional[HardwareInfo] = None


def get_hardware_info(refresh: bool = False) -> HardwareInfo:
    """
    Get cached hardware info

    Args:
        refresh: Force re-detection

    Returns:
        HardwareInfo
    """
    global _hardware_cache
    if _hardware_cache is None or refresh:
        _hardware_cache = detect_hardware()
    return _hardware_cache


__all__ = [
    "HardwareInfo",
    "detect_hardware",
    "validate_model_fits",
    "recommend_quantization",
    "get_hardware_info",
]
