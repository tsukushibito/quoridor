// SPDX-License-Identifier: GPL-3.0-or-later
// New strict boundary fixtures only. Root owns compile/runtime admission.
// No explicit real weight/RNG initialization or search call in the fixture body.
// Original linked global constructors still belong to Root's runtime admission.
#define EGAROUCID_SEARCH_ORACLE_NO_MAIN
#include "../tools/egaroucid-search-oracle.cpp"

#include <sstream>

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
    require(rejected, "invalid reference controls accepted");
}

json options() {
    return {{"fixedDepth", 3}, {"selectivity", 6}, {"mpc", false}};
}

int main() {
    try {
        static_assert(!USE_MID_MPC && MPC_100_LEVEL == 6);
        require(reference::read_options(options()).depth == 3, "fixed depth parser");
        for (const json value : {json(0), json(61), json(true), json(3.0), json(4294967297ULL)}) {
            auto input = options();
            input["fixedDepth"] = value;
            rejects([&] { reference::read_options(input); });
        }
        for (const char* key : {"etc", "stability", "parity", "shallowOrdering"}) {
            auto input = options();
            input[key] = true;
            require(reference::read_options(input).depth == 3, "supported original flags");
            input[key] = false;
            rejects([&] { reference::read_options(input); });
        }
        auto input = options();
        input["selectivity"] = 0;
        rejects([&] { reference::read_options(input); });
        input = options();
        input["mpc"] = true;
        rejects([&] { reference::read_options(input); });
        input = options();
        input["timeMs"] = 1000;
        rejects([&] { reference::read_options(input); });
        input = options();
        input.erase("selectivity");
        rejects([&] { reference::read_options(input); });
        require(reference::read_case_id("dev/family:depth3") == "dev/family:depth3",
            "case binding");
        rejects([&] { reference::read_case_id(1); });
        rejects([&] { reference::read_case_id(""); });
        rejects([&] { reference::read_case_id("bad id"); });
        rejects([&] { reference::read_case_id(std::string(129, 'x')); });
        reference::Session session;
        const auto info = reference::request({{"op", "info"}}, session);
        require(info["profile"] == "original-avx2-fixed-depth-mpc-off"
            && info["controls"]["compiledMpc"] == false
            && info["entry"] == "first_nega_scout_legal", "explicit reference profile");
        require(info["weightIdentity"]["callerVerified"] == true,
            "reported identities remain caller authority");
        rejects([&] { reference::request({{"op", "info"}, {"state", nullptr}}, session); });
        rejects([&] { reference::request({{"op", "genmove"}}, session); });
        // Only info/error frames are exercised: no clear/TT writes or engine calls.
        std::istringstream incomplete("{\"op\":\"info\"}");
        std::ostringstream output;
        require(reference::serve(incomplete, output, session) == 1, "incomplete frame stops");
        std::istringstream bad_then_info("{\"op\":\"genmove\"}\n{\"op\":\"info\"}\n");
        std::ostringstream stopped;
        require(reference::serve(bad_then_info, stopped, session) == 1, "first bad stop");
        require(stopped.str().find('\n') == stopped.str().size() - 1, "no retry/second response");
        std::cout << "fixed-depth reference strict boundary fixtures PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
