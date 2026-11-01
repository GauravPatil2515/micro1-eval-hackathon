#!/usr/bin/env python3
"""
Failure Taxonomy Auto-Classifier for MechanismTrace-DDI
Module: Automatically classifies grader failure reasons into taxonomy categories
for analysis depth reporting (Section 7 of README).
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent

# Taxonomy categories with keyword patterns
TAXONOMY_PATTERNS = {
    "TRANSPORTER_BLINDNESS": [
        r"missing mandatory causal edge.*(OAT1|OAT3|P-GP|BCRP|P-gp|PGP)",
        r"missing.*transporter",
        r"missed.*(renal|active).*(secretion|clearance)",
        r"P-gp.*missing",
        r"OAT[13].*missing",
    ],
    "ENZYME_BLINDNESS": [
        r"missing mandatory causal edge.*(CYP3A4|CYP2C19|CYP2C9|CYP2D6|CYP3A5)",
        r"missed.*enzyme",
        r"CYP.*missing",
    ],
    "COUNTERFACTUAL_COLLAPSE": [
        r"counterfactual invariant failure",
        r"residual_risk_remains.*false.*should be true",
        r"wrong residual_risk",
        r"failed to preserve.*invariant",
        r"all.clear.*incorrect",
        r"false.*all.clear",
    ],
    "FATAL_ANTI_PATTERN": [
        r"fatal safety trap triggered",
        r"unauthorized dose reduction",
        r"fatal trap",
        r"safe with meals",
        r"reduce.*dose.*trap",
    ],
    "STEREOSELECTIVE_BLINDNESS": [
        r"stereoselect",
        r"S-warfarin",
        r"R-warfarin",
        r"enantiomer",
        r"warfarin.*monolithic",
    ],
    "PHYSIOLOGICAL_MODIFIER_IGNORED": [
        r"failed to identify active physiological modifier",
        r"modifier_present.*false",
        r"missed.*(CrCl|renal|hypokalemia|electrolyte|genotype)",
        r"physiological modifier.*absent",
    ],
    "OVER_FLAGGING": [
        r"safe combination.*over.flag",
        r"false alarm",
        r"over.flag",
        r"unnecessary.*contraindicated",
    ],
    "INVERTED_CAUSATION": [
        r"inverted_causation",
        r"cause.effect.*inverted",
        r"victim.*perpetrator",
    ],
    "DISCONNECTED_GRAPH": [
        r"disconnected.*path",
        r"orphaned.*edge",
        r"graph.*disconnected",
        r"no continuous path",
    ],
    "HALLUCINATED_EDGE": [
        r"spurious.*edge",
        r"hallucinated.*edge",
        r"hallucinated pathway",
    ],
    "VERDICT_MISMATCH": [
        r"regulatory verdict mismatch",
        r"verdict.*mismatch",
        r"wrong verdict",
    ],
    "PARTIAL_EDGE_RECALL": [
        r"missing mandatory causal edge",
        r"partial.*recall",
    ],
}

# Human-readable category names
CATEGORY_DISPLAY = {
    "TRANSPORTER_BLINDNESS": "Transporter Blindness (P-gp/OAT1/OAT3/BCRP)",
    "ENZYME_BLINDNESS": "Enzyme Blindness (CYP450)",
    "COUNTERFACTUAL_COLLAPSE": "Counterfactual Collapse (False All-Clear)",
    "FATAL_ANTI_PATTERN": "Fatal Anti-Pattern (Unauthorized Dose/Reassurance)",
    "STEREOSELECTIVE_BLINDNESS": "Stereoselective Blindness",
    "PHYSIOLOGICAL_MODIFIER_IGNORED": "Physiological Modifier Ignored",
    "OVER_FLAGGING": "Over-Flagging / Clinical Paranoia",
    "INVERTED_CAUSATION": "Inverted Causation",
    "DISCONNECTED_GRAPH": "Disconnected Graph (CPCS)",
    "HALLUCINATED_EDGE": "Hallucinated Edge",
    "VERDICT_MISMATCH": "Verdict Mismatch",
    "PARTIAL_EDGE_RECALL": "Partial Edge Recall",
}


def classify_reason(reason: str) -> List[str]:
    """Classify a single grader reason into taxonomy categories."""
    reason_lower = reason.lower()
    matched = []
    for category, patterns in TAXONOMY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, reason_lower, re.IGNORECASE):
                matched.append(category)
                break
    return matched


def classify_task_failure(reasons: List[str]) -> Dict[str, int]:
    """Classify all reasons for a single task into categories."""
    category_counts = Counter()
    for reason in reasons:
        cats = classify_reason(reason)
        if not cats:
            cats = ["UNCLASSIFIED"]
        for cat in cats:
            category_counts[cat] += 1
    return dict(category_counts)


def analyze_model_results(raw_runs_dir: Path) -> Dict[str, Any]:
    """Analyze all raw run JSONs and produce failure taxonomy."""
    model_taxonomy = {}
    
    for json_file in raw_runs_dir.glob("*.json"):
        with open(json_file) as f:
            run = json.load(f)
        
        model = run.get("model", "unknown")
        task_id = run.get("task_id", "unknown")
        grade = run.get("eval_grade", {})
        reasons = grade.get("reasons", [])
        
        if model not in model_taxonomy:
            model_taxonomy[model] = {
                "task_breakdown": {},
                "category_totals": Counter(),
                "total_tasks": 0,
                "failed_tasks": 0
            }
        
        model_taxonomy[model]["total_tasks"] += 1
        if not grade.get("passed", False):
            model_taxonomy[model]["failed_tasks"] += 1
        
        task_cats = classify_task_failure(reasons)
        model_taxonomy[model]["task_breakdown"][task_id] = {
            "passed": grade.get("passed", False),
            "score": grade.get("total_score", 0),
            "categories": task_cats
        }
        
        for cat, count in task_cats.items():
            model_taxonomy[model]["category_totals"][cat] += count
    
    # Convert Counters to dicts for JSON serialization
    for model in model_taxonomy:
        model_taxonomy[model]["category_totals"] = dict(model_taxonomy[model]["category_totals"])
        # Add display names
        model_taxonomy[model]["category_display"] = {
            cat: CATEGORY_DISPLAY.get(cat, cat) 
            for cat in model_taxonomy[model]["category_totals"]
        }
    
    return model_taxonomy


def generate_taxonomy_report(model_taxonomy: Dict[str, Any]) -> str:
    """Generate a human-readable taxonomy report."""
    lines = []
    lines.append("=" * 70)
    lines.append("FAILURE TAXONOMY REPORT")
    lines.append("=" * 70)
    
    for model, data in model_taxonomy.items():
        lines.append(f"\n--- {model} ---")
        lines.append(f"  Tasks: {data['total_tasks']} | Failed: {data['failed_tasks']} | Pass Rate: {round((data['total_tasks'] - data['failed_tasks']) / data['total_tasks'] * 100, 1)}%")
        lines.append(f"\n  Category Breakdown:")
        
        # Sort by frequency
        sorted_cats = sorted(data["category_totals"].items(), key=lambda x: -x[1])
        for cat, count in sorted_cats:
            display = CATEGORY_DISPLAY.get(cat, cat)
            lines.append(f"    {display}: {count}")
        
        # Per-task detail
        lines.append(f"\n  Per-Task Breakdown:")
        for task_id, tdata in data["task_breakdown"].items():
            status = "✅" if tdata["passed"] else "❌"
            cats_str = ", ".join([f"{CATEGORY_DISPLAY.get(c, c)}:{cnt}" for c, cnt in tdata["categories"].items()])
            lines.append(f"    {task_id}: {status} (Score: {tdata['score']}) [{cats_str}]")
    
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Failure Taxonomy from Raw Runs")
    parser.add_argument("--raw-runs", type=str, default="results/raw_runs", help="Path to raw_runs directory")
    parser.add_argument("--output", type=str, help="Output JSON file for taxonomy data")
    parser.add_argument("--report", action="store_true", help="Print human-readable report")
    args = parser.parse_args()

    raw_runs_dir = BASE_DIR / args.raw_runs
    if not raw_runs_dir.exists():
        print(f"Raw runs directory not found: {raw_runs_dir}")
        return 1

    taxonomy = analyze_model_results(raw_runs_dir)
    
    if args.output:
        out_path = BASE_DIR / args.output
        with open(out_path, "w") as f:
            json.dump(taxonomy, f, indent=2)
        print(f"Taxonomy saved to: {out_path}")
    
    if args.report or not args.output:
        print(generate_taxonomy_report(taxonomy))
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())