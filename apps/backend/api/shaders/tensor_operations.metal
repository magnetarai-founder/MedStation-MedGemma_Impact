/**
 * Metal 4 Tensor Operations
 *
 * "The Lord is my rock, in whom I take refuge" - Psalm 18:2
 *
 * Implements Phase 4.1 of Metal 4 Optimization Roadmap:
 * - Native tensor operations in Metal shaders
 * - Matrix multiplication (GEMM) optimized for Apple Silicon
 * - Convolution operations for neural networks
 * - Attention mechanisms (scaled dot-product)
 * - Element-wise tensor operations
 *
 * Performance Target: 10-20x faster than CPU for large tensors
 *
 * Architecture:
 * - Threadgroup memory for tile-based GEMM
 * - SIMD operations for vectorization
 * - Memory coalescing for bandwidth optimization
 * - Metal 4 tensor API when available
 */

#include <metal_stdlib>
using namespace metal;

// ========================================================================
// KERNEL 1: Matrix Multiplication (GEMM) - Tiled Algorithm
// ========================================================================

/**
 * Optimized matrix multiplication using threadgroup memory
 *
 * Computes C = A * B where:
 * - A is [M, K]
 * - B is [K, N]
 * - C is [M, N]
 *
 * Uses tiled algorithm with threadgroup memory for cache optimization.
 * Tile size: 16x16 (optimal for Apple Silicon)
 */

#define TILE_SIZE 16

kernel void matmul_float32(
    device const float* A [[buffer(0)]],
    device const float* B [[buffer(1)]],
    device float* C [[buffer(2)]],
    constant uint& M [[buffer(3)]],
    constant uint& N [[buffer(4)]],
    constant uint& K [[buffer(5)]],
    uint2 gid [[thread_position_in_grid]],
    uint2 tid [[thread_position_in_threadgroup]],
    uint2 tg_size [[threads_per_threadgroup]]
) {
    // Threadgroup memory for tiles
    threadgroup float tileA[TILE_SIZE][TILE_SIZE];
    threadgroup float tileB[TILE_SIZE][TILE_SIZE];

    uint row = gid.y;
    uint col = gid.x;

    float sum = 0.0f;

    // Iterate over tiles
    uint numTiles = (K + TILE_SIZE - 1) / TILE_SIZE;

    for (uint t = 0; t < numTiles; t++) {
        // Load tile from A into threadgroup memory
        uint tileRow = tid.y;
        uint tileCol = tid.x;
        uint aRow = row;
        uint aCol = t * TILE_SIZE + tileCol;

        if (aRow < M && aCol < K) {
            tileA[tileRow][tileCol] = A[aRow * K + aCol];
        } else {
            tileA[tileRow][tileCol] = 0.0f;
        }

        // Load tile from B into threadgroup memory
        uint bRow = t * TILE_SIZE + tileRow;
        uint bCol = col;

        if (bRow < K && bCol < N) {
            tileB[tileRow][tileCol] = B[bRow * N + bCol];
        } else {
            tileB[tileRow][tileCol] = 0.0f;
        }

        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Compute partial dot product
        for (uint k = 0; k < TILE_SIZE; k++) {
            sum += tileA[tileRow][k] * tileB[k][tileCol];
        }

        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // Write result
    if (row < M && col < N) {
        C[row * N + col] = sum;
    }
}


// ========================================================================
// KERNEL 2: Batched Matrix Multiplication
// ========================================================================

/**
 * Batched matrix multiplication for transformer models
 *
 * Computes C[b] = A[b] * B[b] for batch b
 *
 * Args:
 *   A: [batch_size, M, K]
 *   B: [batch_size, K, N]
 *   C: [batch_size, M, N]
 */
kernel void batched_matmul_float32(
    device const float* A [[buffer(0)]],
    device const float* B [[buffer(1)]],
    device float* C [[buffer(2)]],
    constant uint& batch_size [[buffer(3)]],
    constant uint& M [[buffer(4)]],
    constant uint& N [[buffer(5)]],
    constant uint& K [[buffer(6)]],
    uint3 gid [[thread_position_in_grid]]
) {
    uint batch = gid.z;
    uint row = gid.y;
    uint col = gid.x;

    if (batch >= batch_size || row >= M || col >= N) return;

    // Offset into batch
    uint a_offset = batch * M * K;
    uint b_offset = batch * K * N;
    uint c_offset = batch * M * N;

    float sum = 0.0f;

    for (uint k = 0; k < K; k++) {
        sum += A[a_offset + row * K + k] * B[b_offset + k * N + col];
    }

    C[c_offset + row * N + col] = sum;
}


// ========================================================================
// KERNEL 3: Scaled Dot-Product Attention
// ========================================================================

/**
 * Scaled dot-product attention for transformers
 *
 * Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V
 *
 * Args:
 *   Q: Query [seq_len, d_k]
 *   K: Key [seq_len, d_k]
 *   V: Value [seq_len, d_v]
 *   output: Attention output [seq_len, d_v]
 *   seq_len: Sequence length
 *   d_k: Key dimension
 *   d_v: Value dimension
 */
kernel void scaled_dot_product_attention(
    device const float* Q [[buffer(0)]],
    device const float* K [[buffer(1)]],
    device const float* V [[buffer(2)]],
    device float* output [[buffer(3)]],
    constant uint& seq_len [[buffer(4)]],
    constant uint& d_k [[buffer(5)]],
    constant uint& d_v [[buffer(6)]],
    uint2 gid [[thread_position_in_grid]]
) {
    uint i = gid.y;  // Query position
    uint j = gid.x;  // Key/Value position

    if (i >= seq_len || j >= d_v) return;

    // Compute attention scores for position i
    float score_sum = 0.0f;
    float max_score = -INFINITY;

    // Find max score for numerical stability
    for (uint k = 0; k < seq_len; k++) {
        float score = 0.0f;
        for (uint d = 0; d < d_k; d++) {
            score += Q[i * d_k + d] * K[k * d_k + d];
        }
        score /= sqrt(float(d_k));  // Scale
        max_score = max(max_score, score);
    }

    // Compute softmax
    threadgroup float attention_weights[256];  // Assuming seq_len <= 256
    float exp_sum = 0.0f;

    for (uint k = 0; k < seq_len; k++) {
        float score = 0.0f;
        for (uint d = 0; d < d_k; d++) {
            score += Q[i * d_k + d] * K[k * d_k + d];
        }
        score /= sqrt(float(d_k));

        float exp_score = exp(score - max_score);
        attention_weights[k] = exp_score;
        exp_sum += exp_score;
    }

    // Normalize and apply to values
    float result = 0.0f;
    for (uint k = 0; k < seq_len; k++) {
        float weight = attention_weights[k] / exp_sum;
        result += weight * V[k * d_v + j];
    }

    output[i * d_v + j] = result;
}


// ========================================================================
// KERNEL 4: 2D Convolution
// ========================================================================

/**
 * 2D Convolution for CNNs
 *
 * Args:
 *   input: Input tensor [batch, in_channels, height, width]
 *   kernel: Convolution kernel [out_channels, in_channels, kernel_h, kernel_w]
 *   output: Output tensor [batch, out_channels, out_height, out_width]
 *   bias: Bias terms [out_channels]
 */
kernel void conv2d_float32(
    device const float* input [[buffer(0)]],
    device const float* kernel [[buffer(1)]],
    device const float* bias [[buffer(2)]],
    device float* output [[buffer(3)]],
    constant uint& batch_size [[buffer(4)]],
    constant uint& in_channels [[buffer(5)]],
    constant uint& out_channels [[buffer(6)]],
    constant uint& input_height [[buffer(7)]],
    constant uint& input_width [[buffer(8)]],
    constant uint& kernel_height [[buffer(9)]],
    constant uint& kernel_width [[buffer(10)]],
    constant uint& stride [[buffer(11)]],
    constant uint& padding [[buffer(12)]],
    uint3 gid [[thread_position_in_grid]]
) {
    uint b = gid.z;  // Batch
    uint oc = gid.y; // Output channel
    uint out_idx = gid.x;  // Flattened output position

    uint output_height = (input_height + 2 * padding - kernel_height) / stride + 1;
    uint output_width = (input_width + 2 * padding - kernel_width) / stride + 1;

    if (b >= batch_size || oc >= out_channels || out_idx >= output_height * output_width) {
        return;
    }

    uint oh = out_idx / output_width;
    uint ow = out_idx % output_width;

    float sum = bias[oc];

    // Convolve
    for (uint ic = 0; ic < in_channels; ic++) {
        for (uint kh = 0; kh < kernel_height; kh++) {
            for (uint kw = 0; kw < kernel_width; kw++) {
                int ih = int(oh * stride + kh) - int(padding);
                int iw = int(ow * stride + kw) - int(padding);

                if (ih >= 0 && ih < int(input_height) && iw >= 0 && iw < int(input_width)) {
                    uint input_idx = b * in_channels * input_height * input_width +
                                   ic * input_height * input_width +
                                   ih * input_width + iw;

                    uint kernel_idx = oc * in_channels * kernel_height * kernel_width +
                                    ic * kernel_height * kernel_width +
                                    kh * kernel_width + kw;

                    sum += input[input_idx] * kernel[kernel_idx];
                }
            }
        }
    }

    uint output_idx = b * out_channels * output_height * output_width +
                     oc * output_height * output_width +
                     oh * output_width + ow;

    output[output_idx] = sum;
}


// ========================================================================
// KERNEL 5: Element-wise Operations
// ========================================================================

/**
 * Element-wise tensor addition
 */
kernel void tensor_add_float32(
    device const float* A [[buffer(0)]],
    device const float* B [[buffer(1)]],
    device float* C [[buffer(2)]],
    constant uint& size [[buffer(3)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= size) return;
    C[gid] = A[gid] + B[gid];
}

/**
 * Element-wise tensor multiplication
 */
kernel void tensor_mul_float32(
    device const float* A [[buffer(0)]],
    device const float* B [[buffer(1)]],
    device float* C [[buffer(2)]],
    constant uint& size [[buffer(3)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= size) return;
    C[gid] = A[gid] * B[gid];
}

/**
 * ReLU activation
 */
kernel void relu_float32(
    device const float* input [[buffer(0)]],
    device float* output [[buffer(1)]],
    constant uint& size [[buffer(2)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= size) return;
    output[gid] = max(0.0f, input[gid]);
}

/**
 * GELU activation (Gaussian Error Linear Unit)
 */
kernel void gelu_float32(
    device const float* input [[buffer(0)]],
    device float* output [[buffer(1)]],
    constant uint& size [[buffer(2)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= size) return;

    float x = input[gid];
    // GELU approximation: 0.5 * x * (1 + tanh(sqrt(2/π) * (x + 0.044715 * x^3)))
    float x3 = x * x * x;
    float inner = 0.7978845608f * (x + 0.044715f * x3);
    output[gid] = 0.5f * x * (1.0f + tanh(inner));
}


// ========================================================================
// KERNEL 6: Softmax
// ========================================================================

/**
 * Softmax activation
 *
 * Numerically stable softmax with two-pass algorithm
 */
kernel void softmax_float32(
    device const float* input [[buffer(0)]],
    device float* output [[buffer(1)]],
    constant uint& num_rows [[buffer(2)]],
    constant uint& num_cols [[buffer(3)]],
    uint2 gid [[thread_position_in_grid]],
    uint tid [[thread_position_in_threadgroup]]
) {
    uint row = gid.y;

    if (row >= num_rows) return;

    threadgroup float shared_data[256];

    // Find max for numerical stability
    float max_val = -INFINITY;
    for (uint col = tid; col < num_cols; col += 256) {
        max_val = max(max_val, input[row * num_cols + col]);
    }

    shared_data[tid] = max_val;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // Reduce to find global max
    for (uint stride = 128; stride > 0; stride /= 2) {
        if (tid < stride) {
            shared_data[tid] = max(shared_data[tid], shared_data[tid + stride]);
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    max_val = shared_data[0];

    // Compute exp and sum
    float sum = 0.0f;
    for (uint col = tid; col < num_cols; col += 256) {
        float exp_val = exp(input[row * num_cols + col] - max_val);
        output[row * num_cols + col] = exp_val;
        sum += exp_val;
    }

    shared_data[tid] = sum;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // Reduce sum
    for (uint stride = 128; stride > 0; stride /= 2) {
        if (tid < stride) {
            shared_data[tid] += shared_data[tid + stride];
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    sum = shared_data[0];

    // Normalize
    for (uint col = tid; col < num_cols; col += 256) {
        output[row * num_cols + col] /= sum;
    }
}


// ========================================================================
// KERNEL 7: Layer Normalization
// ========================================================================

/**
 * Layer normalization for transformers
 *
 * LayerNorm(x) = gamma * (x - mean) / sqrt(var + eps) + beta
 */
kernel void layer_norm_float32(
    device const float* input [[buffer(0)]],
    device const float* gamma [[buffer(1)]],
    device const float* beta [[buffer(2)]],
    device float* output [[buffer(3)]],
    constant uint& num_rows [[buffer(4)]],
    constant uint& num_cols [[buffer(5)]],
    constant float& eps [[buffer(6)]],
    uint2 gid [[thread_position_in_grid]],
    uint tid [[thread_position_in_threadgroup]]
) {
    uint row = gid.y;

    if (row >= num_rows) return;

    threadgroup float shared_sum[256];
    threadgroup float shared_sq_sum[256];

    // Compute mean and variance
    float sum = 0.0f;
    float sq_sum = 0.0f;

    for (uint col = tid; col < num_cols; col += 256) {
        float val = input[row * num_cols + col];
        sum += val;
        sq_sum += val * val;
    }

    shared_sum[tid] = sum;
    shared_sq_sum[tid] = sq_sum;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // Reduce
    for (uint stride = 128; stride > 0; stride /= 2) {
        if (tid < stride) {
            shared_sum[tid] += shared_sum[tid + stride];
            shared_sq_sum[tid] += shared_sq_sum[tid + stride];
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    float mean = shared_sum[0] / float(num_cols);
    float variance = (shared_sq_sum[0] / float(num_cols)) - (mean * mean);
    float std_dev = sqrt(variance + eps);

    // Normalize
    for (uint col = tid; col < num_cols; col += 256) {
        float normalized = (input[row * num_cols + col] - mean) / std_dev;
        output[row * num_cols + col] = gamma[col] * normalized + beta[col];
    }
}
