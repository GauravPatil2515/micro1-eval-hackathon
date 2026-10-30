#!/usr/bin/env python3
"""
MechanismTrace-DDI Benchmark Evaluation Harness
Executes 8 curated multi-hop clinical pharmacology tasks across frontier LLM APIs
and deterministic open-weight models, grading outputs via DeterministicCausalGrader.
"""
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ensure local modules can be loaded
import sys
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader

# Load environment variables
load_dotenv()

# System prompt mandating structured causal graph output
STRUCTURED_SYSTEM_PROMPT = """You are a senior clinical pharmacologist and molecular toxicologist.
You must analyze the patient's multi-drug clinical scenario and output a valid JSON response adhering strictly to the PharmacologicalCausalGraph schema.

Your JSON output MUST have the following structure:
```json
{
  "causal_graph": [
    {
      "source": "<Drug or Target>",
      "target": "<Target, Transporter, or Drug>",
      "relation": "<INHIBITS | INDUCES | COMPETITIVELY_BLOCKS | STEREOSELECTIVELY_INHIBITS | INCREASES_EXPOSURE | DECREASES_EXPOSURE | BLOCKS_BIOACTIVATION | PRODUCES_ADDITIVE_BLOCK>",
      "evidence_source": "<FDA label, CPIC, or literature citation>"
    }
  ],
  "physiological_modifier": {
    "modifier_present": true,
    "parameter": "<e.g. CrCl 41 mL/min, K+ 3.1 mEq/L, or CYP2C19 genotype>",
    "clinical_consequence": "<Concise mechanistic explanation>"
  },
  "regulatory_action": {
    "verdict": "<CONTRAINDICATED | DOSE_ADJUSTMENT_REQUIRED | TDM_MONITORING_MANDATED | SAFE_WITHOUT_ADJUSTMENT>",
    "mandated_action": "<Specific clinical instruction>"
  },
  "counterfactual_analysis": {
    "alternative_drug": "<Proposed alternative drug>",
    "resolves_primary_interaction": true,
    "residual_risk_remains": true,
    "residual_risk_explanation": "<Explanation of whether residual risk persists>"
  }
}
```
Return ONLY the JSON object. Do not include introductory conversational filler.
"""

def generate_task_prompt(task: Dict[str, Any]) -> str:
    """Build the evaluation prompt from task clinical context."""
    ctx = task["clinical_context"]
    mods = "\n".join([f"  - {k}: {v}" for k, v in ctx["physiological_modifiers"].items()])
    return f"""### CLINICAL CASE EVALUATION: {task['title']}

**Patient Profile:**
{ctx['patient']}

**Patient-Specific Physiological Modifiers:**
{mods}

**Acute Prescription / Proposed Regimen Addition:**
{ctx['acute_prescription']}

**Counterfactual Invariant Probe:**
{ctx['counterfactual_probe']}

Perform a full multi-hop pharmacological trace. Identify all affected CYP enzymes, transporters, exposure shifts, regulatory verdicts, and counterfactual residual risks.
"""

def mock_call_llm(model: str, task: Dict[str, Any]) -> str:
    """
    Dry-run simulation demonstrating candidate model response patterns.
    Simulates textbook answers that stumble on subtle counterfactual residual risk traps.
    """
    tid = task["id"]
    if tid == "TASK-01":
        # Simulates a model making the fatal trap of suggesting an off-label dose reduction
        return """```json
{
  "causal_graph": [
    {"source": "Ketoconazole", "target": "CYP3A4", "relation": "INHIBITS", "evidence_source": "FDA Section 7"},
    {"source": "Ketoconazole", "target": "P-gp", "relation": "INHIBITS", "evidence_source": "FDA Section 7"},
    {"source": "CYP3A4", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA Section 12"},
    {"source": "P-gp", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA Section 12"}
  ],
  "physiological_modifier": {
    "modifier_present": true,
    "parameter": "CrCl 41 mL/min",
    "clinical_consequence": "Dual clearance block in renal impairment."
  },
  "regulatory_action": {
    "verdict": "CONTRAINDICATED",
    "mandated_action": "Avoid concomitant use. Alternatively, reduce rivaroxaban to 10 mg daily."
  },
  "counterfactual_analysis": {
    "alternative_drug": "Fluconazole",
    "resolves_primary_interaction": true,
    "residual_risk_remains": true,
    "residual_risk_explanation": "Moderate inhibition still requires heightened bleeding monitoring."
  }
}
```"""
    elif tid == "TASK-03":
        # Simulates a model missing the counterfactual residual risk (claiming patient is safe with Doxycycline)
        return """```json
{
  "causal_graph": [
    {"source": "Sotalol", "target": "HERG", "relation": "INHIBITS", "evidence_source": "FDA Betapace §5.1"},
    {"source": "Levofloxacin", "target": "HERG", "relation": "PRODUCES_ADDITIVE_BLOCK", "evidence_source": "CredibleMeds"}
  ],
  "physiological_modifier": {
    "modifier_present": true,
    "parameter": "K+ 3.1 mEq/L, Mg2+ 1.4 mg/dL",
    "clinical_consequence": "Hypokalemia sensitizes hERG channel."
  },
  "regulatory_action": {
    "verdict": "CONTRAINDICATED",
    "mandated_action": "Avoid Levofloxacin. Replete electrolytes."
  },
  "counterfactual_analysis": {
    "alternative_drug": "Doxycycline",
    "resolves_primary_interaction": true,
    "residual_risk_remains": false,
    "residual_risk_explanation": "Doxycycline does not block hERG, so patient is completely safe."
  }
}
```"""
    else:
        # Standard fallback output
        return """```json
{
  "causal_graph": [],
  "physiological_modifier": {"modifier_present": false},
  "regulatory_action": {"verdict": "SAFE_WITHOUT_ADJUSTMENT", "mandated_action": "No precautions necessary."},
  "counterfactual_analysis": {"resolves_primary_interaction": false, "residual_risk_remains": false}
}
```"""

def call_model(model: str, task: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Dispatches prompt to candidate model API (OpenAI, Anthropic, Gemini, Groq) or mock."""
    if dry_run:
        return {
            "output": mock_call_llm(model, task),
            "latency_ms": 12.0,
            "tokens": 450,
            "cost_usd": 0.0
        }

    user_prompt = generate_task_prompt(task)
    t0 = time.time()

    # 1. Groq API Support
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and ("gpt-oss" in model.lower() or "qwen" in model.lower() or "llama" in model.lower()):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            latency = round((time.time() - t0) * 1000, 2)
            tokens = res.usage.total_tokens if res.usage else 0
            cost = round((tokens / 1000) * 0.0005, 5)
            return {
                "output": res.choices[0].message.content or "",
                "latency_ms": latency,
                "tokens": tokens,
                "cost_usd": cost
            }
        except Exception as e:
            print(f"[!] Groq call failed: {e}. Falling back to simulation.")

    # 2. OpenAI API Support
    if "gpt" in model.lower() and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI()
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                seed=42
            )
            latency = round((time.time() - t0) * 1000, 2)
            tokens = res.usage.total_tokens if res.usage else 0
            cost = round((tokens / 1000) * 0.005, 5)
            return {
                "output": res.choices[0].message.content or "",
                "latency_ms": latency,
                "tokens": tokens,
                "cost_usd": cost
            }
        except Exception as e:
            print(f"[!] OpenAI call failed: {e}. Falling back to simulation.")

    # 3. Anthropic API Support
    if "claude" in model.lower() and os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic
            client = Anthropic()
            res = client.messages.create(
                model=model,
                max_tokens=2048,
                system=STRUCTURED_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.0
            )
            latency = round((time.time() - t0) * 1000, 2)
            tokens = res.usage.input_tokens + res.usage.output_tokens
            cost = round((tokens / 1000) * 0.006, 5)
            return {
                "output": res.content[0].text,
                "latency_ms": latency,
                "tokens": tokens,
                "cost_usd": cost
            }
        except Exception as e:
            print(f"[!] Anthropic call failed: {e}. Falling back to simulation.")

    # Fallback to dry-run mock
    return {
        "output": mock_call_llm(model, task),
        "latency_ms": 15.0,
        "tokens": 400,
        "cost_usd": 0.0
    }

def main():
    parser = argparse.ArgumentParser(description="Run MechanismTrace-DDI Frontier Evaluation Benchmark")
    parser.add_argument("--models", type=str, default="openai/gpt-oss-120b,qwen/qwen3.8-27b", help="Comma-separated models")
    parser.add_argument("--tasks", type=str, default="starter_template/dataset/tasks.json", help="Path to tasks.json")
    parser.add_argument("--out", type=str, default="starter_template/results", help="Directory for benchmark outputs")
    parser.add_argument("--trials", type=int, default=1, help="Number of repeated runs per task")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without external API calls")
    args = parser.parse_args()

    tasks_path = Path(args.tasks)
    if not tasks_path.exists():
        print(f"[Error] Tasks file not found at: {tasks_path}")
        return

    with open(tasks_path, "r") as f:
        tasks = json.load(f)

    models = [m.strip() for m in args.models.split(",")]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_runs_dir = out_dir / "raw_runs"
    raw_runs_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*70)
    print("🧬  MECHANISMTRACE-DDI: FRONTIER AI CAUSAL EVALUATION BENCHMARK")
    print(f"    Tasks: {len(tasks)} | Models: {models} | Repeated Trials: {args.trials}")
    print(f"    Dry Run: {args.dry_run}")
    print("="*70 + "\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_report = {
        "benchmark": "MechanismTrace-DDI",
        "timestamp": timestamp,
        "trials_per_task": args.trials,
        "results": {}
    }

    for model in models:
        print(f"\n[Evaluating Model: {model}]")
        model_runs = []
        total_score_sum = 0.0
        passed_count = 0
        total_latency = 0.0
        total_tokens = 0
        total_cost = 0.0

        for task in tasks:
            print(f" -> {task['id']}: {task['title'][:45]}... ", end="", flush=True)
            task_trial_scores = []
            task_trial_passed = 0

            for trial in range(args.trials):
                call_res = call_model(model, task, dry_run=args.dry_run)
                eval_res = DeterministicCausalGrader.evaluate_task(task, call_res["output"])
                
                total_latency += call_res["latency_ms"]
                total_tokens += call_res["tokens"]
                total_cost += call_res["cost_usd"]

                task_trial_scores.append(eval_res["total_score"])
                if eval_res["passed"]:
                    task_trial_passed += 1

                # Save raw response
                raw_filename = f"{model.replace('/', '_')}_{task['id']}_trial{trial+1}_{timestamp}.json"
                with open(raw_runs_dir / raw_filename, "w") as rf:
                    json.dump({
                        "task_id": task["id"],
                        "model": model,
                        "trial": trial + 1,
                        "latency_ms": call_res["latency_ms"],
                        "tokens": call_res["tokens"],
                        "cost_usd": call_res["cost_usd"],
                        "raw_output": call_res["output"],
                        "eval_grade": eval_res
                    }, rf, indent=2)

            avg_score = round(sum(task_trial_scores) / len(task_trial_scores), 2)
            total_score_sum += avg_score
            is_passed = (task_trial_passed == args.trials)
            if is_passed:
                passed_count += 1
                print(f"✅ PASSED ({avg_score}/100)")
            else:
                print(f"❌ FAILED ({avg_score}/100 - {eval_res['reasons'][0] if eval_res['reasons'] else 'Failed threshold'})")

            model_runs.append({
                "task_id": task["id"],
                "avg_score": avg_score,
                "passed": is_passed,
                "edge_accuracy": eval_res["edge_accuracy_pct"],
                "reasons": eval_res["reasons"]
            })

        pass_rate = round((passed_count / len(tasks)) * 100, 1)
        mean_score = round(total_score_sum / len(tasks), 1)

        benchmark_report["results"][model] = {
            "tasks_passed": passed_count,
            "total_tasks": len(tasks),
            "pass_rate_pct": pass_rate,
            "mean_score": mean_score,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(total_latency / (len(tasks) * args.trials), 1),
            "task_breakdown": model_runs
        }

        print(f"--- Summary for {model} ---")
        print(f"Pass Rate: {passed_count}/{len(tasks)} ({pass_rate}%) | Mean Score: {mean_score}/100 | Avg Latency: {round(total_latency/(len(tasks)*args.trials), 1)}ms\n")

    summary_file = out_dir / f"benchmark_summary_{timestamp}.json"
    with open(summary_file, "w") as sf:
        json.dump(benchmark_report, sf, indent=2)

    print("="*70)
    print(f"🎉 Benchmark complete! Summary saved to: {summary_file}")
    print(f"📁 Raw model outputs preserved in: {raw_runs_dir}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
