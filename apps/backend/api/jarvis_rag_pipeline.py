#!/usr/bin/env python3
"""
RAG pipeline for Jarvis.
- Ingestion: chunk files and store embeddings into SQLite content_chunks table
- Retrieval: cosine similarity against stored embeddings, with keyword/history fallback
- Enhanced with auto-ingestion, tagging, and biased retrieval
"""

import os
import re
from pathlib import Path
from typing import Any, List, Tuple
import json
import math
import os

from jarvis_bigquery_memory import JarvisBigQueryMemory

# Import enhanced functionality
try:
    from rag_pipeline_enhanced import EnhancedRAGPipeline
    _enhanced_pipeline = None
    
    def get_enhanced_pipeline() -> Any:
        global _enhanced_pipeline
        if _enhanced_pipeline is None:
            _enhanced_pipeline = EnhancedRAGPipeline()
        return _enhanced_pipeline
except ImportError:
    _enhanced_pipeline = None


def _read_file_snippet(path: Path, max_chars: int = 400) -> str:
    try:
        text = path.read_text(errors="ignore")
        return text[:max_chars]
    except Exception:
        return ""


def _extract_candidate_files(command: str) -> List[Path]:
    files: List[Path] = []
    # explicit filenames in the command
    for m in re.findall(r"([\w./\\-]+\.(?:py|js|ts|json|md|txt|yml|yaml|html|css))", command, flags=re.I):
        p = Path(m).expanduser()
        if p.exists() and p.is_file():
            files.append(p)
    return files[:3]


def retrieve_context_for_command(command: str, memory=None, max_snippets: int = 4) -> List[str]:
    """Retrieve context via EnhancedRAGPipeline when available."""
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            chunks = pipeline.retrieve_context(command, max_snippets=max_snippets)
            snippets: List[str] = []
            for ch in chunks:
                bias_info = f" [{', '.join(ch.get('bias_reasons', []))}]" if ch.get('bias_reasons') else ""
                header = f"File: {ch['path']} [{ch['start_line']}-{ch['end_line']}] (sim {ch.get('similarity', 0):.2f}){bias_info}\n"
                snippets.append(header + ch['chunk'])
            return snippets
        except Exception:
            pass
    # Fallback to legacy behavior if enhanced pipeline import failed
    # (Keep minimal legacy retrieval path)
    budget_chars = 8000
    snippets: List[str] = []
    used = 0
    try:
        chunks = _retrieve_by_embedding(command, k=max_snippets * 2)
        for (path, start, end, chunk, score, _tags) in chunks:
            header = f"File: {path} [{start}-{end}] (sim {score:.2f})\n"
            text = header + chunk
            if used + len(text) > budget_chars:
                break
            snippets.append(text)
            used += len(text)
            if len(snippets) >= max_snippets:
                break
    except Exception:
        pass
    return snippets[:max_snippets]


def ingest_paths(paths: List[str], tags: List[str] = None, chunk_lines: int = 80) -> None:
    """Delegate to enhanced pipeline ingestion when available."""
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            for p in paths:
                pipeline.ingest_file(p, tags=tags)
            return
        except Exception:
            pass
    # Fallback: legacy ingestion
    mem = JarvisBigQueryMemory()
    tags_str = ",".join(tags or [])
    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(errors='ignore')
        except Exception:
            continue
        lines = text.splitlines()
        start = 1
        while start <= len(lines):
            end = min(len(lines), start + chunk_lines - 1)
            chunk = "\n".join(lines[start-1:end])
            emb = _embed_text(chunk)
            with mem._write_lock:
                mem.conn.execute(
                    "INSERT INTO content_chunks(path, start_line, end_line, chunk, embedding_json, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(path), start, end, chunk, json.dumps(emb), tags_str)
                )
            start = end + 1
    mem.conn.commit()


def _retrieve_by_embedding(query: str, k: int = 4) -> List[Tuple[str,int,int,str,float,str]]:
    """Use enhanced pipeline scoring when available; keep legacy shape."""
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            chunks = pipeline.retrieve_context(query, max_snippets=k)
            out: List[Tuple[str,int,int,str,float,str]] = []
            for ch in chunks:
                out.append((ch['path'], ch['start_line'], ch['end_line'], ch['chunk'], float(ch.get('similarity', 0.0)), ch.get('tags') or ''))
            return out
        except Exception:
            pass
    # Fallback to legacy computation
    mem = JarvisBigQueryMemory()
    q = _embed_text(query)
    rows = mem.conn.execute("SELECT path, start_line, end_line, chunk, embedding_json, COALESCE(tags,'') AS tags FROM content_chunks").fetchall()
    scored = []
    for r in rows:
        try:
            emb = json.loads(r['embedding_json'])
        except Exception:
            continue
        score = _cosine(q, emb)
        scored.append((score, r['path'], r['start_line'], r['end_line'], r['chunk'], r['tags']))
    scored.sort(reverse=True, key=lambda x: x[0])
    out = []
    for s, path, start, end, chunk, tags in scored[:k]:
        out.append((path, start, end, chunk, s, tags))
    return out


def _embed_text(text: str) -> List[float]:
    """Unified embedding backend with intelligent fallback."""
    try:
        from unified_embedder import embed_text
        return embed_text(text)
    except Exception as e:
        # If unified embedder fails, use the legacy approach
        backend = _read_embed_backend()
        
        # Primary backend
        if backend == 'ollama':
            emb = _ollama_embed(text)
            if emb:
                return emb
            # Fallback to MLX if ollama fails
            emb = _mlx_embed(text)
            if emb:
                return emb
        elif backend == 'mlx':
            emb = _mlx_embed(text)
            if emb:
                return emb
            # Fallback to ollama if MLX fails
            emb = _ollama_embed(text)
            if emb:
                return emb
        
        # Final fallback to CPU/hash
        return _hash_embed(text)


def _mlx_embed(text: str) -> List[float]:
    """MLX embedder using real MLX models or sentence transformers"""
    try:
        # First try MLX sentence transformer
        from mlx_sentence_transformer import MLXSentenceTransformer
        transformer = MLXSentenceTransformer()
        if transformer.initialize():
            embeddings = transformer.encode([text])
            if embeddings.size > 0:
                return embeddings[0].tolist()
    except ImportError:
        pass
    
    try:
        # Fall back to embedding system which can use sentence-transformers
        from embedding_system import EmbeddingSystem
        embedder = EmbeddingSystem()
        embedding = embedder.embed(text)
        if isinstance(embedding, (list, tuple)) and len(embedding) > 0:
            return list(embedding)
        elif hasattr(embedding, 'tolist'):
            return embedding.tolist()
    except ImportError:
        pass
    
    try:
        # Try original mlx_embedder
        from mlx_embedder import mlx_embed
        embedding = mlx_embed(text)
        if embedding:
            return embedding
    except ImportError:
        pass
    
    # Final fallback to hash
    return _hash_embed(text, dim=384)


def _ollama_embed(text: str) -> List[float]:
    model = _read_embed_model()
    try:
        import json, urllib.request
        req = urllib.request.Request(
            url='http://127.0.0.1:11434/api/embeddings',
            data=json.dumps({"model": model, "prompt": text}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            emb = data.get('embedding') or data.get('data',{}).get('embedding')
            if emb:
                return emb
    except Exception:
        return []
    return []


def _hash_embed(text: str, dim: int = 128) -> List[float]:
    words = text.lower().split()
    vec = [0.0]*dim
    for w in words:
        idx = abs(hash(w)) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)) or 1.0
    nb = math.sqrt(sum(y*y for y in b)) or 1.0
    return dot/(na*nb)


def _read_embed_model() -> str:
    try:
        cfg_path = Path(os.getenv('JARVIS_HOME', str(Path.home()/'.ai_agent'))).expanduser()/ 'config.json'
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text())
            return data.get('embedding_model', 'nomic-embed-text')
    except Exception:
        pass
    return 'nomic-embed-text'


def _read_embed_backend() -> str:
    # Prefer config, then env, default mlx
    try:
        cfg_path = Path(os.getenv('JARVIS_HOME', str(Path.home()/'.ai_agent'))).expanduser()/ 'config.json'
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text())
            return data.get('embedding_backend', os.getenv('JARVIS_EMBED_BACKEND', 'mlx'))
    except Exception:
        pass
    return os.getenv('JARVIS_EMBED_BACKEND', 'mlx')
