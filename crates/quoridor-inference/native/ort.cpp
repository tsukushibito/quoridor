// ONNX Runtime C ABI, dynamically loaded; no Python dependency.
#include "onnxruntime_c_api.h"
#include "work_counts.h"
#include <cstring>
#include <dlfcn.h>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
struct OrtBackend {
  WorkCounts counts;
  void *library = nullptr;
  const OrtApi *api = nullptr;
  OrtEnv *env = nullptr;
  OrtSession *session = nullptr;
  OrtMemoryInfo *memory = nullptr;
  std::string input_name;
  std::vector<std::string> output_names;
  ~OrtBackend() {
    if (api) {
      if (memory)
        api->ReleaseMemoryInfo(memory);
      if (session)
        api->ReleaseSession(session);
      if (env)
        api->ReleaseEnv(env);
    }
    if (library)
      dlclose(library);
  }
  void check(OrtStatus *status) {
    if (status) {
      std::string error = api->GetErrorMessage(status);
      api->ReleaseStatus(status);
      throw std::runtime_error(error);
    }
  }
};
void error(char *out, size_t cap, const std::exception &e) {
  if (cap) {
    strncpy(out, e.what(), cap - 1);
    out[cap - 1] = 0;
  }
}
} // namespace
extern "C" void *qort_create(const char *lib, const char *model, char *err,
                             size_t cap) {
  try {
    auto b = std::make_unique<OrtBackend>();
    b->library = dlopen(lib, RTLD_NOW | RTLD_LOCAL);
    if (!b->library)
      throw std::runtime_error(dlerror());
    auto get = reinterpret_cast<const OrtApiBase *(*)()>(
        dlsym(b->library, "OrtGetApiBase"));
    if (!get)
      throw std::runtime_error("missing OrtGetApiBase");
    b->api = get()->GetApi(ORT_API_VERSION);
    if (!b->api)
      throw std::runtime_error("ORT does not support API23");
    b->check(b->api->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "quoridor", &b->env));
    OrtSessionOptions *options = nullptr;
    b->check(b->api->CreateSessionOptions(&options));
    auto option_guard =
        std::unique_ptr<OrtSessionOptions, void (*)(OrtSessionOptions *)>(
            options, b->api->ReleaseSessionOptions);
    b->check(b->api->SetIntraOpNumThreads(options, 1));
    b->check(b->api->SetInterOpNumThreads(options, 1));
    b->check(b->api->SetSessionExecutionMode(options, ORT_SEQUENTIAL));
    b->check(b->api->SetSessionGraphOptimizationLevel(options, ORT_ENABLE_ALL));
    b->check(b->api->CreateSession(b->env, model, options, &b->session));
    b->check(b->api->CreateCpuMemoryInfo(OrtArenaAllocator, OrtMemTypeDefault,
                                         &b->memory));
    OrtAllocator *allocator = nullptr;
    b->check(b->api->GetAllocatorWithDefaultOptions(&allocator));
    size_t inputs = 0, outputs = 0;
    b->check(b->api->SessionGetInputCount(b->session, &inputs));
    b->check(b->api->SessionGetOutputCount(b->session, &outputs));
    if (inputs != 1 || outputs != 2)
      throw std::runtime_error(
          "expected one feature input and policy/value outputs");
    char *name = nullptr;
    b->check(b->api->SessionGetInputName(b->session, 0, allocator, &name));
    b->input_name = name;
    allocator->Free(allocator, name);
    for (size_t i = 0; i < outputs; i++) {
      name = nullptr;
      b->check(b->api->SessionGetOutputName(b->session, i, allocator, &name));
      b->output_names.emplace_back(name);
      allocator->Free(allocator, name);
    }
    return b.release();
  } catch (const std::exception &e) {
    error(err, cap, e);
    return nullptr;
  }
}
extern "C" int qort_run(void *ptr, const float *input, size_t batch,
                        float *output, char *err, size_t cap) {
  auto &b = *static_cast<OrtBackend *>(ptr);
  try {
    // Fixed batch-one teacher model: serialize samples within one held native
    // session.
    for (size_t row = 0; row < batch; row++) {
      OrtValue *raw = nullptr;
      const int64_t dims[4] = {1, 8, 9, 9};
      b.check(b.api->CreateTensorWithDataAsOrtValue(
          b.memory, const_cast<float *>(input + row * 648), 648 * sizeof(float),
          dims, 4, ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT, &raw));
      auto input_guard = std::unique_ptr<OrtValue, void (*)(OrtValue *)>(
          raw, b.api->ReleaseValue);
      const OrtValue *inputs[] = {raw};
      const char *in[] = {b.input_name.c_str()};
      const char *names[] = {b.output_names[0].c_str(),
                             b.output_names[1].c_str()};
      OrtValue *results[2] = {nullptr, nullptr};
      b.counts.executed_rows += 1;
      OrtStatus *status =
          b.api->Run(b.session, nullptr, in, inputs, 1, names, 2, results);
      auto r0 = std::unique_ptr<OrtValue, void (*)(OrtValue *)>(
          results[0], b.api->ReleaseValue);
      auto r1 = std::unique_ptr<OrtValue, void (*)(OrtValue *)>(
          results[1], b.api->ReleaseValue);
      b.check(status);
      bool seen_policy = false, seen_value = false;
      for (auto value : results) {
        OrtTensorTypeAndShapeInfo *info = nullptr;
        b.check(b.api->GetTensorTypeAndShape(value, &info));
        auto guard = std::unique_ptr<OrtTensorTypeAndShapeInfo,
                                     void (*)(OrtTensorTypeAndShapeInfo *)>(
            info, b.api->ReleaseTensorTypeAndShapeInfo);
        size_t size = 0;
        ONNXTensorElementDataType type;
        b.check(b.api->GetTensorShapeElementCount(info, &size));
        b.check(b.api->GetTensorElementType(info, &type));
        if (type != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT)
          throw std::runtime_error("non-f32 output");
        void *data = nullptr;
        b.check(b.api->GetTensorMutableData(value, &data));
        if (size == 136 && !seen_policy) {
          memcpy(output + row * 137, data, 136 * sizeof(float));
          seen_policy = true;
        } else if (size == 1 && !seen_value) {
          output[row * 137 + 136] = *static_cast<float *>(data);
          seen_value = true;
        } else
          throw std::runtime_error("invalid policy/value dimensions");
      }
      if (!seen_policy || !seen_value)
        throw std::runtime_error("missing output");
    }
    return 0;
  } catch (const std::exception &e) {
    error(err, cap, e);
    return -1;
  }
}
extern "C" void qort_counters(void *ptr, WorkCounts *counts) {
  *counts = static_cast<OrtBackend *>(ptr)->counts;
}
extern "C" void qort_destroy(void *ptr) {
  delete static_cast<OrtBackend *>(ptr);
}
