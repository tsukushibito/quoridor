// SPDX-License-Identifier: GPL-3.0-or-later
// New selective profile boundary definitions only; execution is Root-owned UNRUN.
#ifndef EGAROUCID_SEARCH_ORACLE_SELECTIVE
#error "These boundary fixtures require the selective fixed-depth profile"
#endif
#define EGAROUCID_SEARCH_ORACLE_NO_MAIN
#include "../tools/egaroucid-search-oracle.cpp"

namespace reference = egaroucid_search_oracle;
using json = nlohmann::json;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template<typename F>
void rejects(F action) {
    bool rejected = false;
    try {
        action();
    } catch (const std::exception&) {
        rejected = true;
    }
    require(rejected, "unsupported or unbound selective request accepted");
}

int main() {
    try {
        static_assert(USE_MID_MPC && USE_MPC_PRE_CALCULATION && MPC_100_LEVEL == 6);
        for (int level = 0; level < N_SELECTIVITY_LEVEL; ++level) {
            json input = {{"fixedDepth", 4}, {"selectivity", level}, {"mpc", true}};
            const auto parsed = reference::read_options(input);
            require(parsed.depth == 4 && parsed.selectivity == level, "actual root level binding");
            input["mpc"] = false;
            rejects([&] { reference::read_options(input); });
        }
        for (const json bad : {json(-1), json(7), json(6.0), json(true), json(4294967296ULL)}) {
            const json input = {{"fixedDepth", 4}, {"selectivity", bad}, {"mpc", true}};
            rejects([&] { reference::read_options(input); });
        }
        json input = {{"fixedDepth", 4}, {"selectivity", 6}, {"mpc", true}};
        input.erase("selectivity");
        rejects([&] { reference::read_options(input); });
        input = {{"fixedDepth", 4}, {"selectivity", 6}, {"mpc", true}, {"etc", false}};
        rejects([&] { reference::read_options(input); });
        reference::Session unbound;
        rejects([&] { reference::require_mpc_binding(unbound); });
        rejects([&] { reference::require_original_center(Board(0, 0)); });
        reference::require_original_center(Board(LEGAL_UNDEFINED, 0));
        require(!reference::completed_proven(false) && !reference::completed_proven(true),
            "selective profile, including root6, cannot promote end-depth to proven");
        require(std::string(reference::completed_kind(true))
            == "engine_selective_end_estimate_winner_empties_stm", "end estimate kind");
        const auto flags = reference::controls();
        require(flags["compiledMpc"] == true && flags["selectivity"].is_null()
            && flags["orderingSelectivity"] == MPC_74_LEVEL, "actual compile/ordering domain");
        require(std::string(reference::PROFILE) == "original-avx2-selective-fixed-depth",
            "profile distinct from compile-OFF");
        // No initialize/mpc_init/info-table iteration/clear/Search calls in this body.
        // Original linked global constructors still require Root runtime admission.
        std::cout << "selective fixed-depth new boundary fixtures PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
