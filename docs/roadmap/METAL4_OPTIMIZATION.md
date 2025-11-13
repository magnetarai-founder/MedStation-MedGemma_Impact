# ElohimOS Metal 4 + macOS Tahoe 26 Optimization Roadmap

**Project**: ElohimOS - Offline-First AI Operating System
**Target**: macOS Tahoe 26 (Metal 4, MetalFX, Apple Silicon)
**Goal**: Maximum GPU acceleration for AI operations in harsh offline environments
**Status**: Phase 0 Complete (Hardening) → Ready for Metal 4 Implementation

---

## Executive Summary

ElohimOS currently runs primarily on CPU with minimal Metal GPU utilization. This roadmap outlines a phased approach to leverage **Metal 4**, **MetalFX**, and **macOS Tahoe 26** features for 5-20x performance improvements in ML operations, data processing, and UI rendering.

**Current State**:
- ❌ Embeddings: CPU-bound (NumPy/PyTorch)
- ❌ Vector Search: CPU-bound (cosine similarity)
- ❌ SQL: CPU-bound (SQLite)
- ❌ Data Processing: CPU-bound (Pandas)
- ✅ Metal 4: Initialized but only used for diagnostics

**Target State**:
- ✅ Embeddings: Metal Performance Shaders Graph
- ✅ Vector Search: Metal compute shaders (GPU parallel)
- ✅ SQL Aggregations: Metal kernels (GROUP BY, JOIN on GPU)
- ✅ Data Processing: Metal-accelerated Pandas operations
- ✅ UI: MetalFX upscaling + frame interpolation for 120fps

---

## Phase 1: ML Acceleration (Highest Impact)

**Objective**: Move embeddings and RAG retrieval to Metal GPU
**Estimated Impact**: 5-10x faster embeddings, 10-20x faster vector search
**Duration**: 2-3 weeks

### Task 1.1: Text Embeddings → Metal Performance Shaders

**Current**:
```python
# CPU-bound embedding (apps/backend/api/chat_service.py)
embedding = embedder(user_message)  # Runs on CPU
```

**Target**:
```python
# GPU-accelerated embedding using MPS Graph
import Metal
import MetalPerformanceShaders as mps

class MetalEmbedder:
    def __init__(self):
        self.device = Metal.MTLCreateSystemDefaultDevice()
        self.graph = mps.MPSGraph()
        # Load embedding model as Metal neural network
        self.model = self._load_embedding_model()

    def embed(self, text: str) -> np.ndarray:
        # Tokenize on CPU
        tokens = self.tokenizer(text)

        # Create Metal buffer (zero-copy unified memory)
        tokens_buffer = self.device.newBufferWithBytes_length_options_(
            tokens.tobytes(), len(tokens) * 4, Metal.MTLResourceStorageModeShared
        )

        # Run inference on GPU
        output_buffer = self.graph.executeWithInputs_outputBuffers_(
            [tokens_buffer], [self.output_buffer]
        )

        # Zero-copy read from unified memory
        return np.frombuffer(output_buffer.contents(), dtype=np.float32)
```

**Implementation Steps**:
1. Install `pyobjc-framework-MetalPerformanceShaders`
2. Load embedding model (e.g., `all-MiniLM-L6-v2`) as MPS Graph
3. Replace CPU embedder in `unified_embedder.py`
4. Benchmark: Compare CPU vs. Metal embedding speed
5. Add fallback to CPU if Metal unavailable

**Files to Modify**:
- `apps/backend/api/unified_embedder.py`
- `apps/backend/api/metal4_engine.py` (add `MetalEmbedder` class)
- `apps/backend/api/chat_service.py` (use Metal embedder)

**Success Criteria**:
- ✅ Embedding time < 10ms per message (vs. 50-100ms CPU)
- ✅ Zero crashes on Metal-unavailable systems (CPU fallback)
- ✅ Memory usage stable (no leaks in Metal buffers)

---

### Task 1.2: Vector Search → Metal Compute Shaders

**Current**:
```python
# CPU-bound cosine similarity (apps/backend/api/jarvis_rag_pipeline.py)
similarities = cosine_similarity(query_embedding, all_embeddings)  # NumPy CPU
```

**Target**:
```python
# GPU-accelerated vector search using Metal compute shader
class MetalVectorSearch:
    def __init__(self):
        self.device = Metal.MTLCreateSystemDefaultDevice()
        self.library = self._load_shader_library()
        self.kernel = self.library.newFunctionWithName_("cosine_similarity_kernel")
        self.pipeline = self.device.newComputePipelineStateWithFunction_error_(self.kernel, None)

    def search(self, query: np.ndarray, embeddings: np.ndarray, top_k: int = 5):
        # Upload embeddings to GPU (one-time for cached embeddings)
        embeddings_buffer = self.device.newBufferWithBytes_length_options_(
            embeddings.tobytes(), embeddings.nbytes, Metal.MTLResourceStorageModeShared
        )

        # Upload query to GPU
        query_buffer = self.device.newBufferWithBytes_length_options_(
            query.tobytes(), query.nbytes, Metal.MTLResourceStorageModeShared
        )

        # Allocate output buffer
        results_buffer = self.device.newBufferWithLength_options_(
            top_k * 8, Metal.MTLResourceStorageModeShared  # top_k × (index + score)
        )

        # Dispatch compute shader
        cmd = self.queue.commandBuffer()
        encoder = cmd.computeCommandEncoder()
        encoder.setComputePipelineState_(self.pipeline)
        encoder.setBuffer_offset_atIndex_(query_buffer, 0, 0)
        encoder.setBuffer_offset_atIndex_(embeddings_buffer, 0, 1)
        encoder.setBuffer_offset_atIndex_(results_buffer, 0, 2)

        # Grid size: 1 thread per embedding
        threads_per_grid = Metal.MTLSizeMake(len(embeddings), 1, 1)
        threads_per_group = Metal.MTLSizeMake(256, 1, 1)  # 256 threads per group
        encoder.dispatchThreads_threadsPerThreadgroup_(threads_per_grid, threads_per_group)
        encoder.endEncoding()
        cmd.commit()
        cmd.waitUntilCompleted()

        # Zero-copy read results
        return np.frombuffer(results_buffer.contents(), dtype=np.float32)
```

**Metal Shader** (`cosine_similarity.metal`):
```metal
#include <metal_stdlib>
using namespace metal;

kernel void cosine_similarity_kernel(
    constant float* query [[buffer(0)]],
    constant float* embeddings [[buffer(1)]],
    device float* results [[buffer(2)]],
    uint idx [[thread_position_in_grid]],
    constant uint& embedding_dim [[buffer(3)]],
    constant uint& num_embeddings [[buffer(4)]]
) {
    if (idx >= num_embeddings) return;

    // Compute cosine similarity: dot(query, embedding) / (norm(query) * norm(embedding))
    float dot_product = 0.0;
    float query_norm = 0.0;
    float embedding_norm = 0.0;

    constant float* embedding = embeddings + (idx * embedding_dim);

    for (uint i = 0; i < embedding_dim; i++) {
        dot_product += query[i] * embedding[i];
        query_norm += query[i] * query[i];
        embedding_norm += embedding[i] * embedding[i];
    }

    query_norm = sqrt(query_norm);
    embedding_norm = sqrt(embedding_norm);

    results[idx] = dot_product / (query_norm * embedding_norm + 1e-8);
}
```

**Implementation Steps**:
1. Create Metal shader library (`apps/backend/api/shaders/vector_search.metal`)
2. Compile shader library in `metal4_engine.py`
3. Implement `MetalVectorSearch` class
4. Replace CPU vector search in `jarvis_rag_pipeline.py`
5. Add Metal sparse resources for large embedding stores (Tahoe 26 feature)

**Files to Modify**:
- `apps/backend/api/shaders/vector_search.metal` (new file)
- `apps/backend/api/metal4_engine.py` (add `MetalVectorSearch`)
- `apps/backend/api/jarvis_rag_pipeline.py` (use Metal vector search)

**Success Criteria**:
- ✅ Vector search < 5ms for 10K embeddings (vs. 100-500ms CPU)
- ✅ Scales to 1M+ embeddings with Metal sparse resources
- ✅ Top-K results identical to CPU implementation (correctness)

---

### Task 1.3: Metal Sparse Resources for Embedding Storage

**Objective**: Use Tahoe 26's sparse resources to efficiently store millions of embeddings

**Current Limitation**:
- Embeddings stored in RAM → limited by system memory
- Large embedding stores (1M+ vectors) require 4-8GB RAM

**Metal Sparse Resources Solution**:
```python
class SparseEmbeddingStore:
    def __init__(self, max_embeddings: int = 10_000_000):
        self.device = Metal.MTLCreateSystemDefaultDevice()

        # Create sparse heap (only allocates physical memory when accessed)
        heap_desc = Metal.MTLHeapDescriptor.new()
        heap_desc.setSize_(max_embeddings * 768 * 4)  # 768-dim float32
        heap_desc.setType_(Metal.MTLHeapTypePlacement)  # Tahoe 26 feature
        heap_desc.setStorageMode_(Metal.MTLStorageModeShared)

        self.sparse_heap = self.device.newHeapWithDescriptor_(heap_desc)

    def add_embedding(self, idx: int, embedding: np.ndarray):
        # Only allocate physical memory for this embedding
        offset = idx * 768 * 4
        buffer = self.sparse_heap.newBufferWithLength_options_offset_(
            768 * 4, Metal.MTLResourceStorageModeShared, offset
        )
        buffer.contents().writeBytes_length_(embedding.tobytes(), 768 * 4)
```

**Benefits**:
- Store 10M embeddings with only ~2GB physical RAM (vs. 30GB dense)
- Lazy allocation: Only used embeddings consume memory
- OS-managed paging to SSD for cold embeddings

**Implementation Steps**:
1. Detect Tahoe 26 / Metal 4 support for sparse resources
2. Implement `SparseEmbeddingStore` in `metal4_engine.py`
3. Migrate existing embedding storage
4. Add metrics for physical vs. virtual memory usage

**Success Criteria**:
- ✅ Store 1M+ embeddings with <5GB RAM
- ✅ No performance regression for hot embeddings
- ✅ Graceful fallback to dense storage on older macOS

---

## Phase 2: Data Processing Acceleration

**Objective**: GPU-accelerate SQL queries and data transformations
**Estimated Impact**: 3-5x faster for large datasets (>100K rows)
**Duration**: 3-4 weeks

### Task 2.1: SQL Aggregations → Metal Compute Shaders

**Current**:
```sql
-- CPU-bound SQLite query
SELECT category, SUM(revenue), AVG(price), COUNT(*)
FROM sales
GROUP BY category;
```

**Target**: Compile to Metal kernel

```metal
kernel void sql_group_by_aggregate(
    constant SalesRecord* sales [[buffer(0)]],
    device AggregateResult* results [[buffer(1)]],
    constant uint& num_rows [[buffer(2)]],
    uint idx [[thread_position_in_grid]]
) {
    // Each thread processes one category
    // Use atomic operations for thread-safe aggregation
    // ...
}
```

**Implementation Strategy**:
1. **Intercept SQL queries** in `data_engine.py`
2. **Parse SQL** to detect aggregation patterns
3. **Compile to Metal** for GPU execution
4. **Fallback to SQLite** for complex queries

**Supported Operations**:
- ✅ `SUM`, `AVG`, `COUNT`, `MIN`, `MAX`
- ✅ `GROUP BY` (up to 2 columns)
- ✅ `WHERE` with simple predicates
- ❌ `JOIN` (Phase 3)
- ❌ Subqueries (fallback to CPU)

**Files to Modify**:
- `apps/backend/api/data_engine.py` (add SQL → Metal compiler)
- `apps/backend/api/shaders/sql_kernels.metal` (new file)
- `apps/backend/api/metal4_engine.py` (add `MetalSQLEngine`)

**Success Criteria**:
- ✅ 3-5x faster for `GROUP BY` on 100K+ rows
- ✅ Correctness: Results match SQLite exactly
- ✅ Transparent fallback for unsupported queries

---

### Task 2.2: Pandas Operations → Metal Acceleration

**Current**:
```python
# CPU-bound Pandas (apps/backend/api/data_engine.py)
df['total'] = df['price'] * df['quantity']  # NumPy CPU
df_grouped = df.groupby('category').sum()   # CPU
```

**Target**: Use Metal-backed PyTorch tensors

```python
import torch

# Enable Metal backend (macOS 12.3+)
device = torch.device("mps")  # Metal Performance Shaders

class MetalDataFrame:
    def __init__(self, df: pd.DataFrame):
        # Convert Pandas → PyTorch Metal tensors
        self.columns = {
            col: torch.tensor(df[col].values, device=device)
            for col in df.columns
        }

    def multiply(self, col1: str, col2: str) -> torch.Tensor:
        # Runs on Metal GPU
        return self.columns[col1] * self.columns[col2]

    def groupby_sum(self, group_col: str, value_col: str):
        # GPU-accelerated groupby using scatter_add
        groups = self.columns[group_col]
        values = self.columns[value_col]
        result = torch.zeros(groups.max() + 1, device=device)
        result.scatter_add_(0, groups, values)
        return result
```

**Implementation Steps**:
1. Add PyTorch with MPS support: `pip install torch`
2. Create `MetalDataFrame` wrapper in `data_engine.py`
3. Use Metal-accelerated operations for large datasets (>10K rows)
4. Benchmark: Compare Pandas CPU vs. Metal GPU

**Files to Modify**:
- `apps/backend/api/data_engine.py` (add `MetalDataFrame`)
- `apps/backend/api/metal4_engine.py` (MPS device management)

**Success Criteria**:
- ✅ 2-4x faster for arithmetic operations (>10K rows)
- ✅ 3-5x faster for groupby aggregations (>100K rows)
- ✅ Memory efficient (zero-copy unified memory)

---

## Phase 3: UI Rendering Enhancement (Tahoe 26 MetalFX)

**Objective**: 120fps animations, GPU-accelerated data visualizations
**Estimated Impact**: Smoother UI, faster chart rendering
**Duration**: 2 weeks

### Task 3.1: MetalFX Frame Interpolation for Animations

**Tahoe 26 Feature**: MetalFX generates intermediate frames for smooth 120fps

**Use Cases**:
- Chat message scrolling
- Settings panel transitions
- Data table sorting animations

**Implementation** (WebGPU in React):
```typescript
// apps/frontend/src/lib/metalfx.ts
export async function enableMetalFXInterpolation() {
  if (!navigator.gpu) {
    console.warn('WebGPU not available');
    return false;
  }

  const adapter = await navigator.gpu.requestAdapter();
  const device = await adapter.requestDevice();

  // Check for MetalFX support (Tahoe 26+)
  const hasMetalFX = adapter.features.has('metalfx-interpolation');

  if (hasMetalFX) {
    // Enable frame interpolation for 120fps
    device.configure({
      preferredFrameRate: 120,
      enableFrameInterpolation: true
    });
    return true;
  }
  return false;
}
```

**Files to Modify**:
- `apps/frontend/src/lib/metalfx.ts` (new file)
- `apps/frontend/src/App.tsx` (initialize MetalFX)

**Success Criteria**:
- ✅ 120fps animations on ProMotion displays
- ✅ Graceful fallback to 60fps on older Macs
- ✅ No jank during chat scrolling

---

### Task 3.2: GPU-Accelerated Data Visualizations

**Current**: React components render charts on CPU (D3.js, Recharts)

**Target**: WebGPU-accelerated canvas rendering

```typescript
// apps/frontend/src/components/MetalChart.tsx
import { useEffect, useRef } from 'react';

export function MetalChart({ data }: { data: number[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Initialize WebGPU
    const ctx = canvas.getContext('webgpu');
    if (!ctx) {
      // Fallback to 2D canvas
      const ctx2d = canvas.getContext('2d');
      renderWithCanvas2D(ctx2d, data);
      return;
    }

    // GPU-accelerated rendering
    renderWithWebGPU(ctx, data);
  }, [data]);

  return <canvas ref={canvasRef} width={800} height={600} />;
}

async function renderWithWebGPU(ctx: GPUCanvasContext, data: number[]) {
  const adapter = await navigator.gpu.requestAdapter();
  const device = await adapter.requestDevice();

  // Upload data to GPU buffer
  const dataBuffer = device.createBuffer({
    size: data.length * 4,
    usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST
  });
  device.queue.writeBuffer(dataBuffer, 0, new Float32Array(data));

  // Render pipeline (vertex shader, fragment shader)
  // ... Metal-backed WebGPU rendering
}
```

**Use Cases**:
- Large dataset charts (100K+ data points)
- Real-time updating graphs (query results)
- Heatmaps, scatter plots, histograms

**Files to Modify**:
- `apps/frontend/src/components/MetalChart.tsx` (new component)
- `apps/frontend/src/components/ResultsTable.tsx` (use MetalChart)

**Success Criteria**:
- ✅ Render 100K+ data points at 60fps
- ✅ Smooth zoom/pan interactions
- ✅ Fallback to Canvas 2D on non-WebGPU browsers

---

### Task 3.3: MetalFX Upscaling for Data Visualizations

**Tahoe 26 Feature**: Dynamic resolution scaling for performance

**Use Case**: Render large tables at lower resolution, upscale to 4K/5K displays

```typescript
// apps/frontend/src/lib/metalfx-upscaling.ts
export async function enableMetalFXUpscaling(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('webgpu');
  const device = await (await navigator.gpu.requestAdapter()).requestDevice();

  // Render at 1080p, upscale to 4K
  const renderWidth = 1920;
  const renderHeight = 1080;
  const displayWidth = canvas.width;   // 3840 (4K)
  const displayHeight = canvas.height; // 2160

  // Create MetalFX upscaler
  const upscaler = device.createMetalFXUpscaler({
    inputWidth: renderWidth,
    inputHeight: renderHeight,
    outputWidth: displayWidth,
    outputHeight: displayHeight,
    quality: 'ultra'  // Ultra quality mode
  });

  // Render at lower res, upscale with MetalFX
  const renderTarget = device.createTexture({
    size: [renderWidth, renderHeight],
    format: 'bgra8unorm',
    usage: GPUTextureUsage.RENDER_ATTACHMENT
  });

  const upscaledTarget = upscaler.upscale(renderTarget);

  return upscaledTarget;
}
```

**Benefits**:
- 2-3x faster rendering (render at 1080p vs. 4K)
- Minimal quality loss (MetalFX high-quality upscaling)
- Lower power consumption (battery life)

**Files to Modify**:
- `apps/frontend/src/lib/metalfx-upscaling.ts` (new file)
- `apps/frontend/src/components/MetalChart.tsx` (use upscaling)

**Success Criteria**:
- ✅ 4K rendering performance matches 1080p
- ✅ Visual quality indistinguishable from native 4K
- ✅ Battery life improved by 20-30%

---

## Phase 4: Advanced Optimizations

**Objective**: Metal 4 tensor operations, unified memory optimization
**Duration**: 2-3 weeks

### Task 4.1: Metal 4 Tensor Operations in Shaders

**Tahoe 26 Feature**: Native tensor support in Metal shading language

**Use Case**: Inline ML inference in rendering pipeline

```metal
#include <metal_stdlib>
using namespace metal;

kernel void inference_with_tensors(
    constant float4x4* weights [[buffer(0)]],
    constant float4* input [[buffer(1)]],
    device float4* output [[buffer(2)]],
    uint idx [[thread_position_in_grid]]
) {
    // Metal 4: Native matrix multiply
    output[idx] = weights[idx] * input[idx];

    // Apply ReLU activation
    output[idx] = max(output[idx], float4(0.0));
}
```

**Implementation**:
1. Migrate embedding models to Metal 4 tensor format
2. Use tensor operations for faster inference
3. Combine inference with rendering (e.g., sentiment analysis during chat)

**Files to Modify**:
- `apps/backend/api/shaders/ml_kernels.metal` (new file)
- `apps/backend/api/metal4_engine.py` (tensor operation wrappers)

---

### Task 4.2: Unified Memory Optimization

**Objective**: Zero-copy data transfer between CPU and GPU

**Current Problem**:
```python
# SLOW: Copy data CPU → GPU → CPU
data_cpu = np.array([...])
data_gpu = torch.tensor(data_cpu, device='mps')  # Copy to GPU
result = model(data_gpu)
result_cpu = result.cpu().numpy()  # Copy back to CPU
```

**Optimized (Unified Memory)**:
```python
# FAST: Zero-copy shared memory
buffer = device.newBufferWithLength_options_(
    data.nbytes,
    Metal.MTLResourceStorageModeShared  # Unified memory
)

# CPU writes directly to GPU-visible memory
buffer.contents().writeBytes_length_(data.tobytes(), data.nbytes)

# GPU reads from same memory (no copy)
result = gpu_kernel(buffer)

# CPU reads result (no copy)
result_array = np.frombuffer(buffer.contents(), dtype=np.float32)
```

**Implementation Steps**:
1. Audit all CPU↔GPU data transfers
2. Replace copies with unified memory buffers
3. Measure memory bandwidth savings

**Files to Modify**:
- `apps/backend/api/metal4_engine.py` (unified memory allocator)
- All files using PyTorch MPS or Metal buffers

**Success Criteria**:
- ✅ 2-3x reduction in memory copies
- ✅ Latency reduced by 10-50ms per operation
- ✅ Memory usage reduced (no duplicate buffers)

---

## Phase 5: Final Hardening & Polish

**Objective**: Complete remaining LOW items, add monitoring, finalize setup
**Duration**: 1 week

### Task 5.1: Permission Change Audit Logging (LOW-07)

**Objective**: Track when user permissions are modified

**Implementation**:
```python
# apps/backend/api/permission_engine.py

def grant_permission(self, user_id: str, permission: str, granted_by: str):
    # Existing permission grant logic
    # ...

    # LOW-07: Audit log permission change
    audit_logger = get_audit_logger()
    audit_logger.log(
        user_id=granted_by,
        action=AuditAction.PERMISSION_GRANTED,
        details={
            "target_user_id": user_id,
            "permission": permission,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

**Files to Modify**:
- `apps/backend/api/permission_engine.py` (add logging to grant/revoke methods)
- `apps/backend/api/audit_logger.py` (add `PERMISSION_GRANTED`, `PERMISSION_REVOKED` actions)

**Success Criteria**:
- ✅ All permission changes logged with timestamp, actor, target user
- ✅ Audit log query: "Show me who granted admin to user X"
- ✅ Compliance-ready logging format

---

### Task 5.2: Prometheus Metrics (LOW-08)

**Objective**: Export system metrics for monitoring dashboards

**Implementation**:
```python
# apps/backend/api/main.py

from prometheus_fastapi_instrumentator import Instrumentator

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Custom metrics
from prometheus_client import Counter, Histogram, Gauge

# Track Metal 4 operations
metal_operations = Counter(
    'metal4_operations_total',
    'Total Metal 4 GPU operations',
    ['operation_type']
)

embedding_latency = Histogram(
    'embedding_latency_seconds',
    'Embedding generation latency',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

gpu_memory_usage = Gauge(
    'metal4_gpu_memory_bytes',
    'Metal 4 GPU memory usage'
)

# Usage
@app.post("/api/chat/message")
async def send_message(...):
    with embedding_latency.time():
        embedding = metal_embedder.embed(message)
    metal_operations.labels(operation_type='embedding').inc()
    # ...
```

**Metrics Exposed**:
- HTTP request count, latency, status codes
- Database query latency
- Metal 4 operation count (embeddings, vector search, SQL kernels)
- GPU memory usage
- Session count, active users

**Files to Modify**:
- `apps/backend/api/main.py` (add Prometheus instrumentator)
- `apps/backend/api/metal4_engine.py` (add GPU metrics)
- `requirements.txt` (add `prometheus-fastapi-instrumentator`)

**Success Criteria**:
- ✅ Metrics endpoint: `GET /metrics` (Prometheus format)
- ✅ Grafana dashboard showing Metal 4 performance
- ✅ Alerting on slow operations (>100ms embedding latency)

**Grafana Dashboard Example**:
```
┌─────────────────────────────────────┐
│ Metal 4 GPU Operations/sec          │
│ ▁▂▃▅▇██▇▅▃▂▁                        │
│ Current: 1,234 ops/sec              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Embedding Latency (p95)             │
│ ▁▁▁▁▁▂▂▂▃▃▃▂▂▁▁                     │
│ Current: 8.3ms                      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ GPU Memory Usage                    │
│ ▆▆▆▆▇▇▇▇▇▇▆▆▆▆▆                     │
│ Current: 2.4GB / 16GB (15%)         │
└─────────────────────────────────────┘
```

---

### Task 5.3: Founder Password & Setup Wizard (FINAL)

**Objective**: Professional first-run setup experience

**Current State**:
- Hardcoded founder password in environment variable
- No guided setup for first user
- Unclear permission model for new deployments

**Target**:

#### **Setup Wizard Flow**:

```
┌─────────────────────────────────────────────┐
│ Welcome to ElohimOS                         │
│ Offline-First AI Operating System          │
│                                             │
│ No users detected - let's set up your      │
│ first administrator account.               │
│                                             │
│ [Continue to Setup] →                      │
└─────────────────────────────────────────────┘

↓

┌─────────────────────────────────────────────┐
│ Step 1: Administrator Account              │
│                                             │
│ Username: [________________]                │
│ Password: [________________]                │
│ Confirm:  [________________]                │
│                                             │
│ This account will have full system access. │
│                                             │
│ [← Back]              [Continue →]         │
└─────────────────────────────────────────────┘

↓

┌─────────────────────────────────────────────┐
│ Step 2: Founder Rights Password            │
│                                             │
│ Set a separate Founder Rights password     │
│ for emergency access and field support.    │
│                                             │
│ Founder Password: [________________]        │
│ Confirm:          [________________]        │
│                                             │
│ ⚠️  Store this securely - it bypasses all  │
│    access controls.                         │
│                                             │
│ [← Back]              [Continue →]         │
└─────────────────────────────────────────────┘

↓

┌─────────────────────────────────────────────┐
│ Step 3: Metal 4 GPU Acceleration           │
│                                             │
│ ✅ Metal 4 detected (macOS Tahoe 26)       │
│ ✅ Apple Silicon: M3 Pro                   │
│ ✅ GPU Memory: 18GB unified                │
│                                             │
│ Enable GPU acceleration for:               │
│ ☑ ML Embeddings (5-10x faster)             │
│ ☑ Vector Search (10-20x faster)            │
│ ☑ SQL Aggregations (3-5x faster)           │
│ ☑ UI Rendering (120fps MetalFX)            │
│                                             │
│ [← Back]              [Finish Setup →]     │
└─────────────────────────────────────────────┘

↓

┌─────────────────────────────────────────────┐
│ Setup Complete!                             │
│                                             │
│ ElohimOS is ready for offline operations.  │
│                                             │
│ Your founder rights credentials:           │
│ Username: elohim_founder                   │
│ Password: (stored securely in keychain)    │
│                                             │
│ [Launch ElohimOS →]                        │
└─────────────────────────────────────────────┘
```

#### **Backend Implementation**:

**1. Setup Wizard API** (`apps/backend/api/setup_wizard.py`):
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

class SetupStep1Request(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=12)

class SetupStep2Request(BaseModel):
    founder_password: str = Field(..., min_length=16)

class SetupStep3Request(BaseModel):
    enable_metal_embeddings: bool = True
    enable_metal_vector_search: bool = True
    enable_metal_sql: bool = True
    enable_metalfx_ui: bool = True

@router.get("/status")
async def get_setup_status():
    """Check if setup is required"""
    user_count = auth_service.get_user_count()
    founder_password_set = os.getenv("ELOHIM_FOUNDER_PASSWORD") is not None

    return {
        "setup_required": user_count == 0,
        "founder_password_set": founder_password_set,
        "metal4_available": get_metal4_engine().is_available()
    }

@router.post("/step1")
async def setup_step1(body: SetupStep1Request):
    """Create first administrator account"""
    # Check no users exist
    if auth_service.get_user_count() > 0:
        raise HTTPException(status_code=400, detail="Setup already completed")

    # Create admin user
    user = auth_service.create_user(
        username=body.username,
        password=body.password,
        device_id="setup-device"
    )

    # Grant super_admin role
    auth_service.set_user_role(user.user_id, "super_admin")

    return {"success": True, "user_id": user.user_id}

@router.post("/step2")
async def setup_step2(body: SetupStep2Request):
    """Set founder rights password"""
    # Store in macOS Keychain (secure storage)
    import keyring
    keyring.set_password(
        "ElohimOS",
        "elohim_founder",
        body.founder_password
    )

    # Update environment for current session
    os.environ["ELOHIM_FOUNDER_PASSWORD"] = body.founder_password

    return {"success": True}

@router.post("/step3")
async def setup_step3(body: SetupStep3Request):
    """Configure Metal 4 acceleration"""
    config = {
        "metal4_enabled": True,
        "embeddings": body.enable_metal_embeddings,
        "vector_search": body.enable_metal_vector_search,
        "sql_kernels": body.enable_metal_sql,
        "metalfx_ui": body.enable_metalfx_ui
    }

    # Save to config file
    config_path = get_config_paths().data_dir / "metal4_config.json"
    config_path.write_text(json.dumps(config, indent=2))

    return {"success": True, "config": config}

@router.post("/complete")
async def complete_setup():
    """Mark setup as complete"""
    # Create marker file
    marker = get_config_paths().data_dir / ".setup_complete"
    marker.touch()

    return {"success": True, "message": "Setup complete"}
```

**2. Frontend Setup Wizard** (`apps/frontend/src/components/SetupWizard.tsx`):
```typescript
import { useState } from 'react';
import { api } from '@/lib/api';

export function SetupWizard() {
  const [step, setStep] = useState(1);
  const [adminCreds, setAdminCreds] = useState({ username: '', password: '' });
  const [founderPassword, setFounderPassword] = useState('');
  const [metalConfig, setMetalConfig] = useState({
    embeddings: true,
    vectorSearch: true,
    sqlKernels: true,
    metalfxUI: true
  });

  const handleStep1 = async () => {
    await api.post('/api/v1/setup/step1', adminCreds);
    setStep(2);
  };

  const handleStep2 = async () => {
    await api.post('/api/v1/setup/step2', { founder_password: founderPassword });
    setStep(3);
  };

  const handleStep3 = async () => {
    await api.post('/api/v1/setup/step3', {
      enable_metal_embeddings: metalConfig.embeddings,
      enable_metal_vector_search: metalConfig.vectorSearch,
      enable_metal_sql: metalConfig.sqlKernels,
      enable_metalfx_ui: metalConfig.metalfxUI
    });
    await api.post('/api/v1/setup/complete');
    window.location.href = '/';
  };

  // Render steps...
}
```

**3. Founder Password Security**:
```python
# Store in macOS Keychain (encrypted by FileVault)
import keyring

def get_founder_password() -> str:
    # Try keychain first
    password = keyring.get_password("ElohimOS", "elohim_founder")
    if password:
        return password

    # Fallback to environment variable (dev only)
    return os.getenv("ELOHIM_FOUNDER_PASSWORD", "")

def set_founder_password(password: str):
    # Store in macOS Keychain
    keyring.set_password("ElohimOS", "elohim_founder", password)
    logger.info("✅ Founder password stored in macOS Keychain")
```

**Files to Create/Modify**:
- `apps/backend/api/setup_wizard.py` (new file)
- `apps/frontend/src/components/SetupWizard.tsx` (new file)
- `apps/frontend/src/App.tsx` (check setup status, redirect to wizard)
- `apps/backend/api/auth_middleware.py` (use keychain for founder password)
- `requirements.txt` (add `keyring`)

**Success Criteria**:
- ✅ First-run setup guides user through admin + founder setup
- ✅ Founder password stored securely in macOS Keychain
- ✅ Metal 4 configuration saved to persistent config file
- ✅ Setup wizard only shown once (marker file prevents re-run)
- ✅ Professional UX matching Apple's setup assistants

---

## Implementation Timeline

**Total Duration**: 10-12 weeks

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| **Phase 0**: Hardening (DONE) | ✅ Complete | Critical | None |
| **Phase 1**: ML Acceleration | 2-3 weeks | High | Phase 0 |
| **Phase 2**: Data Processing | 3-4 weeks | Medium | Phase 1 |
| **Phase 3**: UI Enhancement | 2 weeks | Low | Phase 1 |
| **Phase 4**: Advanced Optimizations | 2-3 weeks | Low | Phase 2 |
| **Phase 5**: Final Hardening | 1 week | High | All phases |

**Recommended Order**:
1. Phase 1 (ML) → Highest performance impact
2. Phase 5 (Hardening) → Production readiness
3. Phase 2 (Data) → Large dataset support
4. Phase 3 (UI) → Polish and UX
5. Phase 4 (Advanced) → Optional bleeding-edge features

---

## Performance Targets

| Component | Current (CPU) | Target (Metal 4) | Improvement |
|-----------|--------------|------------------|-------------|
| Text Embedding (768-dim) | 50-100ms | 5-10ms | **5-10x faster** |
| Vector Search (10K vectors) | 100-500ms | 5-10ms | **10-50x faster** |
| Vector Search (1M vectors) | N/A (OOM) | 50-100ms | **Enables new scale** |
| SQL GROUP BY (100K rows) | 200-500ms | 50-100ms | **3-5x faster** |
| Pandas multiply (1M rows) | 100-200ms | 20-50ms | **4-5x faster** |
| Chart rendering (100K points) | 2000-5000ms | 50-100ms | **20-40x faster** |
| UI animations | 60fps | 120fps | **2x smoother** |

---

## Risk Assessment

### High Risk
- ❌ **Metal 4 Complexity**: Shader programming, memory management
  - **Mitigation**: Extensive testing, CPU fallbacks for all features

- ❌ **Breaking Changes**: Metal API changes in future macOS versions
  - **Mitigation**: Abstract Metal behind wrapper, easy to swap backends

### Medium Risk
- ⚠️ **Performance Regression**: GPU overhead for small datasets
  - **Mitigation**: Adaptive thresholds (use GPU only for large data)

- ⚠️ **Compatibility**: Older Macs without Metal 4
  - **Mitigation**: Feature detection, graceful degradation

### Low Risk
- ✅ **Setup Wizard**: Well-defined UI/UX patterns
- ✅ **Prometheus Metrics**: Standard library, proven solution

---

## Success Metrics

**Phase 1 (ML) Success**:
- ✅ 90%+ of embeddings run on Metal GPU (vs. CPU fallback)
- ✅ Average embedding latency <15ms (p95)
- ✅ Vector search handles 1M+ embeddings without OOM

**Phase 2 (Data) Success**:
- ✅ 50%+ of SQL queries use Metal kernels
- ✅ GROUP BY on 100K rows <100ms (p95)
- ✅ No regression in query correctness (exact match with SQLite)

**Phase 3 (UI) Success**:
- ✅ 120fps animations on ProMotion displays
- ✅ Chart rendering 10x faster than current (100K points <500ms)
- ✅ WebGPU works in Chrome + Safari on macOS Tahoe

**Phase 5 (Final) Success**:
- ✅ Prometheus metrics endpoint live, Grafana dashboard deployed
- ✅ All permission changes logged with audit trail
- ✅ Setup wizard completed by 10+ alpha testers (feedback collected)

---

## Future Enhancements (Post-Roadmap)

### Apple Intelligence Integration
- On-device LLM inference using Apple Neural Engine
- Private Cloud Compute for larger models
- Integration with Siri for voice commands

### Vision Pro Support
- visionOS port with spatial UI
- 3D data visualizations in AR
- Hand gesture controls for offline operations

### Metal Ray Tracing
- Real-time 3D data visualizations
- Path-traced lighting for UI elements
- Cinematic effects for marketing materials

---

## Appendix: Metal 4 Resources

### Documentation
- [Metal Shading Language Specification](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf)
- [Metal Performance Shaders](https://developer.apple.com/documentation/metalperformanceshaders)
- [MetalFX Documentation](https://developer.apple.com/documentation/metalfx)
- [Metal Best Practices Guide](https://developer.apple.com/documentation/metal/best_practices)

### Sample Code
- [Metal Compute Shaders Sample](https://developer.apple.com/documentation/metal/performing_calculations_on_a_gpu)
- [MetalFX Frame Interpolation Sample](https://developer.apple.com/documentation/metalfx/enabling_frame_interpolation)
- [Metal Neural Network Sample](https://developer.apple.com/documentation/metalperformanceshadersgraph)

### Community
- [Metal Developer Forums](https://developer.apple.com/forums/tags/metal)
- [PyObjC Metal Examples](https://github.com/ronaldoussoren/pyobjc)
- [WebGPU Samples](https://webgpu.github.io/webgpu-samples/)

---

**Document Version**: 1.0
**Last Updated**: November 10, 2025
**Author**: Claude (Anthropic) + ElohimOS Development Team
**Next Review**: Post Phase 1 Completion
