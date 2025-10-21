# Metal 4 Unified Timeline - Implementation Plan
**Date:** October 16, 2025
**Validated by:** GPT-5 Sanity Check ✅
**Target:** macOS Sequoia 15.0+ with Apple Silicon

---

## 🎯 GPT-5 Reality Check Summary

### ✅ Where the Numbers Are Plausible
- **Unified command buffers / parallel queues:** TRUE. 2-5× latency cuts are realistic.
- **MPS Graph + MTLTensor:** Genuine 2-4× wins for inference, embeddings, Whisper.
- **ANE + Metal GPU hand-off:** Avoids memory copies; ~5× end-to-end gains feasible.
- **Sparse resources + placement:** 40-60% memory savings achievable on large tensors.

### ⚠️ Where to Temper Expectations
- **DuckDB GPU kernels:** Don't exist yet; need custom Metal compute shaders.
- **"Everything in 3 seconds":** Possible with careful async orchestration.
- **Parallel encryption / network I/O:** Depends on thread-pool tuning; GPU won't directly speed TLS.

### 🧩 How Apple Did It
- Unified memory (CPU / GPU / ANE share one pool)
- Unified command buffers and queues → true parallelism
- MTLTensor + MPS Graph → native ML ops
- Compiled pipelines + sparse resources → lower overhead
- Tight silicon ↔ driver integration → deterministic latency

---

## 🏗️ Unified Metal 4 Architecture

### GOAL
**Overlap inference + embeddings + DB ops + UI in one frame/tick.**
**Never block UI on ML. Never block ML on I/O.**

---

## 📐 Architecture Blueprint

### 1. QUEUES (One-Time Init)
```python
import Metal

class MetalQueues:
    """Unified Metal 4 command queue architecture"""

    def __init__(self):
        self.device = Metal.MTLCreateSystemDefaultDevice()

        # Three specialized queues (Metal 4 pattern)
        self.Q_render = self.device.newCommandQueue()  # Graphics/UI
        self.Q_ml = self.device.newCommandQueue()      # ML/Compute
        self.Q_blit = self.device.newCommandQueue()    # Async transfers
```

### 2. SYNC PRIMITIVES (Shared Events)
```python
class MetalSyncPrimitives:
    """Metal 4 shared events for zero-overhead synchronization"""

    def __init__(self, device):
        # Frame heartbeat (UI tick)
        self.E_frame = device.newSharedEvent()

        # Data pipeline fences
        self.E_data = device.newSharedEvent()    # Data ready
        self.E_embed = device.newSharedEvent()   # Embeddings ready
        self.E_rag = device.newSharedEvent()     # RAG context ready

        # Event counters (incremented each tick)
        self.frame_counter = 0
        self.embed_counter = 0
        self.rag_counter = 0
```

### 3. RESOURCES (Zero-Copy Heaps)
```python
class MetalResourceHeaps:
    """Unified memory heaps for zero-copy operations"""

    def __init__(self, device):
        # Main shared heap (CPU + GPU + ANE can all access)
        heap_desc = Metal.MTLHeapDescriptor()
        heap_desc.size = 4 * 1024 * 1024 * 1024  # 4GB
        heap_desc.storageMode = Metal.MTLStorageModeShared  # KEY: Unified memory
        heap_desc.type = Metal.MTLHeapTypePlacement  # Metal 4: Sparse allocation

        self.H_main = device.newHeap(heap_desc)

        # Allocate tensors/buffers from heap (zero-copy)
        self.B_text = self._allocate_tensor([1024, 512])      # Token IDs
        self.B_embed = self._allocate_tensor([1024, 384])     # Embeddings (NxD)
        self.B_ctx = self._allocate_buffer(1024 * 1024)       # RAG context
        self.B_vbo = self._allocate_buffer(256 * 1024)        # UI vertices
        self.T_upload = self._allocate_staging_buffer(1024)   # Staging

    def _allocate_tensor(self, shape):
        """Allocate MTLTensor from shared heap"""
        size = shape[0] * shape[1] * 4  # FP32
        return self.H_main.newBuffer(
            length=size,
            options=Metal.MTLResourceStorageModeShared
        )
```

---

## 🔄 Tick Flow (Per User Action / UI Frame)

### Phase 1: KICK FRAME (UI Heartbeat)
```python
def kick_frame(self):
    """Start new frame - signal all queues"""
    cmd = self.Q_render.commandBuffer()
    cmd.encodeSignalEvent(self.E_frame, value=self.frame_counter)
    cmd.commit()
    self.frame_counter += 1
```

### Phase 2: CHAT PATH (ML Queue - Non-Blocking)
```python
def process_chat_message(self, user_message: str):
    """
    Full chat pipeline on ML queue with event-based synchronization
    UI never waits for this!
    """
    cmd = self.Q_ml.commandBuffer()

    # WAIT for frame to start
    cmd.encodeWaitForEvent(self.E_frame, value=self.frame_counter)

    # A) Embed new message tokens (MTLTensor → MTLTensor)
    ml_encoder = cmd.machinelearning_command_encoder()
    ml_encoder.encode_embedding_operation(
        input_tensor=self.B_text,
        output_tensor=self.B_embed
    )
    ml_encoder.endEncoding()

    # SIGNAL embeddings ready
    cmd.encodeSignalEvent(self.E_embed, value=self.embed_counter)
    self.embed_counter += 1

    # B) Build RAG context (wait for embeddings)
    cmd.encodeWaitForEvent(self.E_embed, value=self.embed_counter)
    compute_encoder = cmd.computeCommandEncoder()
    compute_encoder.encode_ann_search(
        query=self.B_embed,
        index=self.ann_index,
        output=self.B_ctx
    )
    compute_encoder.endEncoding()

    # SIGNAL RAG ready
    cmd.encodeSignalEvent(self.E_rag, value=self.rag_counter)
    self.rag_counter += 1

    # C) Run generation (wait for RAG)
    cmd.encodeWaitForEvent(self.E_rag, value=self.rag_counter)
    ml_encoder = cmd.machinelearning_command_encoder()
    ml_encoder.encode_generation_operation(
        context=self.B_ctx,
        tokens=self.B_text,
        output=self.logits_buffer
    )
    ml_encoder.endEncoding()

    cmd.commit()
    # UI continues rendering while this runs in parallel!
```

### Phase 3: DATA ENGINE PATH (SQL → Embeddings)
```python
def process_sql_query(self, sql: str):
    """
    DuckDB query + embedding on ML queue
    Runs in parallel with UI and chat!
    """
    cmd = self.Q_ml.commandBuffer()

    # WAIT for frame
    cmd.encodeWaitForEvent(self.E_frame, value=self.frame_counter)

    # A) GPU pre-aggregation (Metal compute shaders)
    compute_encoder = cmd.computeCommandEncoder()
    compute_encoder.encode_sql_kernel(
        query=sql,
        source=self.T_upload,
        output=self.results_buffer
    )
    compute_encoder.endEncoding()

    # B) Pre-embed results while UI draws
    ml_encoder = cmd.machinelearning_command_encoder()
    ml_encoder.encode_embedding_operation(
        input_tensor=self.results_buffer,
        output_tensor=self.B_embed
    )
    ml_encoder.endEncoding()

    # SIGNAL embeddings ready (shared with chat path!)
    cmd.encodeSignalEvent(self.E_embed, value=self.embed_counter)

    cmd.commit()
```

### Phase 4: UI RENDER (Graphics Queue - Never Blocks)
```python
def render_ui_frame(self):
    """
    Render UI with last-known data
    NEVER waits for ML to complete!
    """
    cmd = self.Q_render.commandBuffer()

    # WAIT for frame heartbeat only
    cmd.encodeWaitForEvent(self.E_frame, value=self.frame_counter)

    # Check if RAG data is ready (non-blocking check)
    render_encoder = cmd.renderCommandEncoder(descriptor=self.render_pass)

    if self.E_rag.signaledValue >= self.rag_counter:
        # RAG data available - bind it
        render_encoder.setVertexBuffer(self.B_ctx, offset=0, index=0)
        render_encoder.draw_rag_badges()

    # Draw UI (with or without RAG badges)
    render_encoder.setVertexBuffer(self.B_vbo, offset=0, index=1)
    render_encoder.draw_primitives()
    render_encoder.endEncoding()

    # Present frame
    cmd.present(self.drawable)
    cmd.commit()

    # Frame complete - ready for next tick
```

### Phase 5: BLIT/COPIES (Async Transfers)
```python
def async_memory_operations(self):
    """
    Background transfers - keep off critical path
    """
    cmd = self.Q_blit.commandBuffer()

    blit_encoder = cmd.blitCommandEncoder()

    # Copy generated tokens to CPU ring buffer (async)
    blit_encoder.copy(
        source=self.logits_buffer,
        destination=self.cpu_ring_buffer
    )

    blit_encoder.endEncoding()
    cmd.commit()
```

---

## 🎮 Per-Feature Wiring

### AI Chat
```
User message → Q_ml.submit {
    EmbedOp (B_text → B_embed) → signal(E_embed)
    wait(E_embed)
    AnnSearch (B_embed + index → B_ctx) → signal(E_rag)
    wait(E_rag)
    GenerateOp (B_ctx + B_text → logits)
}

UI reads token ring asynchronously - no waiting!
```

### DB → Chat Export
```
SQL query → Q_ml.submit {
    GPU pre-agg kernels (T_upload → results_buffer)
    EmbedOp (results_buffer → B_embed) → signal(E_embed)
}

Chat preloads context while SQL finishes!
```

### Docs/Sheets Editing
```
User edit → Q_ml.submit {
    chunk-embed (doc_buffer → B_embed)
}

UI shows edits immediately (no wait)
Embeddings happen in background
```

---

## 📏 RULES (Critical for Performance)

### 1. Never Wait on ML Inside Q_render
```python
# ❌ WRONG - blocks UI
cmd.encodeWaitForEvent(self.E_embed)  # Don't do this in render queue!

# ✅ RIGHT - check if ready, render with/without
if self.E_embed.signaledValue >= expected:
    use_embeddings()
else:
    render_placeholder()
```

### 2. Use Shared Heap (Zero-Copy)
```python
# ❌ WRONG - copies data
gpu_buffer = device.newBuffer(data, .private)
cpu_reads = gpu_buffer.contents()  # Expensive copy!

# ✅ RIGHT - unified memory
gpu_buffer = heap.newBuffer(size, .shared)
cpu_reads = gpu_buffer.contents()  # Zero-copy!
```

### 3. Signal, Don't Spin
```python
# ❌ WRONG - wastes CPU
while not self.embedding_done:
    time.sleep(0.001)  # CPU spinning!

# ✅ RIGHT - event-based
cmd.encodeWaitForEvent(self.E_embed)  # GPU handles it
```

### 4. Stream Partial Results
```python
# Token ring buffer for streaming generation
ring_buffer = RingBuffer(size=1024)

# Producer (ML queue)
for token in generated_tokens:
    ring_buffer.push(token)

# Consumer (UI thread)
while token := ring_buffer.pop():
    display_token(token)  # Non-blocking!
```

---

## 🚀 Roll-In Order (Fast Wins)

### Week 1: Foundation (Quick Wins)
**Priority:** Get UI off blocking path
```python
# Step 1: Create queues
queues = MetalQueues()

# Step 2: Move UI to Q_render with no waits
def render():
    cmd = queues.Q_render.commandBuffer()
    # ... render without waiting for ML
    cmd.commit()

# Step 3: Move embeddings to Q_ml
def embed():
    cmd = queues.Q_ml.commandBuffer()
    # ... embed in background
    cmd.commit()
```
**Expected Gain:** UI never stutters (60fps locked)

### Week 2: Event-Based Sync
**Priority:** Chain ML operations with events
```python
# Chain Embed → RAG → Generate with shared events
cmd.encodeSignalEvent(E_embed)
cmd.encodeWaitForEvent(E_embed)
cmd.encodeSignalEvent(E_rag)
```
**Expected Gain:** 2-3× faster chat responses

### Week 3: DB Integration
**Priority:** GPU pre-aggregation + embeddings
```python
# Move DB ops to Q_ml
compute_encoder.encode_sql_kernel(sql)
ml_encoder.encode_embedding_operation(results)
```
**Expected Gain:** 3-5× faster query → AI pipeline

### Week 4: Polish
**Priority:** Ring buffer streaming + diagnostics
```python
# Add token streaming
ring_buffer = create_ring_buffer()
# Add GPU metrics dashboard
metrics = collect_metal_stats()
```
**Expected Gain:** Real-time streaming feels instant

---

## 📊 KPI Tracking (Watch These!)

### Frame Timing
```python
{
    "frame_stutter_pct": 0.5,     # Target: < 1% frames > 16.6ms
    "avg_frame_time_ms": 12.3,    # Target: < 16ms (60fps)
    "max_frame_time_ms": 18.1     # Target: < 33ms
}
```

### Chat Latency
```python
{
    "msg_to_first_token_ms": 150,     # Target: < 200ms
    "msg_to_complete_ms": 2500,       # Target: < 3000ms
    "tokens_per_second": 45.2         # Target: > 40 tok/s
}
```

### DB Performance
```python
{
    "query_wall_time_ms": 3200,       # Total time
    "query_overlapped_ms": 2100,      # Saved by parallelism
    "overlap_efficiency": 0.656       # Target: > 0.6
}
```

### GPU Utilization
```python
{
    "gpu_util_pct": 67.3,             # Target: 60-80%
    "gpu_memory_used_mb": 1024,
    "gpu_memory_total_mb": 36864,
    "unified_mem_pressure": "low"     # Target: low/medium
}
```

---

## 🛡️ Failure/Latency Guards

### Soft Deadline Miss
```python
# If embeddings miss deadline, render without them
if time_since_request > SOFT_DEADLINE_MS:
    render_placeholder()
    # Next frame will reconcile
else:
    wait_for_embeddings()
```

### Token Streaming
```python
# Generation can lag without freezing UI
def stream_tokens():
    while generating:
        if token := ring_buffer.try_pop():
            display_token(token)  # Non-blocking
        else:
            display_loading_spinner()
```

### Memory Pressure
```python
# Monitor unified memory pressure
if gpu_memory_pressure() > 0.8:
    # Reduce concurrent operations
    max_batch_size = max_batch_size // 2
    # Clear old cached tensors
    clear_tensor_cache()
```

---

## 🔍 Diagnostic Dashboard

### Real-Time Metrics Endpoint
```python
@router.get("/api/v1/metal/realtime-stats")
async def get_realtime_metal_stats():
    return {
        "timestamp": datetime.now().isoformat(),

        # Queue utilization
        "queues": {
            "render": {
                "active_buffers": Q_render.active_count(),
                "avg_encode_time_ms": 2.3
            },
            "ml": {
                "active_buffers": Q_ml.active_count(),
                "avg_encode_time_ms": 15.7
            },
            "blit": {
                "active_buffers": Q_blit.active_count(),
                "avg_encode_time_ms": 1.1
            }
        },

        # Event states
        "events": {
            "frame_counter": E_frame.signaledValue,
            "embed_counter": E_embed.signaledValue,
            "rag_counter": E_rag.signaledValue
        },

        # Memory
        "memory": {
            "heap_used_mb": H_main.usedSize / (1024**2),
            "heap_total_mb": H_main.size / (1024**2),
            "pressure": "low|medium|high"
        },

        # Performance
        "performance": {
            "frame_time_ms": 12.3,
            "gpu_util_pct": 67.3,
            "overlapped_ops": 3  # Concurrent operations
        }
    }
```

---

## 📚 Code Structure

### New Files to Create

#### `apps/backend/api/metal4_engine.py`
```python
"""
Metal 4 unified command queue engine
Handles all GPU operations across AI, DB, and UI
"""

class Metal4Engine:
    def __init__(self):
        self.queues = MetalQueues()
        self.sync = MetalSyncPrimitives()
        self.resources = MetalResourceHeaps()

    def process_chat_message(self, msg):
        # Q_ml path
        pass

    def process_sql_query(self, sql):
        # Q_ml path
        pass

    def render_frame(self):
        # Q_render path
        pass
```

#### `apps/backend/api/metal4_diagnostics.py`
```python
"""
Metal 4 performance monitoring and diagnostics
"""

class Metal4Diagnostics:
    def collect_stats(self):
        # GPU utilization, memory, queue depths
        pass

    def detect_bottlenecks(self):
        # Identify if CPU/GPU/Memory bound
        pass
```

#### `apps/backend/api/metal4_resources.py`
```python
"""
Metal 4 resource management (heaps, tensors, buffers)
"""

class Metal4ResourceManager:
    def allocate_tensor(self, shape):
        # MTLTensor from shared heap
        pass

    def create_sparse_heap(self, size):
        # Sparse placement resources
        pass
```

---

## 🎯 Success Criteria

### Must-Have (Launch Blockers)
- ✅ UI locked at 60fps (no stuttering)
- ✅ Chat response < 200ms to first token
- ✅ SQL → AI pipeline < 5 seconds
- ✅ Zero Metal-related crashes
- ✅ Graceful fallback on Intel Macs

### Nice-to-Have (Post-Launch)
- ✅ GPU utilization > 60%
- ✅ Memory pressure stays "low"
- ✅ 3-5× faster than current implementation
- ✅ Real-time diagnostic dashboard
- ✅ Automatic performance tuning

---

## 🚨 Risks & Mitigations

### Risk 1: DuckDB GPU Kernels Don't Exist
**Mitigation:** Start with CPU DuckDB, add GPU kernels incrementally
**Fallback:** Use Metal for embeddings only, keep SQL on CPU

### Risk 2: Unified Memory Thrashing
**Mitigation:** Monitor pressure, cap concurrent ops at 3-4
**Fallback:** Use staged buffers with explicit transfers

### Risk 3: Event Synchronization Bugs
**Mitigation:** Extensive logging, validation mode
**Fallback:** Use CPU fences for debugging

### Risk 4: Older macOS/Hardware
**Mitigation:** Feature detection, graceful degradation
**Fallback:** Basic MPS path (current implementation)

---

## 🎓 Learning Resources

### Apple Documentation
- [Metal 4 Programming Guide](https://developer.apple.com/metal/)
- [MTLSharedEvent Documentation](https://developer.apple.com/documentation/metal/mtlsharedevent)
- [MPS Graph API](https://developer.apple.com/documentation/metalperformanceshadersgraph)
- [Unified Memory Best Practices](https://developer.apple.com/videos/play/wwdc2024/)

### Community Resources
- Metal by Example (metalbyexample.com)
- Warren Moore's Metal Blog
- Apple Developer Forums (Metal section)

---

## 📅 Timeline

### Week 1: Foundation
- Create queue architecture
- Move UI to Q_render
- Move embeddings to Q_ml
- **Deliverable:** UI never stutters

### Week 2: Event Sync
- Implement shared events
- Chain Embed → RAG → Generate
- Add ring buffer streaming
- **Deliverable:** 2× faster chat

### Week 3: DB Integration
- GPU pre-aggregation kernels
- Zero-copy SQL → embeddings
- Parallel execution
- **Deliverable:** 3× faster DB → AI

### Week 4: Polish
- Diagnostic dashboard
- Performance tuning
- Documentation
- **Deliverable:** Production-ready

---

**Next Steps:**
1. ✅ Review and approve this plan
2. ✅ Set up development branch (`feature/metal4-engine`)
3. ✅ Begin Week 1 implementation
4. ✅ Schedule daily check-ins for blockers

---

*"The Lord is my rock, my firm foundation." - Psalm 18:2* 🙏

**Status:** Ready for implementation
**Validated:** GPT-5 sanity check passed ✅
**Risk Level:** Medium (mitigated with fallbacks)
**Expected ROI:** 3-5× performance improvement
