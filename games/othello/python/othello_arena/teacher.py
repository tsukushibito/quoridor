"""Fixed external estimates, retaining upstream truth and independently measured costs.

Only teacherEstimate labels: no outcome consistency or promotion to minimax truth.
Teacher id binds source/weights/adapter/argv once in Root's config. The unchanged
Console7.8.1-engine + fixed-time adapter returns STM engine-disc score. Its
reported probability is search selectivity, not a derived proof or bound.
"""

import json
import math
import time

from .protocol import EngineError

OPTIONAL_FIELDS = {
    "completedDepth": "completedDepth",
    "probability": "reportedProbability",
    "elapsedMs": "internalElapsedMs",
}


def response_row(observation, response, teacher_id, outer_wall_ms):
    """Convert one known-orientation response; preserve unknowns and reported values."""
    if (
        type(outer_wall_ms) not in (int, float)
        or not math.isfinite(outer_wall_ms)
        or not 0 <= outer_wall_ms <= 1100
    ):
        raise EngineError("timeout", "teacher outer request outside monotonic1100ms")
    score = response.get("score")
    if type(score) not in (int, float) or not math.isfinite(score) or not -64 <= score <= 64:
        raise EngineError("protocol", "teacher score must be finite STM engine-disc in [-64,64]")
    if type(response.get("move")) is not int or response["move"] not in observation["legalMoves"]:
        raise EngineError("illegal", "teacher move differs from Rust legal moves")
    if type(response.get("completedDepth")) is not int or response["completedDepth"] < 1:
        raise EngineError("incomplete", "no reported completed teacher iteration")
    for field in ("probability", "elapsedMs", "budgetMs", "nodes"):
        value = response.get(field)
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
        ):
            raise EngineError("protocol", "nonfinite/invalid teacher metric: " + field)
    if response.get("probability") is not None and response["probability"] > 100:
        raise EngineError("protocol", "invalid reported probability")
    if response.get("budgetMs", 1000) != 1000:
        raise EngineError("protocol", "reported teacher budget differs")
    proven = response.get("proven")
    if proven is not None and type(proven) is not bool:
        raise EngineError("protocol", "teacher proven must be actual bool or null")
    if response.get("scoreKind") not in ("engine_estimate_stm", "engine_exact_winner_empties_stm"):
        raise EngineError("protocol", "fixed adapter STM score convention not established")
    if response.get("bound", "UNKNOWN") not in ("UNKNOWN", "EXACT", "LOWER", "UPPER"):
        raise EngineError("protocol", "unrecognized reported bound")
    metadata = {
        "id": teacher_id,
        "rawSTMScore": score,
        "scorePerspective": "state.toMove",
        "scoreUnits": "engine-disc",
        "scaleToCentidiscs": 100,
        "bound": response.get("bound", "UNKNOWN"),
        "proven": proven,
        "outerWallMs": outer_wall_ms,
        "requestedTimeMs": 1000,
    }
    metadata.update({dest: response.get(source) for source, dest in OPTIONAL_FIELDS.items()})
    return {
        "gameId": observation["gameId"],
        "openingFamily": observation["openingFamily"],
        "state": observation["state"],
        "labelKind": "teacherEstimate",
        "targetCentidiscs": score * 100,
        "teacher": metadata,
    }


def estimate(
    adapter, observation, teacher_id, evidence, *, cancelled=lambda: False, clock=time.monotonic
):
    """One attempt. TT reset is outside the monotonic1100ms search request boundary."""
    evidence.update(
        request={"op": "search", "state": observation["state"], "timeMs": 1000},
        status="failed",
        phase="reset",
        rawResponse=None,
        searchAttempted=False,
        transportMs=None,
        cancelJoinMs=None,
        internalSearchEnvelopeMs=None,
    )
    try:
        if cancelled():
            raise EngineError("cancelled", "teacher cancelled before reset")
        start = clock()
        try:
            adapter.reset(deadline=start + 5)
        finally:
            evidence["resetWallMs"] = (clock() - start) * 1000
        if cancelled():
            raise EngineError("cancelled", "teacher cancelled before request")
        evidence["phase"] = "search"
        evidence["searchAttempted"] = True
        adapter.last_search = None
        start = clock()
        try:
            response = adapter.search_response(observation["state"], deadline=start + 1.1)
        finally:
            evidence["outerWallMs"] = (clock() - start) * 1000
            evidence["rawResponse"] = adapter.last_search
        evidence["rawResponse"] = response
        if evidence["outerWallMs"] > 1100:
            raise EngineError("timeout", "teacher request exceeded monotonic1100ms")
        row = response_row(observation, response, teacher_id, evidence["outerWallMs"])
        internal = response.get("elapsedMs")
        # Search+transport+cooperative-cancel/join are inseparable on this protocol.
        evidence["internalSearchEnvelopeMs"] = internal
        evidence.update(status="complete", phase="complete")
        return row
    except Exception as error:
        raw = evidence.get("rawResponse")
        if raw is not None:
            try:
                json.dumps(raw, allow_nan=False)
            except ValueError:
                evidence["rejectedRawJSON"] = json.dumps(raw, allow_nan=True, separators=(",", ":"))
                evidence["rawResponse"] = None
        evidence["failure"] = {
            "kind": getattr(error, "kind", type(error).__name__),
            "message": str(error),
        }
        raise


def collect(native, config, observations, output, rows, requests, session, *, cancelled):
    """One persistent initialized teacher for a frozen T/V-only observation schedule."""
    from .__main__ import checked_spec
    from .engines import EgaroucidFixedTime
    from .protocol import Process

    spec = config["teacher"]
    if (
        not isinstance(spec["id"], str)
        or not spec["id"]
        or len(spec["id"].encode()) > 128
        or spec["upstreamCommit"] != "570d5e0a478c9d720d75de06a5d31995f412704a"
    ):
        raise EngineError("protocol", "explicit fixed Console7.8.1 teacher identity required")
    for key in ("source", "weights", "adapter"):
        if not isinstance(spec.get(key), (str, dict)) or not spec[key]:
            raise EngineError("protocol", "teacher config identity missing " + key)
    if spec.get("args") != spec["engine"]["argv"]:
        raise EngineError("protocol", "teacher identity args differ from bound executable argv")
    checked_spec(spec["engine"])
    # Root's config binds immutable adapter source, weights and argv once; no bulk per row.
    started = time.monotonic()
    process = None
    session.update(
        phase="initialization", initializationWallMs=None, transportMs=None, cancelJoinMs=None
    )
    try:
        process = Process(
            spec["engine"]["argv"],
            cwd=spec["engine"]["cwd"],
            log=output / "teacher-protocol.log",
            cancelled=cancelled,
        )
        adapter = EgaroucidFixedTime(process)
        try:
            info = process.json_request({"op": "info"}, deadline=started + 30)
        finally:
            session["initializationWallMs"] = (time.monotonic() - started) * 1000
        session["info"] = info
        if (
            info.get("label") != "Console7.8.1-engine + fixed-time adapter"
            or info.get("engineCommit") != spec["upstreamCommit"]
            or info.get("api") != "tree_search_legal(time_limit_ms)"
            or info.get("searchThreads") != 1
            or info.get("workerPool") != 0
            or info.get("hashLevel") != 20
            or info.get("activeTTBytes", 32 * 1024**2 + 1) > 32 * 1024**2
            or info.get("book") is not False
            or info.get("ponder") is not False
        ):
            raise EngineError(
                "protocol", "teacher runtime differs from frozen single-worker profile"
            )
        session["phase"] = "requests"
        for observation in observations:
            if len(requests) >= config["limits"]["teacherAttempts"]:
                raise EngineError("bounds", "teacher attempt cap; no refill")
            evidence = {
                "gameId": observation["row"]["gameId"],
                "openingFamily": observation["row"]["openingFamily"],
                "placement": observation["placement"],
                "status": "failed",
                "phase": "rules",
                "searchAttempted": False,
                "request": {"op": "search", "state": observation["row"]["state"], "timeMs": 1000},
            }
            requests.append(evidence)
            try:
                if cancelled():
                    raise EngineError("cancelled", "teacher cancelled before Rust status")
                position = observation["row"]["state"]
                status = native.request("status", state=position, deadline=time.monotonic() + 5)[
                    "status"
                ]
                if status["terminal"] or status["mustPass"] or not status["legalMoves"]:
                    raise EngineError("protocol", "scheduled teacher state is terminal/no-legal")
                source = {**observation["row"], "legalMoves": status["legalMoves"]}
                rows.append(estimate(adapter, source, spec["id"], evidence, cancelled=cancelled))
            except Exception as error:
                evidence.setdefault(
                    "failure",
                    {"kind": getattr(error, "kind", type(error).__name__), "message": str(error)},
                )
                raise
        session["phase"] = "complete"
    except Exception as error:
        session["failure"] = {
            "kind": getattr(error, "kind", type(error).__name__),
            "message": str(error),
        }
        raise
    finally:
        if session["initializationWallMs"] is None:
            session["initializationWallMs"] = (time.monotonic() - started) * 1000
        shutdown = time.monotonic()
        try:
            if process is not None:
                process.close()
        finally:
            session.update(
                shutdownWallMs=(time.monotonic() - shutdown) * 1000,
                cleanup=process.cleanup if process else None,
            )
    if process.cleanup["unexpectedExit"]:
        raise EngineError("crash", "teacher exited nonzero before shutdown")
