// SPDX-License-Identifier: GPL-3.0-or-later
// Focused synthetic fixtures for the external-only Console7.8.1 oracle.
// Root compiles/runs this later; no real weight body is needed by this executable.
#define EGAROUCID_ORACLE_NO_MAIN
#include "../tools/egaroucid-eval-oracle.cpp"

#include <filesystem>
#include <sstream>
#include <vector>

using namespace egaroucid_oracle;

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
    require(rejected, "invalid input accepted");
}

json initial_state() {
    std::vector<int> cells(64, 0);
    cells[27] = cells[36] = 2;
    cells[28] = cells[35] = 1;
    return {{"version", 1}, {"board", cells}, {"toMove", 1}};
}

void board_and_protocol() {
    json state = initial_state();
    state["board"][0] = 1;
    state["board"][63] = 2;
    const Board black = read_board(state);
    require((black.player & (1ULL << 63)) != 0 && (black.opponent & 1ULL) != 0,
        "A1/H8 orientation");
    state["toMove"] = 2;
    const Board white = read_board(state);
    require(white.player == black.opponent && white.opponent == black.player,
        "STM board conversion");
    for (const json bad : {json(true), json(1.0), json(0), json(3), json(4294967297ULL)}) {
        state["toMove"] = bad;
        rejects([&] { read_board(state); });
    }
    state = initial_state();
    state["board"][0] = true;
    rejects([&] { read_board(state); });
    state = initial_state();
    state["board"][0] = 3;
    rejects([&] { read_board(state); });
    state = initial_state();
    state["extra"] = 0;
    rejects([&] { read_board(state); });
    state = initial_state();
    state["version"] = 1.0;
    rejects([&] { read_board(state); });
    require(swap_player_idx(5, 3) == 11 && swap_player_idx(11, 3) == 5,
        "MSB digits012 ->102 and empty2 unchanged");
    Initialization init;
    const auto info = request({{"op", "info"}}, init);
    require(info["engineCommit"] == ENGINE_COMMIT && info["search"] == false,
        "static identity");
    rejects([&] { request({{"op", "search"}, {"state", initial_state()}}, init); });
    std::istringstream valid("{\"op\":\"info\"}\n{\"op\":\"info\"}\n");
    std::ostringstream output;
    require(serve(valid, output, init) == 0, "persistent protocol");
    std::istringstream incomplete("{\"op\":\"info\"}");
    std::ostringstream error;
    require(serve(incomplete, error, init) == 1 && json::parse(error.str())["ok"] == false,
        "incomplete frame must stop");
    std::istringstream oversized(std::string(LINE_BYTES, ' ') + "\n");
    std::ostringstream bounded;
    require(serve(oversized, bounded, init) == 1, "oversized frame must stop");
    const std::string nul_frame = std::string("{\"op\":\"info\"}") + '\0' + "ignored\n";
    std::istringstream nul_input(nul_frame);
    std::ostringstream nul_output;
    require(serve(nul_input, nul_output, init) == 1, "embedded NUL must stop");
    std::istringstream first_bad("{\"op\":\"search\"}\n{\"op\":\"info\"}\n");
    std::ostringstream stopped;
    require(serve(first_bad, stopped, init) == 1, "first error stop");
    require(stopped.str().find("\n") == stopped.str().size() - 1,
        "no second response after failure");
}

void synthetic_terms_and_boundaries() {
    // Static C++ arrays are initially zero. Inject only the owned-count auxiliary;
    // do not load, export or copy any real weights.
    const json state = initial_state();
    for (int raw : {0, 15, 16, 17, -15, -16, -17, 47, 48, -47, -48, 4095, -4095}) {
        eval_num_arr[0][2] = static_cast<int16_t>(raw);
        const auto result = evaluate(state);
        const int bias = raw >= 0 ? 16 : -16;
        require(result["rawTotalStep"] == raw && result["roundingBiasStep"] == bias,
            "expose raw and signed half step");
        require(result["roundedDiscScore"] == (raw + bias) / 32,
            "negative C++ division must truncate toward zero");
        require(result["score"] == std::clamp((raw + bias) / 32, -64, 64), "clamp");
        require(result["patternIndices"].size() == 64
            && result["patternTermsStep"].size() == 64
            && result["patternSumsStep"].size() == 16, "full occurrence terms");
        require(result["endOrdering"]["clamped"] == false, "ordering separate");
    }
    eval_num_arr[0][2] = 0;
    // One empty A1, white B1, remaining black: black has A1; white must pass.
    json late = {{"version", 1}, {"board", std::vector<int>(64, 1)}, {"toMove", 1}};
    late["board"][0] = 0;
    late["board"][1] = 2;
    eval_num_arr[59][62] = 17;
    const auto black = evaluate(late);
    require(black["tablePhase"] == 59 && black["score"] == 1 && black["terminal"] == false,
        "phase59 at63occupied");
    late["toMove"] = 2;
    eval_num_arr[59][1] = -17;
    const auto white = evaluate(late);
    require(white["mustPass"] == true && white["tablePhase"] == 59 && white["score"] == -1,
        "forced pass not silently normalized and phase unchanged");
    // An early terminal with63 actual black discs awards the last empty to winner.
    late["toMove"] = 1;
    late["board"][1] = 1;
    const auto early = evaluate(late);
    require(early["terminal"] == true && early["tablePhase"].is_null()
        && early["rawTotalStep"].is_null() && early["score"] == 64
        && early["stmActualDiscDifference"] == 63, "early-terminal empty convention");
    late["board"][0] = 1;
    const auto full = evaluate(late);
    require(full["phase"] == 60 && full["tablePhase"].is_null() && full["score"] == 64,
        "full board cannot index phase60 or clamp phase to59");
    late["toMove"] = 2;
    require(evaluate(late)["score"] == -64, "terminal STM perspective");
}

void decoder_fixtures(const std::filesystem::path& tmp) {
    const auto path = tmp / "oracle-synthetic.egev2";
    const int count = 6;
    const int16_t tokens[] = {0, -7, 4096, 4099, 4095, -32768};
    {
        std::ofstream file(path, std::ios::binary);
        file.write(reinterpret_cast<const char*>(&count), sizeof(count));
        file.write(reinterpret_cast<const char*>(tokens), sizeof(tokens));
        require(static_cast<bool>(file), "synthetic fixture write");
    }
    bool failed = false;
    auto values = load_unzip_egev2(path.c_str(), false, &failed);
    require(!failed && values == std::vector<int16_t>({0, -7, 0, 0, 0, 4095, -32768}),
        "original signed token decoder, zero-length marker and zero run");
    const auto truncated = tmp / "oracle-truncated.egev2";
    {
        std::ofstream file(truncated, std::ios::binary);
        file.write(reinterpret_cast<const char*>(&count), sizeof(count));
        file.write(reinterpret_cast<const char*>(tokens), sizeof(int16_t));
    }
    load_unzip_egev2(truncated.c_str(), false, &failed);
    require(failed, "truncated token payload refused");
    rejects([&] { check_weight_header(path.c_str(), EVAL_BYTES, true); });
}

int main(int argc, char** argv) {
    try {
        require(argc == 2 && std::filesystem::is_directory(argv[1]), "owned TMP argument required");
        bit_init();
        mobility_init();
        board_and_protocol();
        synthetic_terms_and_boundaries();
        decoder_fixtures(argv[1]);
        std::cout << "focused protocol/synthetic terms/decoder fixtures PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
