"""Recorded training observations as standalone SVG; stdlib only, no inference."""

from collections import defaultdict
from html import escape
import math
from pathlib import Path


def _number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _ticks(maximum, count=5):
    rough = maximum / count
    exponent = 10 ** math.floor(math.log10(rough)) if rough else 1
    step = next(v * exponent for v in (1, 2, 5, 10) if v * exponent >= rough)
    return [i * step for i in range(math.ceil(maximum / step) + 1)]


def _label(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.3g}"


def render_learning_curves(
    curves,
    path,
    *,
    selected_step=None,
    references=None,
    sampling=None,
    title="Recorded learning observations",
):
    """Render measured points only; the caller supplies the frozen selection step."""
    references = references or {}
    records = sorted(curves, key=lambda p: p["step"])
    if any(not _number(p.get("step")) or p["step"] < 0 for p in records):
        raise ValueError("recorded optimizer steps must be finite and nonnegative")
    width, height = 1120, 720
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>" + escape(title) + "</title>",
        "<desc>Markers are recorded measurements. Lines only guide between recorded points, not measured interpolation. No heldout labels are read.</desc>",
        '<rect width="1120" height="720" fill="#fff"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#233247} .tick{font-size:12px} .legend{font-size:13px} .axis{stroke:#718096;stroke-width:1} .grid{stroke:#e6ebf1;stroke-width:1}</style>",
        f'<text x="58" y="34" font-size="21" font-weight="600">{escape(title)}</text>',
    ]
    actual_epochs = sampling == "epoch" or (
        sampling is None and records and all(p.get("completed_epochs") is not None for p in records)
    )
    exposure_label = (
        "Actual epochs (completed + partial)"
        if actual_epochs
        else "Equivalent random row-passes (not complete epochs)"
    )
    out.append(
        f'<text x="58" y="58" font-size="13">{escape(exposure_label)}; exposure labels below are recorded values.</text>'
    )
    colors = {
        "full_train": "#0079a8",
        "fixed_diagnostic_subset": "#1768c5",
        "train_scope_unavailable": "#67778b",
        "full_selector": "#ce3945",
        "validation_diagnostic_subset": "#ab569a",
    }
    labels = {
        "full_train": "Train: full corpus (separate scope)",
        "fixed_diagnostic_subset": "Train: fixed diagnostic subset",
        "train_scope_unavailable": "Train: scope unavailable",
        "full_selector": "Validation: full selector",
        "validation_diagnostic_subset": "Validation: diagnostic subset",
    }

    def scope(point, part):
        if part == "train":
            if point.get("scope") == "fixed_target_blind_subset":
                return "fixed_diagnostic_subset"
            current = point.get("train_scope", "train_scope_unavailable")
            return current if current in colors else "train_scope_unavailable"
        return (
            "validation_diagnostic_subset"
            if point.get("used_for_selection") is False
            else "full_selector"
        )

    def reference(point, part, kind, field):
        metric = point.get(part, {})
        if kind == "constant":
            return metric.get(
                "constant_game_equal_mse" if field == "target_game_equal_mse" else "constant_mse"
            )
        direct = metric.get("distance")
        ref = references.get(metric.get("distance_ref"), {})
        return (direct or ref.get("distance", {})).get(field)

    measured_count, selected_count = 0, 0
    for panel, (field, heading) in enumerate(
        [
            ("target_game_equal_mse", "Group / family-equal MSE"),
            ("target_mse", "Row MSE"),
        ]
    ):
        left, top, plot_w, plot_h = 84 + panel * 550, 126, 438, 330
        series, baselines = defaultdict(list), defaultdict(list)
        for point in records:
            for part in ("train", "validation"):
                current_scope = scope(point, part)
                value = point.get(part, {}).get(field)
                if _number(value) and value >= 0:
                    series[current_scope].append((point, value))
                for kind in ("distance", "constant"):
                    value = reference(point, part, kind, field)
                    if _number(value) and value >= 0:
                        # The reference-set identity prevents mixing fixed subsets/full corpus.
                        key = (
                            current_scope,
                            kind,
                            point.get(part, {}).get("distance_ref", current_scope),
                        )
                        baselines[key].append((point["step"], value))
        ys = [v for values in series.values() for _, v in values]
        ys += [v for values in baselines.values() for _, v in values]
        yticks = _ticks(max(ys, default=1) * 1.08 or 1)
        ymax = yticks[-1] or 1
        xticks = _ticks(max((p["step"] for p in records), default=1) or 1)
        xmax = xticks[-1] or 1
        x = lambda step: left + plot_w * step / xmax
        y = lambda value: top + plot_h * (1 - value / ymax)
        out.append(f'<g class="panel" data-metric="{field}">')
        out.append(f'<text x="{left}" y="102" font-size="17" font-weight="600">{heading}</text>')
        for tick in yticks:
            yy = y(tick)
            out += [
                f'<line class="grid" x1="{left}" x2="{left + plot_w}" y1="{yy:.2f}" y2="{yy:.2f}"/>',
                f'<text class="tick y-tick" x="{left - 12}" y="{yy + 4:.2f}" text-anchor="end">{_label(tick)}</text>',
            ]
        for tick in xticks:
            xx = x(tick)
            out += [
                f'<line class="grid" x1="{xx:.2f}" x2="{xx:.2f}" y1="{top}" y2="{top + plot_h}"/>',
                f'<text class="tick x-tick" x="{xx:.2f}" y="{top + plot_h + 22}" text-anchor="middle">{_label(tick)}</text>',
            ]
        out += [
            f'<path class="axis" d="M{left} {top}V{top + plot_h}H{left + plot_w}" fill="none"/>',
            f'<text x="{left + plot_w / 2}" y="{top + plot_h + 47}" text-anchor="middle" font-size="14">Actual optimizer steps</text>',
            f'<text transform="translate({left - 58},{top + plot_h / 2}) rotate(-90)" text-anchor="middle" font-size="13">Recorded MSE</text>',
        ]
        # Secondary labels use actual recorded points, not interpolated exposure.
        labeled_x = -math.inf
        for point in records:
            xx = x(point["step"])
            if xx - labeled_x < 260 or not _number(point.get("training_seen")):
                continue
            passes = point.get("row_epoch")
            suffix = (
                f" / {_label(passes)} {'epochs' if actual_epochs else 'passes'}"
                if _number(passes)
                else ""
            )
            anchor = "end" if xx > left + plot_w - 160 else "start"
            out.append(
                f'<text class="tick exposure-tick" data-step="{point["step"]}" x="{xx:.2f}" y="{top - 10}" text-anchor="{anchor}">seen {_label(point["training_seen"])}{suffix}</text>'
            )
            labeled_x = xx
        for (current_scope, kind, _), values in baselines.items():
            color = colors.get(current_scope, "#67778b")
            dash = "2 5" if kind == "distance" else "8 5"
            points = " ".join(f"{x(step):.2f},{y(value):.2f}" for step, value in values)
            out.append(
                f'<polyline class="baseline" data-scope="{current_scope}" data-kind="{kind}" points="{points}" fill="none" stroke="{color}" stroke-opacity=".45" stroke-dasharray="{dash}"/>'
            )
        for current_scope, values in series.items():
            color = colors.get(current_scope, "#67778b")
            points = " ".join(f"{x(p['step']):.2f},{y(value):.2f}" for p, value in values)
            # Full-train endpoints are separate measured markers, never a subset trajectory.
            if current_scope != "full_train" and len(values) > 1:
                out.append(
                    f'<polyline class="recorded-guide" data-scope="{current_scope}" points="{points}" fill="none" stroke="{color}" stroke-width="1.8"/>'
                )
            for point, value in values:
                xx, yy = x(point["step"]), y(value)
                attrs = f'class="measured-point" data-scope="{current_scope}" data-step="{point["step"]}" data-seen="{escape(str(point.get("training_seen", "unavailable")))}"'
                if current_scope == "full_train":
                    out.append(
                        f'<path {attrs} d="M{xx:.2f},{yy - 5:.2f}l5,5 -5,5 -5,-5z" fill="{color}"/>'
                    )
                else:
                    out.append(
                        f'<circle {attrs} cx="{xx:.2f}" cy="{yy:.2f}" r="3" fill="{color}"/>'
                    )
                measured_count += 1
                if point["step"] == selected_step and current_scope == "full_selector":
                    out.append(
                        f'<circle class="selected-marker" data-step="{point["step"]}" cx="{xx:.2f}" cy="{yy:.2f}" r="7" fill="none" stroke="#202a38" stroke-width="2"/>'
                    )
                    out.append(
                        f'<text class="selected-label" x="{xx - 8:.2f}" y="{yy - 13:.2f}" text-anchor="end" font-size="12">Selected step {point["step"]}</text>'
                    )
                    selected_count += 1
        if not series:
            out.append(
                f'<text class="empty-state" x="{left + plot_w / 2}" y="{top + plot_h / 2}" text-anchor="middle" font-size="16">No completed measurements</text>'
            )
        out.append("</g>")
    legend_scopes = []
    for point in records:
        for part in ("train", "validation"):
            current = scope(point, part)
            if current not in legend_scopes:
                legend_scopes.append(current)
    for i, current in enumerate(legend_scopes):
        row, column = divmod(i, 2)
        xx, yy = 84 + column * 550, 532 + row * 24
        out += [
            f'<circle cx="{xx}" cy="{yy - 4}" r="4" fill="{colors.get(current, "#67778b")}"/>',
            f'<text class="legend" x="{xx + 13}" y="{yy}">{escape(labels.get(current, current))}</text>',
        ]
    out.append(
        '<text class="legend" x="84" y="614">Reference guides: dotted = analytic D; dashed = train-only constant; colors retain measurement scope.</text>'
    )
    if records:
        last = records[-1]
        chosen = next((p for p in records if p["step"] == selected_step), None)
        pieces = [
            f"Executed: step {last['step']}, seen {last.get('training_seen', 'unavailable')}, {'epochs' if actual_epochs else 'equivalent passes'} {_label(last['row_epoch']) if _number(last.get('row_epoch')) else 'unavailable'}",
            f"Selected: step {selected_step}, seen {chosen.get('training_seen', 'unavailable')}"
            if chosen
            else "Selection marker unavailable (no recorded selector point supplied)",
        ]
        out.append(f'<text class="legend" x="84" y="642">{escape(" | ".join(pieces))}</text>')
        sign = (chosen or last).get("validation", {}).get("z_sign_accuracy")
        sign_text = (
            f"Recorded validation row sign accuracy: {sign:.4f}; group sign not supplied"
            if _number(sign)
            else "Validation row/group sign: unavailable; missing eligible z is not zero accuracy"
        )
        out.append(f'<text class="legend" x="84" y="665">{escape(sign_text)}</text>')
    out.append(
        '<text x="84" y="690" font-size="12">Lines guide recorded points only. Input groups do not establish independent games; validation selection is not heldout strength.</text>'
    )
    out.append("</svg>")
    Path(path).write_text("\n".join(out) + "\n")
    return {
        "measured_markers": measured_count,
        "selected_markers": selected_count,
        "records": len(records),
    }
