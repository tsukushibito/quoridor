// SPDX-License-Identifier: GPL-3.0-or-later
// External fixed-depth reference for Console7.8.1 / Takuto Yamana.
// Original headers and the held evaluation oracle remain byte-identical.
#ifndef EGAROUCID_SEARCH_ORACLE_NONSELECTIVE
#error "Select the explicitly qualified fixed-depth MPC-off reference profile"
#endif
#ifndef EGAROUCID_ORACLE_SIMD
#error "This reference requires the original actual AVX2 evaluation profile"
#endif

#include "engine/setting.hpp"
// External comparison profile, not an upstream edit. Root level6 alone is not
// sufficient: original shallow ordering temporarily sets MPC_74_LEVEL internally.
#if !USE_MID_MPC
#error "Pinned upstream setting.hpp was expected to enable MID MPC before the override"
#endif
#undef USE_MID_MPC
#define USE_MID_MPC false

#define EGAROUCID_ORACLE_NO_MAIN
#include "egaroucid-eval-oracle.cpp"
#include "engine/engine_all.hpp"

namespace egaroucid_search_oracle {
using json = nlohmann::json;
using Clock = std::chrono::steady_clock;
constexpr const char* PROTOCOL = "egaroucid-fixed-depth-v1";
constexpr const char* PROFILE = "original-avx2-fixed-depth-mpc-off";
constexpr int HASH_LEVEL = 20;
constexpr uint32_t HASH_SEED = 20261022;
static_assert(MPC_100_LEVEL == 6 && !USE_MID_MPC);
static_assert(USE_END_PO && USE_END_SC && USE_MID_ETC && LAST_PO_OPTIMIZE);
static_assert(!USE_LAST4_SC && !USE_ASPIRATION_NEGASCOUT && !USE_KILLER_MOVE_MO);
static_assert(!USE_KILLER_MOVE_NWS_MO && USE_SIMD_EVALUATION);

struct Options {
    int depth;
};

Options read_options(const json& input) {
    if (!input.is_object() || !input.contains("fixedDepth") || !input.contains("selectivity")
        || !input.contains("mpc") || !input.at("fixedDepth").is_number_integer()
        || input.at("fixedDepth") < 1 || input.at("fixedDepth") > 60
        || !input.at("selectivity").is_number_integer() || input.at("selectivity") != 6
        || !input.at("mpc").is_boolean() || input.at("mpc") != false) {
        throw std::invalid_argument("fixedDepth1..60, selectivity6, mpc=false required");
    }
    for (auto item = input.begin(); item != input.end(); ++item) {
        const auto& key = item.key();
        if (key == "fixedDepth" || key == "selectivity" || key == "mpc") {
            continue;
        }
        if ((key != "etc" && key != "stability" && key != "parity"
                && key != "shallowOrdering") || !item.value().is_boolean()
            || item.value() != true) {
            throw std::invalid_argument(
                "unsupported option; original ordering/cuts remain enabled");
        }
    }
    return {input.at("fixedDepth").get<int>()};
}

std::string read_case_id(const json& value) {
    if (!value.is_string()) {
        throw std::invalid_argument("caseId string required");
    }
    const auto id = value.get<std::string>();
    if (id.empty() || id.size() > 128 || !std::all_of(id.begin(), id.end(), [](unsigned char c) {
            return c >= 33 && c <= 126;
        })) {
        throw std::invalid_argument("caseId must be1..128 printable nonspace ASCII bytes");
    }
    return id;
}

struct Session {
    egaroucid_oracle::Initialization evaluation;
    std::string midgame_id;
    std::string ordering_id;
    double engine_setup_ms = 0;
    double entry_init_ms = 0;
    uint64_t generation = 0;
    bool cleared = false;
};

json identity() {
    return {{"ok", true}, {"protocol", PROTOCOL}, {"profile", PROFILE},
        {"engineCommit", egaroucid_oracle::ENGINE_COMMIT},
        {"evaluationImplementation", "evaluate_simd.hpp"}};
}

json controls() {
    return {{"selectivity", MPC_100_LEVEL}, {"probabilityPercent", 100},
        {"compiledMpc", false}, {"etc", bool(USE_MID_ETC)},
        {"stability", bool(USE_END_SC)}, {"parity", bool(USE_END_PO)},
        {"lastParity", bool(LAST_PO_OPTIMIZE)}, {"shallowOrdering", true},
        {"last4Stability", bool(USE_LAST4_SC)},
        {"aspiration", bool(USE_ASPIRATION_NEGASCOUT)}, {"workerPool", thread_pool.size()},
        {"useMultiThread", false}, {"book", false}, {"ponder", false}};
}

void require_completion(bool searching, const Search& search, Board expected,
    int score, int policy, uint64_t legal) {
    if (!searching || !global_searching || search.mpc_level != MPC_100_LEVEL
        || score == SCORE_UNDEFINED || score < -SCORE_MAX || score > SCORE_MAX
        || policy < 0 || policy >= HW2 || !(legal & (1ULL << policy))
        || search.board.player != expected.player || search.board.opponent != expected.opponent
        || search.n_discs != expected.n_discs() || search.eval.feature_idx != 0) {
        throw std::runtime_error("incomplete/stopped/illegal or unrestored original fixed search");
    }
}

json fixed_search(const json& input, Session& session) {
    const auto prepare_start = Clock::now();
    if (input.size() != 4 || !input.contains("caseId") || !input.contains("state")
        || !input.contains("options")) {
        throw std::invalid_argument("search requires exactly op/caseId/state/options");
    }
    const auto id = read_case_id(input.at("caseId"));
    const Options options = read_options(input.at("options"));
    Board board = egaroucid_oracle::read_board(input.at("state"));
    if (!session.cleared) {
        throw std::invalid_argument("clear required outside each independent case clock");
    }
    session.cleared = false;
    const int actual_difference = board.count_player() - board.count_opponent();
    uint64_t legal = board.get_legal();
    const bool root_passed = legal == 0;
    if (root_passed) {
        board.pass();
        legal = board.get_legal();
    }
    json result = identity();
    result.update({{"caseId", id}, {"state", input.at("state")},
        {"options", input.at("options")}, {"clearGeneration", session.generation},
        {"requestedDepth", options.depth}, {"completedSelectivity", MPC_100_LEVEL},
        {"probabilityPercent", SELECTIVITY_PERCENTAGE[MPC_100_LEVEL]}, {"mpc", false},
        {"scorePerspective", "state.toMove"}, {"scoreUnits", "engine-disc"},
        {"actualDiscDifference", actual_difference}, {"bound", "UNKNOWN"},
        {"ttHits", nullptr}, {"orderingNodes", nullptr}, {"shutdownMs", nullptr},
        {"processWholeMs", nullptr}, {"transportMs", nullptr}});
    // Terminal before Search construction: full64 must never index phase60.
    if (legal == 0) {
        board.pass(); // Restore original requested STM after the terminal test.
        result.update({{"action", "terminal"}, {"rootPassed", false}, {"move", nullptr},
            {"searchedPolicyBit", nullptr}, {"searchedMove", nullptr},
            {"searchedRawScore", nullptr}, {"rawScore", end_evaluate(&board)},
            {"scoreKind", "engine_terminal_winner_empties_stm"},
            {"proven", true}, {"proofDomain", "original-engine-only"},
            {"completedDepth", 0}, {"nodes", 0}, {"engineSearchMs", 0.0},
            {"prepareMs", egaroucid_oracle::elapsed_ms(prepare_start, Clock::now())}});
        return result;
    }
    const int empties = HW2 - board.n_discs();
    if (options.depth > empties) {
        throw std::invalid_argument("fixedDepth exceeds remaining placements; no silent clamp");
    }
    if (!global_searching || thread_pool.size() != 0) {
        throw std::runtime_error("original stop/pool state not eligible for reference call");
    }
    const bool end_search = options.depth == empties;
    Search search(&board, MPC_100_LEVEL, false, false);
    bool searching = true;
    const std::vector<Clog_result> no_clogs;
    const auto ready = Clock::now();
    // One genuine root PVS iteration: no iterative wrapper, clog prepass or smoothing.
    const auto answer = first_nega_scout_legal(&search, -SCORE_MAX, SCORE_MAX,
        options.depth, end_search, no_clogs, legal, tim(), &searching);
    const auto finished = Clock::now();
    require_completion(searching, search, board, answer.first, answer.second, legal);
    result.update({{"action", root_passed ? "pass" : "move"}, {"rootPassed", root_passed},
        {"move", root_passed ? json(nullptr) : json(63 - answer.second)},
        {"searchedPolicyBit", answer.second}, {"searchedMove", 63 - answer.second},
        {"searchedRawScore", answer.first},
        {"rawScore", root_passed ? -answer.first : answer.first},
        {"scoreKind", end_search ? "engine_nonselective_end_winner_empties_stm"
            : "engine_fixed_depth_estimate_stm"},
        {"proven", end_search}, {"proofDomain", "original-engine-only"},
        {"completedDepth", options.depth}, {"nodes", search.n_nodes},
        {"prepareMs", egaroucid_oracle::elapsed_ms(prepare_start, ready)},
        {"engineSearchMs", egaroucid_oracle::elapsed_ms(ready, finished)}});
    return result;
}

json request(const json& input, Session& session) {
    if (!input.is_object() || !input.contains("op") || !input.at("op").is_string()) {
        throw std::invalid_argument("object with string op required");
    }
    const auto op = input.at("op").get<std::string>();
    if (op == "search") {
        return fixed_search(input, session);
    }
    if (input.size() != 1) {
        throw std::invalid_argument("info/clear accept only op");
    }
    json result = identity();
    if (op == "clear") {
        const auto start = Clock::now();
        transposition_table.init();
        global_searching = true;
        session.cleared = true;
        ++session.generation;
        result.update({{"clearGeneration", session.generation}, {"ttReset", true},
            {"resetMs", egaroucid_oracle::elapsed_ms(start, Clock::now())}});
        return result;
    }
    if (op != "info") {
        throw std::invalid_argument("only info/clear/search supported");
    }
    result.update({{"label", "Console7.8.1-engine + fixed-depth AVX2 MPC-off reference"},
        {"engineTag", "console_v7.8.1"}, {"controls", controls()},
        {"entry", "first_nega_scout_legal"}, {"alpha", -SCORE_MAX}, {"beta", SCORE_MAX},
        {"hashLevel", HASH_LEVEL}, {"hashSeed", HASH_SEED},
        {"activeTTBytes", sizeof(Hash_node)
            * (hash_sizes[HASH_LEVEL] + TRANSPOSITION_TABLE_N_LOOP - 1)},
        {"staticTTVirtualBytes", sizeof(Hash_node) * TRANSPOSITION_TABLE_STACK_SIZE},
        {"initialization", {{"evalSetupMs", session.evaluation.setup_ms},
            {"weightLoadAndEvalPrecomputeMs", session.evaluation.load_ms},
            {"engineAndHashSetupMs", session.engine_setup_ms},
            {"entryInitMs", session.entry_init_ms}, {"preMainMs", nullptr}}},
        {"weightIdentity", {{"midgameId", session.midgame_id},
            {"orderingId", session.ordering_id}, {"callerVerified", true},
            {"midgamePath", session.evaluation.eval_path},
            {"orderingPath", session.evaluation.ordering_path},
            {"expectedMidgameSha256", egaroucid_oracle::EVAL_SHA256},
            {"expectedOrderingSha256", egaroucid_oracle::ORDERING_SHA256}}},
        {"clock", "fixed depth; Root outer deadline only; no internal timer thread"}});
    return result;
}

Session initialize(const char* eval, const char* ordering,
    const std::string& midgame_id, const std::string& ordering_id) {
    if (midgame_id != std::string("sha256:") + egaroucid_oracle::EVAL_SHA256
        || ordering_id != std::string("sha256:") + egaroucid_oracle::ORDERING_SHA256) {
        throw std::invalid_argument("explicit pinned caller-verified weight IDs required");
    }
    const auto start = Clock::now();
    Session session;
    session.midgame_id = midgame_id;
    session.ordering_id = ordering_id;
    session.evaluation = egaroucid_oracle::initialize(eval, ordering);
    const auto engine_start = Clock::now();
    flip_init();
    last_flip_init();
    endsearch_init();
    move_ordering_init();
    stability_init();
    raw_myrandom.seed(HASH_SEED);
    if (!transposition_table.resize(HASH_LEVEL)) {
        throw std::runtime_error("original TT allocation failed");
    }
    hash_init_rand(HASH_LEVEL);
    global_hash_level = HASH_LEVEL;
#if USE_CRC32C_HASH
    global_hash_bit_mask = (1U << global_hash_level) - 1;
#endif
    global_searching = true;
    const auto ready = Clock::now();
    session.engine_setup_ms = egaroucid_oracle::elapsed_ms(engine_start, ready);
    session.entry_init_ms = egaroucid_oracle::elapsed_ms(start, ready);
    return session;
}

int serve(std::istream& input, std::ostream& output, Session& session) {
    char line[egaroucid_oracle::LINE_BYTES];
    for (;;) {
        input.getline(line, sizeof(line));
        if (input.eof() && input.gcount() == 0) {
            return 0;
        }
        try {
            const auto start = Clock::now();
            if (!input || input.eof()) {
                throw std::invalid_argument("oversized or incomplete JSONL frame");
            }
            const auto length = input.gcount() - 1;
            if (std::find(line, line + length, '\0') != line + length) {
                throw std::invalid_argument("embedded NUL in JSONL frame");
            }
            json result = request(json::parse(line), session);
            result["requestWallMs"] = egaroucid_oracle::elapsed_ms(start, Clock::now());
            output << result.dump() << std::endl;
        } catch (const std::exception& error) {
            output << json({{"ok", false}, {"protocol", PROTOCOL}, {"profile", PROFILE},
                {"error", error.what()}}).dump() << std::endl;
            return 1;
        }
    }
}
} // namespace egaroucid_search_oracle

#ifndef EGAROUCID_SEARCH_ORACLE_NO_MAIN
int main(int argc, char** argv) {
    try {
        if (argc != 7 || std::string(argv[3]) != "--midgame-id"
            || std::string(argv[5]) != "--ordering-id") {
            throw std::invalid_argument(
                "usage: oracle EVAL ORDERING --midgame-id sha256:HEX --ordering-id sha256:HEX");
        }
        auto session = egaroucid_search_oracle::initialize(argv[1], argv[2], argv[4], argv[6]);
        return egaroucid_search_oracle::serve(std::cin, std::cout, session);
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
#endif
