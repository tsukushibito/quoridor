#ifndef QUORIDOR_WORK_COUNTS_H
#define QUORIDOR_WORK_COUNTS_H
#include <cstdint>

// Layout shared with Rust NativeCounters. Counts include attempted model work.
struct WorkCounts {
  std::uint64_t executed_rows = 0;
  std::uint64_t warm_rows = 0;
  std::uint64_t failed_warm_rows = 0;
  std::uint64_t capture_unknown = 0;

  template <class Run>
  decltype(auto) warm_attempt(std::uint64_t rows, Run run) {
    warm_rows += rows;
    try {
      return run();
    } catch (...) {
      failed_warm_rows += rows;
      throw;
    }
  }
};
#endif
