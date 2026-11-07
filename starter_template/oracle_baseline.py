"""
Oracle Baseline for MechanismTrace-DDI
Runs gold answers through the deterministic grader to verify that the
benchmark is correctly constructed (gold answers should score 100%).
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure local modules can be loaded
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader
from graders.normalizer import normalize_entity, normalize_relation


def build_oracle_response(task: Dict[str, Any]) -> str:
    """
    Build a perfect oracle response from task ground truth.
    Maps causal_edges to causal_graph, sets all counterfactual fields
    from ground truth, and marks physiological modifier as present.
    """
    gt = task["ground_truth"]
    edges = []
    for e in gt.get("causal_edges", []):
        edges.append({
            "source": e["source"],
            "target": e["target"],
            "relation": e["relation"],
            "evidence_source": "FDA label / CPIC guideline"
        })

    return json.dumps({
        "causal_graph": edges,
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "From ground truth",
            "clinical_consequence": gt.get("physiological_modifier_impact", "")
        },
        "regulatory_action": {
            "verdict": gt.get("expected_verdict", "CONTRAINDICATED"),
            "mandated_action": gt.get("mandated_action", "Avoid concomitant administration.")
        },
        "counterfactual_analysis": {
            "alternative_drug": "From ground truth counterfactual",
            "resolves_primary_interaction": gt.get("counterfactual", {}).get("resolves_primary", True),
            "residual_risk_remains": gt.get("counterfactual", {}).get("residual_risk_remains", True),
            "residual_risk_explanation": gt.get("counterfactual", {}).get("explanation", "")
        }
    })


def build_paraphrased_oracle_response(task: Dict[str, Any]) -> str:
    """
    Build a paraphrased oracle response using accepted alternates
    and synonym variations to verify the grader accepts valid alternate paths.
    """
    gt = task["ground_truth"]
    alternates = gt.get("accepted_alternates", [])

    # Use primary edges, but swap some to alternates if available
    edges = []
    primary = gt.get("causal_edges", [])
    alt_set = alternates[0] if alternates else []

    for i, e in enumerate(primary):
        if i < len(alt_set):
            alt = alt_set[i]
            edges.append({
                "source": alt["source"],
                "target": alt["target"],
                "relation": alt["relation"],
                "evidence_source": "FDA label / CPIC guideline"
            })
        else:
            edges.append({
                "source": e["source"],
                "target": e["target"],
                "relation": e["relation"],
                "evidence_source": "FDA label / CPIC guideline"
            })

    cf = gt.get("counterfactual", {})
    return json.dumps({
        "causal_graph": edges,
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "From ground truth",
            "clinical_consequence": gt.get("physiological_modifier_impact", "")
        },
        "regulatory_action": {
            "verdict": gt.get("expected_verdict", "CONTRAINDICATED"),
            "mandated_action": gt.get("mandated_action", "Avoid concomitant administration.")
        },
        "counterfactual_analysis": {
            "alternative_drug": "From ground truth counterfactual",
            "resolves_primary_interaction": cf.get("resolves_primary", True),
            "residual_risk_remains": cf.get("residual_risk_remains", True),
            "residual_risk_explanation": cf.get("explanation", "")
        }
    })


def run_oracle_baseline(tasks_path: str = None) -> Dict[str, Any]:
    """
    Run gold answers through the grader and verify scoring.
    Returns summary of oracle performance.
    """
    if tasks_path is None:
        tasks_path = BASE_DIR / "dataset" / "tasks.json"

    with open(tasks_path, "r") as f:
        tasks = json.load(f)

    results = {
        "oracle_perfect": [],
        "oracle_paraphrased": [],
        "overall": {}
    }

    perfect_scores = []
    paraphrase_scores = []

    for task in tasks:
        task_id = task["id"]

        # Perfect oracle (primary edges)
        perfect_response = build_oracle_response(task)
        perfect_eval = DeterministicCausalGrader.evaluate_task(task, perfect_response)
        results["oracle_perfect"].append({
            "task_id": task_id,
            "score": perfect_eval["total_score"],
            "passed": perfect_eval["passed"],
            "edge_accuracy": perfect_eval["edge_accuracy_pct"],
            "cpcs": perfect_eval["cpcs_score"],
            "reasons": perfect_eval["reasons"]
        })
        perfect_scores.append(perfect_eval["total_score"])

        # Paraphrased oracle (accepted alternates)
        para_response = build_paraphrased_oracle_response(task)
        para_eval = DeterministicCausalGrader.evaluate_task(task, para_response)
        results["oracle_paraphrased"].append({
            "task_id": task_id,
            "score": para_eval["total_score"],
            "passed": para_eval["passed"],
            "edge_accuracy": para_eval["edge_accuracy_pct"],
            "cpcs": para_eval["cpcs_score"],
            "reasons": para_eval["reasons"]
        })
        paraphrase_scores.append(para_eval["total_score"])

    results["overall"] = {
        "perfect_mean": round(sum(perfect_scores) / len(perfect_scores), 2),
        "perfect_pass_rate": round(sum(1 for s in perfect_scores if s >= 80.0) / len(perfect_scores) * 100, 1),
        "perfect_all_100": all(s == 100.0 for s in perfect_scores),
        "paraphrase_mean": round(sum(paraphrase_scores) / len(paraphrase_scores), 2),
        "paraphrase_pass_rate": round(sum(1 for s in paraphrase_scores if s >= 80.0) / len(paraphrase_scores) * 100, 1),
        "paraphrase_all_ge_90": all(s >= 90.0 for s in paraphrase_scores),
        "paraphrase_all_ge_85": all(s >= 85.0 for s in paraphrase_scores),
        "total_tasks": len(tasks)
    }

    return results


def main():
    results = run_oracle_baseline()
    overall = results["overall"]

    print("=" * 70)
    print("ORACLE BASELINE VALIDATION")
    print("=" * 70)
    print(f"Perfect oracle (primary edges):")
    print(f"  Mean score: {overall['perfect_mean']}/100")
    print(f"  Pass rate: {overall['perfect_pass_rate']}%")
    print(f"  All 100%: {overall['perfect_all_100']}")
    print(f"\nParaphrased oracle (accepted alternates):")
    print(f"  Mean score: {overall['paraphrase_mean']}/100")
    print(f"  Pass rate: {overall['paraphrase_pass_rate']}%")
    print(f"  All >= 90%: {overall['paraphrase_all_ge_90']}")
    print(f"\nTotal tasks: {overall['total_tasks']}")

    # Validation assertions
    assert overall["perfect_all_100"], f"Oracle perfect not all 100%: {results['oracle_perfect']}"
    assert overall["paraphrase_all_ge_85"], f"Oracle paraphrase not all >= 85%: {results['oracle_paraphrased']}"
    print("\n✅ Oracle baseline validation PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()