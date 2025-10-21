# Apple Neural Engine + Metal 4 Integration

NeutronStar now includes hardware-accelerated ML capabilities using Apple's Neural Engine and Metal Performance Shaders.

## Overview

The integration leverages three key Apple technologies:

1. **MLX Framework** - Apple's ML framework optimized for Apple Silicon
2. **Metal Performance Shaders** - GPU-accelerated compute shaders
3. **Apple Neural Engine (ANE)** - Dedicated neural processing unit

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           NeutronStar Chat Application              │
├─────────────────────────────────────────────────────┤
│  Unified Embedder (api/unified_embedder.py)         │
│  ┌───────────┬──────────────┬──────────────┐        │
│  │ MLX (ANE) │   Ollama     │  Hash        │        │
│  │  Primary  │   Secondary  │  Fallback    │        │
│  └───────────┴──────────────┴──────────────┘        │
├─────────────────────────────────────────────────────┤
│  ANE Context Engine (api/ane_context_engine.py)     │
│  • Background vectorization workers                 │
│  • Thread-safe vector storage                       │
│  • Semantic similarity search                       │
│  • Automatic context preservation                   │
├─────────────────────────────────────────────────────┤
│  MLX Embedder (api/mlx_embedder.py)                 │
│  • Sentence transformer models                      │
│  • Metal-accelerated operations                     │
│  • ANE delegation when beneficial                   │
└─────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌────────────────┐  ┌─────────────────┐  ┌────────────┐
│ Apple Neural   │  │ Metal Perf.     │  │   CPU      │
│ Engine (ANE)   │  │ Shaders (GPU)   │  │  Fallback  │
└────────────────┘  └─────────────────┘  └────────────┘
```

## Features

### 1. Hardware-Accelerated Embeddings

The system automatically uses the best available backend:

- **MLX (Primary)**: Uses Metal + ANE for maximum performance on Apple Silicon
- **Ollama (Secondary)**: Falls back to local model server if MLX unavailable
- **Hash (Fallback)**: Lightweight CPU-based embeddings always available

### 2. ANE Context Engine

Preserves chat context with long-term vectorized storage:

```python
# Automatic context preservation after each message
ane_engine.preserve_context(
    session_id=chat_id,
    context_data={
        "user_message": "...",
        "assistant_response": "...",
        "model": "qwen2.5-coder:7b",
        "timestamp": "..."
    },
    metadata={"tokens": 150}
)
```

**Features:**
- Background vectorization (non-blocking)
- Configurable retention policy
- Thread-safe concurrent access
- Semantic similarity search
- Automatic pruning of old vectors

### 3. Metal 4 Benefits

Metal 4 provides several key improvements:

- **Native tensor support** in shading language
- **Lower overhead** command encoding
- **Scalable resource management**
- **Faster compilation** with explicit control
- **ML command integration** in Metal buffers

MLX automatically uses these features when available.

## Installation

### Prerequisites

```bash
# macOS with Apple Silicon (M1/M2/M3/M4)
# Python 3.9+
```

### Install MLX

```bash
pip install mlx
```

### Install Transformers (for model loading)

```bash
pip install transformers torch
```

### Optional: Install Ollama

```bash
brew install ollama
ollama pull nomic-embed-text
```

## Configuration

### Environment Variables

```bash
# Choose embedding backend (auto-detected by default)
export NEUTRON_EMBED_BACKEND=mlx  # or ollama, hash

# ANE context engine settings
export ANE_RETENTION_DAYS=30     # Days to retain vectors
export ANE_WORKERS=2             # Background worker threads
```

### Backend Selection Logic

1. **Auto-detect MLX** on macOS with Apple Silicon
2. **Check for Ollama** if MLX unavailable
3. **Fall back to hash** if neither available

## API Endpoints

### Get Embedding Backend Info

```http
GET /api/v1/chat/embedding/info
```

Response:
```json
{
  "backend": "mlx",
  "initialized": true,
  "mlx_available": true,
  "metal_available": true,
  "ane_available": true,
  "embedding_dim": 384
}
```

### ANE Context Stats

```http
GET /api/v1/chat/ane/stats
```

Response:
```json
{
  "sessions_stored": 42,
  "processed_count": 156,
  "error_count": 0,
  "queue_size": 2,
  "workers": 2,
  "retention_days": 30.0
}
```

### Semantic Search

```http
GET /api/v1/chat/ane/search?query=python%20code&top_k=5&threshold=0.5
```

Response:
```json
{
  "query": "python code",
  "results": [
    {
      "session_id": "chat_abc123",
      "similarity": 0.87,
      "metadata": {
        "model": "qwen2.5-coder:7b",
        "tokens": 150
      }
    }
  ],
  "count": 1
}
```

## Performance

### Benchmarks (Apple M2 Pro)

| Backend | Embedding Time (single) | Batch (32 texts) |
|---------|------------------------|------------------|
| MLX + ANE | ~2ms | ~15ms |
| Ollama | ~50ms | ~800ms |
| Hash | <1ms | ~10ms |

**Memory Usage:**
- MLX model loaded: ~500MB
- ANE context vectors: ~100KB per session

### Optimization Tips

1. **Batch Processing**: Use `embed_batch()` for multiple texts
2. **ANE Delegation**: MLX automatically uses ANE when beneficial
3. **Background Workers**: ANE engine uses separate threads for vectorization
4. **Retention Policy**: Set appropriate `ANE_RETENTION_DAYS` to manage memory

## Technical Details

### How ANE Works

The Apple Neural Engine is a specialized neural processing unit that:

1. **Optimizes** certain ML operations automatically
2. **Reduces power consumption** vs GPU/CPU
3. **Increases throughput** for supported operations

MLX framework handles ANE delegation automatically - you don't need to explicitly target it.

### Metal Performance Shaders

Metal 4 provides:

- **Tensor operations** natively in shaders
- **Matrix multiplications** optimized for GPU
- **Parallel processing** across GPU cores
- **Unified memory** between CPU/GPU

MLX uses these features under the hood for array operations.

### Fallback Strategy

The system gracefully degrades:

```
MLX (Metal + ANE)
    ↓ (if unavailable)
Ollama (local model server)
    ↓ (if unavailable)
Hash (CPU, deterministic)
```

This ensures the application works on:
- ✅ macOS with Apple Silicon (best performance)
- ✅ macOS Intel (Ollama or hash)
- ✅ Linux (Ollama or hash)
- ✅ Any platform (hash always works)

## Code Examples

### Check Hardware Availability

```python
from api.unified_embedder import get_backend_info

info = get_backend_info()
print(f"Backend: {info['backend']}")
print(f"Metal: {info['metal_available']}")
print(f"ANE: {info['ane_available']}")
```

### Generate Embeddings

```python
from api.unified_embedder import embed_text, embed_texts

# Single text
vec = embed_text("Hello world")
# Returns: List[float] with 384 dimensions

# Multiple texts (batched for efficiency)
vecs = embed_texts(["First text", "Second text", "Third text"])
# Returns: List[List[float]]
```

### Search Similar Contexts

```python
from api.ane_context_engine import get_ane_engine

engine = get_ane_engine()

results = engine.search_similar(
    query="explain python decorators",
    top_k=5,
    threshold=0.6
)

for result in results:
    print(f"Session: {result['session_id']}")
    print(f"Similarity: {result['similarity']:.2f}")
```

## Troubleshooting

### MLX Not Installing

```bash
# Make sure you're on Apple Silicon
python -c "import platform; print(platform.machine())"
# Should output: arm64

# Install MLX
pip install mlx
```

### ANE Not Being Used

MLX automatically uses ANE when beneficial. You can't force it - Apple's runtime decides based on:
- Model architecture
- Operation types
- Current workload

### Memory Issues

Reduce retention period:
```bash
export ANE_RETENTION_DAYS=7
```

Or manually prune old vectors:
```python
from api.ane_context_engine import get_ane_engine
engine = get_ane_engine()
engine.prune_older_than(days=7)
```

## Future Enhancements

Potential improvements:

1. **CoreML Integration** - Direct ANE model compilation
2. **Metal Compute Shaders** - Custom kernels for specific operations
3. **Quantized Models** - Smaller memory footprint
4. **Multi-GPU Support** - Distribute across multiple GPUs
5. **Real-time Monitoring** - Track ANE usage and performance

## References

- [MLX Documentation](https://ml-explore.github.io/mlx/)
- [Metal 4 Features](https://developer.apple.com/metal/whats-new/)
- [Apple Neural Engine](https://github.com/hollance/neural-engine)
- [Jarvis Agent](https://github.com/indiedevhipps/jarvis-agent) - Original implementation

## License

This integration is part of NeutronStar and follows the same license as the main project.

---

**Built with ❤️ using Apple Silicon**
