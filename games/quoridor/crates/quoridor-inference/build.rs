use std::{env, path::PathBuf};
fn main() {
    let mut build = cc::Build::new();
    build
        .cpp(true)
        .std("c++20")
        .file("native/ort.cpp")
        .include("native");
    if env::var_os("CARGO_FEATURE_CUDA_AOTI").is_some() {
        let root = PathBuf::from(
            env::var("QUORIDOR_TORCH_ROOT")
                .expect("cuda-aoti requires QUORIDOR_TORCH_ROOT (installed torch directory)"),
        );
        let cuda = PathBuf::from(
            env::var("QUORIDOR_CUDA_ROOT")
                .expect("cuda-aoti requires QUORIDOR_CUDA_ROOT (CUDA include/lib directory)"),
        );
        build
            .file("native/aoti.cpp")
            .include(root.join("include"))
            .include(root.join("include/torch/csrc/api/include"))
            .include(cuda.join("include"))
            .include(
                root.parent()
                    .unwrap()
                    .join("triton/backends/nvidia/include"),
            )
            .define("_GLIBCXX_USE_CXX11_ABI", "1");
        if let Ok(p) = env::var("QUORIDOR_CCCL_INCLUDE") {
            build.include(p);
        };
        println!(
            "cargo:rustc-link-search=native={}",
            root.join("lib").display()
        );
        println!(
            "cargo:rustc-link-search=native={}",
            cuda.join("lib").display()
        );
        println!("cargo:rustc-link-lib=dylib:+verbatim=libcudart.so.13");
        for lib in ["torch", "torch_cpu", "torch_cuda", "c10", "c10_cuda"] {
            println!("cargo:rustc-link-lib=dylib={lib}");
        }
        println!(
            "cargo:rustc-link-arg=-Wl,-rpath,{}",
            root.join("lib").display()
        );
        println!(
            "cargo:rustc-link-arg=-Wl,-rpath,{}",
            cuda.join("lib").display()
        );
    }
    if env::var_os("CARGO_FEATURE_TENSORRT").is_some() {
        let root = PathBuf::from(
            env::var("QUORIDOR_TENSORRT_ROOT")
                .expect("tensorrt requires isolated QUORIDOR_TENSORRT_ROOT"),
        );
        let cuda = PathBuf::from(
            env::var("QUORIDOR_CUDA_ROOT").expect("tensorrt requires QUORIDOR_CUDA_ROOT"),
        );
        build
            .file("native/tensorrt.cpp")
            .include(root.join("include"))
            .include(cuda.join("include"))
            .include(
                cuda.parent()
                    .unwrap()
                    .parent()
                    .unwrap()
                    .join("triton/backends/nvidia/include"),
            );
        println!(
            "cargo:rustc-link-search=native={}",
            root.join("lib").display()
        );
        println!(
            "cargo:rustc-link-search=native={}",
            cuda.join("lib").display()
        );
        println!("cargo:rustc-link-lib=dylib=nvinfer");
        if env::var_os("CARGO_FEATURE_CUDA_AOTI").is_none() {
            println!("cargo:rustc-link-lib=dylib:+verbatim=libcudart.so.13");
        }
        println!(
            "cargo:rustc-link-arg=-Wl,-rpath,{}",
            root.join("lib").display()
        );
        println!(
            "cargo:rustc-link-arg=-Wl,-rpath,{}",
            cuda.join("lib").display()
        );
    }
    build.compile("quoridor_inference_native");
    println!("cargo:rustc-link-lib=dl");
    for p in [
        "native/ort.cpp",
        "native/work_counts.h",
        "native/aoti.cpp",
        "native/tensorrt.cpp",
        "native/onnxruntime_c_api.h",
        "native/onnxruntime_ep_c_api.h",
    ] {
        println!("cargo:rerun-if-changed={p}");
    }
    for p in [
        "QUORIDOR_TORCH_ROOT",
        "QUORIDOR_CUDA_ROOT",
        "QUORIDOR_TENSORRT_ROOT",
        "QUORIDOR_CCCL_INCLUDE",
    ] {
        println!("cargo:rerun-if-env-changed={p}");
    }
}
