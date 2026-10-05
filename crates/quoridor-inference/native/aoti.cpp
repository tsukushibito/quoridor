// Thin LibTorch/CUDA ABI. A Rust owner holds this object and its
// stream/buffers.
#include <ATen/ATen.h>
#include <ATen/Context.h>
#include <ATen/cuda/CUDAGraph.h>
#include <c10/core/InferenceMode.h>
#include <c10/cuda/CUDAGuard.h>
#include <c10/cuda/CUDAStream.h>
#include <cstring>
#include <map>
#include <memory>
#include <stdexcept>
#include <torch/csrc/inductor/aoti_package/model_package_loader.h>
#include <torch/version.h>
static void reserve_vram() {
  size_t available = 0, total = 0;
  if (cudaMemGetInfo(&available, &total) != cudaSuccess ||
      available < static_cast<size_t>(2048) * 1024 * 1024)
    throw std::runtime_error("VRAM reserve would be breached");
}
struct BatchState {
  at::Tensor input_cpu, input_gpu, policy_cpu, value_cpu;
  std::vector<at::Tensor> output;
  std::unique_ptr<at::cuda::CUDAGraph> graph;
};
struct AotiState {
  int device;
  size_t max_batch;
  bool graph;
  c10::cuda::CUDAStream stream;
  torch::inductor::AOTIModelPackageLoader loader;
  std::map<size_t, std::unique_ptr<BatchState>> batches;
  AotiState(const char *package, size_t maximum, int dev, bool capture)
      : device(dev), max_batch(maximum), graph(capture),
        stream(c10::cuda::getStreamFromPool(false, dev)),
        loader(package, "model", true, 1, dev) {}
  ~AotiState() {
    try {
      stream.synchronize();
    } catch (...) {
    }
  }
  BatchState &state(size_t batch) {
    auto it = batches.find(batch);
    if (it != batches.end())
      return *it->second;
    reserve_vram();
    auto s = std::make_unique<BatchState>();
    auto cpu = at::TensorOptions()
                   .dtype(at::kFloat)
                   .device(at::kCPU)
                   .pinned_memory(true);
    s->input_cpu = at::zeros({static_cast<int64_t>(batch), 8, 9, 9}, cpu);
    s->input_gpu = at::empty({static_cast<int64_t>(batch), 8, 9, 9},
                             at::TensorOptions()
                                 .dtype(at::kFloat)
                                 .device(at::Device(at::kCUDA, device)));
    s->policy_cpu = at::empty({static_cast<int64_t>(batch), 136}, cpu);
    s->value_cpu = at::empty({static_cast<int64_t>(batch), 1}, cpu);
    auto run = [&] {
      s->input_gpu.copy_(s->input_cpu, true);
      s->output = loader.run({s->input_gpu}, stream.stream());
      if (s->output.size() != 2 ||
          s->output[0].numel() != static_cast<int64_t>(batch * 136) ||
          s->output[1].numel() != static_cast<int64_t>(batch))
        throw std::runtime_error("AOTI output shape mismatch");
      s->policy_cpu.copy_(s->output[0], true);
      s->value_cpu.copy_(s->output[1], true);
    };
    run();
    run();
    stream.synchronize();
    if (graph) {
      s->graph = std::make_unique<at::cuda::CUDAGraph>();
      s->graph->capture_begin();
      try {
        run();
        s->graph->capture_end();
        stream.synchronize();
      } catch (...) {
        cudaStreamCaptureStatus status = cudaStreamCaptureStatusNone;
        if (cudaStreamIsCapturing(stream.stream(), &status) == cudaSuccess &&
            status != cudaStreamCaptureStatusNone) {
          try {
            s->graph->capture_end();
          } catch (...) {
            cudaGraph_t abandoned = nullptr;
            cudaStreamEndCapture(stream.stream(), &abandoned);
            if (abandoned)
              cudaGraphDestroy(abandoned);
          }
        }
        s->graph.reset();
        throw;
      }
    }
    try {
      reserve_vram();
    } catch (...) {
      s.reset();
      c10::cuda::CUDACachingAllocator::emptyCache();
      throw;
    }
    return *batches.emplace(batch, std::move(s)).first->second;
  }
};
static void fail(char *err, size_t cap, const std::exception &e) {
  if (cap) {
    strncpy(err, e.what(), cap - 1);
    err[cap - 1] = 0;
  }
}
extern "C" const char *qaoti_runtime_version() { return TORCH_VERSION; }
extern "C" void *qaoti_create(const char *package, size_t maximum, int device,
                              int graph, char *err, size_t cap) {
  try {
    if (maximum == 0 || maximum > 4096)
      throw std::runtime_error("invalid maximum batch");
    int devices = 0;
    if (cudaGetDeviceCount(&devices) != cudaSuccess || device < 0 ||
        device >= devices)
      throw std::runtime_error("CUDA device unavailable");
    c10::cuda::CUDAGuard guard(device);
    size_t available = 0, total = 0;
    if (cudaMemGetInfo(&available, &total) != cudaSuccess ||
        available < static_cast<size_t>(2560) * 1024 * 1024)
      throw std::runtime_error("insufficient free VRAM after 2 GiB reserve");
    at::globalContext().setAllowTF32CuBLAS(false);
    at::globalContext().setAllowTF32CuDNN(false);
    at::globalContext().setBenchmarkCuDNN(false);
    auto state =
        std::make_unique<AotiState>(package, maximum, device, graph != 0);
    reserve_vram();
    return state.release();
  } catch (const std::exception &e) {
    fail(err, cap, e);
    return nullptr;
  }
}
extern "C" int qaoti_run(void *ptr, const float *input, size_t batch,
                         float *output, char *err, size_t cap) {
  try {
    auto &a = *static_cast<AotiState *>(ptr);
    if (batch == 0 || batch > a.max_batch)
      throw std::runtime_error("batch outside package bound");
    c10::InferenceMode inference;
    c10::cuda::CUDAStreamGuard guard(a.stream);
    auto &s = a.state(batch);
    memcpy(s.input_cpu.data_ptr<float>(), input, batch * 648 * sizeof(float));
    if (a.graph) {
      s.graph->replay();
    } else {
      s.input_gpu.copy_(s.input_cpu, true);
      s.output = a.loader.run({s.input_gpu}, a.stream.stream());
      s.policy_cpu.copy_(s.output[0], true);
      s.value_cpu.copy_(s.output[1], true);
    }
    // Synchronize only this owned stream before CPU reads; never synchronize
    // the device.
    a.stream.synchronize();
    auto p = s.policy_cpu.data_ptr<float>();
    auto v = s.value_cpu.data_ptr<float>();
    for (size_t row = 0; row < batch; row++) {
      memcpy(output + row * 137, p + row * 136, 136 * sizeof(float));
      output[row * 137 + 136] = v[row];
    }
    return 0;
  } catch (const std::exception &e) {
    fail(err, cap, e);
    return -1;
  }
}
extern "C" void qaoti_destroy(void *ptr) {
  delete static_cast<AotiState *>(ptr);
}
