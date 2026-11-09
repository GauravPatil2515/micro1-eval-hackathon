"""
Statistical Analysis for MechanismTrace-DDI
Bootstrap confidence intervals, variance analysis, McNemar's test, Wilson intervals,
and statistical rigor utilities.
"""
import json
import math
import random
import statistics
from typing import List, Dict, Any, Tuple, Callable
from pathlib import Path


def bootstrap_confidence_interval(
    data: List[float], 
    statistic: Callable[[List[float]], float] = statistics.mean,
    confidence: float = 0.95,
    n_bootstrap: int = 10000,
    random_seed: int = 42
) -> Tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for a statistic.
    
    Returns: (point_estimate, ci_lower, ci_upper)
    """
    if len(data) < 2:
        return (statistic(data), statistic(data), statistic(data))
    
    random.seed(random_seed)
    n = len(data)
    bootstrap_stats = []
    
    for _ in range(n_bootstrap):
        sample = [random.choice(data) for _ in range(n)]
        bootstrap_stats.append(statistic(sample))
    
    bootstrap_stats.sort()
    alpha = (1 - confidence) / 2
    lower_idx = int(alpha * n_bootstrap)
    upper_idx = int((1 - alpha) * n_bootstrap)
    
    point_est = statistic(data)
    ci_lower = bootstrap_stats[lower_idx]
    ci_upper = bootstrap_stats[upper_idx]
    
    return (point_est, ci_lower, ci_upper)


def bootstrap_ci_proportion(
    successes: int, 
    total: int,
    confidence: float = 0.95,
    n_bootstrap: int = 10000,
    random_seed: int = 42
) -> Tuple[float, float, float]:
    """
    Bootstrap CI for a proportion (pass rate).
    
    Returns: (point_estimate, ci_lower, ci_upper) as percentages
    """
    if total == 0:
        return (0.0, 0.0, 0.0)
    
    # Create binary data
    data = [1] * successes + [0] * (total - successes)
    
    def prop_stat(d):
        return (sum(d) / len(d)) * 100
    
    return bootstrap_confidence_interval(data, prop_stat, confidence, n_bootstrap, random_seed)


def compute_task_level_ci(
    task_scores: List[List[float]],  # [task][trial] = score
    confidence: float = 0.95
) -> List[Dict[str, Any]]:
    """
    Compute per-task confidence intervals across trials.
    """
    results = []
    for i, scores in enumerate(task_scores):
        if not scores:
            results.append({"task_index": i, "mean": 0.0, "ci_lower": 0.0, "ci_upper": 0.0})
            continue
        
        mean, lower, upper = bootstrap_confidence_interval(scores, confidence=confidence)
        results.append({
            "task_index": i,
            "mean": round(mean, 2),
            "ci_lower": round(lower, 2),
            "ci_upper": round(upper, 2),
            "std": round(statistics.stdev(scores) if len(scores) > 1 else 0.0, 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
        })
    return results


def compute_model_level_ci(
    all_trial_scores: List[float],  # All trials across all tasks
    n_tasks: int,
    confidence: float = 0.95
) -> Dict[str, Any]:
    """
    Compute model-level confidence intervals.
    """
    if not all_trial_scores:
        return {"mean": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}
    
    mean, lower, upper = bootstrap_confidence_interval(all_trial_scores, confidence=confidence)
    
    # Also compute pass rate CI
    passed = sum(1 for s in all_trial_scores if s >= 80.0)
    total = len(all_trial_scores)
    pass_rate, pr_lower, pr_upper = bootstrap_ci_proportion(passed, total, confidence)
    
    return {
        "mean_score": round(mean, 2),
        "ci_lower": round(lower, 2),
        "ci_upper": round(upper, 2),
        "std": round(statistics.stdev(all_trial_scores) if len(all_trial_scores) > 1 else 0.0, 2),
        "pass_rate_pct": round(pass_rate, 1),
        "pass_rate_ci_lower": round(pr_lower, 1),
        "pass_rate_ci_upper": round(pr_upper, 1),
        "total_trials": total,
        "trials_passed": passed,
    }


def analyze_trial_variance(trial_scores: List[List[float]]) -> Dict[str, Any]:
    """
    Analyze trial-to-trial variance (model output stability).
    """
    if not trial_scores:
        return {}
    
    n_tasks = len(trial_scores)
    n_trials = len(trial_scores[0]) if trial_scores[0] else 0
    
    # Per-task variance
    task_vars = []
    for scores in trial_scores:
        if len(scores) > 1:
            task_vars.append(statistics.variance(scores))
    
    # Overall trial variance (flattened)
    all_scores = [s for task in trial_scores for s in task]
    
    return {
        "n_tasks": n_tasks,
        "n_trials_per_task": n_trials,
        "mean_task_variance": round(statistics.mean(task_vars), 4) if task_vars else 0.0,
        "max_task_variance": round(max(task_vars), 4) if task_vars else 0.0,
        "overall_variance": round(statistics.variance(all_scores), 4) if len(all_scores) > 1 else 0.0,
        "stability_score": round(1.0 - min(1.0, statistics.mean(task_vars) / 1000.0), 3) if task_vars else 1.0,
    }


def generate_statistical_report(benchmark_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive statistical report from benchmark results.
    Expects benchmark_results with structure from run_eval.py
    """
    report = {
        "models": {},
        "summary": {}
    }
    
    for model, model_data in benchmark_results.get("results", {}).items():
        task_breakdown = model_data.get("task_breakdown", [])
        
        # Collect all trial scores
        # Note: run_eval.py stores avg_score per task, but we need raw trial scores
        # For now, we'll use the avg_scores and compute approximate CI
        # In a full multi-trial run, we'd load raw_runs/
        
        task_scores_list = []
        all_scores = []
        
        for task in task_breakdown:
            # We only have avg_score, not individual trials
            # For proper CI, we'd need to load raw_runs
            avg = task.get("avg_score", 0.0)
            all_scores.append(avg)
        
        # Model-level CI (using task averages as proxy)
        if all_scores:
            model_ci = compute_model_level_ci(all_scores, len(task_breakdown))
            
            # Per-task CI (approximate - using single value per task)
            task_cis = []
            for task in task_breakdown:
                task_cis.append({
                    "task_id": task["task_id"],
                    "score": task.get("avg_score", 0.0),
                    "passed": task.get("passed", False),
                    "edge_accuracy": task.get("edge_accuracy", 0.0),
                    "atomic_accuracy": task.get("atomic_accuracy", 0.0),
                    "cpcs_score": task.get("cpcs_score", 0.0),
                })
            
            report["models"][model] = {
                **model_ci,
                "task_breakdown": task_cis,
            }
    
    return report


def load_raw_trial_scores(raw_runs_dir: Path, model: str) -> List[List[float]]:
    """
    Load raw trial scores from raw_runs directory.
    Returns: [task][trial] = score
    """
    model_prefix = model.replace("/", "_")
    task_scores = {}
    
    for filepath in sorted(raw_runs_dir.glob(f"{model_prefix}_*_trial*_{model_prefix}.json")):
        # Actually the format is: {model}_{task}_trial{N}_{timestamp}.json
        pass
    
    # Simpler approach: scan all files
    trial_data = {}
    for filepath in raw_runs_dir.glob(f"{model_prefix}_*.json"):
        with open(filepath) as f:
            data = json.load(f)
        task_id = data["task_id"]
        trial = data["trial"]
        score = data["eval_grade"]["total_score"]
        
        if task_id not in trial_data:
            trial_data[task_id] = {}
        trial_data[task_id][trial] = score
    
    # Convert to list of lists
    task_list = sorted(trial_data.keys())
    result = []
    for task_id in task_list:
        trials = trial_data[task_id]
        max_trial = max(trials.keys())
        task_scores = [trials.get(t, 0.0) for t in range(1, max_trial + 1)]
        result.append(task_scores)
    
    return result


def main():
    """Demo with sample data."""
    # Sample: 5 trials across 3 tasks
    sample_trials = [
        [85, 82, 88, 84, 86],  # Task 1
        [45, 50, 42, 48, 44],  # Task 2
        [90, 92, 88, 91, 89],  # Task 3
    ]
    
    print("=== Bootstrap CI Demo ===")
    for i, scores in enumerate(sample_trials):
        mean, lower, upper = bootstrap_confidence_interval(scores)
        print(f"Task {i+1}: mean={mean:.1f}, 95% CI=[{lower:.1f}, {upper:.1f}]")
    
    # Flatten for model-level
    all_scores = [s for task in sample_trials for s in task]
    model_ci = compute_model_level_ci(all_scores, len(sample_trials))
    print(f"\nModel: {model_ci}")
    
    # Variance analysis
    var_analysis = analyze_trial_variance(sample_trials)
    print(f"\nVariance: {var_analysis}")


# ============================================================================
# McNemar's Test for Paired Comparisons (Atomic vs Composed)
# ============================================================================

def mcnemar_test(
    both_correct: int,
    model_a_only: int,
    model_b_only: int,
    both_wrong: int,
    continuity_correction: bool = True
) -> Dict[str, Any]:
    """
    McNemar's test for paired nominal data.
    
    Used to compare atomic vs composed accuracy on the same test items.
    
    Args:
        both_correct: Both model A and model B correct
        model_a_only: Model A correct, Model B wrong
        model_b_only: Model B correct, Model A wrong
        both_wrong: Both wrong
        continuity_correction: Apply Yates' continuity correction
    
    Returns:
        Dict with chi2 statistic, p-value, and interpretation
    """
    # McNemar's test statistic: (|b - c| - 1)^2 / (b + c) with continuity correction
    # or (b - c)^2 / (b + c) without correction
    b = model_a_only
    c = model_b_only
    
    if b + c == 0:
        return {
            "chi2": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "No discordant pairs - cannot compute test",
            "discordant_pairs": 0
        }
    
    if continuity_correction:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    else:
        chi2 = (b - c) ** 2 / (b + c)
    
    # p-value from chi-square distribution with 1 df
    # Using survival function approximation
    p_value = 1.0 - _chi2_cdf(chi2, 1)
    
    return {
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 4),
        "significant": p_value < 0.05,
        "interpretation": "Significant difference between paired proportions" if p_value < 0.05 else "No significant difference",
        "discordant_pairs": b + c,
        "model_a_only": b,
        "model_b_only": c,
        "both_correct": both_correct,
        "both_wrong": both_wrong
    }


def _chi2_cdf(x: float, df: int) -> float:
    """Approximate chi-square CDF using incomplete gamma function."""
    # Simple approximation for df=1
    if df == 1:
        # For df=1, chi2 CDF = erf(sqrt(x/2))
        import math
        return math.erf(math.sqrt(x / 2))
    # Fallback for other df
    return 0.5


def wilson_proportion_interval(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Wilson score interval for a binomial proportion.
    
    More accurate than normal approximation, especially for small samples
    or extreme proportions.
    
    Returns: (point_estimate, ci_lower, ci_upper) as percentages
    """
    if total == 0:
        return (0.0, 0.0, 0.0)
    
    p = successes / total
    z = _z_score(confidence)
    
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    
    lower = max(0.0, center - margin) * 100
    upper = min(1.0, center + margin) * 100
    point = p * 100
    
    return (round(point, 1), round(lower, 1), round(upper, 1))


def _z_score(confidence: float) -> float:
    """Get z-score for common confidence levels."""
    z_scores = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }
    return z_scores.get(confidence, 1.960)


def compare_atomic_vs_composed(
    atomic_results: List[bool],  # True if atomic correct
    composed_results: List[bool]  # True if composed correct
) -> Dict[str, Any]:
    """
    Compare atomic vs composed performance using McNemar's test.
    
    Args:
        atomic_results: List of booleans for atomic probe accuracy per item
        composed_results: List of booleans for composed task accuracy per item
        (Must be same length - same items evaluated)
    
    Returns:
        Dict with McNemar's test result and summary stats
    """
    if len(atomic_results) != len(composed_results):
        raise ValueError("atomic_results and composed_results must have same length")
    
    both_correct = sum(1 for a, c in zip(atomic_results, composed_results) if a and c)
    atomic_only = sum(1 for a, c in zip(atomic_results, composed_results) if a and not c)
    composed_only = sum(1 for a, c in zip(atomic_results, composed_results) if not a and c)
    both_wrong = sum(1 for a, c in zip(atomic_results, composed_results) if not a and not c)
    
    mcnemar_result = mcnemar_test(both_correct, atomic_only, composed_only, both_wrong)
    
    atomic_acc = sum(atomic_results) / len(atomic_results) * 100
    composed_acc = sum(composed_results) / len(composed_results) * 100
    
    # Wilson CIs for each
    atomic_wilson = wilson_proportion_interval(sum(atomic_results), len(atomic_results))
    composed_wilson = wilson_proportion_interval(sum(composed_results), len(composed_results))
    
    return {
        "mcnemar": mcnemar_result,
        "atomic_accuracy_pct": round(atomic_acc, 1),
        "atomic_wilson_ci": atomic_wilson,
        "composed_accuracy_pct": round(composed_acc, 1),
        "composed_wilson_ci": composed_wilson,
        "accuracy_gap_pct": round(atomic_acc - composed_acc, 1),
        "n_items": len(atomic_results)
    }


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Statistical Analysis for MechanismTrace-DDI")
    parser.add_argument("--summary", type=str, default="", help="Path to benchmark_summary.json")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    summary_path = Path(args.summary) if args.summary else base_dir / "results" / "benchmark_summary_20261106_235505.json"

    if summary_path.exists():
        with open(summary_path) as f:
            data = json.load(f)
        
        print("=" * 70)
        print("📊 MECHANISMTRACE-DDI: STATISTICAL RIGOR & BOOTSTRAP ANALYSIS")
        print(f"File: {summary_path.name}")
        print("=" * 70)

        for model_id, model_data in data.get("results", {}).items():
            print(f"\nModel: {model_id}")
            task_breakdown = model_data.get("task_breakdown", [])
            scores = [t.get("avg_score", 0.0) for t in task_breakdown]
            if not scores:
                continue

            # Bootstrap Mean CI (10,000 resamples)
            mean_pt, mean_lo, mean_hi = bootstrap_confidence_interval(scores, n_bootstrap=10000)
            print(f"  Mean Score: {mean_pt:.2f}/100 (95% Bootstrap CI: [{mean_lo:.2f}, {mean_hi:.2f}])")

            # Wilson Score Interval for Strict Pass Rate (>= 80)
            strict_passes = sum(1 for s in scores if s >= 80.0)
            pt_s, lo_s, hi_s = wilson_proportion_interval(strict_passes, len(scores))
            print(f"  Strict Pass Rate (>=80): {pt_s:.1f}% ({strict_passes}/{len(scores)}) [95% Wilson CI: {lo_s:.1f}% - {hi_s:.1f}%]")

            # Wilson Score Interval for Relaxed Pass Rate (>= 60)
            relaxed_passes = sum(1 for s in scores if s >= 60.0)
            pt_r, lo_r, hi_r = wilson_proportion_interval(relaxed_passes, len(scores))
            print(f"  Relaxed Pass Rate (>=60): {pt_r:.1f}% ({relaxed_passes}/{len(scores)}) [95% Wilson CI: {lo_r:.1f}% - {hi_r:.1f}%]")

            # Edge Accuracy & Atomic Accuracy summary
            edge_accs = [t.get("edge_accuracy", 0.0) for t in task_breakdown]
            if edge_accs:
                e_pt, e_lo, e_hi = bootstrap_confidence_interval(edge_accs, n_bootstrap=10000)
                print(f"  Mean Causal Edge Accuracy: {e_pt:.1f}% [95% Bootstrap CI: {e_lo:.1f}% - {e_hi:.1f}%]")
            
            cpcs_scores = [t.get("cpcs_score", 0.0) for t in task_breakdown]
            if cpcs_scores:
                c_pt, c_lo, c_hi = bootstrap_confidence_interval(cpcs_scores, n_bootstrap=10000)
                print(f"  Mean CPCS_v2 Graph Score: {c_pt:.3f} [95% Bootstrap CI: {c_lo:.3f} - {c_hi:.3f}]")

        print("\n" + "=" * 70)
    else:
        main()
