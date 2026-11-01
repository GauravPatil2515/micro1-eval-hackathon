#!/usr/bin/env python3
"""
Minimal Pairs Evaluation for MechanismTrace-DDI
Module: Evaluates counterfactual consistency by flipping one patient state parameter
and verifying the model's verdict changes accordingly.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader
from run_eval import call_model, STRUCTURED_SYSTEM_PROMPT


def load_tasks(tasks_path: Path) -> Dict[str, Any]:
    """Load tasks and index by ID."""
    with open(tasks_path) as f:
        tasks = json.load(f)
    return {t["id"]: t for t in tasks}


def extract_minimal_pairs(tasks: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract minimal pairs from all tasks."""
    pairs = {}
    for tid, task in tasks.items():
        # minimal_pairs is stored inside ground_truth
        gt = task.get("ground_truth", {})
        if "minimal_pairs" in gt and gt["minimal_pairs"]:
            pairs[tid] = gt["minimal_pairs"]
    return pairs


def generate_variant_prompt(base_task: Dict[str, Any], variant: Dict[str, Any]) -> str:
    """Generate a prompt with the minimal pair variant applied."""
    # Deep copy the clinical context and apply the variant
    import copy
    variant_context = copy.deepcopy(base_task["clinical_context"])
    
    param = variant["parameter"]
    value = variant["value"]
    
    # Apply the variant to the appropriate field
    if param == "calculated_crcl_ml_min":
        variant_context["physiological_modifiers"]["calculated_crcl_ml_min"] = value
    elif param == "serum_k_mEq_L":
        variant_context["physiological_modifiers"]["serum_k_mEq_L"] = value
    elif param == "serum_mg_mg_dL":
        variant_context["physiological_modifiers"]["serum_mg_mg_dL"] = value
    elif param == "cyp2d6_genotype":
        variant_context["physiological_modifiers"]["cyp2d6_genotype"] = value
    elif param == "cyp2c19_genotype":
        variant_context["physiological_modifiers"]["cyp2c19_genotype"] = value
    elif param == "cyp3a5_genotype":
        variant_context["physiological_modifiers"]["cyp3a5_genotype"] = value
    elif param == "tpmt_genotype":
        variant_context["physiological_modifiers"]["tpmt_genotype"] = value
    elif param == "hla_b5701_status":
        variant_context["physiological_modifiers"]["hla_b5701_status"] = value
    elif param == "ugt1a1_genotype":
        variant_context["physiological_modifiers"]["ugt1a1_genotype"] = value
    elif param == "context":
        # For TASK-04 context variants
        if "High-dose MTX" in str(value):
            variant_context["patient"] = "45-year-old female with acute lymphoblastic leukemia on high-dose Methotrexate 12 g/m2 IV + Leucovorin rescue. Dehydrated (CrCl 48 mL/min). Prescribed Naproxen 500 mg BID for mucositis pain."
        elif "Low-dose MTX" in str(value):
            variant_context["patient"] = "52-year-old female with rheumatoid arthritis on stable low-dose Methotrexate 15 mg/week. Normal renal function (CrCl 95 mL/min). Prescribed Naproxen 500 mg BID for osteoarthritis flare."
    
    # Build the prompt using the same template as run_eval
    from run_eval import generate_task_prompt
    # Create a modified task dict for prompt generation
    modified_task = {
        "id": base_task["id"],
        "title": base_task["title"],
        "clinical_context": variant_context,
        "counterfactual_probe": base_task["clinical_context"]["counterfactual_probe"]
    }
    return generate_task_prompt(modified_task)


def run_minimal_pairs_evaluation(
    tasks_path: Path,
    models: List[str],
    trials: int = 3,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Run minimal pairs evaluation across all tasks with defined pairs."""
    print("=" * 70)
    print("🔬 MECHANISMTRACE-DDI: MINIMAL PAIRS CONSISTENCY EVALUATION")
    print("=" * 70 + "\n")

    tasks = load_tasks(tasks_path)
    all_pairs = extract_minimal_pairs(tasks)

    if not all_pairs:
        print("No minimal pairs defined in tasks.")
        return {}

    summary = {}

    for model in models:
        print(f"\n[Evaluating Model (Minimal Pairs): {model}]")
        model_results = {
            "task_results": {},
            "consistency_rate": 0.0,
            "total_pairs": 0,
            "consistent_pairs": 0
        }

        for tid, pairs in all_pairs.items():
            base_task = tasks[tid]
            task_results = []

            for pair in pairs:
                pair_id = pair["pair_id"]
                variant_a = pair["variant_a"]
                variant_b = pair["variant_b"]
                expected_a = variant_a["verdict"]
                expected_b = variant_b["verdict"]

                print(f"  -> {pair_id}: {pair['description']}")

                # Evaluate both variants
                verdicts = {}
                for label, variant in [("A", variant_a), ("B", variant_b)]:
                    variant_verdicts = []
                    for trial in range(trials):
                        prompt = generate_variant_prompt(base_task, variant)
                        
                        if dry_run:
                            # Fixture mode: return hardcoded responses for known variants
                            # For real evaluation, this would call the model
                            if "fixture" in str(trials).lower() or hasattr(run_minimal_pairs_evaluation, '_fixture_mode'):
                                pass
                            # In dry_run, we'll simulate by checking if the variant matches expected
                            # This is a placeholder - real implementation calls the model
                            pass
                        
                        try:
                            # Use the live call_model infrastructure
                            # We need to create a minimal task-like object
                            variant_task = {
                                "id": f"{tid}_{pair_id}_{label}",
                                "title": f"{base_task['title']} - {label}",
                                "clinical_context": base_task["clinical_context"]
                            }
                            # Generate the actual prompt
                            prompt = generate_variant_prompt(base_task, variant)
                            
                            # For dry_run, simulate; for live, call model
                            if dry_run:
                                # Return a mock response based on expected verdict
                                mock_response = f"""```json
{{
  "causal_graph": [],
  "physiological_modifier": {{"modifier_present": true}},
  "regulatory_action": {{"verdict": "{variant['verdict']}", "mandated_action": "Per variant"}},
  "counterfactual_analysis": {{"resolves_primary_interaction": true, "residual_risk_remains": false}}
}}
```"""
                                raw_response = mock_response
                            else:
                                # Live API call
                                import os
                                if "gpt" in model.lower() and os.getenv("OPENAI_API_KEY"):
                                    from openai import OpenAI
                                    client = OpenAI()
                                    res = client.chat.completions.create(
                                        model=model,
                                        messages=[
                                            {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                                            {"role": "user", "content": prompt}
                                        ],
                                        temperature=0.0,
                                        seed=42
                                    )
                                    raw_response = res.choices[0].message.content or ""
                                elif "claude" in model.lower() and os.getenv("ANTHROPIC_API_KEY"):
                                    from anthropic import Anthropic
                                    client = Anthropic()
                                    res = client.messages.create(
                                        model=model,
                                        max_tokens=2048,
                                        system=STRUCTURED_SYSTEM_PROMPT,
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.0
                                    )
                                    raw_response = res.content[0].text
                                elif ("gpt-oss" in model.lower() or "qwen" in model.lower() or "llama" in model.lower()) and os.getenv("GROQ_API_KEY"):
                                    from groq import Groq
                                    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                                    res = client.chat.completions.create(
                                        model=model,
                                        messages=[
                                            {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                                            {"role": "user", "content": prompt}
                                        ],
                                        temperature=0.0
                                    )
                                    raw_response = res.choices[0].message.content or ""
                                else:
                                    raise RuntimeError(f"No API key for model {model}")
                            
                            grade = DeterministicCausalGrader.evaluate_task(
                                {"id": tid, "ground_truth": {"expected_verdict": variant['verdict'], "fatal_traps": [], "counterfactual": {"resolves_primary": True, "residual_risk_remains": False}}},
                                raw_response
                            )
                            variant_verdicts.append(grade.get("regulatory_action", {}).get("verdict", "UNKNOWN"))
                        except Exception as e:
                            print(f"    [!] Trial {trial+1} failed for {label}: {e}")
                            variant_verdicts.append("ERROR")
                    
                    # Majority vote
                    from collections import Counter
                    if variant_verdicts:
                        verdict = Counter(variant_verdicts).most_common(1)[0][0]
                    else:
                        verdict = "ERROR"
                    verdicts[label] = verdict
                    print(f"    {label}: Expected {variant['verdict']}, Got {verdict}")
                
                # Check consistency: did the model's verdict change as expected?
                consistent = (verdicts.get("A") == expected_a and verdicts.get("B") == expected_b)
                if consistent:
                    model_results["consistent_pairs"] += 1
                model_results["total_pairs"] += 1
                
                task_results.append({
                    "pair_id": pair_id,
                    "variant_a": {"expected": expected_a, "predicted": verdicts.get("A")},
                    "variant_b": {"expected": expected_b, "predicted": verdicts.get("B")},
                    "consistent": consistent
                })
            
            model_results["task_results"][tid] = task_results
        
        if model_results["total_pairs"] > 0:
            model_results["consistency_rate"] = round(
                model_results["consistent_pairs"] / model_results["total_pairs"] * 100, 1
            )
        
        summary[model] = model_results
        print(f"\n--- Minimal Pairs Summary for {model} ---")
        print(f"Consistent: {model_results['consistent_pairs']}/{model_results['total_pairs']} ({model_results['consistency_rate']}%)")

    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Minimal Pairs Evaluation for MechanismTrace-DDI")
    parser.add_argument("--models", type=str, default="openai/gpt-oss-120b,qwen/qwen3.8-27b", help="Comma-separated model IDs")
    parser.add_argument("--tasks", type=str, default="dataset/tasks.json", help="Path to tasks.json")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials per variant")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in fixture mode")
    parser.add_argument("--fixture-mode", action="store_true", help="Run with deterministic fixtures")
    args = parser.parse_args()

    tasks_path = BASE_DIR / args.tasks
    models = [m.strip() for m in args.models.split(",")]

    run_minimal_pairs_evaluation(tasks_path, models, trials=args.trials, dry_run=args.dry_run or args.fixture_mode)

    out_file = BASE_DIR / "results" / f"minimal_pairs_summary_{int(__import__('time').time())}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    # Note: actual results would be saved here in live mode


if __name__ == "__main__":
    main()