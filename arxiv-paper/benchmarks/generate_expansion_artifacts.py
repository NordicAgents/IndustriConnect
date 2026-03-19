from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ARXIV_PAPER = ROOT / "arxiv-paper"
GENERATED = ARXIV_PAPER / "generated"
FIGURES = ARXIV_PAPER / "figures"

RESULTS_PATH = GENERATED / "flagship_benchmark_results.json"
SUMMARY_PATH = GENERATED / "paper_metrics_summary.json"
UI_SCREENSHOT_PATH = GENERATED / "mcp_manager_ui_real.png"
PROTOCOL_MAP_PATH = FIGURES / "fig3_protocol_map.png"
SUPPORT_CONTEXT_PATH = FIGURES / "fig2_support_context.png"
RECOVERY_BREAKDOWN_PATH = FIGURES / "fig4_recovery_breakdown.png"

TASK_ORDER = [
    "M1",
    "M2",
    "M3",
    "M4",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "O1",
    "O2",
    "O3",
    "O4",
    "X1",
    "X2",
    "X1p",
    "X2p",
]

FAULT_TASK_ORDER = [
    "FM1",
    "FM2",
    "FQ1",
    "FQ2",
    "FO1",
    "FO2",
    "FX1",
]

ERROR_DIST_PATH = FIGURES / "fig6_error_distribution.png"

PROTOCOL_DETAILS = {
    "Modbus": {
        "mock_endpoint": "TCP mock device",
        "operation_class": "register and coil I/O",
    },
    "MQTT + Sparkplug B": {
        "mock_endpoint": "broker simulator",
        "operation_class": "publish, subscribe, Sparkplug DDATA",
    },
    "OPC UA": {
        "mock_endpoint": "local OPC UA server",
        "operation_class": "browse, node read/write",
    },
    "BACnet/IP": {
        "mock_endpoint": "BACnet mock device",
        "operation_class": "object property access",
    },
    "DNP3": {
        "mock_endpoint": "mock outstation",
        "operation_class": "point poll and control",
    },
    "EtherCAT": {
        "mock_endpoint": "mock slave",
        "operation_class": "PDO and SDO access",
    },
    "EtherNet/IP": {
        "mock_endpoint": "mock PLC",
        "operation_class": "controller tag access",
    },
    "PROFIBUS DP/PA": {
        "mock_endpoint": "mock slave",
        "operation_class": "bus scan and cyclic I/O",
    },
    "PROFINET": {
        "mock_endpoint": "mock IO device",
        "operation_class": "discovery and IO exchange",
    },
    "Siemens S7comm": {
        "mock_endpoint": "mock PLC",
        "operation_class": "DB, I/O, diagnostics",
    },
}


def percentile(values: List[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = (len(ordered) - 1) * (pct / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    value = ordered[lower] * (1.0 - weight) + ordered[upper] * weight
    return round(value, 3)


def load_results() -> Dict[str, Any]:
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def build_protocol_rows(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    inventory = {
        row["protocol"]: row
        for row in results["protocol_inventory"]
    }
    rows = []
    for protocol in PROTOCOL_DETAILS:
        row = inventory[protocol]
        rows.append(
            {
                "protocol": protocol,
                "tool_count": row["tool_count"],
                "evaluation_status": row["maturity"],
                "mock_endpoint": PROTOCOL_DETAILS[protocol]["mock_endpoint"],
                "operation_class": PROTOCOL_DETAILS[protocol]["operation_class"],
            }
        )
    return rows


def build_task_rows(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_task = results["normal_summary"]["by_task"]
    rows = []
    for task_id in TASK_ORDER:
        summary = by_task[task_id]
        rows.append(
            {
                "task_id": task_id,
                "family": summary["family"],
                "description": summary["description"],
                "median_latency_ms": summary["median_latency_ms"],
                "p95_latency_ms": summary["p95_latency_ms"],
            }
        )
    return rows


def build_recovery_rows(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    trials_by_family = results["recovery_trials"]
    summary = results["recovery_summary"]
    for family in ("Modbus", "MQTT", "OPC UA"):
        trials = trials_by_family[family]
        failure_phase = [
            float((trial["failure_result"].get("meta") or {}).get("wall_clock_ms", 0.0))
            for trial in trials
        ]
        recovery_phase = [
            max(float(trial["trial_latency_ms"]) - float((trial["failure_result"].get("meta") or {}).get("wall_clock_ms", 0.0)), 0.0)
            for trial in trials
        ]
        healthy_call = [
            float((trial["success_result"].get("meta") or {}).get("wall_clock_ms", 0.0))
            for trial in trials
        ]
        rows.append(
            {
                "family": family,
                "outage_detection_rate": summary[family]["outage_detection_rate"],
                "recovery_success_rate": summary[family]["recovery_success_rate"],
                "median_failure_phase_ms": round(statistics.median(failure_phase), 3),
                "median_restart_to_healthy_ms": round(statistics.median(recovery_phase), 3),
                "median_healthy_call_ms": round(statistics.median(healthy_call), 3),
                "median_total_trial_ms": summary[family]["median_trial_latency_ms"],
            }
        )
    return rows


def build_fault_task_rows(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    fault_summary = results.get("fault_injection_summary", {})
    by_task = fault_summary.get("by_task", {})
    rows = []
    for task_id in FAULT_TASK_ORDER:
        if task_id not in by_task:
            continue
        summary = by_task[task_id]
        rows.append(
            {
                "task_id": task_id,
                "family": summary["family"],
                "description": summary["description"],
                "error_handling_rate": summary["error_handling_rate"],
                "median_latency_ms": summary["median_latency_ms"],
                "p95_latency_ms": summary["p95_latency_ms"],
                "error_class_distribution": summary["error_class_distribution"],
            }
        )
    return rows


def write_summary_json(results: Dict[str, Any]) -> Dict[str, Any]:
    fault_rows = build_fault_task_rows(results)
    fault_summary = results.get("fault_injection_summary", {})
    summary = {
        "generated_from": str(RESULTS_PATH.relative_to(ROOT)),
        "protocol_rows": build_protocol_rows(results),
        "family_rows": results["normal_summary"]["by_family"],
        "task_rows": build_task_rows(results),
        "fault_task_rows": fault_rows,
        "fault_overall": {
            "overall_error_handling_rate": fault_summary.get("overall_error_handling_rate", 0.0),
            "total_runs": fault_summary.get("total_runs", 0),
            "total_tool_calls": fault_summary.get("total_tool_calls", 0),
        },
        "recovery_phase_rows": build_recovery_rows(results),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def render_protocol_map(protocol_rows: List[Dict[str, Any]]) -> None:
    flagship = [row for row in protocol_rows if row["evaluation_status"] == "evaluated flagship"]
    scaffolds = [row for row in protocol_rows if row["evaluation_status"] != "evaluated flagship"]

    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=300)
    ax.set_xlim(-6.4, 6.4)
    ax.set_ylim(-5.1, 5.2)
    ax.axis("off")

    hub = FancyBboxPatch(
        (-1.9, -0.9),
        3.8,
        1.8,
        boxstyle="round,pad=0.02,rounding_size=0.24",
        linewidth=1.8,
        edgecolor="#3a4a5a",
        facecolor="#e8eef4",
    )
    ax.add_patch(hub)
    ax.text(0, 0.18, "IndustriConnect", ha="center", va="center", fontsize=15, weight="bold", color="#22313f")
    ax.text(0, -0.28, "MCP adapter ecosystem", ha="center", va="center", fontsize=9.5, color="#4c5b68")

    points = [
        ("Modbus", (0.0, 4.0)),
        ("MQTT + Sparkplug B", (3.8, 2.8)),
        ("OPC UA", (5.0, 0.0)),
        ("BACnet/IP", (3.7, -2.7)),
        ("DNP3", (0.0, -4.1)),
        ("EtherCAT", (-3.7, -2.7)),
        ("EtherNet/IP", (-5.1, 0.0)),
        ("PROFIBUS DP/PA", (-3.8, 2.8)),
        ("PROFINET", (2.4, -4.0)),
        ("Siemens S7comm", (-2.4, -4.0)),
    ]

    flagship_style = {"facecolor": "#d7ecf4", "edgecolor": "#1f5f82", "text": "#123e58"}
    scaffold_style = {"facecolor": "#edf1f5", "edgecolor": "#708090", "text": "#314252"}

    for protocol, (x, y) in points:
        row = next(item for item in protocol_rows if item["protocol"] == protocol)
        style = flagship_style if row["evaluation_status"] == "evaluated flagship" else scaffold_style
        ax.plot([0, x], [0, y], color="#8d99a6", linewidth=1.2, zorder=0)
        width = 2.8 if len(protocol) < 12 else 3.35
        box = FancyBboxPatch(
            (x - width / 2.0, y - 0.52),
            width,
            1.04,
            boxstyle="round,pad=0.02,rounding_size=0.18",
            linewidth=1.35,
            edgecolor=style["edgecolor"],
            facecolor=style["facecolor"],
            linestyle="solid" if row["evaluation_status"] == "evaluated flagship" else (0, (4, 2)),
        )
        ax.add_patch(box)
        ax.text(x, y + 0.04, protocol, ha="center", va="center", fontsize=10.5, color=style["text"], weight="bold")

    legend_x = -6.0
    legend_y = -4.85
    ax.add_patch(FancyBboxPatch((legend_x, legend_y), 0.42, 0.24, boxstyle="round,pad=0.02,rounding_size=0.05", facecolor=flagship_style["facecolor"], edgecolor=flagship_style["edgecolor"], linewidth=1.2))
    ax.text(legend_x + 0.56, legend_y + 0.12, "evaluated flagship", va="center", ha="left", fontsize=8.7, color="#314252")
    ax.add_patch(FancyBboxPatch((legend_x + 2.55, legend_y), 0.42, 0.24, boxstyle="round,pad=0.02,rounding_size=0.05", facecolor=scaffold_style["facecolor"], edgecolor=scaffold_style["edgecolor"], linewidth=1.2, linestyle=(0, (4, 2))))
    ax.text(legend_x + 3.10, legend_y + 0.12, "roadmap/scaffold", va="center", ha="left", fontsize=8.7, color="#314252")

    fig.tight_layout(pad=0.25)
    fig.savefig(PROTOCOL_MAP_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    if bold:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        ] + candidates

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_support_context_figure() -> None:
    if not UI_SCREENSHOT_PATH.exists() or not PROTOCOL_MAP_PATH.exists():
        return

    protocol_map = Image.open(PROTOCOL_MAP_PATH).convert("RGB")
    ui = Image.open(UI_SCREENSHOT_PATH).convert("RGB")

    left_panel = Image.new("RGB", (1350, 1000), "white")
    left_map = protocol_map.copy()
    left_map.thumbnail((1230, 860))
    left_panel.paste(left_map, ((left_panel.width - left_map.width) // 2, 110))

    right_panel = Image.new("RGB", (1650, 1000), "white")
    ui_crop = ui.crop((0, 0, ui.width, int(ui.height * 0.95)))
    ui_crop.thumbnail((1510, 860))
    right_panel.paste(ui_crop, ((right_panel.width - ui_crop.width) // 2, 110))

    canvas = Image.new("RGB", (3120, 1120), "white")
    draw = ImageDraw.Draw(canvas)
    label_font = _load_font(34, bold=True)
    title_font = _load_font(28, bold=True)
    subtitle_font = _load_font(22)

    canvas.paste(left_panel, (40, 70))
    canvas.paste(right_panel, (1430, 70))

    draw.text((60, 20), "(a)", fill="#1b2838", font=label_font)
    draw.text((160, 24), "Protocol coverage and evaluation status", fill="#1b2838", font=title_font)
    draw.text((1450, 20), "(b)", fill="#1b2838", font=label_font)
    draw.text((1550, 24), "Real MCP Manager UI screenshot", fill="#1b2838", font=title_font)
    draw.text((1550, 1060), "Operator/developer console for registering protocol adapters; shown for context only.", fill="#4f5d6b", font=subtitle_font)
    draw.text((160, 1060), "Ten protocol modules are present in the repository; highlighted cards mark the three evaluated flagships.", fill="#4f5d6b", font=subtitle_font)

    canvas.save(SUPPORT_CONTEXT_PATH, format="PNG")


def render_recovery_breakdown_figure(recovery_rows: List[Dict[str, Any]], recovery_reps: int = 20) -> None:
    labels = [row["family"] for row in recovery_rows]
    failure = [row["median_failure_phase_ms"] / 1000.0 for row in recovery_rows]
    restart = [row["median_restart_to_healthy_ms"] / 1000.0 for row in recovery_rows]

    fig, ax = plt.subplots(figsize=(7.0, 3.1), dpi=300)
    colors = {"failure": "#7a8aa0", "restart": "#2f6eaa"}
    bars_failure = ax.bar(labels, failure, color=colors["failure"], width=0.62, label="outage detection and failed call")
    bars_restart = ax.bar(labels, restart, bottom=failure, color=colors["restart"], width=0.62, label="restart to healthy response")

    ax.set_ylabel("Median recovery time (s)")
    ax.set_title(f"Recovery phase breakdown over {recovery_reps} restart trials per flagship adapter")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="upper left")

    for fail_bar, restart_bar, fail_seconds, restart_seconds in zip(bars_failure, bars_restart, failure, restart):
        total_seconds = fail_seconds + restart_seconds
        ax.text(
            fail_bar.get_x() + fail_bar.get_width() / 2.0,
            total_seconds + 0.08,
            f"{total_seconds:.2f}s",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
        ax.text(
            fail_bar.get_x() + fail_bar.get_width() / 2.0,
            fail_seconds / 2.0,
            f"{fail_seconds:.2f}",
            ha="center",
            va="center",
            fontsize=8,
            color="white",
        )
        ax.text(
            restart_bar.get_x() + restart_bar.get_width() / 2.0,
            fail_seconds + restart_seconds / 2.0,
            f"{restart_seconds:.2f}",
            ha="center",
            va="center",
            fontsize=8,
            color="white",
        )

    ax.set_ylim(0.0, max(f + r for f, r in zip(failure, restart)) * 1.23)
    fig.tight_layout()
    fig.savefig(RECOVERY_BREAKDOWN_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def render_error_distribution_figure(fault_task_rows: List[Dict[str, Any]], fault_reps: int = 30) -> None:
    if not fault_task_rows:
        return

    all_classes = set()
    for row in fault_task_rows:
        all_classes.update(row.get("error_class_distribution", {}).keys())
    all_classes = sorted(all_classes)
    if not all_classes:
        return

    class_colors = {
        "protocol_error": "#B45309",
        "illegal_address": "#DC2626",
        "type_mismatch": "#7C3AED",
        "invalid_input": "#2563EB",
        "guarded_write": "#0F766E",
        "endpoint_unavailable": "#6B7280",
        "timeout": "#D97706",
        "other": "#9CA3AF",
    }

    task_ids = [row["task_id"] for row in fault_task_rows]
    fig, ax = plt.subplots(figsize=(7.0, 3.4), dpi=300)
    bottoms = [0.0] * len(task_ids)

    for cls in all_classes:
        values = [
            row.get("error_class_distribution", {}).get(cls, 0) for row in fault_task_rows
        ]
        color = class_colors.get(cls, "#9CA3AF")
        ax.bar(task_ids, values, bottom=bottoms, color=color, width=0.62, label=cls.replace("_", " "))
        bottoms = [b + v for b, v in zip(bottoms, values)]

    ax.set_ylabel(f"Error occurrences ({fault_reps} runs)")
    ax.set_title("Error class distribution across fault-injected tasks")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right", ncol=2)

    ax.set_ylim(0, max(bottoms) * 1.2 if max(bottoms) > 0 else 10)
    fig.tight_layout()
    fig.savefig(ERROR_DIST_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    GENERATED.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)

    results = load_results()
    rep_counts = results.get("repetition_counts", {})
    summary = write_summary_json(results)
    render_protocol_map(summary["protocol_rows"])
    render_support_context_figure()
    render_recovery_breakdown_figure(
        summary["recovery_phase_rows"],
        recovery_reps=rep_counts.get("recovery", 20),
    )
    render_error_distribution_figure(
        summary.get("fault_task_rows", []),
        fault_reps=rep_counts.get("fault", 30),
    )

    print(f"Wrote summary JSON to {SUMMARY_PATH}")
    print(f"Wrote protocol map to {PROTOCOL_MAP_PATH}")
    print(f"Wrote support context figure to {SUPPORT_CONTEXT_PATH}")
    print(f"Wrote recovery breakdown figure to {RECOVERY_BREAKDOWN_PATH}")
    if summary.get("fault_task_rows"):
        print(f"Wrote error distribution figure to {ERROR_DIST_PATH}")


if __name__ == "__main__":
    main()
