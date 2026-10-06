// Model-free coverage of the exact native warm-attempt bookkeeping.
#include "../native/work_counts.h"
#include <cassert>
#include <stdexcept>

int main() {
  WorkCounts counts;
  auto forward = [] { return 42; };
  assert(counts.warm_attempt(8, forward) == 42);
  assert(counts.warm_attempt(8, forward) == 42);
  assert(counts.warm_rows == 16);
  assert(counts.failed_warm_rows == 0);
  try {
    counts.warm_attempt(3, []() -> int {
      throw std::runtime_error("partial initialization failure");
    });
    assert(false);
  } catch (const std::runtime_error &) {
  }
  assert(counts.warm_rows == 19);
  assert(counts.failed_warm_rows == 3);
  counts.warm_attempt(3, [] {});
  assert(counts.warm_rows == 22);
  assert(counts.failed_warm_rows == 3);
}
