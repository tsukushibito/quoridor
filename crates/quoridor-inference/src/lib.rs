//! Held native inference runtimes. Python is used only for artifact export.
use sha2::{Digest, Sha256};
use std::{
    ffi::{CStr, CString, c_char, c_void},
    fmt,
    path::Path,
    ptr::NonNull,
};
pub const FEATURES: usize = 648;
pub const POLICY: usize = 136;
#[derive(Clone, Debug, PartialEq)]
pub struct NetworkOutput {
    pub logits: [f32; POLICY],
    pub value: f32,
}
#[derive(Clone, Debug)]
pub struct BackendMetadata {
    pub backend: String,
    pub model_sha: String,
    pub max_batch: usize,
    pub input_features: usize,
    pub output_values: usize,
}
#[derive(Debug)]
pub struct InferenceError(pub String);
impl fmt::Display for InferenceError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}
impl std::error::Error for InferenceError {}
pub trait InferenceBackend: Send {
    fn infer(&mut self, inputs: &[[f32; FEATURES]]) -> Result<Vec<NetworkOutput>, InferenceError>;
    fn metadata(&self) -> &BackendMetadata;
}
fn path_string(path: &Path) -> Result<CString, InferenceError> {
    CString::new(path.as_os_str().as_encoded_bytes())
        .map_err(|_| InferenceError("NUL in path".into()))
}
fn native_error(error: &[c_char]) -> InferenceError {
    InferenceError(
        unsafe { CStr::from_ptr(error.as_ptr()) }
            .to_string_lossy()
            .into_owned(),
    )
}
fn metadata(name: &str, sha: &str, batch: usize) -> Result<BackendMetadata, InferenceError> {
    if sha.len() != 64 || !sha.bytes().all(|v| v.is_ascii_hexdigit()) {
        return Err(InferenceError("model SHA256 must be 64 hex digits".into()));
    }
    if batch == 0 || batch > 4096 {
        return Err(InferenceError("batch limit must be 1..4096".into()));
    }
    Ok(BackendMetadata {
        backend: name.into(),
        model_sha: sha.to_ascii_lowercase(),
        max_batch: batch,
        input_features: FEATURES,
        output_values: POLICY + 1,
    })
}
fn check_inputs(inputs: &[[f32; FEATURES]], max: usize) -> Result<(), InferenceError> {
    if inputs.is_empty() || inputs.len() > max {
        return Err(InferenceError(format!(
            "batch size {} outside 1..={max}",
            inputs.len()
        )));
    }
    if inputs.iter().flatten().any(|v| !v.is_finite()) {
        return Err(InferenceError("non-finite features".into()));
    }
    Ok(())
}
fn outputs(raw: Vec<f32>) -> Result<Vec<NetworkOutput>, InferenceError> {
    if raw.iter().any(|v| !v.is_finite()) {
        return Err(InferenceError("backend returned non-finite output".into()));
    }
    if !raw.as_chunks::<{ POLICY + 1 }>().1.is_empty() {
        return Err(InferenceError("backend output length mismatch".into()));
    }
    raw.as_chunks::<{ POLICY + 1 }>()
        .0
        .iter()
        .map(|row| {
            let value = row[POLICY];
            if !(-1.0..=1.0).contains(&value) {
                return Err(InferenceError("value outside tanh range".into()));
            }
            Ok(NetworkOutput {
                logits: row[..POLICY].try_into().unwrap(),
                value,
            })
        })
        .collect()
}
fn verify_sha(path: &Path, expected: &str) -> Result<(), InferenceError> {
    use std::io::Read;
    let mut file = std::fs::File::open(path)
        .map_err(|e| InferenceError(format!("{}: {e}", path.display())))?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = file
            .read(&mut buffer)
            .map_err(|e| InferenceError(e.to_string()))?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    let actual = format!("{:x}", hash.finalize());
    if actual != expected.to_ascii_lowercase() {
        return Err(InferenceError(format!(
            "artifact hash mismatch: expected {expected}, got {actual}"
        )));
    }
    Ok(())
}
#[cfg(any(feature = "cuda-aoti", feature = "tensorrt"))]
fn verify_package(
    path: &Path,
    sha: &str,
    max_batch: usize,
    backend: &str,
) -> Result<(), InferenceError> {
    let manifest = std::path::PathBuf::from(format!("{}.manifest.json", path.display()));
    let bytes = std::fs::read(&manifest)
        .map_err(|e| InferenceError(format!("{}: {e}", manifest.display())))?;
    let meta: serde_json::Value =
        serde_json::from_slice(&bytes).map_err(|e| InferenceError(e.to_string()))?;
    if meta["schema"] != "quoridor-native-inference-v1"
        || meta["backend"] != backend
        || meta["source_model_sha256"] != sha
        || meta["input_shape"] != serde_json::json!(["batch", 8, 9, 9])
        || meta["output_shapes"] != serde_json::json!([["batch", 136], ["batch", 1]])
        || meta["dtype"] != "float32"
        || meta["tf32"] != false
        || meta["amp"] != false
        || meta["max_batch"].as_u64().unwrap_or(0) < max_batch as u64
    {
        return Err(InferenceError("incompatible package manifest".into()));
    }
    verify_sha(
        path,
        meta["artifact_sha256"]
            .as_str()
            .ok_or_else(|| InferenceError("missing artifact hash".into()))?,
    )
}
#[cfg(any(feature = "cuda-aoti", feature = "tensorrt"))]
fn verify_runtime(path: &Path, actual: &str) -> Result<(), InferenceError> {
    let file = std::path::PathBuf::from(format!("{}.manifest.json", path.display()));
    let bytes = std::fs::read(file).map_err(|e| InferenceError(e.to_string()))?;
    let meta: serde_json::Value =
        serde_json::from_slice(&bytes).map_err(|e| InferenceError(e.to_string()))?;
    let version = meta["runtime_version"]
        .as_str()
        .or_else(|| {
            if meta["backend"] == "aoti" {
                meta["torch"].as_str()
            } else {
                None
            }
        })
        .ok_or_else(|| InferenceError("missing backend runtime version".into()))?;
    if version
        .split('+')
        .next()
        .unwrap()
        .split('.')
        .take(3)
        .collect::<Vec<_>>()
        .join(".")
        != actual
    {
        return Err(InferenceError(format!(
            "backend runtime mismatch: artifact {version}, linked {actual}"
        )));
    }
    Ok(())
}
unsafe extern "C" {
    fn qort_create(
        lib: *const c_char,
        model: *const c_char,
        err: *mut c_char,
        cap: usize,
    ) -> *mut c_void;
    fn qort_run(
        handle: *mut c_void,
        input: *const f32,
        batch: usize,
        out: *mut f32,
        err: *mut c_char,
        cap: usize,
    ) -> i32;
    fn qort_destroy(handle: *mut c_void);
}
pub struct OrtBackend {
    handle: NonNull<c_void>,
    metadata: BackendMetadata,
}
// Every session is accessed exclusively through &mut self; ownership can move to its worker.
unsafe impl Send for OrtBackend {}
impl OrtBackend {
    pub fn new(
        model_path: &Path,
        library_path: &Path,
        model_sha: &str,
    ) -> Result<Self, InferenceError> {
        verify_sha(model_path, model_sha)?;
        let metadata = metadata("onnxruntime-cpu", model_sha, 4096)?;
        let model = path_string(model_path)?;
        let lib = path_string(library_path)?;
        let mut error = [0; 4096];
        let handle = NonNull::new(unsafe {
            qort_create(
                lib.as_ptr(),
                model.as_ptr(),
                error.as_mut_ptr(),
                error.len(),
            )
        })
        .ok_or_else(|| native_error(&error))?;
        Ok(Self { handle, metadata })
    }
}
impl InferenceBackend for OrtBackend {
    fn infer(&mut self, inputs: &[[f32; FEATURES]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        check_inputs(inputs, self.metadata.max_batch)?;
        let mut output = vec![0.; inputs.len() * (POLICY + 1)];
        let mut error = [0; 4096];
        if unsafe {
            qort_run(
                self.handle.as_ptr(),
                inputs.as_ptr().cast(),
                inputs.len(),
                output.as_mut_ptr(),
                error.as_mut_ptr(),
                error.len(),
            )
        } != 0
        {
            return Err(native_error(&error));
        }
        outputs(output)
    }
    fn metadata(&self) -> &BackendMetadata {
        &self.metadata
    }
}
impl Drop for OrtBackend {
    fn drop(&mut self) {
        unsafe { qort_destroy(self.handle.as_ptr()) }
    }
}
#[cfg(feature = "cuda-aoti")]
mod cuda;
#[cfg(feature = "cuda-aoti")]
pub use cuda::AotiBackend;
#[cfg(feature = "tensorrt")]
mod tensorrt;
#[cfg(feature = "tensorrt")]
pub use tensorrt::TensorRtBackend;
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_invalid_features() {
        assert!(check_inputs(&[], 8).is_err());
        assert!(check_inputs(&[[f32::NAN; FEATURES]], 8).is_err());
        assert!(check_inputs(&[[0.; FEATURES]; 9], 8).is_err());
    }
    #[test]
    fn rejects_invalid_output() {
        assert!(outputs(vec![f32::NAN; 137]).is_err());
        let mut values = vec![0.; 137];
        values[136] = 2.;
        assert!(outputs(values).is_err());
    }
    #[test]
    fn model_identity() {
        assert!(metadata("test", "bad", 8).is_err());
        assert!(metadata("test", &"a".repeat(64), 0).is_err());
    }
    #[test]
    fn missing_runtime_is_reported() {
        assert!(
            OrtBackend::new(Path::new("missing"), Path::new("missing"), &"a".repeat(64)).is_err()
        );
    }
}
