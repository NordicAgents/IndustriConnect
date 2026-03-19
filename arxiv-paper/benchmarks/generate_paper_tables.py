#!/usr/bin/env python3
"""Generate LaTeX table fragments from benchmark results JSON."""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
ARXIV_PAPER = ROOT / "arxiv-paper"
GENERATED = ARXIV_PAPER / "generated"
TABLES = GENERATED / "tables"

TASK_ORDER = ["M1", "M2", "M3", "M4", "Q1", "Q2", "Q3", "Q4", "O1", "O2", "O3", "O4", "X1", "X2", "X1p", "X2p"]
FAULT_ORDER = ["FM1", "FM2", "FQ1", "FQ2", "FO1", "FO2", "FX1"]
FAMILY_ORDER = ["Modbus", "MQTT", "OPC UA", "Cross-protocol"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Dict[str, Any] | None:
    """Load a JSON file, returning None if it does not exist."""
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _pct(value: float) -> str:
    """Format a 0-1 rate as a percentage string like '100.0'."""
    return f"{value * 100:.1f}"


def _ms(value: float) -> str:
    """Format a millisecond value to one decimal place."""
    return f"{value:.1f}"


def _t_critical(df: int, confidence: float = 0.95) -> float:
    """Approximate two-tailed t critical value for the given df and confidence.

    Uses scipy if available, otherwise falls back to a conservative manual
    lookup for common small-sample degrees of freedom.
    """
    try:
        from scipy.stats import t as t_dist

        alpha = 1.0 - confidence
        return float(t_dist.ppf(1.0 - alpha / 2.0, df))
    except ImportError:
        pass

    # Manual lookup table for two-tailed 95 % critical values.
    _table: Dict[int, float] = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        25: 2.060, 30: 2.042, 40: 2.021, 50: 2.009, 60: 2.000,
        80: 1.990, 100: 1.984, 200: 1.972,
    }
    if df in _table:
        return _table[df]
    # Find closest key above df
    for k in sorted(_table.keys()):
        if k >= df:
            return _table[k]
    return 1.960  # Normal approximation for large df


def _escape_latex(text: str) -> str:
    """Minimal LaTeX escaping for table cell content."""
    return text.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


def _safe_get(d: Dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    """Navigate nested dicts safely."""
    current: Any = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k, default)
    return current


# ---------------------------------------------------------------------------
# Table generators
# ---------------------------------------------------------------------------


def generate_tab_results(data: Dict[str, Any]) -> str:
    """Family-level normal results table (complete tabular environment)."""
    by_family = _safe_get(data, "normal_summary", "by_family", default={})
    recovery = _safe_get(data, "recovery_summary", default={})

    rows: List[str] = []
    for family in FAMILY_ORDER:
        fam = by_family.get(family)
        if fam is None:
            continue
        rec = recovery.get(family)
        rec_str = _pct(rec["recovery_success_rate"]) if rec else "---"

        rows.append(
            f"        {family} & {fam['tasks']} & {_pct(fam['task_success_rate'])} "
            f"& {_pct(fam['tool_call_success_rate'])} & {_ms(fam['median_latency_ms'])} "
            f"& {_ms(fam['p95_latency_ms'])} & {rec_str} \\\\"
        )

    lines = [
        r"    \begin{tabular}{@{}lcccccc@{}}",
        r"        \toprule",
        r"        Family & Tasks & Task & Tool & Med. & p95 & Rec. \\",
        r"        & & (\%) & (\%) & (ms) & (ms) & (\%) \\",
        r"        \midrule",
    ]
    lines.extend(rows)
    lines.append(r"        \bottomrule")
    lines.append(r"    \end{tabular}")
    return "\n".join(lines) + "\n"


def generate_tab_taskbreakdown(data: Dict[str, Any]) -> str:
    """Per-task latency breakdown table (complete tabularx environment)."""
    by_task = _safe_get(data, "normal_summary", "by_task", default={})

    rows: List[str] = []
    prev_family = None
    for tid in TASK_ORDER:
        t = by_task.get(tid)
        if t is None:
            continue
        if prev_family and t["family"] != prev_family:
            rows.append(r"        \midrule")
        prev_family = t["family"]
        desc = _escape_latex(t.get("description", ""))
        rows.append(
            f"        {tid} & {t['family']} & {desc} "
            f"& {_ms(t['median_latency_ms'])} & {_ms(t['p95_latency_ms'])} \\\\"
        )

    lines = [
        r"    \begin{tabularx}{\textwidth}{@{}llYcc@{}}",
        r"        \toprule",
        r"        ID & Family & Operation & Median (ms) & p95 (ms) \\",
        r"        \midrule",
    ]
    lines.extend(rows)
    lines.append(r"        \bottomrule")
    lines.append(r"    \end{tabularx}")
    return "\n".join(lines) + "\n"


def generate_tab_faultresults(data: Dict[str, Any]) -> str:
    """Fault injection results table (complete tabularx environment)."""
    by_task = _safe_get(data, "fault_injection_summary", "by_task", default={})

    rows: List[str] = []
    for tid in FAULT_ORDER:
        t = by_task.get(tid)
        if t is None:
            continue
        desc = _escape_latex(t.get("description", ""))
        dist = t.get("error_class_distribution", {})
        primary_class = max(dist, key=dist.get) if dist else "---"
        primary_class_escaped = _escape_latex(primary_class.replace("_", " "))

        rows.append(
            f"        {tid} & {t['family']} & {desc} "
            f"& {_pct(t['error_handling_rate'])} & {_ms(t['median_latency_ms'])} "
            f"& {primary_class_escaped} \\\\"
        )

    lines = [
        r"    \begin{tabularx}{\columnwidth}{@{}llYccc@{}}",
        r"        \toprule",
        r"        ID & Family & Fault scenario & EH\% & Med. (ms) & Error class \\",
        r"        \midrule",
    ]
    lines.extend(rows)
    lines.append(r"        \bottomrule")
    lines.append(r"    \end{tabularx}")
    return "\n".join(lines) + "\n"


def generate_tab_stress(data: Dict[str, Any]) -> str | None:
    """Stress suite results table (complete tabularx environment). Returns None if no stress data."""
    stress_summary = _safe_get(data, "stress_summary")
    stress_tasks = _safe_get(data, "stress_tasks")
    if not stress_summary and not stress_tasks:
        return None

    by_task = _safe_get(stress_summary, "by_task", default={})

    rows: List[str] = []

    if by_task:
        for tid in sorted(by_task.keys()):
            t = by_task[tid]
            desc = _escape_latex(t.get("description", ""))
            sr = _pct(t.get("success_rate", t.get("task_success_rate", 0)))
            rows.append(
                f"        {tid} & {t.get('family', '---')} & {desc} "
                f"& {sr} & {_ms(t.get('median_latency_ms', 0))} "
                f"& {_ms(t.get('p95_latency_ms', 0))} \\\\"
            )
    elif isinstance(stress_tasks, list) and stress_tasks:
        from collections import defaultdict
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for task in stress_tasks:
            groups[task.get("task_id", "?")].append(task)
        for tid in sorted(groups.keys()):
            task_rows = groups[tid]
            latencies = [r["task_latency_ms"] for r in task_rows]
            sr = sum(1 for r in task_rows if r.get("task_success")) / len(task_rows)
            med = statistics.median(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
            family = task_rows[0].get("family", "---")
            desc = _escape_latex(task_rows[0].get("description", ""))
            rows.append(
                f"        {tid} & {family} & {desc} "
                f"& {_pct(sr)} & {_ms(med)} & {_ms(p95)} \\\\"
            )

    if not rows:
        return None

    lines = [
        r"    \begin{tabularx}{\columnwidth}{@{}llYccc@{}}",
        r"        \toprule",
        r"        ID & Family & Scenario & SR (\%) & Med. (ms) & p95 (ms) \\",
        r"        \midrule",
    ]
    lines.extend(rows)
    lines.append(r"        \bottomrule")
    lines.append(r"    \end{tabularx}")
    return "\n".join(lines) + "\n"


def generate_tab_stats(data: Dict[str, Any]) -> str:
    """Variance statistics: mean, stddev, 95% CI for each task.

    Computed from raw normal_tasks grouped by task_id.

    Columns: Task ID | Family | N | Mean (ms) | Stddev (ms) | 95% CI low | 95% CI high
    """
    normal_tasks: List[Dict[str, Any]] = data.get("normal_tasks", [])

    # Group by task_id
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for task in normal_tasks:
        groups.setdefault(task["task_id"], []).append(task)

    lines: List[str] = []
    for tid in TASK_ORDER:
        rows = groups.get(tid)
        if not rows:
            continue
        latencies = [r["task_latency_ms"] for r in rows]
        n = len(latencies)
        mean = statistics.mean(latencies)
        family = rows[0]["family"]

        if n >= 2:
            sd = statistics.stdev(latencies)
            se = sd / math.sqrt(n)
            t_crit = _t_critical(n - 1)
            ci_lo = mean - t_crit * se
            ci_hi = mean + t_crit * se
        else:
            sd = 0.0
            ci_lo = mean
            ci_hi = mean

        lines.append(
            f"{tid} & {family} & {n} & {_ms(mean)} & {_ms(sd)} "
            f"& {_ms(ci_lo)} & {_ms(ci_hi)} \\\\"
        )

    return "\n".join(lines) + "\n"


def generate_tab_baseline(data: Dict[str, Any]) -> str | None:
    """Adapter overhead / baseline measurements.  Returns None if absent."""
    baseline = _safe_get(data, "baseline_measurements")
    if not baseline:
        return None

    lines: List[str] = []

    if isinstance(baseline, dict):
        # Expect something like {family: {raw_latency_ms, adapter_latency_ms, overhead_ms, overhead_pct}}
        for family in FAMILY_ORDER:
            b = baseline.get(family)
            if b is None:
                continue
            raw = _ms(b.get("raw_latency_ms", 0))
            adapter = _ms(b.get("adapter_latency_ms", 0))
            overhead = _ms(b.get("overhead_ms", 0))
            pct = f"{b.get('overhead_pct', 0):.1f}"
            lines.append(
                f"{family} & {raw} & {adapter} & {overhead} & {pct}\\% \\\\"
            )
    elif isinstance(baseline, list):
        for entry in baseline:
            family = entry.get("family", entry.get("protocol", "---"))
            raw = _ms(entry.get("raw_latency_ms", 0))
            adapter = _ms(entry.get("adapter_latency_ms", 0))
            overhead = _ms(entry.get("overhead_ms", 0))
            pct = f"{entry.get('overhead_pct', 0):.1f}"
            lines.append(
                f"{family} & {raw} & {adapter} & {overhead} & {pct}\\% \\\\"
            )

    if not lines:
        return None

    return "\n".join(lines) + "\n"


def generate_tab_llm_assessment(llm_data: Dict[str, Any] | None) -> str | None:
    """LLM assessment results table body.  Returns None if no data.

    Expected input format (from run_llm_assessment.py):
    {
      "models": {
        "claude-sonnet-4-20250514": {
          "discovery": {"recall": 0.95, ...},
          "tool_selection": {"accuracy": 0.93, ...},
          "parameter_correctness": {"accuracy": 0.87, "per_field_accuracy": 0.91, ...},
          "error_interpretation": {"accuracy": 0.90, ...}
        },
        ...
      }
    }

    Output: rows for a table with columns: Model | Discovery | Selection | Param. | Error Interp.
    """
    if not llm_data:
        return None

    models = llm_data.get("models", {})
    if not models:
        return None

    categories = ["discovery", "tool_selection", "parameter_correctness", "error_interpretation"]
    metric_keys = ["recall", "accuracy", "accuracy", "accuracy"]

    rows: List[str] = []
    for model_id, model_data in models.items():
        if not isinstance(model_data, dict):
            continue
        # Shorten model name for display
        short_name = model_id.replace("claude-", "").replace("-20250514", "").replace("-20251001", "")
        short_name = _escape_latex(short_name)

        values = []
        for cat, metric_key in zip(categories, metric_keys):
            cat_data = model_data.get(cat, {})
            val = cat_data.get(metric_key, cat_data.get("accuracy", 0.0))
            if isinstance(val, (int, float)):
                values.append(f"{val * 100:.1f}")
            else:
                values.append("---")

        rows.append(f"        {short_name} & {' & '.join(values)} \\\\")

    if not rows:
        return None

    lines = [
        r"    \begin{tabular}{@{}lcccc@{}}",
        r"        \toprule",
        r"        Model & Discovery & Selection & Param. & Error \\",
        r"        & recall (\%) & acc. (\%) & acc. (\%) & acc. (\%) \\",
        r"        \midrule",
    ]
    lines.extend(rows)
    lines.append(r"        \bottomrule")
    lines.append(r"    \end{tabular}")
    return "\n".join(lines) + "\n"


def generate_exact_counts(data: Dict[str, Any]) -> str:
    r"""Generate \newcommand definitions for exact run/call counts."""
    normal_tasks: List[Dict[str, Any]] = data.get("normal_tasks", [])
    fault_tasks: List[Dict[str, Any]] = data.get("fault_injection_tasks", [])
    stress_tasks: List[Dict[str, Any]] = data.get("stress_tasks", [])
    recovery_trials: Dict[str, List[Dict[str, Any]]] = data.get("recovery_trials", {})

    total_normal_runs = len(normal_tasks)
    total_fault_runs = len(fault_tasks)
    total_stress_runs = len(stress_tasks) if stress_tasks else 0
    total_recovery_trials = sum(len(trials) for trials in recovery_trials.values())
    total_runs = total_normal_runs + total_fault_runs + total_stress_runs + total_recovery_trials

    normal_tool_calls = sum(t.get("tool_calls", 0) for t in normal_tasks)
    fault_tool_calls = sum(t.get("tool_calls", 0) for t in fault_tasks)
    stress_tool_calls = sum(t.get("tool_calls", 0) for t in stress_tasks) if stress_tasks else 0
    total_tool_calls = normal_tool_calls + fault_tool_calls + stress_tool_calls

    # If the JSON carries pre-computed exact counts, prefer those
    exact_tc = data.get("exact_tool_call_counts", {})
    # Map the tool-call count keys to the run/call newcommand keys
    exact: Dict[str, Any] = {}
    if exact_tc:
        exact["normal_tool_calls"] = exact_tc.get("normal", normal_tool_calls)
        exact["fault_tool_calls"] = exact_tc.get("fault", fault_tool_calls)
        exact["stress_tool_calls"] = exact_tc.get("stress", stress_tool_calls)
        exact["total_tool_calls"] = exact_tc.get("total", total_tool_calls)

    # Per-protocol tool counts from protocol_inventory
    inventory = data.get("protocol_inventory", [])
    protocol_tool_counts: Dict[str, int] = {}
    for entry in inventory:
        proto = entry.get("protocol", "")
        count = entry.get("tool_count", 0)
        # Normalize protocol names to LaTeX-friendly identifiers
        if "modbus" in proto.lower():
            protocol_tool_counts["modbus"] = count
        elif "mqtt" in proto.lower():
            protocol_tool_counts["mqtt"] = count
        elif "opc" in proto.lower():
            protocol_tool_counts["opcua"] = count

    lines: List[str] = [
        f"\\newcommand{{\\totalNormalRuns}}{{{exact.get('total_normal_runs', total_normal_runs)}}}",
        f"\\newcommand{{\\totalFaultRuns}}{{{exact.get('total_fault_runs', total_fault_runs)}}}",
        f"\\newcommand{{\\totalStressRuns}}{{{exact.get('total_stress_runs', total_stress_runs)}}}",
        f"\\newcommand{{\\totalRecoveryTrials}}{{{exact.get('total_recovery_trials', total_recovery_trials)}}}",
        f"\\newcommand{{\\totalRuns}}{{{exact.get('total_runs', total_runs)}}}",
        f"\\newcommand{{\\totalToolCalls}}{{{exact.get('total_tool_calls', total_tool_calls)}}}",
        f"\\newcommand{{\\normalToolCalls}}{{{exact.get('normal_tool_calls', normal_tool_calls)}}}",
        f"\\newcommand{{\\faultToolCalls}}{{{exact.get('fault_tool_calls', fault_tool_calls)}}}",
        f"\\newcommand{{\\stressToolCalls}}{{{exact.get('stress_tool_calls', stress_tool_calls)}}}",
        f"\\newcommand{{\\modbusToolCount}}{{{protocol_tool_counts.get('modbus', 0)}}}",
        f"\\newcommand{{\\mqttToolCount}}{{{protocol_tool_counts.get('mqtt', 0)}}}",
        f"\\newcommand{{\\opcuaToolCount}}{{{protocol_tool_counts.get('opcua', 0)}}}",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)

    data = _load_json(GENERATED / "flagship_benchmark_results.json")
    if data is None:
        raise SystemExit("ERROR: flagship_benchmark_results.json not found in generated/")

    llm_data = _load_json(GENERATED / "llm_assessment_results.json")

    # 1. Family-level normal results
    (TABLES / "tab_results.tex").write_text(
        generate_tab_results(data), encoding="utf-8"
    )
    print("  wrote tab_results.tex")

    # 2. Per-task latency breakdown
    (TABLES / "tab_taskbreakdown.tex").write_text(
        generate_tab_taskbreakdown(data), encoding="utf-8"
    )
    print("  wrote tab_taskbreakdown.tex")

    # 3. Fault injection results
    (TABLES / "tab_faultresults.tex").write_text(
        generate_tab_faultresults(data), encoding="utf-8"
    )
    print("  wrote tab_faultresults.tex")

    # 4. Stress suite results (optional)
    stress = generate_tab_stress(data)
    if stress is not None:
        (TABLES / "tab_stress.tex").write_text(stress, encoding="utf-8")
        print("  wrote tab_stress.tex")
    else:
        print("  skipped tab_stress.tex (no stress data)")

    # 5. Variance statistics
    (TABLES / "tab_stats.tex").write_text(
        generate_tab_stats(data), encoding="utf-8"
    )
    print("  wrote tab_stats.tex")

    # 6. Baseline / adapter overhead (optional)
    baseline = generate_tab_baseline(data)
    if baseline is not None:
        (TABLES / "tab_baseline.tex").write_text(baseline, encoding="utf-8")
        print("  wrote tab_baseline.tex")
    else:
        print("  skipped tab_baseline.tex (no baseline data)")

    # 7. LLM assessment (optional)
    llm = generate_tab_llm_assessment(llm_data)
    if llm is not None:
        (TABLES / "tab_llm_assessment.tex").write_text(llm, encoding="utf-8")
        print("  wrote tab_llm_assessment.tex")
    else:
        print("  skipped tab_llm_assessment.tex (no LLM assessment data)")

    # 8. Exact counts as LaTeX newcommands
    (TABLES / "exact_counts.tex").write_text(
        generate_exact_counts(data), encoding="utf-8"
    )
    print("  wrote exact_counts.tex")

    print(f"\nAll tables written to {TABLES}/")


if __name__ == "__main__":
    main()
