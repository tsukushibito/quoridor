use super::*;
unsafe extern "C" {
    fn qaoti_runtime_version() -> *const c_char;
    fn qaoti_create(
        package: *const c_char,
        max_batch: usize,
        device: i32,
        graph: i32,
        err: *mut c_char,
        cap: usize,
    ) -> *mut c_void;
    fn qaoti_run(
        handle: *mut c_void,
        input: *const f32,
        batch: usize,
        out: *mut f32,
        err: *mut c_char,
        cap: usize,
    ) -> i32;
    fn qaoti_destroy(handle: *mut c_void);
}
pub struct AotiBackend {
    handle: NonNull<c_void>,
    metadata: BackendMetadata,
}
unsafe impl Send for AotiBackend {}
impl AotiBackend {
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
        verify_package(package_path, model_sha, max_batch, "aoti")?;
        verify_runtime(
            package_path,
            unsafe { CStr::from_ptr(qaoti_runtime_version()) }
                .to_str()
                .map_err(|e| InferenceError(e.to_string()))?,
        )?;
        let metadata = metadata(
            if graph {
                "cuda-aoti-graph"
            } else {
                "cuda-aoti"
            },
            model_sha,
            max_batch,
        )?;
        let package = path_string(package_path)?;
        let mut error = [0; 4096];
        let handle = NonNull::new(unsafe {
            qaoti_create(
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
impl InferenceBackend for AotiBackend {
    fn infer(&mut self, inputs: &[[f32; FEATURES]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        check_inputs(inputs, self.metadata.max_batch)?;
        let mut output = vec![0.; inputs.len() * (POLICY + 1)];
        let mut error = [0; 4096];
        if unsafe {
            qaoti_run(
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
impl Drop for AotiBackend {
    fn drop(&mut self) {
        unsafe { qaoti_destroy(self.handle.as_ptr()) }
    }
}
