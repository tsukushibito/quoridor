//! SIMD is optional and selected at runtime; scalar order remains the float oracle.
//! Products are vectorized, then reduced in original order (no FMA/reassociation).
pub(crate) fn dot(weights: &[f32], values: &[f32], mut bias: f32, vector: bool) -> f32 {
    debug_assert_eq!(weights.len(), values.len());
    #[cfg(target_arch = "x86_64")]
    if vector && std::is_x86_feature_detected!("avx2") {
        // SAFETY: feature checked; the private implementation bounds every load.
        return unsafe { avx2_dot(weights, values, bias) };
    }
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    if vector {
        return unsafe { wasm_dot(weights, values, bias) };
    }
    let _ = vector;
    for (&w, &x) in weights.iter().zip(values) {
        bias += w * x;
    }
    bias
}

pub(crate) fn add_column(values: &mut [f32], column: &[f32], subtract: bool, vector: bool) {
    #[cfg(target_arch = "x86_64")]
    if vector && std::is_x86_feature_detected!("avx2") {
        // SAFETY: feature checked; both slices have the same length.
        unsafe { avx2_column(values, column, subtract) };
        return;
    }
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    if vector {
        unsafe { wasm_column(values, column, subtract) };
        return;
    }
    let _ = vector;
    for (v, &w) in values.iter_mut().zip(column) {
        *v += if subtract { -w } else { w };
    }
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn avx2_dot(w: &[f32], x: &[f32], mut sum: f32) -> f32 {
    use std::arch::x86_64::*;
    let mut i = 0;
    while i + 8 <= w.len() {
        let mut product = [0.0; 8];
        // SAFETY: i+8 is within both input slices; local output has eight lanes.
        unsafe {
            let a = _mm256_loadu_ps(w.as_ptr().add(i));
            let b = _mm256_loadu_ps(x.as_ptr().add(i));
            _mm256_storeu_ps(product.as_mut_ptr(), _mm256_mul_ps(a, b));
        }
        for v in product {
            sum += v;
        }
        i += 8;
    }
    for j in i..w.len() {
        sum += w[j] * x[j];
    }
    sum
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn avx2_column(v: &mut [f32], w: &[f32], subtract: bool) {
    use std::arch::x86_64::*;
    let mut i = 0;
    while i + 8 <= v.len() {
        // SAFETY: i+8 is within both slices. Unaligned loads/stores are intentional.
        unsafe {
            let a = _mm256_loadu_ps(v.as_ptr().add(i));
            let b = _mm256_loadu_ps(w.as_ptr().add(i));
            let b = if subtract {
                _mm256_xor_ps(b, _mm256_set1_ps(-0.0))
            } else {
                b
            };
            _mm256_storeu_ps(v.as_mut_ptr().add(i), _mm256_add_ps(a, b));
        }
        i += 8;
    }
    for j in i..v.len() {
        v[j] += if subtract { -w[j] } else { w[j] };
    }
}

#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
#[target_feature(enable = "simd128")]
unsafe fn wasm_dot(w: &[f32], x: &[f32], mut sum: f32) -> f32 {
    use std::arch::wasm32::*;
    let mut i = 0;
    while i + 4 <= w.len() {
        let mut products = [0.; 4];
        // SAFETY: four-element windows and a local four-element output.
        unsafe {
            let a = v128_load(w.as_ptr().add(i).cast());
            let b = v128_load(x.as_ptr().add(i).cast());
            v128_store(products.as_mut_ptr().cast(), f32x4_mul(a, b));
        }
        for v in products {
            sum += v;
        }
        i += 4;
    }
    for j in i..w.len() {
        sum += w[j] * x[j];
    }
    sum
}
#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
#[target_feature(enable = "simd128")]
unsafe fn wasm_column(v: &mut [f32], w: &[f32], subtract: bool) {
    use std::arch::wasm32::*;
    let mut i = 0;
    while i + 4 <= v.len() {
        // SAFETY: each load/store is wholly inside the paired slices.
        unsafe {
            let a = v128_load(v.as_ptr().add(i).cast());
            let b = v128_load(w.as_ptr().add(i).cast());
            let b = if subtract { f32x4_neg(b) } else { b };
            v128_store(v.as_mut_ptr().add(i).cast(), f32x4_add(a, b));
        }
        i += 4;
    }
    for j in i..v.len() {
        v[j] += if subtract { -w[j] } else { w[j] };
    }
}
