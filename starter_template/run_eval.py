#!/usr/bin/env python3
"""
MechanismTrace-DDI Benchmark Evaluation Harness
Executes 14 curated multi-hop clinical pharmacology tasks across frontier LLM APIs
and deterministic open-weight models, grading outputs via DeterministicCausalGrader.
"""
import os
import sys
import json
import time
import argparse
import locale
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Rich terminal formatting
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.text import Text
    from rich.columns import Columns
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Fix locale/encoding for headless environments
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        pass  # Fall back to default

# Force UTF-8 encoding for stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Disable matplotlib GUI backend if present
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

# Ensure local modules can be loaded from any cwd
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader
from graders.atomic_composed import evaluate_atomic_accuracy, analyze_atomic_composed_gap
from graders.stats_bootstrap import (
    bootstrap_confidence_interval,
    compute_model_level_ci,
    analyze_trial_variance,
    load_raw_trial_scores,
)

# Load environment variables
load_dotenv()

# Initialize rich console
console = Console() if RICH_AVAILABLE else None

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

# =============================================================================
# SYSTEM-2 CAUSAL SCAFFOLD PROMPT (Graph-of-Thoughts Reasoning)
# Forces explicit multi-hop causal trace before JSON output
# =============================================================================

SYSTEM_PROMPT_CAUSAL_SCAFFOLD = """You are a senior clinical pharmacologist and molecular toxicologist.
You must analyze the patient's multi-drug clinical scenario and output a valid JSON response adhering strictly to the PharmacologicalCausalGraph schema.

CRITICAL: You must NOT jump straight to the conclusion. You must FIRST explicitly trace the multi-hop causal chain in a <scratchpad> block using this EXACT structural causal trace:

<scratchpad>
1. IDENTIFY OFFENDING DRUG: [Name]
2. IDENTIFY PRIMARY TARGET: [Must specify exact Enzyme (e.g., CYP3A4) OR Transporter (e.g., P-gp, OAT1)]
3. CLEARANCE ALTERATION: [Does it inhibit/induce clearance of the victim drug?]
4. VICTIM DRUG EXPOSURE: [Name and exposure change]
5. PATIENT MODIFIERS: [Identify background risks like CrCl < 50 or Hypokalemia]
6. COUNTERFACTUAL CHECK: If the offending drug is swapped, does the background patient modifier still pose a risk? [Yes/No]
</scratchpad>

Only AFTER completing the scratchpad, output the final JSON graph formulation.

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

def _generate_transcription_control_prompt(task: Dict[str, Any]) -> str:
    """Generate a transcription control prompt: provide gold mechanism in prose, ask model to emit schema."""
    gt = task["ground_truth"]
    
    # Build prose description of the gold mechanism
    edges_prose = []
    for edge in gt.get("causal_edges", []):
        edges_prose.append(f"- {edge['source']} {edge['relation'].lower().replace('_', ' ')} {edge['target']}")
    
    edges_text = "\n".join(edges_prose)
    
    mods = task["clinical_context"]["physiological_modifiers"]
    mods_text = "\n".join([f"  - {k}: {v}" for k, v in mods.items()])
    
    return f"""### CLINICAL CASE EVALUATION (TRANSCRIPTION CONTROL): {task['title']}

**Patient Profile:**
{task['clinical_context']['patient']}

**Patient-Specific Physiological Modifiers:**
{mods_text}

**VERIFIED MECHANISM (provided for transcription):**
{edges_text}

**Counterfactual Question:**
{task['clinical_context']['counterfactual_probe']}

**YOUR TASK:** The above mechanism is clinically verified. Your job is to transcribe it into the required JSON schema. Do not modify the mechanism — just format it correctly.

Return ONLY the JSON object following the PharmacologicalCausalGraph schema:
```json
{{
  "causal_graph": [
    {{"source": "...", "target": "...", "relation": "...", "evidence_source": "..."}}
  ],
  "physiological_modifier": {{
    "modifier_present": true,
    "parameter": "...",
    "clinical_consequence": "..."
  }},
  "regulatory_action": {{
    "verdict": "...",
    "mandated_action": "..."
  }},
  "counterfactual_analysis": {{
    "alternative_drug": "...",
    "resolves_primary_interaction": true/false,
    "residual_risk_remains": true/false,
    "residual_risk_explanation": "..."
  }}
}}
```"""


def call_model(model: str, task: Dict[str, Any], dry_run: bool = False, fixture_mode: bool = False, transcription_control: bool = False, causal_scaffold: bool = False) -> Dict[str, Any]:
    """Dispatches prompt to candidate model API (OpenAI, Anthropic, Gemini, Groq).
    
    If dry_run=True, raises an exception - use fixture_mode for deterministic demos.
    If fixture_mode=True, returns deterministic fixture responses (clearly labeled as demos).
    If causal_scaffold=True, uses System-2 Causal Scaffold prompt with <scratchpad> reasoning.
    """
    if dry_run and not fixture_mode:
        raise RuntimeError(
            "dry_run=True is not supported for empirical evaluation. "
            "Use --fixture-mode for deterministic demonstration fixtures, "
            "or provide API keys for live model evaluation."
        )

    if fixture_mode:
        if transcription_control:
            return {
                "output": _fixture_call_llm(model, task),
                "latency_ms": 12.0,
                "tokens": 450,
                "cost_usd": 0.0,
                "fixture": True
            }
        return {
            "output": _fixture_call_llm(model, task),
            "latency_ms": 12.0,
            "tokens": 450,
            "cost_usd": 0.0,
            "fixture": True
        }

    if transcription_control:
        user_prompt = _generate_transcription_control_prompt(task)
    else:
        user_prompt = generate_task_prompt(task)
    
    # Select system prompt based on causal_scaffold flag
    system_prompt = SYSTEM_PROMPT_CAUSAL_SCAFFOLD if causal_scaffold else STRUCTURED_SYSTEM_PROMPT
    t0 = time.time()

    # 1. OpenRouter API Support (Hermes, open-weight models via OpenRouter)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    _OPENROUTER_PREFIXES = ("nousresearch/", "meta-llama/", "mistralai/", "anthropic/", "openai/", "qwen/", "google/")
    _is_openrouter_model = openrouter_key and (
        any(model.lower().startswith(p) for p in _OPENROUTER_PREFIXES)
        or "/" in model  # any namespaced model routes to OpenRouter if key is set
    )
    if _is_openrouter_model:
        for attempt in range(3):  # up to 3 retries with backoff
            try:
                from openai import OpenAI as _OAI
                client = _OAI(
                    api_key=openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                )
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=2048,
                    extra_headers={
                        "HTTP-Referer": "https://github.com/mechanismtrace-ddi",
                        "X-Title": "MechanismTrace-DDI Benchmark",
                    },
                )
                latency = round((time.time() - t0) * 1000, 2)
                tokens = res.usage.total_tokens if res.usage else 0
                # OpenRouter pricing for hermes-4-405b: $1/$3 per M prompt/completion tokens
                prompt_tokens = res.usage.prompt_tokens if res.usage else 0
                completion_tokens = res.usage.completion_tokens if res.usage else 0
                cost = round((prompt_tokens / 1_000_000) * 1.0 + (completion_tokens / 1_000_000) * 3.0, 6)
                return {
                    "output": res.choices[0].message.content or "",
                    "latency_ms": latency,
                    "tokens": tokens,
                    "cost_usd": cost,
                    "provider": getattr(res, "provider", "openrouter"),
                }
            except Exception as e:
                err_str = str(e)
                if "402" in err_str or "insufficient" in err_str.lower() or "credits" in err_str.lower():
                    raise RuntimeError(
                        f"[OpenRouter] Insufficient credits for model '{model}'. "
                        "Top up at https://openrouter.ai/settings/credits and retry."
                    ) from e
                if attempt < 2:
                    wait = 2 ** attempt  # 1s, 2s backoff
                    print(f"[!] OpenRouter attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"[OpenRouter] Call failed after 3 attempts: {e}") from e

    # 2. Groq API Support
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and ("gpt-oss" in model.lower() or "qwen" in model.lower() or "llama" in model.lower()):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
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

    # 3. OpenAI API Support (direct, non-namespaced GPT models)
    if "gpt" in model.lower() and "/" not in model and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI()
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                seed=42,
                max_tokens=2048,
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

    # 4. Anthropic API Support
    if "claude" in model.lower() and os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic
            client = Anthropic()
            res = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
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

    # Fallback - raise error instead of silent mock fallback
    raise RuntimeError(
        f"Model '{model}' not supported or no matching API key found.\n"
        "  - For OpenRouter (Hermes, etc.): set OPENROUTER_API_KEY\n"
        "  - For Groq (open-weight): set GROQ_API_KEY\n"
        "  - For OpenAI GPT models: set OPENAI_API_KEY\n"
        "  - For Anthropic Claude: set ANTHROPIC_API_KEY\n"
        "  - For deterministic demo: use --fixture-mode"
    )


def _fixture_call_llm(model: str, task: Dict[str, Any]) -> str:
    """
    Deterministic fixture responses for demonstration purposes only.
    These are NOT empirical results - they are hardcoded demonstrations.
    """
    tid = task["id"]
    if tid == "TASK-01":
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
    "verdict": "AVOID_CONCOMITANT_USE",
    "mandated_action": "Avoid concomitant use per FDA Section 7.1. Do not attempt dose reduction."
  },
  "counterfactual_analysis": {
    "alternative_drug": "Fluconazole",
    "resolves_primary_interaction": true,
    "residual_risk_remains": true,
    "residual_risk_explanation": "Fluconazole weakly inhibits P-gp, but in CrCl <50 mL/min, rivaroxaban exposure remains elevated ~1.4x requiring bleeding vigilance."
  }
}
```"""
    elif tid == "TASK-03":
        return """```json
{
  "causal_graph": [
    {"source": "Sotalol", "target": "HERG", "relation": "INHIBITS", "evidence_source": "FDA Betapace §5.1"},
    {"source": "Levofloxacin", "target": "HERG", "relation": "PRODUCES_ADDITIVE_BLOCK", "evidence_source": "CredibleMeds"}
  ],
  "physiological_modifier": {
    "modifier_present": true,
    "parameter": "K+ 3.1 mEq/L, Mg2+ 1.4 mg/dL",
    "clinical_consequence": "Severe hypokalemia dramatically increases sotalol affinity for hERG and delays repolarization."
  },
  "regulatory_action": {
    "verdict": "CONTRAINDICATED",
    "mandated_action": "Contraindicated. Replete potassium to >4.0 mEq/L and magnesium to >2.0 mg/dL immediately; cardiac telemetry."
  },
  "counterfactual_analysis": {
    "alternative_drug": "Doxycycline",
    "resolves_primary_interaction": true,
    "residual_risk_remains": true,
    "residual_risk_explanation": "Substituting Doxycycline clears fluoroquinolone hERG block, but uncorrected hypokalemia with sotalol maintains high lethal Torsades de Pointes risk."
  }
}
```"""
    else:
        return """```json
{
  "causal_graph": [],
  "physiological_modifier": {"modifier_present": false},
  "regulatory_action": {"verdict": "SAFE_WITHOUT_ADJUSTMENT", "mandated_action": "No precautions necessary."},
  "counterfactual_analysis": {"resolves_primary_interaction": false, "residual_risk_remains": false}
}
```"""

# Color output helper - disable when not a TTY
def _color(text: str, color_code: str) -> str:
    if RICH_AVAILABLE:
        return text  # Rich handles coloring
    if sys.stdout.isatty():
        return f"\033[{color_code}m{text}\033[0m"
    return text

def _green(text: str) -> str:
    return _color(text, "32")

def _red(text: str) -> str:
    return _color(text, "31")

def _yellow(text: str) -> str:
    return _color(text, "33")

def _blue(text: str) -> str:
    return _color(text, "34")

def _bold(text: str) -> str:
    return _color(text, "1")


def main():
    parser = argparse.ArgumentParser(description="Run MechanismTrace-DDI Frontier Evaluation Benchmark")
    parser.add_argument("--models", type=str, default="openai/gpt-oss-120b,qwen/qwen3.8-27b", help="Comma-separated models")
    parser.add_argument("--tasks", type=str, default=str(BASE_DIR / "dataset" / "tasks.json"), help="Path to tasks.json")
    parser.add_argument("--out", type=str, default=str(BASE_DIR / "results"), help="Directory for benchmark outputs")
    parser.add_argument("--trials", type=int, default=1, help="Number of repeated runs per task")
    parser.add_argument("--dry-run", action="store_true", help="Alias for --fixture-mode (deterministic demo mode)")
    parser.add_argument("--fixture-mode", action="store_true", help="Run with deterministic fixture responses (DEMO ONLY - not empirical evidence)")
    parser.add_argument("--thresholds", type=str, default="60,70,80,85", help="Comma-separated pass thresholds for sensitivity analysis")
    parser.add_argument("--transcription-control", action="store_true", help="Transcription control: provide gold mechanism in prose, ask model to emit schema (tests schema burden)")
    parser.add_argument("--causal-scaffold", action="store_true", help="Enable System-2 Causal Scaffold: forces <scratchpad> multi-hop trace before JSON output")
    parser.add_argument("--no-rich", action="store_true", help="Disable rich formatting, use plain text")
    args = parser.parse_args()

    # --dry-run is an alias for --fixture-mode
    if args.dry_run:
        args.fixture_mode = True

    # Disable rich if requested
    global RICH_AVAILABLE
    if args.no_rich:
        RICH_AVAILABLE = False

    tasks_path = Path(args.tasks)
    if not tasks_path.is_absolute():
        # Resolve relative to BASE_DIR (script location), not cwd
        tasks_path = (BASE_DIR / args.tasks).resolve()
    if not tasks_path.exists():
        if RICH_AVAILABLE:
            console.print(f"[red]Error: Tasks file not found at: {tasks_path}[/red]")
        else:
            print(f"[Error] Tasks file not found at: {tasks_path}")
        return

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    models = [m.strip() for m in args.models.split(",")]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_runs_dir = out_dir / "raw_runs"
    raw_runs_dir.mkdir(parents=True, exist_ok=True)

    # Print banner
    if RICH_AVAILABLE:
        banner = Panel.fit(
            "[bold cyan]🧬 MECHANISMTRACE-DDI: FRONTIER AI CAUSAL EVALUATION BENCHMARK[/bold cyan]\n"
            f"[dim]Tasks: {len(tasks)} | Models: {len(models)} | Trials: {args.trials} | Fixture Mode: {args.fixture_mode}[/dim]",
            border_style="cyan"
        )
        console.print(banner)
        console.print()
    else:
        print("\n" + "="*70)
        print(_blue("🧬  MECHANISMTRACE-DDI: FRONTIER AI CAUSAL EVALUATION BENCHMARK"))
        print(f"    Tasks: {len(tasks)} | Models: {models} | Repeated Trials: {args.trials}")
        print(f"    Fixture Mode: {args.fixture_mode}")
        print("="*70 + "\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_report = {
        "benchmark": "MechanismTrace-DDI",
        "timestamp": timestamp,
        "trials_per_task": args.trials,
        "results": {}
    }

    for model_idx, model in enumerate(models):
        if RICH_AVAILABLE:
            console.print(f"\n[bold blue]📊 Evaluating Model: {model}[/bold blue]")
        else:
            print(f"\n[Evaluating Model: {model}]")
        
        model_runs = []
        total_score_sum = 0.0
        passed_count = 0
        total_latency = 0.0
        total_tokens = 0
        total_cost = 0.0

        if RICH_AVAILABLE:
            # Use rich progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True
            ) as progress:
                task_progress = progress.add_task(f"[cyan]{model}", total=len(tasks))
                
                for task in tasks:
                    progress.update(task_progress, description=f"[cyan]{task['id']}: {task['title'][:40]}...")
                    task_trial_scores = []
                    task_trial_passed = 0

                    for trial in range(args.trials):
                        call_res = call_model(model, task, dry_run=args.dry_run, fixture_mode=args.fixture_mode, transcription_control=args.transcription_control, causal_scaffold=args.causal_scaffold)
                        eval_res = DeterministicCausalGrader.evaluate_task(task, call_res["output"])
                        
                        # Compute atomic accuracy
                        model_json = DeterministicCausalGrader.parse_candidate_response(call_res["output"])
                        atomic_metrics = evaluate_atomic_accuracy(model_json, task["id"])
                        eval_res["atomic_accuracy"] = atomic_metrics["atomic_accuracy"]
                        eval_res["atomic_matched"] = atomic_metrics["atomic_matched"]
                        eval_res["atomic_total"] = atomic_metrics["atomic_total"]
                        
                        total_latency += call_res["latency_ms"]
                        total_tokens += call_res["tokens"]
                        total_cost += call_res["cost_usd"]

                        task_trial_scores.append(eval_res["total_score"])
                        if eval_res["passed"]:
                            task_trial_passed += 1

                        # Save raw response
                        raw_filename = f"{model.replace('/', '_')}_{task['id']}_trial{trial+1}_{timestamp}.json"
                        with open(raw_runs_dir / raw_filename, "w", encoding="utf-8") as rf:
                            json.dump({
                                "task_id": task["id"],
                                "model": model,
                                "trial": trial + 1,
                                "latency_ms": call_res["latency_ms"],
                                "tokens": call_res["tokens"],
                                "cost_usd": call_res["cost_usd"],
                                "raw_output": call_res["output"],
                                "eval_grade": eval_res
                            }, rf, indent=2, ensure_ascii=False)

                    avg_score = round(sum(task_trial_scores) / len(task_trial_scores), 2)
                    total_score_sum += avg_score
                    is_passed = (task_trial_passed == args.trials)
                    
                    if is_passed:
                        passed_count += 1
                        if RICH_AVAILABLE:
                            console.print(f"  [green]✅ {task['id']}: PASSED ({avg_score}/100)[/green]")
                        else:
                            print(_green(f" -> {task['id']}: ✅ PASSED ({avg_score}/100)"))
                    else:
                        reason = eval_res['reasons'][0] if eval_res['reasons'] else 'Failed threshold'
                        if RICH_AVAILABLE:
                            console.print(f"  [red]❌ {task['id']}: FAILED ({avg_score}/100 - {reason})[/red]")
                        else:
                            print(_red(f" -> {task['id']}: ❌ FAILED ({avg_score}/100 - {reason})"))

                    model_runs.append({
                        "task_id": task["id"],
                        "avg_score": avg_score,
                        "passed": is_passed,
                        "edge_accuracy": eval_res["edge_accuracy_pct"],
                        "atomic_accuracy": round(eval_res.get("atomic_accuracy", 0.0) * 100, 1),
                        "atomic_matched": eval_res.get("atomic_matched", 0),
                        "atomic_total": eval_res.get("atomic_total", 0),
                        "cpcs_score": eval_res.get("cpcs_score", 0.0),
                        "cpcs_continuity": eval_res.get("cpcs_continuity", "UNKNOWN"),
                        "reasons": eval_res["reasons"]
                    })
                    
                    progress.advance(task_progress)
        else:
            # Fallback without rich progress
            for task in tasks:
                print(f" -> {task['id']}: {task['title'][:45]}... ", end="", flush=True)
                task_trial_scores = []
                task_trial_passed = 0

                for trial in range(args.trials):
                    call_res = call_model(model, task, dry_run=args.dry_run, fixture_mode=args.fixture_mode, transcription_control=args.transcription_control, causal_scaffold=args.causal_scaffold)
                    eval_res = DeterministicCausalGrader.evaluate_task(task, call_res["output"])
                    
                    # Compute atomic accuracy
                    model_json = DeterministicCausalGrader.parse_candidate_response(call_res["output"])
                    atomic_metrics = evaluate_atomic_accuracy(model_json, task["id"])
                    eval_res["atomic_accuracy"] = atomic_metrics["atomic_accuracy"]
                    eval_res["atomic_matched"] = atomic_metrics["atomic_matched"]
                    eval_res["atomic_total"] = atomic_metrics["atomic_total"]
                    
                    total_latency += call_res["latency_ms"]
                    total_tokens += call_res["tokens"]
                    total_cost += call_res["cost_usd"]

                    task_trial_scores.append(eval_res["total_score"])
                    if eval_res["passed"]:
                        task_trial_passed += 1

                    # Save raw response
                    raw_filename = f"{model.replace('/', '_')}_{task['id']}_trial{trial+1}_{timestamp}.json"
                    with open(raw_runs_dir / raw_filename, "w", encoding="utf-8") as rf:
                        json.dump({
                            "task_id": task["id"],
                            "model": model,
                            "trial": trial + 1,
                            "latency_ms": call_res["latency_ms"],
                            "tokens": call_res["tokens"],
                            "cost_usd": call_res["cost_usd"],
                            "raw_output": call_res["output"],
                            "eval_grade": eval_res
                        }, rf, indent=2, ensure_ascii=False)

                avg_score = round(sum(task_trial_scores) / len(task_trial_scores), 2)
                total_score_sum += avg_score
                is_passed = (task_trial_passed == args.trials)
                if is_passed:
                    passed_count += 1
                    print(_green(f"✅ PASSED ({avg_score}/100)"))
                else:
                    reason = eval_res['reasons'][0] if eval_res['reasons'] else 'Failed threshold'
                    print(_red(f"❌ FAILED ({avg_score}/100 - {reason})"))

                model_runs.append({
                    "task_id": task["id"],
                    "avg_score": avg_score,
                    "passed": is_passed,
                    "edge_accuracy": eval_res["edge_accuracy_pct"],
                    "atomic_accuracy": round(eval_res.get("atomic_accuracy", 0.0) * 100, 1),
                    "atomic_matched": eval_res.get("atomic_matched", 0),
                    "atomic_total": eval_res.get("atomic_total", 0),
                    "cpcs_score": eval_res.get("cpcs_score", 0.0),
                    "cpcs_continuity": eval_res.get("cpcs_continuity", "UNKNOWN"),
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

        # Model summary
        if RICH_AVAILABLE:
            summary_table = Table(title=f"Summary: {model}", show_header=True, header_style="bold magenta")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")
            summary_table.add_row("Tasks Passed", f"{passed_count}/{len(tasks)}")
            summary_table.add_row("Pass Rate", f"{pass_rate}%")
            summary_table.add_row("Mean Score", f"{mean_score}/100")
            summary_table.add_row("Avg Latency", f"{round(total_latency/(len(tasks)*args.trials), 1)}ms")
            summary_table.add_row("Total Tokens", f"{total_tokens:,}")
            summary_table.add_row("Total Cost", f"${total_cost:.4f}")
            console.print(summary_table)
            console.print()
        else:
            print(f"--- Summary for {model} ---")
            print(f"Pass Rate: {passed_count}/{len(tasks)} ({pass_rate}%) | Mean Score: {mean_score}/100 | Avg Latency: {round(total_latency/(len(tasks)*args.trials), 1)}ms\n")

    # Threshold Sensitivity Analysis
    thresholds = [int(t.strip()) for t in args.thresholds.split(",")]
    threshold_sensitivity = {}
    for model in models:
        model_data = benchmark_report["results"][model]
        task_scores = [t["avg_score"] for t in model_data["task_breakdown"]]
        threshold_results = {}
        for thresh in thresholds:
            passed = sum(1 for s in task_scores if s >= thresh)
            threshold_results[thresh] = {
                "pass_count": passed,
                "pass_rate_pct": round((passed / len(task_scores)) * 100, 1)
            }
        threshold_sensitivity[model] = threshold_results

    benchmark_report["threshold_sensitivity"] = threshold_sensitivity

    if RICH_AVAILABLE:
        console.print("\n[bold cyan]📊 Threshold Sensitivity Analysis[/bold cyan]")
        thresh_table = Table(show_header=True, header_style="bold magenta")
        thresh_table.add_column("Threshold", justify="center", style="cyan")
        for model in models:
            thresh_table.add_column(model, justify="center", style="green")
        
        for thresh in thresholds:
            row = [str(thresh)]
            for model in models:
                rate = threshold_sensitivity[model][thresh]["pass_rate_pct"]
                row.append(f"{rate}%")
            thresh_table.add_row(*row)
        console.print(thresh_table)
    else:
        print("\n📊 Threshold Sensitivity Analysis:")
        for thresh in thresholds:
            rates = [threshold_sensitivity[m][thresh]["pass_rate_pct"] for m in models]
            print(f"  Threshold {thresh}: pass rates = {[f'{r}%' for r in rates]}")

    # Atomic vs Composed Gap Analysis
    atomic_composed_analysis = analyze_atomic_composed_gap(benchmark_report)
    benchmark_report["atomic_composed_gap"] = atomic_composed_analysis

    # Error Taxonomy Aggregation
    error_taxonomy: Dict[str, Any] = {}
    for model in models:
        model_tax = {
            "missing_hop": 0,
            "inverted_direction": 0,
            "spurious_edges": 0,
            "modifier_ignored": 0,
            "counterfactual_collapse": 0,
            "control_over_flag": 0,
            "fatal_dose_trap": 0
        }
        for task in benchmark_report["results"][model]["task_breakdown"]:
            reasons = task.get("reasons", [])
            for r in reasons:
                r_lower = r.lower()
                if "missing mandatory causal edge" in r_lower:
                    model_tax["missing_hop"] += 1
                if "spurious" in r_lower or "hallucinated" in r_lower:
                    model_tax["spurious_edges"] += 1
                if "modifier" in r_lower:
                    model_tax["modifier_ignored"] += 1
                if "counterfactual invariant failure" in r_lower or "residual_risk_remains" in r_lower:
                    model_tax["counterfactual_collapse"] += 1
                if "fatal safety trap" in r_lower:
                    model_tax["fatal_dose_trap"] += 1
            if task.get("cpcs_continuity") == "INVERTED_CAUSATION":
                model_tax["inverted_direction"] += 1
            if task["task_id"] in ["TASK-09", "TASK-10"] and not task["passed"]:
                model_tax["control_over_flag"] += 1

        error_taxonomy[model] = model_tax

    benchmark_report["error_taxonomy"] = error_taxonomy

    if RICH_AVAILABLE:
        console.print("\n[bold cyan]🔬 Error Taxonomy[/bold cyan]")
        error_table = Table(show_header=True, header_style="bold magenta")
        error_table.add_column("Error Type", style="cyan")
        for model in models:
            error_table.add_column(model, justify="center", style="green")
        
        for error_type in ["missing_hop", "inverted_direction", "spurious_edges", "modifier_ignored", "counterfactual_collapse", "control_over_flag", "fatal_dose_trap"]:
            row = [error_type.replace("_", " ").title()]
            for model in models:
                row.append(str(error_taxonomy[model].get(error_type, 0)))
            error_table.add_row(*row)
        console.print(error_table)

    # =============================================================================
    # TASK 3: Transporter Bias Ratio (TBR) & Alert Fatigue Index (AFI)
    # =============================================================================
    
    # Define transporter and CYP enzyme node identifiers
    CYP_ENZYMES = {
        "CYP3A4", "CYP2C19", "CYP2C9", "CYP2D6", "CYP3A5", "CYP1A2", "CYP2B6",
        "CYP2E1", "CYP2A6", "CYP2J2", "CYP4F2", "CYP11A1", "CYP11B1", "CYP17A1",
        "CYP19A1", "CYP21A2", "CYP24A1", "CYP26A1", "CYP27A1", "CYP27B1"
    }
    
    TRANSPORTERS = {
        "P-GP", "P-GLYCOPROTEIN", "ABCB1", "MDR1",
        "BCRP", "ABCG2",
        "OAT1", "OAT3", "OATP1B1", "OATP1B3", "OATP2B1",
        "OCT1", "OCT2", "OCT3",
        "MATE1", "MATE2K",
        "NKCC2", "NCC", "ENaC",
        "SGLT1", "SGLT2",
        "PEPT1", "PEPT2",
        "MRP2", "MRP3", "MRP4",
        "BSEP", "NTCP",
        "ENT1", "CNT1", "CNT2", "CNT3"
    }
    
    NEGATIVE_CONTROL_TASKS = {"TASK-09", "TASK-10"}
    
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]🔬 Transporter Bias & Alert Fatigue Analysis[/bold cyan]")
    
    bias_results = {}
    for model in models:
        model_data = benchmark_report["results"][model]
        task_breakdown = model_data.get("task_breakdown", [])
        
        # Count correctly identified CYP vs Transporter edges
        cyp_correct = 0
        cyp_total = 0
        transporter_correct = 0
        transporter_total = 0
        
        # False positives on negative controls
        fp_negative_controls = 0
        total_negative_controls = 0
        
        for task in task_breakdown:
            task_id = task.get("task_id", "")
            reasons = task.get("reasons", [])
            
            # Check negative control false positives
            if task_id in NEGATIVE_CONTROL_TASKS:
                total_negative_controls += 1
                # Count spurious edges on negative controls
                for r in reasons:
                    if "spurious" in r.lower() or "hallucinated" in r.lower():
                        fp_negative_controls += 1
            
            # We need to check the raw output for edge-level analysis
            # For now, use the reasons to infer
            for r in reasons:
                r_lower = r.lower()
                # Check for CYP enzyme mentions in missing edges
                for cyp in CYP_ENZYMES:
                    if cyp.lower() in r_lower and ("missing" in r_lower or "matched" in r_lower):
                        cyp_total += 1
                        if "matched" in r_lower or "correct" in r_lower:
                            cyp_correct += 1
                # Check for transporter mentions
                for trans in TRANSPORTERS:
                    if trans.lower() in r_lower and ("missing" in r_lower or "matched" in r_lower):
                        transporter_total += 1
                        if "matched" in r_lower or "correct" in r_lower:
                            transporter_correct += 1
        
        # Calculate TBR (higher = more CYP bias)
        cyp_recall = cyp_correct / cyp_total if cyp_total > 0 else 0
        trans_recall = transporter_correct / transporter_total if transporter_total > 0 else 0
        tbr = cyp_recall / trans_recall if trans_recall > 0 else float('inf') if cyp_recall > 0 else 1.0
        
        # Calculate AFI (False Positive Rate on negative controls)
        afi = fp_negative_controls / (total_negative_controls * 5) if total_negative_controls > 0 else 0.0  # 5 edges per task approx
        
        bias_results[model] = {
            "cyp_recall_pct": round(cyp_recall * 100, 1),
            "transporter_recall_pct": round(trans_recall * 100, 1),
            "tbr": round(tbr, 2) if tbr != float('inf') else "∞",
            "afi_pct": round(afi * 100, 1),
            "fp_negative_controls": fp_negative_controls,
            "total_negative_controls": total_negative_controls
        }
    
    benchmark_report["bias_analysis"] = bias_results
    
    if RICH_AVAILABLE:
        bias_table = Table(title="Transporter Bias Ratio (TBR) & Alert Fatigue Index (AFI)", show_header=True, header_style="bold magenta")
        bias_table.add_column("Model", style="cyan")
        bias_table.add_column("CYP Recall", justify="center", style="green")
        bias_table.add_column("Transporter Recall", justify="center", style="green")
        bias_table.add_column("TBR (CYP/Transporter)", justify="center", style="yellow")
        bias_table.add_column("AFI (%)", justify="center", style="red")
        bias_table.add_column("FP on Neg Controls", justify="center", style="red")
        
        for model in models:
            b = bias_results[model]
            bias_table.add_row(
                model,
                f"{b['cyp_recall_pct']}%",
                f"{b['transporter_recall_pct']}%",
                str(b['tbr']),
                f"{b['afi_pct']}%",
                f"{b['fp_negative_controls']}/{b['total_negative_controls']}"
            )
        console.print(bias_table)
    else:
        print("\n🔬 Transporter Bias & Alert Fatigue:")
        for model in models:
            b = bias_results[model]
            print(f"  {model}: CYP Recall={b['cyp_recall_pct']}%, Transporter Recall={b['transporter_recall_pct']}%, TBR={b['tbr']}, AFI={b['afi_pct']}%")

    # Statistical Rigor: Bootstrap CIs and Variance Analysis
    if args.trials > 1:
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]📊 Computing statistical confidence intervals...[/bold cyan]")
        else:
            print("\n📊 Computing statistical confidence intervals...")
        
        statistical_report = {}
        for model in models:
            trial_scores = load_raw_trial_scores(raw_runs_dir, model)
            if trial_scores:
                model_ci = compute_model_level_ci(
                    [s for task in trial_scores for s in task], 
                    len(tasks)
                )
                variance_analysis = analyze_trial_variance(trial_scores)
                statistical_report[model] = {
                    "bootstrap_ci": model_ci,
                    "variance_analysis": variance_analysis,
                }
        
        benchmark_report["statistical_analysis"] = statistical_report
        
        if RICH_AVAILABLE:
            for model in models:
                if model in statistical_report:
                    stats = statistical_report[model]
                    ci = stats["bootstrap_ci"]
                    var = stats["variance_analysis"]
                    
                    stats_table = Table(title=f"Statistical Analysis: {model}", show_header=True, header_style="bold magenta")
                    stats_table.add_column("Metric", style="cyan")
                    stats_table.add_column("Value", style="green")
                    stats_table.add_row("Mean Score", f"{ci['mean_score']:.1f}")
                    stats_table.add_row("95% CI", f"[{ci['ci_lower']:.1f}, {ci['ci_upper']:.1f}]")
                    stats_table.add_row("Std Dev", f"{ci['std']:.1f}")
                    stats_table.add_row("Pass Rate", f"{ci['pass_rate_pct']:.1f}%")
                    stats_table.add_row("Pass Rate 95% CI", f"[{ci['pass_rate_ci_lower']:.1f}%, {ci['pass_rate_ci_upper']:.1f}%]")
                    stats_table.add_row("Mean Task Variance", f"{var['mean_task_variance']:.4f}")
                    stats_table.add_row("Stability Score", f"{var['stability_score']:.3f}")
                    console.print(stats_table)
        else:
            print("✅ Statistical analysis complete")

    summary_file = out_dir / f"benchmark_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as sf:
        json.dump(benchmark_report, sf, indent=2, ensure_ascii=False)

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold green]🎉 Benchmark complete![/bold green]\n"
            f"[dim]Summary saved to: {summary_file}[/dim]\n"
            f"[dim]Raw model outputs preserved in: {raw_runs_dir}[/dim]",
            border_style="green"
        ))
    else:
        print("="*70)
        print(_bold(_green(f"🎉 Benchmark complete! Summary saved to: {summary_file}")))
        print(f"📁 Raw model outputs preserved in: {raw_runs_dir}")
        print("="*70 + "\n")

if __name__ == "__main__":
    main()
