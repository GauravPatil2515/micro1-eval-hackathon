#!/usr/bin/env python3
"""
Visualization CLI for MechanismTrace-DDI
Generates Mermaid diagrams and terminal comparisons for video walkthrough.
"""
import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.visualization import (
    generate_mermaid_graph, 
    print_terminal_comparison,
    generate_diff_visualization,
    generate_task_mermaid
)
from graders.causal_grader import DeterministicCausalGrader


def main():
    parser = argparse.ArgumentParser(description="Generate MechanismTrace-DDI visualizations")
    parser.add_argument("--task", type=str, help="Task ID to visualize (e.g., TASK-01)")
    parser.add_argument("--all", action="store_true", help="Visualize all tasks")
    parser.add_argument("--model-output", type=str, help="Path to model output JSON file")
    parser.add_argument("--mermaid", action="store_true", help="Output Mermaid diagrams")
    parser.add_argument("--terminal", action="store_true", help="Output terminal comparison")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    # Load tasks
    with open(BASE_DIR / "dataset" / "tasks.json") as f:
        tasks = json.load(f)

    # Filter tasks
    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        if not tasks:
            print(f"Task {args.task} not found")
            return 1
    elif not args.all:
        print("Use --task TASK-01 or --all")
        return 1

    # Load model output if provided
    model_json = None
    if args.model_output:
        with open(args.model_output) as f:
            data = json.load(f)
            model_json = data if "causal_graph" in data else DeterministicCausalGrader.parse_candidate_response(json.dumps(data))

    # If neither flag is set, default to terminal
    show_mermaid = args.mermaid
    show_terminal = args.terminal or (not args.mermaid and not args.output)

    for task in tasks:
        gt = task["ground_truth"]
        expected = gt.get("causal_edges", [])

        if show_mermaid:
            output_lines.append(generate_task_mermaid(task, model_json, show_diff=True))
            output_lines.append("")

        if show_terminal:
            print_terminal_comparison(task, model_json or {"causal_graph": []})
            print("")

    if args.output and output_lines:
        with open(args.output, "w") as f:
            f.write("\n".join(output_lines))
        print(f"Output written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())