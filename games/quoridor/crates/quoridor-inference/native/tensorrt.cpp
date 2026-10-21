// TensorRT native runtime. Stream/event and pinned buffers stay with one Rust
// owner.
#include "work_counts.h"
#include <NvInferRuntime.h>
#include <cstring>
#include <cuda_runtime_api.h>
#include <fstream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
static void cuda_check(cudaError_t status) {
  if (status != cudaSuccess)
    throw std::runtime_error(cudaGetErrorString(status));
}
static void reserve_vram() {
  size_t available = 0, total = 0;
  cuda_check(cudaMemGetInfo(&available, &total));
  if (available < static_cast<size_t>(2048) * 1024 * 1024)
    throw std::runtime_error("VRAM reserve would be breached");
}
struct Logger : nvinfer1::ILogger {
  std::string error;
  void log(Severity severity, const char *text) noexcept override {
    if (severity <= Severity::kERROR)
      error = text;
  }
};
struct TrtBatch {
  std::unique_ptr<nvinfer1::IExecutionContext> context;
  void *host_in = nullptr;
  void *host_p = nullptr;
  void *host_v = nullptr;
  void *gpu_in = nullptr;
  void *gpu_p = nullptr;
  void *gpu_v = nullptr;
  cudaGraph_t graph = nullptr;
  cudaGraphExec_t executable = nullptr;
  ~TrtBatch() {
    if (executable)
      cudaGraphExecDestroy(executable);
    if (graph)
      cudaGraphDestroy(graph);
    if (gpu_in)
      cudaFree(gpu_in);
    if (gpu_p)
      cudaFree(gpu_p);
    if (gpu_v)
      cudaFree(gpu_v);
    if (host_in)
      cudaFreeHost(host_in);
    if (host_p)
      cudaFreeHost(host_p);
    if (host_v)
      cudaFreeHost(host_v);
  }
};
struct OwnedStream {
  cudaStream_t ptr = nullptr;
  operator cudaStream_t() const { return ptr; }
  ~OwnedStream() {
    if (ptr) {
      cudaStreamSynchronize(ptr);
      cudaStreamDestroy(ptr);
    }
  }
};
struct TrtState {
  WorkCounts counts;
  Logger logger;
  std::unique_ptr<nvinfer1::IRuntime> runtime;
  std::unique_ptr<nvinfer1::ICudaEngine> engine;
  OwnedStream stream;
  int device;
  size_t maximum;
  bool capture;
  std::string input, policy, value;
  std::map<size_t, std::unique_ptr<TrtBatch>> batches;
  TrtState(const char *path, size_t limit, int dev, bool graph)
      : device(dev), maximum(limit), capture(graph) {
    cuda_check(cudaSetDevice(device));
    size_t available = 0, total = 0;
    cuda_check(cudaMemGetInfo(&available, &total));
    if (available < static_cast<size_t>(2560) * 1024 * 1024)
      throw std::runtime_error("insufficient free VRAM after 2 GiB reserve");
    cuda_check(cudaStreamCreateWithFlags(&stream.ptr, cudaStreamNonBlocking));
    std::ifstream file(path, std::ios::binary);
    if (!file)
      throw std::runtime_error("missing TensorRT engine");
    std::vector<char> data((std::istreambuf_iterator<char>(file)),
                           std::istreambuf_iterator<char>());
    runtime.reset(nvinfer1::createInferRuntime(logger));
    if (!runtime)
      throw std::runtime_error("TensorRT create runtime failed");
    engine.reset(runtime->deserializeCudaEngine(data.data(), data.size()));
    if (!engine)
      throw std::runtime_error("TensorRT engine deserialization failed: " +
                               logger.error);
    if (engine->getNbIOTensors() != 3)
      throw std::runtime_error("expected exactly 3 I/O tensors");
    for (int i = 0; i < engine->getNbIOTensors(); i++) {
      const char *name = engine->getIOTensorName(i);
      if (engine->getTensorDataType(name) != nvinfer1::DataType::kFLOAT)
        throw std::runtime_error("TensorRT I/O must be float32");
      auto dims = engine->getTensorShape(name);
      if (engine->getTensorIOMode(name) == nvinfer1::TensorIOMode::kINPUT) {
        if (dims.nbDims != 4 || dims.d[1] != 8 || dims.d[2] != 9 ||
            dims.d[3] != 9)
          throw std::runtime_error("invalid input dimensions");
        input = name;
      } else if (dims.nbDims == 2 && dims.d[1] == 136)
        policy = name;
      else if (dims.nbDims == 2 && dims.d[1] == 1)
        value = name;
      else
        throw std::runtime_error("invalid output dimensions");
    }
    if (input.empty() || policy.empty() || value.empty())
      throw std::runtime_error("missing policy/value tensor");
  }
  ~TrtState() {
    cudaSetDevice(device);
    if (stream)
      cudaStreamSynchronize(stream);
    batches.clear();
    engine.reset();
    runtime.reset();
  }
  TrtBatch &state(size_t batch) {
    auto it = batches.find(batch);
    if (it != batches.end())
      return *it->second;
    reserve_vram();
    auto s = std::make_unique<TrtBatch>();
    s->context.reset(engine->createExecutionContext());
    if (!s->context)
      throw std::runtime_error("create TensorRT context failed");
    cuda_check(cudaMallocHost(&s->host_in, batch * 648 * sizeof(float)));
    cuda_check(cudaMallocHost(&s->host_p, batch * 136 * sizeof(float)));
    cuda_check(cudaMallocHost(&s->host_v, batch * sizeof(float)));
    cuda_check(cudaMalloc(&s->gpu_in, batch * 648 * sizeof(float)));
    cuda_check(cudaMalloc(&s->gpu_p, batch * 136 * sizeof(float)));
    cuda_check(cudaMalloc(&s->gpu_v, batch * sizeof(float)));
    memset(s->host_in, 0, batch * 648 * sizeof(float));
    if (!s->context->setOptimizationProfileAsync(0, stream) ||
        !s->context->setInputShape(input.c_str(),
                                   nvinfer1::Dims4(batch, 8, 9, 9)) ||
        !s->context->setTensorAddress(input.c_str(), s->gpu_in) ||
        !s->context->setTensorAddress(policy.c_str(), s->gpu_p) ||
        !s->context->setTensorAddress(value.c_str(), s->gpu_v))
      throw std::runtime_error("TensorRT shape/address binding failed");
    auto run = [&](bool warming) {
      cuda_check(cudaMemcpyAsync(s->gpu_in, s->host_in,
                                 batch * 648 * sizeof(float),
                                 cudaMemcpyHostToDevice, stream));
      auto forward = [&] {
        if (!s->context->enqueueV3(stream))
          throw std::runtime_error("TensorRT enqueue failed");
      };
      if (warming)
        counts.warm_attempt(batch, forward);
      else
        forward();
      cuda_check(cudaMemcpyAsync(s->host_p, s->gpu_p,
                                 batch * 136 * sizeof(float),
                                 cudaMemcpyDeviceToHost, stream));
      cuda_check(cudaMemcpyAsync(s->host_v, s->gpu_v, batch * sizeof(float),
                                 cudaMemcpyDeviceToHost, stream));
    };
    run(true);
    cuda_check(cudaStreamSynchronize(stream));
    if (capture) {
      cuda_check(
          cudaStreamBeginCapture(stream, cudaStreamCaptureModeThreadLocal));
      try {
        counts.capture_unknown = 1;
        run(false);
        cuda_check(cudaStreamEndCapture(stream, &s->graph));
        cuda_check(cudaGraphInstantiate(&s->executable, s->graph, 0));
      } catch (...) {
        cudaGraph_t failed = nullptr;
        cudaStreamEndCapture(stream, &failed);
        if (failed)
          cudaGraphDestroy(failed);
        throw;
      }
    }
    reserve_vram();
    return *batches.emplace(batch, std::move(s)).first->second;
  }
};
static void fail(char *error, size_t cap, const std::exception &e) {
  if (cap) {
    strncpy(error, e.what(), cap - 1);
    error[cap - 1] = 0;
  }
}
extern "C" int qtrt_runtime_version() { return getInferLibVersion(); }
extern "C" void *qtrt_create(const char *path, size_t maximum, int device,
                             int graph, char *error, size_t cap) {
  try {
    auto state = std::make_unique<TrtState>(path, maximum, device, graph != 0);
    reserve_vram();
    return state.release();
  } catch (const std::exception &e) {
    fail(error, cap, e);
    return nullptr;
  }
}
extern "C" int qtrt_run(void *handle, const float *input, size_t batch,
                        float *output, char *error, size_t cap) {
  try {
    auto &a = *static_cast<TrtState *>(handle);
    if (batch == 0 || batch > a.maximum)
      throw std::runtime_error("batch outside bound");
    cuda_check(cudaSetDevice(a.device));
    auto &s = a.state(batch);
    memcpy(s.host_in, input, batch * 648 * sizeof(float));
    if (a.capture) {
      a.counts.executed_rows += batch;
      cuda_check(cudaGraphLaunch(s.executable, a.stream));
    } else {
      cuda_check(cudaMemcpyAsync(s.gpu_in, s.host_in,
                                 batch * 648 * sizeof(float),
                                 cudaMemcpyHostToDevice, a.stream));
      a.counts.executed_rows += batch;
      if (!s.context->enqueueV3(a.stream))
        throw std::runtime_error("TensorRT enqueue failed");
      cuda_check(cudaMemcpyAsync(s.host_p, s.gpu_p, batch * 136 * sizeof(float),
                                 cudaMemcpyDeviceToHost, a.stream));
      cuda_check(cudaMemcpyAsync(s.host_v, s.gpu_v, batch * sizeof(float),
                                 cudaMemcpyDeviceToHost, a.stream));
    }
    cuda_check(cudaStreamSynchronize(a.stream));
    for (size_t i = 0; i < batch; i++) {
      memcpy(output + i * 137, static_cast<float *>(s.host_p) + i * 136,
             136 * sizeof(float));
      output[i * 137 + 136] = static_cast<float *>(s.host_v)[i];
    }
    return 0;
  } catch (const std::exception &e) {
    fail(error, cap, e);
    return -1;
  }
}
extern "C" void qtrt_counters(void *handle, WorkCounts *counts) {
  *counts = static_cast<TrtState *>(handle)->counts;
}
extern "C" void qtrt_destroy(void *handle) {
  delete static_cast<TrtState *>(handle);
}
