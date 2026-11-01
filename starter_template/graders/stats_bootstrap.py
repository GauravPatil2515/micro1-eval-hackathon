"""
Statistical Analysis for MechanismTrace-DDI
Bootstrap confidence intervals, variance analysis, and statistical rigor utilities.
"""
import json
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


if __name__ == "__main__":
    main()