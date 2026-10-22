// SPDX-License-Identifier: GPL-3.0-or-later
// New actual-AVX2 backend boundary fixtures only; no generic suite or real weights.
// Authored source only. Root owns finite compile/runtime admission.
#ifndef EGAROUCID_ORACLE_SIMD
#error "These fixtures require the explicitly selected actual SIMD profile"
#endif
#define EGAROUCID_ORACLE_NO_MAIN
#include "../tools/egaroucid-eval-oracle.cpp"

#include <vector>

using namespace egaroucid_oracle;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

json synthetic_state() {
    std::vector<int> cells(64, 0);
    cells[27] = cells[36] = 2;
    cells[28] = cells[35] = 1;
    // Deliberately asymmetric synthetic input for lane/coordinate diagnostics,
    // without asserting that this board was reached by a legal trajectory.
    cells[0] = 1;
    cells[9] = 2;
    return {{"version", 1}, {"board", cells}, {"toMove", 2}};
}

void backend_identity() {
    const auto info = request({{"op", "info"}}, Initialization{});
    require(info["evaluationImplementation"] == "evaluate_simd.hpp"
        && info["compiledBackend"] == "upstream-avx2"
        && info["label"] == "Console7.8.1-engine + original AVX2 static-evaluation oracle",
        "actual compiled backend identity");
    require(info["workerPool"] == 0 && info["search"] == false
        && info["book"] == false && info["ponder"] == false, "static single-thread domain");
    require(info["mainEntryClip"] == SIMD_EVAL_MAX_VALUE
        && info["orderingEntryClip"] == SIMD_EVAL_MAX_VALUE_MO_END, "original entry clips");
    require(info["identityVerification"] == "caller-must-verify-FileRef-before-launch",
        "reported expected hashes are not measured identity");
}

void packing_and_original_calls() {
    const json state = synthetic_state();
    Board board = read_board(state);
    const int phase = board.n_discs() - 4;
    // Fill only the synthetic in-memory phase with small distinct loaded terms.
    // Neither real payload nor its loader is invoked by these focused fixtures.
    for (int address = 1; address < N_PATTERN_PARAMS; ++address) {
        pattern_arr[phase][address] = SIMD_EVAL_MAX_VALUE + (address % 65) - 32;
    }
    for (int address = 1; address < N_PATTERN_PARAMS_MO_END; ++address) {
        pattern_move_ordering_end_arr[address] = SIMD_EVAL_MAX_VALUE_MO_END
            + (address % 31) - 15;
    }
    eval_num_arr[phase][board.count_player()] = -17;
    const auto result = evaluate(state);
    require(result["compiledBackend"] == "upstream-avx2"
        && result["simdPackedFeatures"].size() == 64, "actual vector diagnostics present");
    // Independent reference for packing, using the pinned coordinate definitions.
    // This is a fixture check, never the oracle's evaluator or rules authority.
    int cells[HW2 + 1];
    board.translate_to_arr_player_rev(cells);
    cells[COORD_NO] = 0;
    for (int i = 0; i < N_PATTERN_FEATURES; ++i) {
        int expected = 0;
        for (int j = 0; j < feature_to_coord[i].n_cells; ++j) {
            expected = expected * 3 + cells[feature_to_coord[i].cells[j]];
        }
        require(result["patternIndices"][i] == expected, "full64 actual packed index order");
        const int offset = i < 32 ? pattern_starts[i / 4] : 0;
        require(result["simdPackedFeatures"][i] == expected + offset,
            "simple/complex packed offset distinction");
    }
    Search original(&board);
    auto* features = &original.eval.features[original.eval.feature_idx];
    require(result["patternSumStep"] == calc_pattern(phase, features), "original raw AVX2 call");
    require(result["discCountTermStep"] == -17, "unmodified auxiliary term");
    require(result["endOrdering"]["rawTotalStep"] == calc_pattern_move_ordering_end(features),
        "original ordering raw call");
    require(result["score"] == mid_evaluate(&board)
        && result["score"] == mid_evaluate_diff(&original), "original score calls");
    require(result["endOrdering"]["discScore"] == mid_evaluate_move_ordering_end(&original),
        "original ordering score call");
}

void terminal_backend_domain() {
    const json state = {{"version", 1}, {"board", std::vector<int>(64, 1)}, {"toMove", 2}};
    const auto result = evaluate(state);
    require(result["compiledBackend"] == "upstream-avx2"
        && result["evaluationImplementation"] == "evaluate_simd.hpp", "terminal backend identity");
    require(result["simdPackedFeatures"].is_null() && result["patternIndices"].is_null()
        && result["tablePhase"].is_null(), "terminal bypasses actual SIMD feature arrays");
}

int main() {
    try {
        thread_pool.resize(0);
        bit_init();
        mobility_init();
        pre_calculate_eval_constant(); // Original SIMD constants, once; no weight load.
        backend_identity();
        packing_and_original_calls();
        terminal_backend_domain();
        std::cout << "actual SIMD backend synthetic fixtures PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
