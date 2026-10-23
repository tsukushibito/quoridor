"""GTP adapters for the pinned official external builds."""

import math
import re
import time

from . import coordinate, move_index
from .protocol import EngineError


class GTP:
    def __init__(self, process, *, engine, time_ms=1000):
        if engine not in ("edax", "egaroucid"):
            raise ValueError("unknown external engine")
        self.process = process
        self.engine = engine
        self.time_ms = time_ms
        self.sequence = 0

    def command(self, command, *, deadline):
        self.sequence += 1
        tag = str(self.sequence)
        self.process.send(f"{tag} {command}", deadline)
        while True:
            line = self.process.line(deadline)
            if line.startswith(("=", "?")):
                break
        match = re.fullmatch(r"([=?])\s*(\d+)\s*(.*)", line)
        if not match or match[2] != tag:
            raise EngineError("protocol", f"GTP response ID mismatch: {line!r}")
        parts = [match[3]]
        while (line := self.process.line(deadline)) != "":
            parts.append(line)
        if match[1] == "?":
            raise EngineError("protocol", "GTP error: " + "\n".join(parts))
        return "\n".join(parts).strip()

    def reset(self, *, deadline):
        self.command("clear_board", deadline=deadline)
        if self.engine == "edax":
            if self.time_ms != 1000:
                raise ValueError("Edax initial GTP clock supports the pinned 1s profile only")
            # Edax uses main_time as options.time even in its per-move mode.
            # A positive stone count selects that mode; 0 1 1 would budget 0ms.
            self.command("time_settings 1 0 1", deadline=deadline)

    def observe(self, side, move, *, deadline):
        color = "black" if side == 1 else "white"
        square = "pass" if move is None else coordinate(move)
        self.command(f"play {color} {square}", deadline=deadline)

    def prepare(self, state, *, deadline):
        if self.engine == "edax":
            color = "black" if state["toMove"] == 1 else "white"
            self.command(f"time_left {color} 1 1", deadline=deadline)

    def choose(self, state, *, deadline):
        color = "black" if state["toMove"] == 1 else "white"
        response = self.command(f"genmove {color}", deadline=deadline)
        try:
            move = move_index(response)
            self.last_search = {
                "protocol": "gtp",
                "engine": self.engine,
                "side": state["toMove"],
                "move": move,
                "response": response,
            }
            return move
        except ValueError as error:
            raise EngineError("protocol", str(error)) from error


def validate_native_search(response, evaluation):
    """Known native contract; timedOut is normal budget exhaustion, cancelled is not."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise EngineError("protocol", "missing successful native search response")
    if response.get("evaluation") != evaluation:
        raise EngineError("identity", "native evaluator response differs from bound identity")
    if (
        type(response.get("move")) is not int
        or not 0 <= response["move"] < 64
        or type(response.get("score")) is not int
        or response.get("scoreKind") not in ("heuristic", "discDifference")
        or type(response.get("completedDepth")) is not int
        or not 0 <= response["completedDepth"] <= 64
        or type(response.get("nodes")) is not int
        or response["nodes"] < 0
        or type(response.get("elapsedMs")) not in (int, float)
        or not math.isfinite(response["elapsedMs"])
        or response["elapsedMs"] < 0
        or type(response.get("timedOut")) is not bool
        or type(response.get("proven")) is not bool
        or response.get("cancelled") is not False
    ):
        raise EngineError("protocol", "incomplete/invalid native search evidence")


class NativePlayer:
    def __init__(self, native, *, simple=False, time_ms=1000, tt_mib=32, evaluation=None):
        self.native = native
        self.simple = simple
        self.time_ms = time_ms
        self.tt_mib = tt_mib
        self.evaluation = evaluation

    def initialize(self, *, deadline):
        """Once after process/model load, outside game clocks; no search or TT reuse."""
        state = self.native.request("new", deadline=deadline)["state"]
        response = self.native.request("evaluate", state=state, deadline=deadline)
        if response.get("evaluation") != self.evaluation:
            raise EngineError("identity", "native initialization evaluator identity mismatch")
        return response

    def reset(self, *, deadline):
        pass

    def observe(self, side, move, *, deadline):
        pass

    def prepare(self, state, *, deadline):
        pass

    def choose(self, state, *, deadline):
        self.last_search = None
        self.native.last_response = None
        try:
            move = self.native.choose(
                state,
                deadline=deadline,
                simple=self.simple,
                time_ms=self.time_ms,
                tt_mib=self.tt_mib,
            )
        finally:
            self.last_search = self.native.last_response
        if self.evaluation is not None:
            validate_native_search(self.last_search, self.evaluation)
        return move


class EgaroucidFixedTime:
    """Pinned Console7.8.1 engine + external fixed-time adapter, separate from GTP."""

    def __init__(self, process, *, evidence=None):
        self.process = process
        self.evidence = evidence

    def reset(self, *, deadline):
        self.process.json_request({"op": "reset"}, deadline=deadline)

    def observe(self, side, move, *, deadline):
        pass

    def prepare(self, state, *, deadline):
        pass

    def search_response(self, state, *, deadline):
        result = self.process.json_request(
            {"op": "search", "state": state, "timeMs": 1000}, deadline=deadline
        )
        self.last_search = result
        if "move" not in result:
            raise EngineError("protocol", "fixed-time adapter omitted move")
        if self.evidence is not None:
            validate_external_search(result, self.evidence, state["toMove"])
        return result

    def choose(self, state, *, deadline):
        return self.search_response(state, deadline=deadline)["move"]


def io_deadline(seconds=5):
    """Protocol setup/transfer envelope, independent of scientific thinking budget."""
    return time.monotonic() + seconds


def validate_full_search(response, identity):
    """Ordinary nested FullSearch evidence; startup identity is checked once separately."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise EngineError("protocol", "unsuccessful FullSearch response")
    result = response.get("result")
    if not isinstance(result, dict):
        raise EngineError("protocol", "missing nested FullSearch result")
    if (
        type(result.get("move")) is not int
        or not 0 <= result["move"] < 64
        or type(result.get("completedDepth")) is not int
        or not 1 <= result["completedDepth"] <= 60
        or type(result.get("selectivity")) is not int
        or not 0 <= result["selectivity"] <= 6
        or type(result.get("nodes")) is not int
        or result["nodes"] < 0
        or type(result.get("elapsedMs")) not in (int, float)
        or not math.isfinite(result["elapsedMs"])
        or not 0 <= result["elapsedMs"] <= 1100
        or result.get("stopped") not in (None, "timeout")
        or type(result.get("proven")) is not bool
        or type(result.get("isEndSearch")) is not bool
        or type(result.get("probability")) not in (int, float)
        or not math.isfinite(result["probability"])
        or not 0 <= result["probability"] <= 100
        or result.get("proven") != (result.get("scoreKind") == "terminalEmptyAward")
        or (result.get("proven") and (not result["isEndSearch"] or result["selectivity"] != 6))
        or result.get("scoreUnits") != "engine-disc"
        or result.get("scoreKind") not in ("heuristic", "terminalEmptyAward")
        or any(
            type(result.get(k)) is not int or not -64 <= result[k] <= 64
            for k in ("rawScore", "score")
        )
        or result.get("terminal") is not False
        or result.get("mustPass") is not False
        or result.get("interpretation") != identity["interpretation"]
        or result.get("coefficients") != identity["coefficients"]
        or type(result.get("ttBytes")) is not int
        or not 0 < result["ttBytes"] <= 32 * 1024**2
    ):
        raise EngineError("protocol", "invalid ordinary FullSearch placement evidence")
    return result


def validate_external_search(response, expected, side):
    """External transport evidence, distinct from same-native evaluator evidence."""
    if not isinstance(response, dict):
        raise EngineError("protocol", "missing external transport response")
    if expected["protocol"] == "gtp":
        if (
            response.get("protocol") != "gtp"
            or expected["engine"] != "edax"
            or response.get("engine") != "edax"
            or response.get("side") != side
            or not isinstance(response.get("response"), str)
            or len(response["response"].encode()) > 256
            or move_index(response["response"]) != response.get("move")
        ):
            raise EngineError("protocol", "invalid bound Edax GTP move evidence")
    elif expected["protocol"] == "fixed_jsonl":
        if (
            response.get("ok") is not True
            or response.get("budgetMs") != 1000
            or response.get("scoreKind")
            not in ("engine_estimate_stm", "engine_exact_winner_empties_stm")
            or type(response.get("completedDepth")) is not int
            or not 1 <= response["completedDepth"] <= 60
            or type(response.get("nodes")) is not int
            or response["nodes"] < 0
            or type(response.get("elapsedMs")) not in (int, float)
            or not math.isfinite(response["elapsedMs"])
            or not 0 <= response["elapsedMs"] <= 1100
            or type(response.get("score")) is not int
            or not -64 <= response["score"] <= 64
            or type(response.get("proven")) is not bool
            or type(response.get("probability")) not in (int, float)
            or not math.isfinite(response["probability"])
            or not 0 <= response["probability"] <= 100
            or response["proven"] != (response["scoreKind"] == "engine_exact_winner_empties_stm")
            or (response["proven"] and response["probability"] != 100)
        ):
            raise EngineError("protocol", "invalid fixed-time Console placement evidence")
    else:
        raise EngineError("protocol", "unbound external protocol")
    if type(response.get("move")) is not int or not 0 <= response["move"] < 64:
        raise EngineError("protocol", "invalid external placement")
    return response["move"]


class FullSearchPlayer:
    """Maintained ordinary CLI owner, persistent weights and TT, no response reshaping."""

    def __init__(self, process, *, identity, options):
        self.process, self.identity, self.options = process, identity, options
        self.last_search = None

    def initialize(self, *, deadline):
        required = {
            "engine",
            "upstreamCommit",
            "interpretation",
            "midgameId",
            "orderingId",
            "identityBinding",
            "hashLevel",
            "hashSeed",
            "coefficients",
            "workerPool",
        }
        if (
            set(self.identity) != required
            or self.identity["identityBinding"] != "callerVerified"
            or self.identity["engine"] != "console7.8.1-rust-singlethread-source-port"
            or self.identity["upstreamCommit"] != "570d5e0a478c9d720d75de06a5d31995f412704a"
            or self.identity["interpretation"] != "simd"
            or self.identity["workerPool"] != 0
            or self.identity["hashLevel"] != 20
            or self.identity["hashSeed"] != 20261022
            or self.options
            != {
                "timeMs": 1000,
                "maxDepth": 60,
                "fixedDepth": None,
                "selectivity": None,
                "mpc": True,
                "etc": True,
                "stability": True,
                "parity": True,
                "shallowOrdering": True,
            }
        ):
            raise EngineError("identity", "explicit supported ordinary timed profile required")
        info = self.process.json_request({"op": "info"}, deadline=deadline)
        if any(info.get(k) != v for k, v in self.identity.items()):
            raise EngineError("identity", "FullSearch startup identity differs")
        return info

    def reset(self, *, deadline):
        self.process.json_request({"op": "clear"}, deadline=deadline)

    def observe(self, side, move, *, deadline):
        pass

    def prepare(self, state, *, deadline):
        pass

    def choose(self, state, *, deadline):
        self.last_search = None
        self.last_search = self.process.json_request(
            {"op": "search", "state": state, "options": self.options}, deadline=deadline
        )
        return validate_full_search(self.last_search, self.identity)["move"]
