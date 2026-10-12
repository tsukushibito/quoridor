"""355 saved-only finite checking/aggregation; no engine, model or data generation.

Functions operate on decoded, hash-bound stopped producer records. This source
phase exposes schema only as a CLI; execution of a real campaign requires the
separately supported lifetime entry owned by integration.
"""

from collections import Counter, defaultdict
import hashlib
import json
import math
import random

PLAN_SHA = "b3e41602eeed250d120444cf65783012e87f8b5f860bef2862c7aac5fd9c24b2"
MATCHUPS = ("retainedBEST51-versus-fixedD", "fresh353BEST43-versus-fixedD")
EVALUATORS = ("D", "BEST51", "BEST43")
MATCHED_IDS = tuple(range(0, 128, 4))
TREE_IDS = tuple(range(0, 128, 16))
BOOTSTRAP_SEED = 35520261010
BOOTSTRAP_RESAMPLES = 10000
MAX_PACKET_BYTES = 67108864
MAX_GAME_BYTES = 1048576
MAX_OBSERVATIONS = 200
MAX_PV = 64
MAX_HISTORY = 17
MAX_STRING = 4096


class Refusal(ValueError):
    """Malformed evidence refuses, while legitimate missing work stays UNKNOWN."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def integer(value, minimum=0, maximum=(1 << 64) - 1):
    require(type(value) is int and minimum <= value <= maximum, "integer domain")
    return value


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value), "finite numeric domain")
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha(value):
    require(
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "SHA256 domain",
    )
    return value


def strict_json(raw, maximum=MAX_GAME_BYTES):
    require(type(raw) is bytes and len(raw) <= maximum, "UTF8 record cap")

    def pairs(rows):
        out = {}
        for key, value in rows:
            require(key not in out, "duplicate JSON key")
            out[key] = value
        return out

    def constant(value):
        raise Refusal("nonfinite JSON constant " + value)

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Refusal("partial or malformed JSON") from error
    validate_finite_tree(value)
    return value


def validate_finite_tree(value, depth=0, index_files=False):
    require(depth <= 24, "JSON nesting cap")
    if type(value) is float:
        finite(value)
    elif isinstance(value, str):
        require(len(value.encode()) <= MAX_STRING, "string cap")
    elif isinstance(value, list):
        require(len(value) <= 1024, "array cap")
        for item in value:
            validate_finite_tree(item, depth + 1)
    elif isinstance(value, dict):
        require(len(value) <= (512 if index_files else 256), "object field cap")
        for key, item in value.items():
            require(isinstance(key, str), "JSON key type")
            validate_finite_tree(key, depth + 1)
            root_files = (
                depth == 0
                and value.get("schema") == "quoridor.strength355.stopped-input-index.v1"
                and key == "files"
            )
            validate_finite_tree(item, depth + 1, root_files)
    else:
        require(value is None or type(value) in (bool, int), "JSON value type")


def planned_slots():
    """Exact prospective plan order; no actual book/games claim."""
    rows = []
    for batch in range(8):
        matchup_order = MATCHUPS if batch % 2 == 0 else tuple(reversed(MATCHUPS))
        for matchup_order_index, matchup in enumerate(matchup_order):
            local_game = 0
            for family in range(16 * batch, 16 * batch + 16):
                first_colour = (family + batch) % 2
                for colour in (first_colour, first_colour ^ 1):
                    rows.append(
                        {
                            "slot_id": len(rows),
                            "family_id": family,
                            "matchup": matchup,
                            "candidate_colour": colour,
                            "batch_id": 2 * batch + matchup_order_index,
                            "local_game": local_game,
                        }
                    )
                    local_game += 1
    return rows


def check_book(book):
    require(book["plan_SHA256"] == PLAN_SHA, "current plan binding")
    require(book["schema"] == "quoridor.strength355.full-history-book.v1", "book schema")
    require(book["provenance"] in ("ACTUAL_GENERATED", "SYNTHETIC"), "book provenance")
    require(len(book["families"]) == 128, "128 family denominator")
    prefixes, histories = set(), set()
    for family_id, row in enumerate(book["families"]):
        require(integer(row["family_id"], 0, 127) == family_id, "family identity/order")
        prefix = row["prefix"]
        require(len(prefix) == (4, 8, 12, 16)[family_id // 32], "prebound length strata")
        require(all(type(a) is int and 0 <= a <= 208 for a in prefix), "action ID domain")
        require(sha(row["prefix_SHA256"]) == digest(prefix), "prefix hash")
        require(sha(row["history_SHA256"]) == digest(row["counted_history"]), "history hash")
        history = row["counted_history"]
        require(
            1 <= len(history) <= MAX_HISTORY
            and sum(integer(n, 1, 2) for _, n in history) == len(prefix) + 1,
            "complete prefix/history census",
        )
        require(len({key for key, _ in history}) == len(history), "duplicate counted Key")
        require(
            row["terminal"] is False and row["current_rules"] == "standard_2p_threefold_goal_first",
            "nonterminal current context",
        )
        require(
            type(row["lineage"]) is dict
            and isinstance(row["lineage"]["shared_root"], str)
            and row["lineage"]["family_seed"]
            == 35520261009 + 8 * family_id + integer(row["attempt_id"], 0, 7),
            "actual stream/lineage binding",
        )
        require(
            tuple(prefix) not in prefixes
            and (row["root_key"], row["history_SHA256"]) not in histories,
            "duplicate family provenance",
        )
        prefixes.add(tuple(prefix))
        histories.add((row["root_key"], row["history_SHA256"]))
    return digest(book)


def check_schedule(schedule, book):
    book_sha = check_book(book)
    require(
        schedule["schema"] == "quoridor.strength355.schedule.v1"
        and schedule["plan_SHA256"] == PLAN_SHA
        and schedule["book_SHA256"] == book_sha,
        "schedule/book binding",
    )
    require(
        digest(schedule["slots"]) == digest(planned_slots()), "fixed512 order/count/colour plan"
    )
    return digest(schedule)


def costs(record):
    """Named measured domains remain separate; None is UNKNOWN, never zero."""
    out = {}
    for name in (
        "search_seconds",
        "setup_search_drop_seconds",
        "caller_seconds",
        "whole_phase_seconds",
        "publication_seconds",
    ):
        value = record.get(name)
        if value is not None:
            finite(value)
            require(value >= 0, "negative cost")
        out[name] = value
    if out["search_seconds"] is not None and out["setup_search_drop_seconds"] is not None:
        require(
            out["search_seconds"] <= out["setup_search_drop_seconds"] + 1e-12,
            "nested search/setup domain",
        )
    if out["publication_seconds"] is not None and out["whole_phase_seconds"] is not None:
        require(
            out["publication_seconds"] <= out["whole_phase_seconds"] + 1e-12,
            "publication/phase domain",
        )
    return out


def check_observation(ob, candidate_colour, expected_ply, previous_drain):
    require(ob["ply"] == expected_ply and ob["side"] == expected_ply % 2, "move chronology")
    require(
        ob["engine_index"] == (0 if ob["side"] == candidate_colour else 1),
        "paired evaluator mapping",
    )
    c = ob["counters"]
    begin, receipt, deadline = (
        integer(ob[key]) for key in ("caller_started_ns", "returned_ns", "deadline_ns")
    )
    require(deadline - begin == 100000000, "actual100ms clock")
    require(
        previous_drain <= begin <= receipt and integer(c["authority_receipt_ns"]) == receipt,
        "matching authority receipt/drain",
    )
    require(c["clock_contract"] == "authority-action-receipt-v1", "clock contract")
    require(integer(c["drain_finished_ns"]) >= receipt, "drain return order")
    sha(c["clock_contract_sha256"])
    finite(ob["thinking_seconds"])
    require(abs(ob["thinking_seconds"] - (receipt - begin) / 1e9) <= 1e-12, "thinking domain")
    require(type(ob["accepted"]) is bool, "accepted type")
    if ob["accepted"]:
        require(
            receipt <= deadline and ob["failure"] is None and ob["engine_error"] is None,
            "late/error accepted",
        )
        require(
            integer(ob["completed_depth"], 1, 64) > 0
            and ob["action"] is not None
            and ob["pv"][0] == ob["action"],
            "accepted immutableAction/PV/depth",
        )
        require(len(ob["pv"]) <= MAX_PV, "PV cap")
        finite(ob["value_stm"])
        require(c["completed_snapshot_validation_failed"] is False, "invalid snapshot accepted")
        require(
            receipt
            <= integer(ob["admission_checked_ns"])
            <= integer(ob["accepted_ns"])
            == integer(c["state_commit_ns"]),
            "legality/commit before receipt",
        )
    else:
        require(isinstance(ob["failure"], str) and bool(ob["failure"]), "unexplained refusal")
        require(ob["accepted_ns"] is None, "refused state committed")
    if c.get("nodes") is not None:
        integer(c["nodes"])
    return c["drain_finished_ns"]


def check_game(game, planned, book, schedule_sha):
    require(
        digest(game["slot"]) == digest(planned) and game["schedule_SHA256"] == schedule_sha,
        "outcome slot/source signature",
    )
    family = book["families"][planned["family_id"]]
    require(
        game["prefix_SHA256"] == family["prefix_SHA256"]
        and game["history_SHA256"] == family["history_SHA256"],
        "outcome fullhistory mismatch",
    )
    require(game["provenance"] == book["provenance"], "synthetic relabel")
    out = game["outcome"]
    require(
        type(out["started"]) is bool and out["status"] in ("goal", "draw", "unknown"),
        "outcome status",
    )
    require(len(out["observations"]) <= MAX_OBSERVATIONS, "observation cap")
    previous_drain, counters = 0, Counter()
    for index, observation in enumerate(out["observations"]):
        previous_drain = check_observation(
            observation, planned["candidate_colour"], len(family["prefix"]) + index, previous_drain
        )
        counters["accepted" if observation["accepted"] else "rejected"] += 1
        if observation["failure"]:
            counters["failure:" + observation["failure"]] += 1
    if out["status"] == "unknown":
        require(
            out["winner"] is None and isinstance(out["reason"], str) and bool(out["reason"]),
            "UNKNOWN disguised as terminal",
        )
        score = None
    else:
        require(
            out["started"] and not counters["rejected"] and out["failure"] is None,
            "terminal after caller refusal",
        )
        if out["status"] == "goal":
            require(
                out["winner"] in (0, 1) and type(out["winner"]) is int and out["reason"] == "goal",
                "goal proof signature",
            )
            score = float(out["winner"] == planned["candidate_colour"])
        else:
            require(
                out["winner"] is None and out["reason"] == "legal_third_repetition",
                "noncanonical draw",
            )
            score = 0.5
    require(out["started"] or not out["observations"], "unentered observations")
    require(out["moves"][: len(family["prefix"])] == family["prefix"], "retained opening prefix")
    require(
        integer(out["plies"], len(family["prefix"]), 200) == len(out["moves"]),
        "committed ply/move count",
    )
    require(
        len(out["moves"]) == len(family["prefix"]) + counters["accepted"],
        "failed caller committed state",
    )
    for observation in out["observations"]:
        if observation["accepted"]:
            require(
                out["moves"][observation["ply"]] == observation["action"],
                "immutable action/move mismatch",
            )
    if out["status"] != "unknown":
        require(bool(out["observations"]), "nonterminal opening became terminal without a move")
        if out["status"] == "goal":
            require(out["winner"] == out["observations"][-1]["side"], "goal winner/last mover")
    return score, counters, costs(game)


def quantile(values, probability):
    """Explicit linear interpolation (sorted sample index(n-1)*p)."""
    rank = (len(values) - 1) * probability
    low = int(rank)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (rank - low)


def bootstrap(scores, confidence=0.975):
    require(
        confidence == 0.975 and all(-1 <= finite(x) <= 1 for x in scores),
        "frozen confidence/finite sample",
    )
    if not scores:
        return {
            "interval": None,
            "reason": "no complete pairs",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
        }
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(scores)
    samples = sorted(
        sum(scores[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAP_RESAMPLES)
    )
    tail = (1 - confidence) / 2
    return {
        "interval": [quantile(samples, tail), quantile(samples, 1 - tail)],
        "confidence": confidence,
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "algorithm": "Python Random MT19937/randrange; linear interpolated percentile; runtime Python identity required",
        "units": n,
        "scope": "conditional complete family pairs; no dependence/selection correction or guaranteed familywise coverage",
    }


def aggregate_games(book, schedule, games, progress=None):
    schedule_sha = check_schedule(schedule, book)
    by_slot, failures, clocks = {}, [], Counter()
    for index, game in enumerate(games):
        require(index < 512, "extra outcomes")
        slot_id = integer(game["slot"]["slot_id"], 0, 511)
        require(slot_id not in by_slot, "duplicate outcome")
        score, census, measured = check_game(game, schedule["slots"][slot_id], book, schedule_sha)
        by_slot[slot_id] = (score, measured)
        clocks.update(census)
        if progress is not None:
            progress["validated_game_scores"] = {
                str(slot): value[0] for slot, value in by_slot.items()
            }
            progress["validated_clock_census"] = dict(clocks)
        if score is None:
            failures.append({"slot_id": slot_id, "reason": game["outcome"]["reason"]})
    output, pairmaps = {}, {}
    for matchup in MATCHUPS:
        families, known_scores, missing = defaultdict(dict), [], []
        for slot in schedule["slots"]:
            if slot["matchup"] != matchup:
                continue
            score = by_slot.get(slot["slot_id"], (None, {}))[0]
            families[slot["family_id"]][slot["candidate_colour"]] = score
            if score is None:
                missing.append(slot["slot_id"])
            else:
                known_scores.append(score)
        complete = {
            family: sum(pair.values()) / 2
            for family, pair in families.items()
            if all(x is not None for x in pair.values())
        }
        pairmaps[matchup] = complete
        output[matchup] = {
            "planned_games": 256,
            "observed_records": sum(
                s["matchup"] == matchup and s["slot_id"] in by_slot for s in schedule["slots"]
            ),
            "known_games": len(known_scores),
            "UNKNOWN_games": len(missing),
            "complete_pairs": len(complete),
            "incomplete_pairs": 128 - len(complete),
            "complete_pair_mean": sum(complete.values()) / len(complete) if complete else None,
            "conditional_interval": bootstrap(list(complete.values())),
            "planned_score_missingness_bounds": [
                sum(known_scores) / 256,
                (sum(known_scores) + len(missing)) / 256,
            ],
            "UNKNOWN_slots": missing,
            "per_family_complete_scores": complete,
        }
    common = sorted(set(pairmaps[MATCHUPS[0]]) & set(pairmaps[MATCHUPS[1]]))
    difference = [
        pairmaps[MATCHUPS[1]][family] - pairmaps[MATCHUPS[0]][family] for family in common
    ]
    # Exactly TWO planned bootstrap comparisons; shared-family contrast only
    # describes paired means and does not add another resampling experiment.
    contrast = {
        "direction": "BEST43-D minus BEST51-D",
        "common_complete_families": common,
        "mean": sum(difference) / len(difference) if difference else None,
        "descriptive_interval": None,
        "scope": "descriptive same-family difference; not a third confirmatory comparison or independent family draw",
    }
    roots = Counter(row["lineage"]["shared_root"] for row in book["families"])
    return {
        "matchups": output,
        "shared_family_contrast": contrast,
        "clock_census": dict(clocks),
        "explicit_UNKNOWN_reasons": failures,
        "lineage": {
            "shared_roots": dict(roots),
            "IID_established": False,
            "scope": "derived seeds/shared initial/generator do not prove independence",
        },
        "cost_domains": [{"slot_id": slot, **v[1]} for slot, v in sorted(by_slot.items())],
        "cost_warning": "Search/setup/caller/phase/publication are nested or different domains; never add them or derive arithmetic speed from differing work.",
    }


def complete_depth(row, requested):
    require(
        row["value_perspective"] == "PARENT_STM"
        and row["score_units"] == "legacy-tanh-search-terminal2",
        "search score perspective/units",
    )
    require(row["requested_depth"] == requested, "depth request changed")
    require(row["status"] in ("COMPLETE", "INCOMPLETE", "ERROR", "UNENTERED"), "search status")
    integer(row["deepest_completed"], 0, requested)
    if row["nodes"] is not None:
        integer(row["nodes"], 0, 2000000 if requested == 4 else 8000000)
    costs(row)
    if row["status"] != "COMPLETE":
        require(row["complete_requested"] is False, "partial complete flag")
        return False
    if row.get("terminal_strength") == "EXACT_CANONICAL_TERMINAL":
        require(row["complete_requested"] is True, "terminal completeness")
        finite(row["value_stm"])
        require(row["value_stm"] in (-2, 0, 2), "canonical terminal domain")
        require(row["action"] is None and row["pv"] == [], "terminal has no proposal")
        require(row["legal_action"] is True, "terminal legality")
        return True
    if row.get("terminal_strength") == "FORCED_CHILD_TERMINAL":
        require(
            row["complete_requested"] is True and row["legal_action"] is True,
            "forced terminal completeness",
        )
        finite(row["value_stm"])
        require(
            row["value_stm"] in (-2, 0, 2)
            and type(row["action"]) is int
            and 0 <= row["action"] <= 208
            and row["pv"] == [row["action"]],
            "forced canonical terminal proof",
        )
        return True
    require(
        row["complete_requested"] is True and row["deepest_completed"] == requested,
        "partial depth cannot rescue",
    )
    require(
        row["bound"] == "EXACT"
        and row["legal_action"] is True
        and type(row["action"]) is int
        and 0 <= row["action"] <= 208,
        "complete exact legal proposal",
    )
    finite(row["value_stm"])
    require(len(row["pv"]) <= MAX_PV and row["pv"] and row["pv"][0] == row["action"], "complete PV")
    return True


def check_matched(book, matched):
    require(matched["book_SHA256"] == check_book(book), "matched book identity")
    require(len(matched["rows"]) <= 96, "matched call cap")
    rows, known_nodes = {}, 0
    for row in matched["rows"]:
        key = (integer(row["family_id"], 0, 127), row["evaluator"])
        require(
            key[0] in MATCHED_IDS and key[1] in EVALUATORS and key not in rows,
            "matched selector/evaluator/duplicate",
        )
        family = book["families"][key[0]]
        require(
            row["history_SHA256"] == family["history_SHA256"]
            and row["prefix_SHA256"] == family["prefix_SHA256"],
            "matched actual parent",
        )
        complete = complete_depth(row, 4)
        if row["nodes"] is not None:
            known_nodes += row["nodes"]
        rows[key] = (row, complete)
    require(known_nodes <= 192000000, "matched aggregate node cap")
    differences, union = {}, defaultdict(set)
    for evaluator in ("BEST51", "BEST43"):
        chosen = []
        for family in MATCHED_IDS:
            d, n = rows.get((family, "D")), rows.get((family, evaluator))
            if (
                d
                and n
                and d[1]
                and n[1]
                and d[0]["action"] is not None
                and n[0]["action"] is not None
                and d[0]["action"] != n[0]["action"]
            ):
                chosen.append(
                    {
                        "family_id": family,
                        "NN": evaluator,
                        "D_action": d[0]["action"],
                        "NN_action": n[0]["action"],
                    }
                )
                if len(chosen) == 8:
                    break
        differences[evaluator] = chosen
        for case in chosen:
            for candidate in EVALUATORS:
                proposal = rows.get((case["family_id"], candidate))
                if proposal and proposal[1] and proposal[0]["action"] is not None:
                    union[case["family_id"]].add(proposal[0]["action"])
    require(
        all(len(actions) <= 3 for actions in union.values()) and len(union) <= 16,
        "prebound candidate union",
    )
    return {
        "planned_calls": 96,
        "available_calls": len(rows),
        "COMPLETE": sum(value[1] for value in rows.values()),
        "UNKNOWN_or_partial": 96 - sum(value[1] for value in rows.values()),
        "known_available_nodes": known_nodes,
        "nodes_of_unavailable_Err": "UNKNOWN",
        "selection": {
            "book_SHA256": matched["book_SHA256"],
            "matched_SHA256": digest(matched),
            "first_differences": differences,
            "unions": [
                {"family_id": family, "actions": sorted(actions)}
                for family, actions in sorted(union.items())
            ],
        },
        "rows": [dict(row, comparable_complete=complete) for row, complete in rows.values()],
        "limits": "Same-depth full-work, not same-time outcomes; deeper agreement not truth; no lowerdepth or game-loss replacement.",
    }


def check_stronger(matched_summary, selection, stronger):
    require(
        selection["content"] == matched_summary["selection"]
        and selection["content_SHA256"] == digest(selection["content"]),
        "stronger cases changed after matched outcomes",
    )
    events = stronger["stage_events"]
    event_kinds = ["MATCHED_STOP", "SELECTION_FSYNC"]
    if stronger["rows"]:
        event_kinds.append("STRONGER_FIRST_CALL")
    require([e["kind"] for e in events] == event_kinds, "unfrozen stronger selection")
    require(
        all(type(e["sequence"]) is int for e in events)
        and all(a["sequence"] < b["sequence"] for a, b in zip(events, events[1:])),
        "stage event order",
    )
    require(
        events[1]["selection_SHA256"] == selection["content_SHA256"], "selection event identity"
    )
    unions = {u["family_id"]: u["actions"] for u in selection["content"]["unions"]}
    calls, nodes, census = set(), 0, Counter()
    expected = {
        (family, evaluator, kind, action)
        for family, actions in unions.items()
        for evaluator in EVALUATORS
        for kind, action in [("natural", None), *[("forced", a) for a in actions]]
    }
    require(len(stronger["rows"]) <= 192, "stronger call cap")
    for row in stronger["rows"]:
        key = (row["family_id"], row["evaluator"], row["kind"], row["forced_action"])
        require(key in expected and key not in calls, "extra/duplicate/unselected stronger call")
        require(
            row["selection_SHA256"] == selection["content_SHA256"],
            "stronger ledger selection mismatch",
        )
        if row["kind"] == "forced":
            require(row["child_depth"] == 5 and row["total_depth"] == 6, "forced root horizon")
        complete = complete_depth(row, 6)
        if complete and row["kind"] == "forced":
            require(row["action"] == row["forced_action"], "forced root/PV action")
        census["COMPLETE" if complete else "UNKNOWN_or_partial"] += 1
        if row["nodes"] is not None:
            nodes += row["nodes"]
        calls.add(key)
    require(
        nodes <= 1536000000
        and sum(k[2] == "natural" for k in calls) <= 48
        and sum(k[2] == "forced" for k in calls) <= 144,
        "stronger aggregate envelope",
    )
    return {
        "selection_SHA256": selection["content_SHA256"],
        "planned_for_frozen_union": len(expected),
        "campaign_upper_calls": 192,
        "available_calls": len(calls),
        "unentered_calls": len(expected - calls),
        "census": dict(census),
        "known_available_nodes": nodes,
        "rows": [
            dict(row, comparable_complete=row["status"] == "COMPLETE") for row in stronger["rows"]
        ],
        "deeper_values": "estimates, not teacher labels or exact truth; exact terminal proof kept separately",
    }


def check_tree(tree):
    require(tree["family_id"] in TREE_IDS and tree["requested_depth"] == 2, "tree selector/depth")
    require(tree["status"] in ("COMPLETE", "INCOMPLETE", "ERROR", "UNENTERED"), "tree status")
    integer(tree["expanded_plus_leaf_nodes"], 0, 100000)
    if tree["status"] != "COMPLETE":
        return {
            "family_id": tree["family_id"],
            "status": "UNKNOWN",
            "reason": tree["reason"],
            "available_nodes": tree["expanded_plus_leaf_nodes"],
            "available_root_values": tree.get("root_values"),
            "available_terminal_proofs": tree.get("terminal_proofs"),
            "raw_ref": tree.get("raw_ref"),
            "primary_error": tree.get("primary_error"),
            "secondary_errors": tree.get("secondary_errors", []),
        }
    require(
        tree["ALL_legal"] is True and tree["missing_responses"] == 0, "heuristic/incomplete tree"
    )
    require(set(tree["root_values"]) == set(EVALUATORS), "common evaluator coverage")
    for value in tree["root_values"].values():
        finite(value)
    nodes = tree["nodes"]
    require(len(nodes) == tree["expanded_plus_leaf_nodes"], "tree node census")
    by_id = {}
    for node in nodes:
        node_id = integer(node["node_id"], 0, 99999)
        require(node_id not in by_id, "duplicate common node")
        integer(node["ply"], 0, 2)
        require(set(node["values_stm"]) == set(EVALUATORS), "node evaluator coverage")
        for value in node["values_stm"].values():
            finite(value)
        by_id[node_id] = node
    require(0 in by_id and by_id[0]["parent"] is None and by_id[0]["ply"] == 0, "common root")
    incoming = Counter()
    for node_id, node in by_id.items():
        children = node["children"]
        if node["terminal_proof"] is not None:
            proof = node["terminal_proof"]
            finite(proof["value_stm"])
            require(
                (proof["kind"] == "goal" and abs(proof["value_stm"]) == 2)
                or (proof["kind"] == "legal_third_repetition" and proof["value_stm"] == 0),
                "goal/draw proof domain",
            )
            require(
                proof["kind"] in ("goal", "legal_third_repetition")
                and proof["rules"] == "standard_2p_threefold_goal_first",
                "canonical terminal proof",
            )
            require(
                proof["value_stm"] in (-2, 0, 2) and not children, "terminal dominance/children"
            )
            require(
                all(value == proof["value_stm"] for value in node["values_stm"].values()),
                "exact terminal evaluator discrepancy",
            )
        elif node["ply"] < 2:
            actions = node["legal_actions"]
            require(
                actions == sorted(set(actions))
                and all(type(a) is int and 0 <= a <= 208 for a in actions),
                "complete legal action set",
            )
            require(
                sorted(c["action"] for c in children) == actions and len(children) > 0,
                "missing/extra legal response",
            )
            for child in children:
                require(child["node_id"] in by_id, "missing child")
                target = by_id[child["node_id"]]
                require(
                    target["parent"] == node_id and target["ply"] == node["ply"] + 1,
                    "tree chronology",
                )
                incoming[child["node_id"]] += 1
            for evaluator in EVALUATORS:
                expected = max(-by_id[c["node_id"]]["values_stm"][evaluator] for c in children)
                require(abs(node["values_stm"][evaluator] - expected) <= 1e-6, "minimax/STM sign")
        else:
            require(
                not children and all(-1 <= v <= 1 for v in node["values_stm"].values()),
                "leaf depth/score",
            )
    require(
        all(incoming[node_id] == 1 for node_id in by_id if node_id != 0) and not incoming[0],
        "unreachable/shared child",
    )
    require(tree["root_values"] == by_id[0]["values_stm"], "root summary discrepancy")
    return {
        "family_id": tree["family_id"],
        "status": "COMPLETE",
        "root_values": tree["root_values"],
        "terminal_proofs": tree["terminal_proofs"],
        "scope": "ALLlegal completeness relies on separately qualified producer hierarchy/geometry; depth2 estimates are not labels",
    }


def analyze_packet(packet):
    """Future admitted saved execution; actual data is forbidden in source phase."""
    require(packet["schema"] == "quoridor.strength355.joint-input.v1", "joint schema")
    require(packet["plan_SHA256"] == PLAN_SHA, "joint current plan")
    require(packet["provenance"] == packet["book"]["provenance"], "synthetic relabel")
    binding = packet["producer_bindings"]
    require(
        binding["book_SHA256"] == check_book(packet["book"])
        and binding["schedule_SHA256"] == check_schedule(packet["schedule"], packet["book"]),
        "joint producer identity",
    )
    for stage in ("arena", "engineering"):
        identity = binding[stage]
        for key in (
            "source_SHA256",
            "private_SHA256",
            "qualification_receipt_SHA256",
            "stopped_input_index_SHA256",
        ):
            sha(identity[key])
        require(
            identity["rules"] == "standard_2p_threefold_goal_first"
            and identity["clock"] == "authority-action-receipt-v1",
            "stage context",
        )
    games = aggregate_games(packet["book"], packet["schedule"], packet["games"])
    matched = check_matched(packet["book"], packet["matched"])
    require(
        len(packet["trees"]) <= 8
        and len({t["family_id"] for t in packet["trees"]}) == len(packet["trees"]),
        "common tree denominator",
    )
    require(
        sum(t["expanded_plus_leaf_nodes"] for t in packet["trees"]) <= 800000, "tree node aggregate"
    )
    trees = [check_tree(tree) for tree in packet["trees"]]
    if packet["selection"] is None:
        require(packet["stronger"] is None, "unfrozen stronger outcomes")
        stronger = {
            "status": "UNKNOWN",
            "reason": "selection/stronger unentered",
            "campaign_upper_calls": 192,
        }
    else:
        stronger = check_stronger(matched, packet["selection"], packet["stronger"])
    return {
        "schema": "quoridor.strength355.joint-summary.v1",
        "provenance": packet["provenance"],
        "plan_SHA256": PLAN_SHA,
        "producer_bindings": binding,
        "games": games,
        "matched": matched,
        "trees": trees,
        "unentered_tree_family_ids": sorted(set(TREE_IDS) - {t["family_id"] for t in trees}),
        "stronger": stronger,
        "partial_errors": packet["partial_errors"],
        "scope": "bounded current-rule/source/model context; no teacher/new objective/default/seed population/unique universal cause",
    }


def report(summary):
    lines = [
        "#355 stopped joint evidence",
        "",
        "Fixed prospective denominator:512 slots,256 per matchup,128 family units each. Missing slots stay UNKNOWN.",
        "",
        "|Matchup|Known/planned|Complete pairs|Conditional score|97.5% interval|Planned missingness bounds|",
        "|---|---:|---:|---:|---|---|",
    ]
    for name in MATCHUPS:
        row = summary["games"]["matchups"][name]
        lines.append(
            f"|{name}|{row['known_games']}/256|{row['complete_pairs']}/128|{row['complete_pair_mean']}|{row['conditional_interval']['interval']}|{row['planned_score_missingness_bounds']}|"
        )
    lines += [
        "",
        "Intervals are conditional complete-family bootstrap summaries; shared initial state/generator, derived seeds and missingness prevent an IID or guaranteed familywise claim. Shared-family contrast is descriptive.",
        "",
        "Same-depth COMPLETE comparisons, common trees and stronger estimates are separate from same100ms game outcomes. Exact canonical terminal proofs are separate from deeper estimates/consensus; no teacher labels or universal defeat cause.",
        "",
        "Cost domains remain separate/nested, unavailable counters stay UNKNOWN, physical NNUE head calls are not inference-pump request counts. No arithmetic speed inference from differing work, no default/model/seed generalization or promotion.",
        "",
        "Independent consequential interpretation and source/private/current-image/whole-runtime proof are required in their actual scopes. No N/fits96/seals/323 pause change.",
    ]
    return "\n".join(lines) + "\n"


def adapt_generated_book(raw, artifact_sha256, provenance):
    """In-memory view of355.1's exact GeneratedBook; never selects/replays cases."""
    sha(artifact_sha256)
    require(
        raw["schema"] == "quoridor.value-search-strength.book.v1"
        and raw["plan_sha256"] == PLAN_SHA
        and raw["complete"] is True,
        "actual complete GeneratedBook/plan",
    )
    require(
        raw["rules"] == "research-standard-2p-threefold-goal-first-v1", "actual book current rules"
    )
    require(
        integer(raw["attempted"], 1, 1024) == len(raw["attempts"])
        and integer(raw["transitions"], 0, 16384) == sum(len(a["prefix"]) for a in raw["attempts"]),
        "generator attempted/transition ledger",
    )
    require(
        len(raw["old_open8_prefixes"]) == 8
        and digest(raw["old_open8_prefixes"])
        == "be50f486ccfdef3ae1c1bddde33d8369398a19c2a6ccd3d3324b64863f322dbc",
        "exact exclusion prefixes",
    )
    sha(raw["old_open8_sha256"])
    attempted = defaultdict(list)
    for attempt in raw["attempts"]:
        fid = integer(attempt["family_id"], 0, 127)
        aid = integer(attempt["attempt_id"], 0, 7)
        require(
            aid == len(attempted[fid]) and attempt["seed"] == 35520261009 + 8 * fid + aid,
            "attempt order/seed",
        )
        require(
            attempt["requested_plies"] == (4, 8, 12, 16)[fid // 32]
            and len(attempt["prefix"]) <= attempt["requested_plies"],
            "attempt horizon",
        )
        require(
            attempt["rejection"]
            in (
                None,
                "terminal",
                "legal_third_draw",
                "old_OPEN8",
                "duplicate_action_prefix",
                "duplicate_full_key_history",
            ),
            "attempt reason",
        )
        require(
            not attempted[fid] or attempted[fid][-1]["rejection"] is not None,
            "attempt after accepted case",
        )
        attempted[fid].append(attempt)
    require(
        [(a["family_id"], a["attempt_id"]) for a in raw["attempts"]]
        == sorted((a["family_id"], a["attempt_id"]) for a in raw["attempts"]),
        "canonical attempt chronology",
    )
    families = []
    for family in raw["families"]:
        fid = integer(family["family_id"], 0, 127)
        entries = attempted[fid]
        require(
            entries
            and entries[-1]["rejection"] is None
            and entries[-1]["prefix"] == family["prefix"]
            and entries[-1]["attempt_id"] == family["attempt_id"]
            and family["seed"] == entries[-1]["seed"],
            "first accepted attempt binding",
        )
        require(
            family["id"] == f"strength355-family-{fid:03d}"
            and family["prefix"] not in raw["old_open8_prefixes"],
            "family/exclusion identity",
        )
        require(
            family["root_key"] in dict(family["history_counts"]), "current root counted history"
        )
        families.append(
            {
                "family_id": fid,
                "attempt_id": family["attempt_id"],
                "root_key": family["root_key"],
                "prefix": family["prefix"],
                "prefix_SHA256": digest(family["prefix"]),
                "counted_history": family["history_counts"],
                "history_SHA256": digest(family["history_counts"]),
                "terminal": False,
                "current_rules": "standard_2p_threefold_goal_first",
                "lineage": {
                    "shared_root": "canonicalStandard2p-initial",
                    "family_seed": family["seed"],
                },
            }
        )
    result = {
        "schema": "quoridor.strength355.full-history-book.v1",
        "plan_SHA256": PLAN_SHA,
        "provenance": provenance,
        "source_book_SHA256": artifact_sha256,
        "families": families,
        "eligibility_scope": "supplied accepted complete GeneratedBook; current native generator/geometry qualification required, this adapter executes none",
    }
    check_book(result)
    return result


def adapt_schedule(raw_slots, book, raw_schedule_sha256):
    sha(raw_schedule_sha256)
    require(len(raw_slots) == 512, "actual ScheduledSlot count")
    slots = []
    for slot in raw_slots:
        integer(slot["matchup"], 0, 1)
        slots.append(
            {
                "slot_id": integer(slot["slot"], 0, 511),
                "batch_id": integer(slot["batch"], 0, 15),
                "matchup": MATCHUPS[slot["matchup"]],
                "family_id": integer(slot["family_id"], 0, 127),
                "candidate_colour": integer(slot["candidate_color"], 0, 1),
                "local_game": integer(slot["local_game"], 0, 31),
            }
        )
    result = {
        "schema": "quoridor.strength355.schedule.v1",
        "plan_SHA256": PLAN_SHA,
        "book_SHA256": check_book(book),
        "source_book_SHA256": book["source_book_SHA256"],
        "source_schedule_SHA256": raw_schedule_sha256,
        "slots": slots,
    }
    check_schedule(result, book)
    return result


def adapt_native_game(raw, native_planned_slot, batch_config, slot, book, schedule):
    """Join by actual batch/opening metadata, never by local family ordinal."""
    require(
        raw["game"] == native_planned_slot["game"] == slot["local_game"],
        "native local game binding",
    )
    require(
        raw["family"] == native_planned_slot["family"]
        and raw["candidate_color"]
        == native_planned_slot["candidate_color"]
        == slot["candidate_colour"],
        "actual native colour/family",
    )
    opening = batch_config["arena"]["book"]["openings"][slot["local_game"] // 2]
    require(
        opening["reference"]["settings"]["family_id"] == slot["family_id"], "global family join"
    )
    family = book["families"][slot["family_id"]]
    require(
        opening["prefix"] == native_planned_slot["opening"] == family["prefix"],
        "actual full prefix join",
    )
    require(
        batch_config["ruleset"] == "standard_2p_threefold"
        and batch_config["inference"] is None
        and batch_config["inference_cpu_core"] is None,
        "pureD/NN current runtime",
    )
    require(
        batch_config["arena"]["return_reserve_ms"] == 5
        and batch_config["arena"]["tt_entries"] == 4096
        and all(
            e["time_ms"] == 100 and e["depth"] == 64 and e["max_nodes"] == 1000000
            for e in batch_config["engines"]
        ),
        "actual identical search limits",
    )
    learned, baseline = batch_config["engines"]
    require(
        baseline["kind"] == "distance"
        and baseline["distance_a"] == 0
        and baseline["distance_b"] == 8
        and baseline["model"] is None,
        "actual fixedD Tanh factory API",
    )
    require(learned["kind"] == "nnue", "actual retainedNN51/freshNN43 condition")
    require(raw["status"] in ("goal", "draw", "unknown"), "native status schema")
    outcome = {
        key: raw[key]
        for key in (
            "started",
            "status",
            "winner",
            "reason",
            "failure",
            "plies",
            "moves",
            "observations",
        )
    }
    record = {
        "slot": slot,
        "schedule_SHA256": digest(schedule),
        "source_book_SHA256": book["source_book_SHA256"],
        "source_schedule_SHA256": schedule["source_schedule_SHA256"],
        "prefix_SHA256": family["prefix_SHA256"],
        "history_SHA256": family["history_SHA256"],
        "provenance": book["provenance"],
        "outcome": outcome,
        "native_local_family_scope": raw["family"],
    }
    check_game(record, slot, book, digest(schedule))
    return record
