use super::*;
unsafe extern "C" {
    fn qtrt_runtime_version() -> i32;
    fn qtrt_create(
        package: *const c_char,
        max_batch: usize,
        device: i32,
        graph: i32,
        err: *mut c_char,
        cap: usize,
    ) -> *mut c_void;
    fn qtrt_run(
        handle: *mut c_void,
        input: *const f32,
        batch: usize,
        out: *mut f32,
        err: *mut c_char,
        cap: usize,
    ) -> i32;
    fn qtrt_destroy(handle: *mut c_void);
}
pub struct TensorRtBackend {
    handle: NonNull<c_void>,
    metadata: BackendMetadata,
}
unsafe impl Send for TensorRtBackend {}
impl TensorRtBackend {
    pub fn new(
        package_path: &Path,
        model_sha: &str,
        max_batch: usize,
        device: i32,
        graph: bool,
    ) -> Result<Self, InferenceError> {
        if !(0..=127).contains(&device) {
            return Err(InferenceError("CUDA device index must be 0..127".into()));
        }
        verify_package(package_path, model_sha, max_batch, "tensorrt")?;
        let version = unsafe { qtrt_runtime_version() };
        verify_runtime(
            package_path,
            &format!(
                "{}.{}.{}",
                version / 10000,
                (version % 10000) / 100,
                version % 100
            ),
        )?;
        let metadata = metadata(
            if graph {
                "cuda-tensorrt-graph"
            } else {
                "cuda-tensorrt"
            },
            model_sha,
            max_batch,
        )?;
        let package = path_string(package_path)?;
        let mut error = [0; 4096];
        let handle = NonNull::new(unsafe {
            qtrt_create(
                package.as_ptr(),
                max_batch,
                device,
                graph.into(),
                error.as_mut_ptr(),
                error.len(),
            )
        })
        .ok_or_else(|| native_error(&error))?;
        Ok(Self { handle, metadata })
    }
}
impl InferenceBackend for TensorRtBackend {
    fn infer(&mut self, inputs: &[[f32; FEATURES]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        check_inputs(inputs, self.metadata.max_batch)?;
        let mut output = vec![0.; inputs.len() * (POLICY + 1)];
        let mut error = [0; 4096];
        if unsafe {
            qtrt_run(
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
impl Drop for TensorRtBackend {
    fn drop(&mut self) {
        unsafe { qtrt_destroy(self.handle.as_ptr()) }
    }
}
