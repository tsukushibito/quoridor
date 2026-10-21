// SPDX-License-Identifier: GPL-3.0-or-later
// External numerical oracle for Egaroucid Console7.8.1, by Takuto Yamana.
// Links unchanged upstream headers; never part of the product engine.
// Build only with the pinned source include root and -DHAS_NO_AVX2.
#ifndef HAS_NO_AVX2
#error "This oracle requires the original scalar evaluator (-DHAS_NO_AVX2)"
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
constexpr const char* LABEL = "Console7.8.1-engine + scalar static-evaluation oracle";
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
    const int count_term = eval_num_arr[phase][board.count_player()];
    const int raw = pattern + count_term;
    const int bias = raw >= 0 ? STEP_2 : -STEP_2;
    const int rounded = (raw + bias) / STEP; // C++ truncation, including negative ties.
    const int capped = std::clamp(rounded, -SCORE_MAX, SCORE_MAX);
    const int original = mid_evaluate(&board);
    if (capped != original || capped != mid_evaluate_diff(&search)) {
        throw std::runtime_error("original evaluator disagrees with exposed terms");
    }
    const int ordering_raw = calc_pattern_move_ordering_end(&search.eval);
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
        return {{"ok", true}, {"protocol", PROTOCOL}, {"label", LABEL},
            {"engineCommit", ENGINE_COMMIT}, {"engineTag", "console_v7.8.1"},
            {"evaluationImplementation", "evaluate_generic.hpp"},
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
