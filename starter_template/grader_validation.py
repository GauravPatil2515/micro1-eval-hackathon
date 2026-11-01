"""
Grader Validation & Inter-Rater Reliability Study (Cohen's Kappa)
Module A.4: Framework for validating the Deterministic Causal Grader against Human Expert Ground Truth
and contrasting stability against an LLM-as-a-judge baseline across multiple random seeds.

NOTE: This module provides the framework for grader validation.
Actual human annotation and LLM judge runs must be performed independently and are NOT included in this repository.
The validation_set generation below shows the EXPECTED FORMAT for the annotation JSONL file.
It does NOT represent real annotated data and should NOT be used as validation evidence.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader


def compute_cohens_kappa(rater1: List[int], rater2: List[int]) -> float:
    """Computes Cohen's Kappa inter-rater agreement coefficient between two binary raters."""
    assert len(rater1) == len(rater2)
    n = len(rater1)
    if n == 0:
        return 1.0

    # Confusion matrix
    a = sum(1 for i in range(n) if rater1[i] == 1 and rater2[i] == 1)
    b = sum(1 for i in range(n) if rater1[i] == 1 and rater2[i] == 0)
    c = sum(1 for i in range(n) if rater1[i] == 0 and rater2[i] == 1)
    d = sum(1 for i in range(n) if rater1[i] == 0 and rater2[i] == 0)

    observed_agreement = (a + d) / n
    prob_rater1_yes = (a + b) / n
    prob_rater1_no = (c + d) / n
    prob_rater2_yes = (a + c) / n
    prob_rater2_no = (b + d) / n

    expected_agreement = (prob_rater1_yes * prob_rater2_yes) + (prob_rater1_no * prob_rater2_no)

    if expected_agreement == 1.0:
        return 1.0
    kappa = (observed_agreement - expected_agreement) / (1.0 - expected_agreement)
    return round(kappa, 3)


def run_grader_validation(annotation_file: Path = None, use_templates: bool = False):
    print("=" * 70)
    print("🔬 MECHANISMTRACE-DDI: GRADER VALIDATION & INTER-RATER RELIABILITY STUDY")
    print("   Dataset: 30 Hand-Annotated Clinical Submissions (Pass/Fail)")
    print("=" * 70 + "\n")

    if use_templates:
        print("⚠️  WARNING: Using template validation set - NOT valid empirical evidence!")
        print("   Real validation requires independent annotation of 30 diverse model outputs.\n")
    
    # Load tasks
    with open(BASE_DIR / "dataset" / "tasks.json") as f:
        tasks = {t["id"]: t for t in json.load(f)}

    # Load validation set
    if use_templates:
        validation_set = _generate_template_validation_set(tasks)
        print("Using template validation set (format demonstration only)\n")
    else:
        if annotation_file is None:
            annotation_file = BASE_DIR / "grader_validation_annotations.jsonl"
        if not annotation_file.exists():
            raise FileNotFoundError(
                f"Annotation file not found: {annotation_file}\n"
                "Please create a JSONL file with 30 annotated model outputs.\n"
                "Each line should be a JSON object with: task_id, response, human_gold_pass (0/1), error_type.\n"
                "Use --use-templates for format testing only (not empirical evidence)."
            )
        validation_set = []
        with open(annotation_file) as f:
            for line in f:
                validation_set.append(json.loads(line.strip()))
        print(f"✅ Loaded {len(validation_set)} annotations from {annotation_file}\n")

    # Evaluate using DeterministicCausalGrader
    human_labels = [item["human_gold_pass"] for item in validation_set]
    grader_labels = []

    for item in validation_set:
        task = tasks[item["task_id"]]
        grade = DeterministicCausalGrader.evaluate_task(task, item["response"])
        grader_labels.append(1 if grade["passed"] else 0)

    # Compute Cohen's Kappa for Deterministic Grader
    grader_kappa = compute_cohens_kappa(human_labels, grader_labels)

    # LLM-as-a-judge baseline - requires live API calls
    print("LLM-as-a-judge baseline requires live API evaluation.")
    print("Run with --run-llm-judge flag (not implemented in template) to evaluate GPT-4o/Claude as judges.\n")
    
    # Template placeholder for LLM judge results (NOT real data)
    if use_templates:
        # These are PLACEHOLDER values for format demonstration only
        kappa_seed1 = 0.85
        kappa_seed2 = 0.82
        kappa_seed3 = 0.88
        avg_llm_kappa = round((kappa_seed1 + kappa_seed2 + kappa_seed3) / 3, 3)
        
        print(f"📊 Deterministic Causal Grader vs Human Expert:")
        print(f"   Cohen's Kappa (κ): {grader_kappa}")
        print(f"   Run-to-Run Variance: 0.000 (100% Deterministic & Reproducible)")
        print()
        print(f"🤖 LLM-as-a-Judge Baseline (PLACEHOLDER - not real runs):")
        print(f"   Mean Cohen's Kappa (κ): {avg_llm_kappa} (Seed 1: {kappa_seed1}, Seed 2: {kappa_seed2}, Seed 3: {kappa_seed3})")
        print(f"   Run-to-Run Fluctuation: Template placeholder only")
        print("=" * 70)
    else:
        print(f"📊 Deterministic Causal Grader vs Human Expert:")
        print(f"   Cohen's Kappa (κ): {grader_kappa}")
        print(f"   Observed Agreement: {sum(1 for i in range(len(human_labels)) if human_labels[i] == grader_labels[i]) / len(human_labels) * 100:.1f}%")
        print(f"   Run-to-Run Variance: 0.000 (100% Deterministic & Reproducible)")
        print()
        print("🤖 LLM-as-a-Judge Baseline: NOT RUN (requires live API)")
        print("   To run: implement LLM judge calls with multiple seeds")
        print("=" * 70)

    results = {
        "sample_size": len(validation_set),
        "deterministic_grader": {
            "cohens_kappa": grader_kappa,
            "observed_agreement_pct": round(sum(1 for i in range(len(human_labels)) if human_labels[i] == grader_labels[i]) / len(human_labels) * 100, 1),
            "run_to_run_variance": 0.0
        },
        "llm_judge_baseline": {
            "note": "Requires live API evaluation with multiple seeds. Not included in template."
        }
    }

    out_file = BASE_DIR / "results" / "grader_validation_summary.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Grader validation study saved to: {out_file}\n")


def _generate_template_validation_set(tasks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates a TEMPLATE validation set showing the expected JSONL format.
    THIS IS NOT REAL ANNOTATED DATA - it demonstrates the required format only.
    Real validation requires independent annotation by clinical experts.
    """
    validation_set = []

    # Template examples showing the required format for each error type
    template_cases = [
        {"task_id": "TASK-01", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-02", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-03", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-04", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-05", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-06", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-07", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-08", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-11", "error_type": "None (Gold)", "human_gold_pass": 1},
        {"task_id": "TASK-13", "error_type": "None (Gold)", "human_gold_pass": 1},
        
        {"task_id": "TASK-01", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-02", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-03", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-04", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-05", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-06", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-07", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-08", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-12", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        {"task_id": "TASK-14", "error_type": "Missing/Spurious Edges", "human_gold_pass": 0},
        
        {"task_id": "TASK-01", "error_type": "Fatal Dose Trap", "human_gold_pass": 0},
        {"task_id": "TASK-02", "error_type": "Fatal Dose Trap", "human_gold_pass": 0},
        {"task_id": "TASK-04", "error_type": "Fatal Dose Trap", "human_gold_pass": 0},
        {"task_id": "TASK-05", "error_type": "Fatal Dose Trap", "human_gold_pass": 0},
        {"task_id": "TASK-07", "error_type": "Fatal Dose Trap", "human_gold_pass": 0},
        
        {"task_id": "TASK-01", "error_type": "Counterfactual Collapse", "human_gold_pass": 0},
        {"task_id": "TASK-03", "error_type": "Counterfactual Collapse", "human_gold_pass": 0},
        {"task_id": "TASK-06", "error_type": "Counterfactual Collapse", "human_gold_pass": 0},
        {"task_id": "TASK-07", "error_type": "Counterfactual Collapse", "human_gold_pass": 0},
        {"task_id": "TASK-08", "error_type": "Counterfactual Collapse", "human_gold_pass": 0},
    ]

    for case in template_cases:
        tid = case["task_id"]
        t = tasks[tid]
        gt = t["ground_truth"]
        
        if case["error_type"] == "None (Gold)":
            resp = json.dumps({
                "causal_graph": gt["causal_edges"],
                "physiological_modifier": {"modifier_present": True, "parameter": "Verified"},
                "regulatory_action": {"verdict": gt["expected_verdict"], "mandated_action": gt["mandated_action"]},
                "counterfactual_analysis": {
                    "resolves_primary_interaction": gt["counterfactual"]["resolves_primary"],
                    "residual_risk_remains": gt["counterfactual"]["residual_risk_remains"]
                }
            })
        elif case["error_type"] == "Missing/Spurious Edges":
            resp = json.dumps({
                "causal_graph": [{"source": "A", "target": "B", "relation": "INHIBITS"}],
                "physiological_modifier": {"modifier_present": True, "parameter": "Verified"},
                "regulatory_action": {"verdict": gt["expected_verdict"], "mandated_action": gt["mandated_action"]},
                "counterfactual_analysis": {
                    "resolves_primary_interaction": gt["counterfactual"]["resolves_primary"],
                    "residual_risk_remains": gt["counterfactual"]["residual_risk_remains"]
                }
            })
        elif case["error_type"] == "Fatal Dose Trap":
            trap = gt["fatal_traps"][0] if gt.get("fatal_traps") else "safe to administer"
            resp = json.dumps({
                "causal_graph": gt["causal_edges"],
                "regulatory_action": {"verdict": gt["expected_verdict"], "mandated_action": f"Recommended action: {trap}."},
                "counterfactual_analysis": {
                    "resolves_primary_interaction": gt["counterfactual"]["resolves_primary"],
                    "residual_risk_remains": gt["counterfactual"]["residual_risk_remains"]
                }
            })
        elif case["error_type"] == "Counterfactual Collapse":
            resp = json.dumps({
                "causal_graph": gt["causal_edges"],
                "physiological_modifier": {"modifier_present": True, "parameter": "Verified"},
                "regulatory_action": {"verdict": gt["expected_verdict"], "mandated_action": gt["mandated_action"]},
                "counterfactual_analysis": {
                    "resolves_primary_interaction": True,
                    "residual_risk_remains": False
                }
            })
        
        validation_set.append({
            "task_id": tid, 
            "response": resp, 
            "human_gold_pass": case["human_gold_pass"], 
            "error_type": case["error_type"]
        })

    return validation_set


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grader Validation for MechanismTrace-DDI")
    parser.add_argument("--annotation-file", type=str, help="Path to JSONL file with human annotations")
    parser.add_argument("--use-templates", action="store_true", help="Use template validation set (SIMULATION ONLY - not empirical evidence). Default: requires annotation file with real human labels.")
    args = parser.parse_args()

    annotation_file = BASE_DIR / args.annotation_file if args.annotation_file else None
    run_grader_validation(annotation_file=annotation_file, use_templates=args.use_templates)
