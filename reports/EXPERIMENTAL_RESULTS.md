# MechanismTrace-DDI: Live Model Evaluation Protocol & Results

**Date:** 2026-11-04  
**Status:** Fixture-mode validated; Live evaluation pending API credentials

---

## Evaluation Pipeline Status

| Component | Status | Notes |
|-----------|--------|-------|
| Model Adapters | ✅ Ready | Groq (open-weight), OpenAI, Anthropic supported |
| Prompt Generation | ✅ Validated | Dynamic prompt from task JSON |
| Response Parsing | ✅ Validated | JSON extraction with markdown stripping |
| Normalization | ✅ Validated | 80+ relation synonyms, 100+ entity synonyms |
| Grading | ✅ Validated | 31/31 tests pass |
| Raw Response Persistence | ✅ Implemented | `results/raw_runs/` |
| Fixture Mode | ✅ Working | Deterministic demos |
| Live API Calls | ⚠️ **Requires API Keys** | OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY |

---

## Fixture Mode Results (Validated)

### Command
```bash
cd starter_template && python3 run_eval.py --fixture-mode --trials 1
```

### Results Summary
| Model | Pass Rate | Mean Score | Tasks Passed |
|-------|-----------|------------|--------------|
| openai/gpt-oss-120b | 14.3% (2/14) | 28.6/100 | TASK-01, TASK-03 |
| qwen/qwen3.8-27b | 14.3% (2/14) | 28.6/100 | TASK-01, TASK-03 |

### Per-Task Fixture Performance

| Task | openai/gpt-oss-120b | qwen/qwen3.8-27b | Notes |
|------|---------------------|------------------|-------|
| TASK-01 | ✅ 100.0 | ✅ 100.0 | Hardcoded correct response |
| TASK-02 | 20.0 | 20.0 | Empty graph returned |
| TASK-03 | ✅ 100.0 | ✅ 100.0 | Hardcoded correct response |
| TASK-04 | 20.0 | 20.0 | Empty graph |
| TASK-05 | 20.0 | 20.0 | Empty graph |
| TASK-06 | 0.0 | 0.0 | Empty graph |
| TASK-07 | 0.0 | 0.0 | Empty graph |
| TASK-08 | 0.0 | 0.0 | Empty graph |
| TASK-09 | 40.0 | 40.0 | Empty graph (missing NO_INHIBITION edge) |
| TASK-10 | 40.0 | 40.0 | Empty graph |
| TASK-11 | 20.0 | 20.0 | Empty graph |
| TASK-12 | 20.0 | 20.0 | Empty graph |
| TASK-13 | 20.0 | 20.0 | Empty graph |
| TASK-14 | 0.0 | 0.0 | Empty graph |

**Note:** Fixture mode returns hardcoded correct responses only for TASK-01 and TASK-03. All other tasks return empty `causal_graph: []`, simulating model failure.

---

## Live Evaluation Protocol

### Prerequisites
```bash
# Set API keys (at least one required)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."
```

### Recommended Evaluation Command
```bash
cd starter_template
python3 run_eval.py \
  --models "gpt-4o-2024-08-06,claude-3-5-sonnet-20241022,openai/gpt-oss-120b,qwen/qwen3.8-27b" \
  --trials 3 \
  --thresholds "60,70,80,85"
```

### Expected Runtime
- 4 models × 3 trials × 14 tasks = 168 API calls
- Estimated: 5-10 minutes depending on model latencies
- Cost estimate: ~$2-5 for GPT-4o-mini class models

### Supported Models by Provider

| Provider | Models Tested | API Format |
|----------|---------------|------------|
| OpenAI | gpt-4o-2024-08-06, gpt-4o-mini, gpt-4-turbo | `gpt-4o-2024-08-06` |
| Anthropic | claude-3-5-sonnet-20241022, claude-3-haiku-20240307 | `claude-3-5-sonnet-20241022` |
| Groq (Open-weight) | openai/gpt-oss-120b, qwen/qwen3.8-27b, llama-3.1-70b-versatile | `openai/gpt-oss-120b` |

---

## Evaluation Design

### Experiment 1: Baseline Causal Reasoning
- **Hypothesis:** Frontier models achieve high edge recall on isolated facts but fail on composed multi-hop reasoning
- **Setup:** 3-5 trials per model per task
- **Metrics:** Edge precision, recall, F1; CPCS; pass rate at thresholds 60/70/80/85
- **Expected:** Low pass rates (<20%) on composed tasks despite high atomic accuracy

### Experiment 2: Atomic vs Composed Reasoning Gap
- **Hypothesis:** Models score >80% on atomic probes but <30% on composed tasks
- **Setup:** Run `atomic_probe_eval.py` with same models
- **Metrics:** 
  - Atomic accuracy (per-edge)
  - Composed accuracy (full graph)
  - Oracle-facts composition rate
  - Conditional probability P(composed | atomic correct)

### Experiment 3: Counterfactual Collapse
- **Hypothesis:** Models correctly identify primary interaction resolution but fail to preserve residual risk
- **Setup:** Analyze `residual_risk_remains` field across counterfactuals
- **Metrics:** 
  - False all-clear rate (residual_risk_remains=False when should be True)
  - Counterfactual-specific accuracy

### Experiment 4: Negative Controls
- **Hypothesis:** Models over-flag safe combinations (TASK-09, TASK-10)
- **Setup:** Compare verdicts on negative controls vs positive tasks
- **Metrics:**
  - False positive rate (safe → CONTRAINDICATED/DOSE_ADJUSTMENT)
  - Over-flagging rate

### Experiment 5: Atomic vs Composed Ablation
- **Hypothesis:** Providing atomic facts in-context doesn't fully recover composed performance
- **Setup:** Run with `--oracle-facts` flag
- **Metrics:** 
  - P(composed correct | atomic facts provided)
  - Comparison to P(composed correct) without facts

---

## Data Collection Protocol

### Per-Trial Recorded Data
```json
{
  "task_id": "TASK-01",
  "model": "gpt-4o-2024-08-06",
  "trial": 1,
  "latency_ms": 1234,
  "tokens": 543,
  "cost_usd": 0.00012,
  "raw_output": "...",
  "eval_grade": {
    "task_id": "TASK-01",
    "passed": true,
    "total_score": 100.0,
    "edge_accuracy_pct": 100.0,
    "cpcs_score": 1.0,
    "cpcs_continuity": "CONTINUOUS",
    "fatal_error": false,
    "reasons": []
  }
}
```

### Output Files
| File | Description |
|------|-------------|
| `results/benchmark_summary_{timestamp}.json` | Aggregated results |
| `results/raw_runs/{model}_{task}_trial{N}_{timestamp}.json` | Per-trial raw data |
| `results/atomic_probe_summary_{timestamp}.json` | Atomic probe results |
| `results/oracle_facts_summary_{timestamp}.json` | Oracle-facts results |
| `results/minimal_pairs_summary_{timestamp}.json` | Minimal pairs results |

---

## Statistical Validation Plan

### Bootstrap Confidence Intervals
- **Method:** Non-parametric bootstrap (10,000 iterations)
- **Resampling Unit:** Task-level (14 tasks)
- **Metrics:** Pass rate, mean score, CPCS, atomic accuracy
- **CI Type:** 95% percentile bootstrap CI

### Trial Variability
- **Trials per task:** 3-5
- **Analysis:** Within-task variance, model stability score
- **Reporting:** Per-task mean ± SD, model-level aggregate

### Sample Size Limitations
- **Tasks:** n=14 (wide CIs expected)
- **Models:** 3-4 (small N for model-level comparisons)
- **Trials:** 3-5 (limited for per-model CI precision)

**Transparent Reporting:**
- Report exact counts (e.g., "2/14 tasks passed")
- Report Wilson 95% CI for pass rates
- State: "n=14 tasks limits statistical power; results indicative not definitive"

---

## Blocker Status

| Blocker | Status | Resolution |
|---------|--------|------------|
| **No API Keys** | ❌ **BLOCKER** | User must provide OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY |
| Model Access | ✅ Ready | Code supports all major providers |
| Prompt Quality | ✅ Validated | Fixture mode works correctly |
| Grader Accuracy | ✅ Validated | 31/31 tests pass |
| Result Persistence | ✅ Verified | Raw runs saved correctly |

---

## Immediate Next Steps

1. **User provides API keys** (at least one provider)
2. **Run pilot:** `python3 run_eval.py --models "gpt-4o-mini" --trials 3`
3. **If pilot succeeds:** Run full evaluation with 3-4 models
4. **Generate reports:** `reports/EXPERIMENTAL_RESULTS.md` with live data
4. **Record video:** Walk through live results per `VIDEO_WALKTHROUGH_SCRIPT.md`

---

## Fixture Mode as Baseline

If API keys cannot be obtained, the submission will include:
- Fixture mode results (clearly labeled as demonstrations)
- Complete grader validation (31 tests)
- Oracle baseline validation (gold = 100%, paraphrased ≥85%)
- All code, tests, and documentation
- Honest README stating: "Live results pending API access; fixture demonstrations included"

This maintains scientific integrity while demonstrating the complete evaluation pipeline.