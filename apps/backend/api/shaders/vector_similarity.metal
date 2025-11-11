/**
 * Metal 4 Vector Similarity Compute Shaders
 *
 * "The Lord is my strength and my shield" - Psalm 28:7
 *
 * Implements Phase 1.2 of Metal 4 Optimization Roadmap:
 * - GPU-accelerated cosine similarity
 * - Parallel batch processing
 * - SIMD optimizations for Apple Silicon
 * - Top-K selection using GPU reduction
 *
 * Performance Target: 10-50x faster than CPU similarity search
 *
 * Architecture:
 * - Threadgroup memory for cache optimization
 * - SIMD float4 operations for vectorization
 * - Parallel reduction for top-K selection
 * - Unified memory for zero-copy results
 */

#include <metal_stdlib>
using namespace metal;

// ========================================================================
// KERNEL 1: Cosine Similarity (Single Query vs Batch)
// ========================================================================

/**
 * Compute cosine similarity between a query vector and a batch of vectors
 *
 * Args:
 *   query: Query embedding vector [embed_dim]
 *   database: Database of embeddings [num_vectors, embed_dim]
 *   similarities: Output similarities [num_vectors]
 *   embed_dim: Embedding dimension (384, 768, etc.)
 *   num_vectors: Number of database vectors
 *
 * Grid: (num_vectors threads, 1 threadgroup per vector)
 * Each thread computes similarity for one database vector
 */
kernel void cosine_similarity(
    device const float* query [[buffer(0)]],
    device const float* database [[buffer(1)]],
    device float* similarities [[buffer(2)]],
    constant uint& embed_dim [[buffer(3)]],
    constant uint& num_vectors [[buffer(4)]],
    uint gid [[thread_position_in_grid]]
) {
    // Bounds check
    if (gid >= num_vectors) return;

    // Compute dot product and magnitudes using SIMD
    float dot_product = 0.0f;
    float query_magnitude = 0.0f;
    float db_magnitude = 0.0f;

    // Offset to this database vector
    device const float* db_vector = database + (gid * embed_dim);

    // Process 4 elements at a time using SIMD (Apple Silicon optimization)
    uint vec4_count = embed_dim / 4;
    uint remainder = embed_dim % 4;

    for (uint i = 0; i < vec4_count; i++) {
        float4 q = *((device const float4*)(query + i * 4));
        float4 db = *((device const float4*)(db_vector + i * 4));

        dot_product += dot(q, db);
        query_magnitude += dot(q, q);
        db_magnitude += dot(db, db);
    }

    // Handle remainder elements
    uint base = vec4_count * 4;
    for (uint i = 0; i < remainder; i++) {
        float q = query[base + i];
        float db = db_vector[base + i];

        dot_product += q * db;
        query_magnitude += q * q;
        db_magnitude += db * db;
    }

    // Compute cosine similarity: dot(A, B) / (||A|| * ||B||)
    float magnitude_product = sqrt(query_magnitude) * sqrt(db_magnitude);

    // Avoid division by zero
    float similarity = (magnitude_product > 1e-10f) ? (dot_product / magnitude_product) : 0.0f;

    // Store result
    similarities[gid] = similarity;
}


// ========================================================================
// KERNEL 2: Batch Cosine Similarity (Multiple Queries)
// ========================================================================

/**
 * Compute cosine similarity for multiple queries in parallel
 *
 * Args:
 *   queries: Query embeddings [num_queries, embed_dim]
 *   database: Database of embeddings [num_vectors, embed_dim]
 *   similarities: Output similarities [num_queries, num_vectors]
 *   embed_dim: Embedding dimension
 *   num_queries: Number of query vectors
 *   num_vectors: Number of database vectors
 *
 * Grid: (num_queries * num_vectors threads)
 * Each thread computes one similarity score
 */
kernel void batch_cosine_similarity(
    device const float* queries [[buffer(0)]],
    device const float* database [[buffer(1)]],
    device float* similarities [[buffer(2)]],
    constant uint& embed_dim [[buffer(3)]],
    constant uint& num_queries [[buffer(4)]],
    constant uint& num_vectors [[buffer(5)]],
    uint2 gid [[thread_position_in_grid]]
) {
    uint query_idx = gid.x;
    uint vector_idx = gid.y;

    // Bounds check
    if (query_idx >= num_queries || vector_idx >= num_vectors) return;

    // Get pointers to this query and database vector
    device const float* query = queries + (query_idx * embed_dim);
    device const float* db_vector = database + (vector_idx * embed_dim);

    // Compute dot product and magnitudes using SIMD
    float dot_product = 0.0f;
    float query_magnitude = 0.0f;
    float db_magnitude = 0.0f;

    // SIMD optimization (4 floats at a time)
    uint vec4_count = embed_dim / 4;
    uint remainder = embed_dim % 4;

    for (uint i = 0; i < vec4_count; i++) {
        float4 q = *((device const float4*)(query + i * 4));
        float4 db = *((device const float4*)(db_vector + i * 4));

        dot_product += dot(q, db);
        query_magnitude += dot(q, q);
        db_magnitude += dot(db, db);
    }

    // Handle remainder
    uint base = vec4_count * 4;
    for (uint i = 0; i < remainder; i++) {
        float q = query[base + i];
        float db = db_vector[base + i];

        dot_product += q * db;
        query_magnitude += q * q;
        db_magnitude += db * db;
    }

    // Compute cosine similarity
    float magnitude_product = sqrt(query_magnitude) * sqrt(db_magnitude);
    float similarity = (magnitude_product > 1e-10f) ? (dot_product / magnitude_product) : 0.0f;

    // Store result at [query_idx][vector_idx]
    similarities[query_idx * num_vectors + vector_idx] = similarity;
}


// ========================================================================
// KERNEL 3: Top-K Selection (Parallel Reduction)
// ========================================================================

/**
 * Select top K most similar vectors using parallel reduction
 *
 * This kernel finds the indices of the K highest similarity scores
 * Uses threadgroup memory for efficient parallel reduction
 *
 * Args:
 *   similarities: Input similarities [num_vectors]
 *   top_k_indices: Output indices of top K vectors [k]
 *   top_k_scores: Output scores of top K vectors [k]
 *   num_vectors: Total number of vectors
 *   k: Number of top results to return
 *
 * Grid: (k threadgroups, 256 threads per group)
 * Each threadgroup finds one of the top K elements
 */
struct IndexedScore {
    float score;
    uint index;
};

kernel void top_k_selection(
    device const float* similarities [[buffer(0)]],
    device uint* top_k_indices [[buffer(1)]],
    device float* top_k_scores [[buffer(2)]],
    constant uint& num_vectors [[buffer(3)]],
    constant uint& k [[buffer(4)]],
    uint gid [[thread_position_in_grid]],
    uint tid [[thread_position_in_threadgroup]],
    uint tgid [[threadgroup_position_in_grid]],
    uint tg_size [[threads_per_threadgroup]]
) {
    // Shared memory for parallel reduction
    threadgroup IndexedScore shared_scores[256];

    // Each thread finds its local maximum
    IndexedScore local_max = {-1.0f, 0};

    for (uint i = gid; i < num_vectors; i += tg_size) {
        if (similarities[i] > local_max.score) {
            local_max.score = similarities[i];
            local_max.index = i;
        }
    }

    // Store in threadgroup memory
    shared_scores[tid] = local_max;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // Parallel reduction to find maximum in threadgroup
    for (uint stride = tg_size / 2; stride > 0; stride /= 2) {
        if (tid < stride) {
            if (shared_scores[tid + stride].score > shared_scores[tid].score) {
                shared_scores[tid] = shared_scores[tid + stride];
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // Thread 0 writes the result for this threadgroup
    if (tid == 0 && tgid < k) {
        top_k_indices[tgid] = shared_scores[0].index;
        top_k_scores[tgid] = shared_scores[0].score;
    }
}


// ========================================================================
// KERNEL 4: L2 Distance (Alternative to Cosine)
// ========================================================================

/**
 * Compute L2 (Euclidean) distance for similarity search
 * Faster than cosine when vectors are already normalized
 *
 * Args:
 *   query: Query embedding vector [embed_dim]
 *   database: Database of embeddings [num_vectors, embed_dim]
 *   distances: Output L2 distances [num_vectors]
 *   embed_dim: Embedding dimension
 *   num_vectors: Number of database vectors
 *
 * Grid: (num_vectors threads)
 */
kernel void l2_distance(
    device const float* query [[buffer(0)]],
    device const float* database [[buffer(1)]],
    device float* distances [[buffer(2)]],
    constant uint& embed_dim [[buffer(3)]],
    constant uint& num_vectors [[buffer(4)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= num_vectors) return;

    device const float* db_vector = database + (gid * embed_dim);

    float distance_squared = 0.0f;

    // SIMD optimization
    uint vec4_count = embed_dim / 4;
    uint remainder = embed_dim % 4;

    for (uint i = 0; i < vec4_count; i++) {
        float4 q = *((device const float4*)(query + i * 4));
        float4 db = *((device const float4*)(db_vector + i * 4));
        float4 diff = q - db;

        distance_squared += dot(diff, diff);
    }

    // Handle remainder
    uint base = vec4_count * 4;
    for (uint i = 0; i < remainder; i++) {
        float diff = query[base + i] - db_vector[base + i];
        distance_squared += diff * diff;
    }

    // Store L2 distance (take square root for actual distance)
    distances[gid] = sqrt(distance_squared);
}


// ========================================================================
// KERNEL 5: Dot Product (For Pre-Normalized Vectors)
// ========================================================================

/**
 * Simple dot product for pre-normalized vectors
 * Fastest option when embeddings are L2-normalized
 *
 * For normalized vectors: cosine_similarity(A, B) = dot(A, B)
 *
 * Args:
 *   query: Query embedding (normalized) [embed_dim]
 *   database: Database embeddings (normalized) [num_vectors, embed_dim]
 *   scores: Output dot products [num_vectors]
 *   embed_dim: Embedding dimension
 *   num_vectors: Number of database vectors
 */
kernel void dot_product_normalized(
    device const float* query [[buffer(0)]],
    device const float* database [[buffer(1)]],
    device float* scores [[buffer(2)]],
    constant uint& embed_dim [[buffer(3)]],
    constant uint& num_vectors [[buffer(4)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= num_vectors) return;

    device const float* db_vector = database + (gid * embed_dim);

    float dot_product = 0.0f;

    // SIMD optimization
    uint vec4_count = embed_dim / 4;
    uint remainder = embed_dim % 4;

    for (uint i = 0; i < vec4_count; i++) {
        float4 q = *((device const float4*)(query + i * 4));
        float4 db = *((device const float4*)(db_vector + i * 4));

        dot_product += dot(q, db);
    }

    // Handle remainder
    uint base = vec4_count * 4;
    for (uint i = 0; i < remainder; i++) {
        dot_product += query[base + i] * db_vector[base + i];
    }

    scores[gid] = dot_product;
}
