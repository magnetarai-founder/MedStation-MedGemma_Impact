"""
Chat Enhancements for Neutron
- Automatic title generation
- RAG for file uploads (PDF, DOCX, TXT)
- Semantic search across conversations
- Analytics and insights
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChatTitleGenerator:
    """Generate smart titles from conversation context"""

    @staticmethod
    def generate_from_first_message(content: str) -> str:
        """Generate title from first user message"""
        # Clean the content
        content = content.strip()

        # If it's a question, use it directly (truncated)
        if content.endswith('?'):
            title = content[:50]
            if len(content) > 50:
                title += "..."
            return title

        # Extract key phrases
        # Look for imperative verbs (write, create, explain, etc.)
        imperative_patterns = [
            r'^(write|create|make|build|explain|show|tell|help|generate|code)\s+(.+)',
            r'^(how|what|why|when|where)\s+(.+)',
            r'^(.+?)\s+(function|class|script|program|code)',
        ]

        for pattern in imperative_patterns:
            match = re.match(pattern, content, re.IGNORECASE)
            if match:
                # Use the matched portion as title
                title = content[:50]
                if len(content) > 50:
                    title = title.rsplit(' ', 1)[0] + "..."
                return title

        # Fallback: first sentence or 50 chars
        sentences = re.split(r'[.!?]', content)
        first_sentence = sentences[0].strip()

        if len(first_sentence) <= 50:
            return first_sentence
        else:
            return first_sentence[:47] + "..."

    @staticmethod
    def generate_from_topic(messages: List[Dict]) -> str:
        """Generate title by analyzing conversation topics"""
        if not messages:
            return "New Chat"

        # Extract first user message
        for msg in messages:
            if msg.get('role') == 'user':
                return ChatTitleGenerator.generate_from_first_message(msg['content'])

        return "New Chat"


class FileTextExtractor:
    """Extract text from various file formats for RAG"""

    @staticmethod
    def extract_from_pdf(file_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            text_parts = []

            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            return "\n\n".join(text_parts)

        except ImportError:
            logger.warning("PyPDF2 not installed - PDF extraction disabled")
            return "[PDF extraction requires PyPDF2: pip install pypdf2]"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"[PDF extraction error: {str(e)}]"

    @staticmethod
    def extract_from_docx(file_path: Path) -> str:
        """Extract text from DOCX file"""
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)

        except ImportError:
            logger.warning("python-docx not installed - DOCX extraction disabled")
            return "[DOCX extraction requires python-docx: pip install python-docx]"
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return f"[DOCX extraction error: {str(e)}]"

    @staticmethod
    def extract_from_text(file_path: Path) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
                return f"[Text extraction error: {str(e)}]"

    @staticmethod
    def extract_from_markdown(file_path: Path) -> str:
        """Extract text from Markdown file"""
        return FileTextExtractor.extract_from_text(file_path)

    @staticmethod
    def extract(file_path: Path, content_type: str) -> Optional[str]:
        """Extract text based on file type"""
        if content_type == "application/pdf":
            return FileTextExtractor.extract_from_pdf(file_path)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return FileTextExtractor.extract_from_docx(file_path)
        elif content_type.startswith("text/"):
            return FileTextExtractor.extract_from_text(file_path)
        elif file_path.suffix.lower() == ".md":
            return FileTextExtractor.extract_from_markdown(file_path)
        else:
            logger.warning(f"Unsupported file type for extraction: {content_type}")
            return None


class SimpleEmbedding:
    """
    Unified embedding interface with hardware acceleration
    Uses MLX (Metal + ANE) when available, falls back gracefully
    """

    @staticmethod
    def create_embedding(text: str) -> List[float]:
        """
        Create embedding vector from text
        Automatically uses best available backend:
        - MLX (Metal + ANE) on Apple Silicon
        - Ollama if running locally
        - Hash-based fallback
        """
        try:
            from api.unified_embedder import embed_text
            return embed_text(text)
        except Exception as e:
            logger.debug(f"Unified embedder unavailable, using hash fallback: {e}")
            # Fallback to hash
            return SimpleEmbedding._hash_embed(text)

    @staticmethod
    def _hash_embed(text: str, dim: int = 384) -> List[float]:
        """Hash-based embedding fallback"""
        text = text.lower().strip()
        embedding = []

        for i in range(dim):
            hash_val = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
            embedding.append((int(hash_val[:8], 16) % 1000) / 500 - 1)

        # L2 normalize
        norm = sum(x*x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


class ConversationAnalytics:
    """Generate analytics and insights from conversations"""

    @staticmethod
    def calculate_session_stats(messages: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for a session"""
        if not messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "total_tokens": 0,
                "models_used": [],
                "avg_response_length": 0
            }

        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']

        total_tokens = sum(m.get('tokens', 0) for m in messages if m.get('tokens'))

        models = set()
        for msg in messages:
            if msg.get('model'):
                models.add(msg['model'])

        response_lengths = [len(m.get('content', '')) for m in assistant_messages]
        avg_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0

        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_tokens": total_tokens,
            "models_used": list(models),
            "avg_response_length": int(avg_length)
        }

    @staticmethod
    def get_conversation_topics(messages: List[Dict]) -> List[str]:
        """Extract key topics from conversation"""
        topics = []

        # Look for common programming keywords
        keywords = [
            'python', 'javascript', 'java', 'code', 'function', 'class',
            'api', 'database', 'sql', 'html', 'css', 'react', 'vue',
            'error', 'debug', 'test', 'refactor'
        ]

        content = " ".join(m.get('content', '').lower() for m in messages)

        for keyword in keywords:
            if keyword in content:
                topics.append(keyword)

        return topics[:5]  # Top 5 topics


class DocumentChunker:
    """Split documents into chunks for RAG"""

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                # Start new chunk with overlap
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    def create_chunks_with_metadata(text: str, file_info: Dict) -> List[Dict[str, Any]]:
        """Create chunks with metadata for storage"""
        chunks = DocumentChunker.chunk_text(text)

        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_objects.append({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content": chunk,
                "file_id": file_info.get("id"),
                "filename": file_info.get("original_name"),
                "file_type": file_info.get("type"),
                "embedding": SimpleEmbedding.create_embedding(chunk)
            })

        return chunk_objects
