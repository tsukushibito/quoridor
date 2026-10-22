// SPDX-License-Identifier: GPL-3.0-or-later
// External numerical oracle for Egaroucid Console7.8.1, by Takuto Yamana.
// Links unchanged upstream headers; never part of the product engine.
// Generic: -DHAS_NO_AVX2. Actual pinned AVX2: -DEGAROUCID_ORACLE_SIMD -march=x86-64-v3.
#if defined(EGAROUCID_ORACLE_SIMD)
#if defined(HAS_NO_AVX2) || defined(HAS_ARM_PROCESSOR) || defined(HAS_AVX512)
#error "Actual SIMD profile requires the pinned x86 AVX2 backend, without scalar/ARM/AVX512"
#endif
#ifndef __AVX2__
#error "Actual SIMD profile requires AVX2 compiler targeting (-march=x86-64-v3)"
#endif
#elif !defined(HAS_NO_AVX2)
#error "Select generic (-DHAS_NO_AVX2) or actual SIMD (-DEGAROUCID_ORACLE_SIMD) explicitly"
#endif

#include <algorithm>
#include <bit>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#include "engine/evaluate.hpp"
#include "console/lib/json.hpp"

namespace egaroucid_oracle {
using json = nlohmann::json;
using Clock = std::chrono::steady_clock;
constexpr const char* ENGINE_COMMIT = "570d5e0a478c9d720d75de06a5d31995f412704a";
constexpr const char* PROTOCOL = "egaroucid-static-eval-v1";
#if defined(EGAROUCID_ORACLE_SIMD)
constexpr const char* LABEL = "Console7.8.1-engine + original AVX2 static-evaluation oracle";
constexpr const char* IMPLEMENTATION = "evaluate_simd.hpp";
#if !USE_SIMD_EVALUATION
#error "Actual SIMD profile did not select the pinned AVX2 evaluation implementation"
#endif
#else
constexpr const char* LABEL = "Console7.8.1-engine + scalar static-evaluation oracle";
constexpr const char* IMPLEMENTATION = "evaluate_generic.hpp";
#endif
constexpr size_t LINE_BYTES = 16384;
constexpr int COMPRESSED_TOKENS = 19121911;
constexpr std::streamoff EVAL_BYTES = 38243826;
constexpr std::streamoff ORDERING_BYTES = 472392;
constexpr const char* EVAL_SHA256 =
    "0a8acbcbc23067933627f1bcc83c3f7ae6b7ff3e603d174a3364271fcaeeef2f";
constexpr const char* ORDERING_SHA256 =
    "bd908885e8bb85e72a9be2b0399f8ca52ed40a138bcaaecca3d13710945b9a93";

static_assert(N_PATTERNS == 16 && N_PATTERN_FEATURES == 64);
static_assert(N_PHASES == 60 && PHASE_N_DISCS == 1 && STEP == 32 && STEP_2 == 16);
static_assert(sizeof(int) == 4 && sizeof(int16_t) == 2 && sizeof(short) == 2);
static_assert(std::endian::native == std::endian::little);
#if defined(EGAROUCID_ORACLE_SIMD)
static_assert(N_EVAL_VECTORS == 4 && CEIL_N_PATTERN_FEATURES == 64);
static_assert(N_PATTERN_PARAMS_RAW == 612360 && SIMD_EVAL_MAX_VALUE == 4092);
static_assert(SIMD_EVAL_MAX_VALUE_MO_END == 16380 && sizeof(__m256i) == 32);
#endif

struct Initialization {
    std::string eval_path;
    std::string ordering_path;
    double setup_ms = 0;
    double load_ms = 0;
    double total_ms = 0;
};

// Cheap framing checks only. SHA256 verification belongs to the existing caller's
// checked immutable FileRefs BEFORE launching; expected hashes are not measurements.
void check_weight_header(const char* path, std::streamoff expected_bytes, bool compressed) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file || file.tellg() != expected_bytes) {
        throw std::invalid_argument("weight file length differs from pinned identity");
    }
    if (compressed) {
        int count = 0;
        file.seekg(0);
        file.read(reinterpret_cast<char*>(&count), sizeof(count));
        if (!file || count != COMPRESSED_TOKENS) {
            throw std::invalid_argument("compressed token header differs from pinned identity");
        }
    }
}

Board read_board(const json& state) {
    if (!state.is_object() || state.size() != 3 || !state.contains("board")
        || !state.contains("version") || !state.contains("toMove")
        || !state.at("version").is_number_integer() || state.at("version") != 1
        || !state.at("toMove").is_number_integer()) {
        throw std::invalid_argument("state requires exactly version=1, board, integer toMove");
    }
    if (state.at("toMove") != 1 && state.at("toMove") != 2) {
        throw std::invalid_argument("side must be 1 or 2");
    }
    const int side = state.at("toMove").get<int>();
    const auto& cells = state.at("board");
    if ((side != 1 && side != 2) || !cells.is_array() || cells.size() != HW2) {
        throw std::invalid_argument("state board/side");
    }
    Board board(0ULL, 0ULL);
    for (int i = 0; i < HW2; ++i) {
        if (!cells[i].is_number_integer() || cells[i] < 0 || cells[i] > 2) {
            throw std::invalid_argument("cells must be integers in [0,2]");
        }
        const int cell = cells[i].get<int>();
        if (cell == side) {
            board.player |= 1ULL << (63 - i);
        } else if (cell != 0) {
            board.opponent |= 1ULL << (63 - i);
        }
    }
    if (board.n_discs() < 4) {
        throw std::invalid_argument("at least four occupied squares required");
    }
    return board;
}

json evaluate(const json& state) {
    Board board = read_board(state);
    Board passed = board;
    passed.pass();
    const bool no_legal = board.get_legal() == 0;
    const bool terminal = no_legal && passed.get_legal() == 0;
    const int discs = board.n_discs();
    json result = {{"ok", true}, {"protocol", PROTOCOL}, {"state", state},
        {"engineCommit", ENGINE_COMMIT}, {"scorePerspective", "state.toMove"},
        {"scoreUnits", "engine-disc"}, {"stepPerDisc", STEP},
        {"occupied", discs}, {"phase", discs - 4}, {"terminal", terminal},
        {"mustPass", no_legal && !terminal},
        {"stmDiscCount", board.count_player()},
        {"stmActualDiscDifference", board.count_player() - board.count_opponent()}};
#if defined(EGAROUCID_ORACLE_SIMD)
    result.update({{"evaluationImplementation", IMPLEMENTATION},
        {"compiledBackend", "upstream-avx2"}, {"simdPackedFeatures", nullptr}});
#endif
    // Never index phase 60 (full board) or evaluate an early terminal heuristically.
    // Terminal winner-empty scoring is explicitly separate from actual disc difference.
    if (terminal) {
        result.update({{"evaluationKind", "terminal_winner_empties"},
            {"tablePhase", nullptr}, {"patternIndices", nullptr},
            {"patternTermsStep", nullptr}, {"patternSumsStep", nullptr},
            {"patternSumStep", nullptr}, {"discCountTermStep", nullptr},
            {"rawTotalStep", nullptr}, {"roundingBiasStep", nullptr},
            {"biasedTotalStep", nullptr}, {"roundedDiscScore", nullptr},
            {"cappedDiscScore", nullptr}, {"endOrdering", nullptr},
            {"score", end_evaluate(&board)}});
        return result;
    }
    Search search(&board);
    const int phase = search.phase();
    if (phase < 0 || phase >= N_PHASES) {
        throw std::runtime_error("nonterminal phase outside original tables");
    }
#if defined(EGAROUCID_ORACLE_SIMD)
    auto& features = search.eval.features[search.eval.feature_idx];
    json indices = json::array(), terms = json::array(), packed = json::array();
    int sums[N_PATTERNS] = {};
    int diagnostic_sum = 0;
    // Inspect actual original feature vectors, not a recomputation from board cells.
    // _mm256_set_epi16 in the original initializer puts source occurrence0 in lane15.
    // Simple groups0/1 carry pattern_starts offsets; compressed groups2/3 do not.
    for (int group = 0; group < N_EVAL_VECTORS; ++group) {
        uint16_t lanes[16];
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(lanes), features.f256[group]);
        for (int local = 0; local < 16; ++local) {
            const int occurrence = group * 16 + local;
            const int shape = occurrence / 4; // Four original occurrences per shape.
            const int stored = lanes[15 - local];
            const int index = stored - (group < 2 ? pattern_starts[shape] : 0);
            const int size = static_cast<int>(pow3[feature_to_coord[occurrence].n_cells]);
            if (index < 0 || index >= size) {
                throw std::runtime_error("original SIMD feature outside source shape domain");
            }
            // These are the same three bases used by original calc_pattern gathers.
            const int base = shape == 4 || shape == 5 ? PATTERN4_START_IDX
                : shape == 6 || shape == 7 ? PATTERN6_START_IDX : 0;
            const int address = base + pattern_starts[shape] + index;
            if (address < 1 || address >= N_PATTERN_PARAMS) {
                throw std::runtime_error("original SIMD table address outside domain");
            }
            // Original loader clips and biases each entry. Expose that loaded term;
            // never recover a supposed raw value by inverting a rounded score.
            const int value = pattern_arr[phase][address] - SIMD_EVAL_MAX_VALUE;
            indices.push_back(index);
            packed.push_back(stored);
            terms.push_back(value);
            sums[shape] += value;
            diagnostic_sum += value;
        }
    }
    const int pattern = calc_pattern(phase, &features); // Genuine original AVX2 gather.
    if (diagnostic_sum != pattern) {
        throw std::runtime_error("SIMD diagnostic terms disagree with original raw call");
    }
    result["simdPackedFeatures"] = packed;
#else
    const int slot = search.eval.feature_idx;
    const int reversed = search.eval.reversed[slot];
    json indices = json::array(), terms = json::array();
    int sums[N_PATTERNS] = {};
    for (int i = 0; i < N_PATTERN_FEATURES; ++i) {
        const int pattern = feature_to_pattern[i];
        const int index = search.eval.features[slot][i];
        const int value = pattern_arr[reversed][phase][pattern][index];
        indices.push_back(index);
        terms.push_back(value);
        sums[pattern] += value;
    }
    const int pattern = calc_pattern(phase, &search.eval);
#endif
    const int count_term = eval_num_arr[phase][board.count_player()];
    const int raw = pattern + count_term;
    const int bias = raw >= 0 ? STEP_2 : -STEP_2;
    const int rounded = (raw + bias) / STEP; // C++ truncation, including negative ties.
    const int capped = std::clamp(rounded, -SCORE_MAX, SCORE_MAX);
    const int original = mid_evaluate(&board);
    if (capped != original || capped != mid_evaluate_diff(&search)) {
        throw std::runtime_error("original evaluator disagrees with exposed terms");
    }
#if defined(EGAROUCID_ORACLE_SIMD)
    const int ordering_raw = calc_pattern_move_ordering_end(&features);
#else
    const int ordering_raw = calc_pattern_move_ordering_end(&search.eval);
#endif
    const int ordering_bias = ordering_raw >= 0 ? STEP_2 : -STEP_2;
    const int ordering_disc = mid_evaluate_move_ordering_end(&search);
    if ((ordering_raw + ordering_bias) / STEP != ordering_disc) {
        throw std::runtime_error("original ordering evaluation disagrees with exposed terms");
    }
    result.update({{"evaluationKind", "heuristic"}, {"tablePhase", phase},
        {"patternIndices", indices}, {"patternTermsStep", terms},
        {"patternSumsStep", sums}, {"patternSumStep", pattern},
        {"stmDiscCount", board.count_player()}, {"discCountTermStep", count_term},
        {"rawTotalStep", raw}, {"roundingBiasStep", bias},
        {"biasedTotalStep", raw + bias}, {"roundedDiscScore", rounded},
        {"cappedDiscScore", capped}, {"score", original},
        {"endOrdering", {{"rawTotalStep", ordering_raw},
            {"roundingBiasStep", ordering_bias}, {"discScore", ordering_disc},
            {"clamped", false}}}});
    return result;
}

json request(const json& input, const Initialization& init) {
    if (!input.is_object() || !input.contains("op") || !input.at("op").is_string()) {
        throw std::invalid_argument("object with string op required");
    }
    const std::string op = input.at("op").get<std::string>();
    if (op == "info" && input.size() == 1) {
        json info = {{"ok", true}, {"protocol", PROTOCOL}, {"label", LABEL},
            {"engineCommit", ENGINE_COMMIT}, {"engineTag", "console_v7.8.1"},
            {"evaluationImplementation", IMPLEMENTATION},
            {"search", false}, {"book", false}, {"ponder", false},
            {"workerPool", thread_pool.size()}, {"libraryThreads", 1},
            {"stepPerDisc", STEP}, {"patterns", N_PATTERNS},
            {"occurrences", N_PATTERN_FEATURES}, {"phases", N_PHASES},
            {"identityVerification", "caller-must-verify-FileRef-before-launch"},
            {"expectedWeights", {{{"path", init.eval_path}, {"bytes", EVAL_BYTES},
                {"sha256", EVAL_SHA256}}, {{"path", init.ordering_path},
                {"bytes", ORDERING_BYTES}, {"sha256", ORDERING_SHA256}}}},
            {"initialization", {{"setupMs", init.setup_ms}, {"loadMs", init.load_ms},
                {"totalMs", init.total_ms}}}};
#if defined(EGAROUCID_ORACLE_SIMD)
        info.update({{"compiledBackend", "upstream-avx2"},
            {"mainEntryClip", SIMD_EVAL_MAX_VALUE},
            {"orderingEntryClip", SIMD_EVAL_MAX_VALUE_MO_END},
            {"packedFeatureDomain", "logical-source-order; groups0/1 include offsets"}});
#endif
        return info;
    }
    if (op != "evaluate" || input.size() != 2 || !input.contains("state")) {
        throw std::invalid_argument("only info or evaluate with state is supported");
    }
    return evaluate(input.at("state"));
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

Initialization initialize(const char* eval, const char* ordering) {
    const auto start = Clock::now();
    check_weight_header(eval, EVAL_BYTES, true);
    check_weight_header(ordering, ORDERING_BYTES, false);
    thread_pool.resize(0);
    bit_init();
    mobility_init();
    const auto ready = Clock::now();
    // Original loader and tables, once per process. No TT/search/book initialization.
    if (!evaluate_init(eval, ordering, true)) {
        throw std::runtime_error("original evaluation loader failed");
    }
    const auto loaded = Clock::now();
    return {eval, ordering, elapsed_ms(start, ready), elapsed_ms(ready, loaded),
        elapsed_ms(start, loaded)};
}

int serve(std::istream& input, std::ostream& output, const Initialization& init) {
    char line[LINE_BYTES];
    for (;;) {
        input.getline(line, sizeof(line));
        if (input.eof() && input.gcount() == 0) {
            return 0;
        }
        try {
            if (!input || input.eof()) {
                throw std::invalid_argument("oversized or incomplete JSONL frame");
            }
            const auto length = input.gcount() - 1; // Delimiter counted by getline.
            if (std::find(line, line + length, '\0') != line + length) {
                throw std::invalid_argument("embedded NUL in JSONL frame");
            }
            output << request(json::parse(line), init).dump() << std::endl;
        } catch (const std::exception& error) {
            output << json({{"ok", false}, {"protocol", PROTOCOL},
                {"error", error.what()}}).dump() << std::endl;
            return 1; // First failure stops; no retries, replacement states or search.
        }
    }
}
} // namespace egaroucid_oracle

#ifndef EGAROUCID_ORACLE_NO_MAIN
int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::invalid_argument("usage: oracle EVAL_FILE MOVE_ORDERING_EVAL_FILE");
        }
        const auto init = egaroucid_oracle::initialize(argv[1], argv[2]);
        return egaroucid_oracle::serve(std::cin, std::cout, init);
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
#endif
