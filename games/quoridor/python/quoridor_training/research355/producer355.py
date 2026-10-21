"""Adapters for the two stopped355 producer interfaces; no engine or model imports.

Normalization is in memory only. Physical file identities remain distinct from
normalized object digests. Geometry/current compiled proofs belong to producers.
"""

import strength355 as s

STATS_FIELDS = {
    "nodes",
    "evaluations",
    "terminal",
    "cutoffs",
    "tt_hits",
    "tt_probes",
    "tt_exact_hits",
    "tt_key_builds",
    "tt_history_items",
    "tt_key_history_capacity_bytes",
    "tt_hashes",
    "tt_usable_depth",
    "tt_order_only",
    "tt_collisions",
    "tt_replacements",
    "tt_capacity_skips",
    "tt_illegal_moves",
    "tt_retained_bytes",
    "tt_generation",
    "tt_cutoffs",
    "pvs_researches",
    "delta_updates",
    "policy_calls",
}


def root_matches(root, family):
    s.require(
        root["key"] == family["root_key"]
        and root["history"] == family["counted_history"]
        and root["ply"] == len(family["prefix"])
        and root["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and root["synthetic"] is False,
        "actual complete root/history context",
    )


def observed(raw, family, evaluator, depth):
    s.require(evaluator in s.EVALUATORS, "producer evaluator")
    status = raw["status"]
    s.require(status in ("COMPLETE", "INCOMPLETE_UNKNOWN", "UNKNOWN"), "observed status")
    requested = raw.get("requested_depth", depth)
    s.require(type(requested) is int and requested == depth, "observed depth request")
    row = {
        "family_id": family["family_id"],
        "evaluator": evaluator,
        "history_SHA256": family["history_SHA256"],
        "prefix_SHA256": family["prefix_SHA256"],
        "requested_depth": depth,
        "deepest_completed": raw.get("deepest_completed_depth", 0),
        "status": {"COMPLETE": "COMPLETE", "INCOMPLETE_UNKNOWN": "INCOMPLETE", "UNKNOWN": "ERROR"}[
            status
        ],
        "complete_requested": status == "COMPLETE",
        "action": raw.get("selected_action"),
        "value_stm": raw.get("value_stm"),
        "pv": raw.get("PV", []),
        "legal_action": raw.get("legal_action", False),
        "bound": "EXACT" if status == "COMPLETE" else "UNKNOWN",
        "value_perspective": "PARENT_STM",
        "score_units": "legacy-tanh-search-terminal2",
        "nodes": raw.get("nodes"),
        "terminal_strength": raw.get("terminal_strength"),
        "search_seconds": raw.get("Search_only_seconds"),
        # call_until_observation EXCLUDES later row IO/session drop. Do not
        # relabel it setup_search_drop_seconds or whole external job time.
        "call_until_observation_seconds": raw.get("call_until_observation_seconds"),
        "setup_seconds": raw.get("setup_seconds"),
        "returned_search_elapsed_seconds_nested": raw.get("returned_search_elapsed_seconds_nested"),
        "stop": raw.get("stop"),
        "full_invocation_stats": raw.get("full_invocation_stats"),
        "TT": raw.get("TT"),
        "original_error": raw.get("original_error"),
        "reserved_unknown_nodes": raw.get("reserved_unknown_nodes"),
        "parent_restored": raw.get("parent_restored"),
        "raw_observed": raw,
    }
    for key in (
        "Search_only_seconds",
        "setup_seconds",
        "call_until_observation_seconds",
        "returned_search_elapsed_seconds_nested",
    ):
        if raw.get(key) is not None:
            s.require(s.finite(raw[key]) >= 0, "producer time domain")
    if raw.get("reserved_unknown_nodes") is not None:
        s.integer(raw["reserved_unknown_nodes"], 0, 2000000 if depth == 4 else 8000000)
    if status != "UNKNOWN":
        s.require(raw["parent_restored"] is True, "producer parent restoration")
        stats = raw["full_invocation_stats"]
        s.require(type(stats) is dict and set(stats) == STATS_FIELDS, "full returned work record")
        for value in stats.values():
            s.integer(value)
        s.require(
            stats["nodes"] == row["nodes"] and stats["evaluations"] == raw["evaluations"],
            "work projection",
        )
    if status == "COMPLETE":
        s.require(
            raw["legal_PV"] is True and raw["PV_matches_selected_action"] is True,
            "complete action/PV coherence",
        )
        terminal = raw["terminal_strength"] == "EXACT_CANONICAL_TERMINAL"
        s.require(
            (terminal and raw["stop"] == "Terminal")
            or (not terminal and raw["stop"] == "DepthComplete"),
            "complete stop domain",
        )
    s.complete_depth(row, depth)
    return row


def search_row(raw, book, kind="matched"):
    fid = s.integer(raw["family"], 0, 127)
    family = book["families"][fid]
    s.require(raw["opening_id"] == f"strength355-family-{fid:03d}", "opening identity")
    if kind != "forced":
        if "root" in raw:
            root_matches(raw["root"], family)
        else:
            s.require(
                kind == "matched"
                and raw["observed"]["status"] == "UNKNOWN"
                and raw["book_sha256"] == book["source_book_SHA256"]
                and "root_error" in raw,
                "unsupported root stays unknown",
            )
        row = observed(raw["observed"], family, raw["engine"], 4 if kind == "matched" else 6)
        row["actual_root_verified"] = "root" in raw
        row["root_error"] = raw.get("root_error")
    else:
        root_matches(raw["parent_root"], family)
        s.require(
            raw["parent_total_depth"] == 6
            and raw["child_requested_depth"] == 5
            and raw["parent_restored"] is True,
            "forced current horizon/restoration",
        )
        action = s.integer(raw["forced_action"], 0, 208)
        child = raw["child_root"]
        s.require(
            child["ply"] == len(family["prefix"]) + 1
            and child["rules"] == raw["parent_root"]["rules"]
            and child["synthetic"] is False,
            "forced actual child chronology",
        )
        row = observed(raw["observed_child"], family, raw["engine"], 5)
        if row["status"] == "COMPLETE":
            value = -s.finite(row["value_stm"])
            s.require(s.finite(raw["parent_value_stm"]) == value, "forced child-parent STM sign")
            row["value_stm"] = value
            row["pv"] = [action, *row["pv"]]
            # Exact child terminal establishes this forced move, with its
            # available child horizon kept separately; no depth rescue.
            row["terminal_child_strength"] = row["terminal_strength"]
            row["terminal_strength"] = (
                "FORCED_CHILD_TERMINAL"
                if row["terminal_strength"] == "EXACT_CANONICAL_TERMINAL"
                else row["terminal_strength"]
            )
            row["deepest_completed"] += 1
        else:
            s.require(raw["parent_value_stm"] is None, "partial forced parent value")
        row["child_deepest_completed"] = raw["observed_child"].get("deepest_completed_depth")
        row["requested_depth"] = 6
        row["action"] = action
        row["legal_action"] = True  # qualified producer constructed this legal child
        row["child_depth"], row["total_depth"] = 5, 6
        row["child_root"] = child
    if kind != "matched":
        row.update(
            kind="forced" if kind == "forced" else "natural",
            forced_action=raw.get("forced_action"),
            source_selection_SHA256=s.sha(raw["selection_sha256"]),
        )
    return row


def frozen_selection(raw, matched_summary, book):
    s.require(
        raw["book_sha256"] == book["source_book_SHA256"]
        and raw["selected_before_stronger_outcomes"] is True
        and raw["matched_call_results_reused"] is True,
        "frozen shared selection",
    )
    expected = matched_summary["selection"]
    unions = {u["family_id"]: u["actions"] for u in expected["unions"]}
    wanted = [
        (c["family_id"], i)
        for i, name in enumerate(("BEST51", "BEST43"))
        for c in expected["first_differences"][name]
    ]
    actual = []
    for case in raw["cases"]:
        fid, matchup = s.integer(case["family"], 0, 127), s.integer(case["matchup"], 0, 1)
        s.require(
            fid in unions
            and sorted(case["actions"]) == unions[fid]
            and len(case["actions"]) == len(set(case["actions"])),
            "all qualified proposal union",
        )
        actual.append((fid, matchup))
    s.require(
        actual == sorted(wanted) and len(actual) == len(set(actual)),
        "first differences selection, no replacement",
    )
    order = list(dict.fromkeys(fid for fid, _ in actual))
    s.require(
        raw["unique_parent_order"] == order
        and raw["planned_natural6"] == 3 * len(unions)
        and raw["planned_forced5"] == 3 * sum(map(len, unions.values())),
        "fixed selected call counts/order",
    )
    return expected


def common_tree(raw, book):
    fid = s.integer(raw["family"], 0, 127)
    s.require(fid in s.TREE_IDS, "common tree selector")
    status = raw["status"]
    if status != "COMPLETE":
        s.require(
            status in ("INCOMPLETE_UNKNOWN", "UNKNOWN") and raw.get("minimax") is None,
            "partial common tree has no minimax",
        )
        return {
            "family_id": fid,
            "requested_depth": 2,
            "status": "INCOMPLETE",
            "reason": "producer partial tree",
            "expanded_plus_leaf_nodes": raw.get("nodes_attempted", 0),
            "primary_error": raw.get("original_error"),
            "raw_ref": raw.get("raw_ref"),
        }
    root_matches(raw["root"], book["families"][fid])
    nodes, proofs = [], []

    def append(parent, ply, values, edges, terminal):
        node_id = len(nodes)
        s.require(node_id < 100000 and len(values) == 3, "common node/value cap")
        values_map = dict(zip(s.EVALUATORS, values))
        proof = None
        if terminal is not None:
            s.require(s.finite(terminal) in (-1, 0, 1), "raw canonical terminal units")
            proof = {
                "kind": "legal_third_repetition" if terminal == 0 else "goal",
                "rules": "standard_2p_threefold_goal_first",
                "value_stm": 2 * terminal,
            }
            proofs.append(proof)
        node = {
            "node_id": node_id,
            "parent": parent,
            "ply": ply,
            "values_stm": values_map,
            "terminal_proof": proof,
            "children": [],
            "legal_actions": sorted(e["action"] for e in edges),
        }
        nodes.append(node)
        s.require(ply <= 2 and (ply < 2 or not edges), "common hierarchy horizon")
        for edge in edges:
            action = s.integer(edge["action"], 0, 208)
            child = append(
                node_id,
                ply + 1,
                [-s.finite(v) for v in edge["value_parent_stm"]],
                edge["responses"],
                edge["terminal_child"],
            )
            s.require(
                edge["leaf_count"] == sum(not n["children"] for n in nodes[child:]),
                "per-edge complete leaf census",
            )
            node["children"].append({"action": action, "node_id": child})
        return node_id

    append(None, 0, raw["values_stm"], raw["ALL_legal_firstmoves_responses"], None)
    leaves = sum(not n["children"] for n in nodes)
    s.require(len(nodes) == raw["nodes"] and leaves == raw["leaves"], "common expanded/leaf census")
    calls = s.integer(raw["actual_leaf_evaluator_calls"], 0, 300000)
    s.require(
        calls == 3 * sum(not n["children"] and n["terminal_proof"] is None for n in nodes),
        "terminal bypass vs three leaf evaluations",
    )
    result = {
        "family_id": fid,
        "requested_depth": 2,
        "status": "COMPLETE",
        "ALL_legal": True,
        "missing_responses": 0,
        "expanded_plus_leaf_nodes": len(nodes),
        "nodes": nodes,
        "root_values": nodes[0]["values_stm"],
        "terminal_proofs": proofs,
        "actual_leaf_evaluator_calls": calls,
        "whole_tree_seconds": s.finite(raw["whole_tree_seconds"]),
    }
    s.check_tree(result)
    return result


def census(raw, rows, maximum_calls, maximum_nodes):
    """Available work vs reserved Err liability; no unavailable counters invented."""
    for name in ("admitted_attempts", "actual_Search_invocations", "Ok_returns", "Err_returns"):
        s.integer(raw[name], 0, maximum_calls)
    s.require(
        raw["Ok_returns"] + raw["Err_returns"]
        == raw["actual_Search_invocations"]
        <= raw["admitted_attempts"],
        "return/invocation/admission census",
    )
    liability = s.integer(raw["nodes_or_unknown_liability"], 0, maximum_nodes)
    known = sum(r["nodes"] for r in rows if r.get("nodes") is not None)
    s.require(known <= liability, "known work cannot exceed whole reserved liability")
    return {
        **raw,
        "available_returned_nodes": known,
        "unavailable_node_work": "UNKNOWN",
        "reserved_minus_available": liability - known,
    }
