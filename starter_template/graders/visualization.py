"""
Graph Visualization for MechanismTrace-DDI
Generates terminal ASCII graphs, Mermaid diagrams, Sankey diagrams, spider charts,
and diff visualizations for model vs ground truth causal graph comparison.
"""
from typing import Dict, Any, List, Set, Tuple
from graders.normalizer import normalize_entity, normalize_relation


def _build_edge_set(edges: List[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    """Build set of normalized (src, rel, tgt) tuples."""
    edge_set = set()
    for e in edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        rel = normalize_relation(e.get("relation", ""))
        if src and tgt:
            edge_set.add((src, rel, tgt))
    return edge_set


def generate_ascii_graph(edges: List[Dict[str, Any]], title: str = "Causal Graph") -> str:
    """Generate a simple ASCII representation of the causal graph."""
    if not edges:
        return f"{title}\n  (empty graph)"
    
    lines = [f"{title}"]
    lines.append("=" * len(title))
    
    edge_set = _build_edge_set(edges)
    for src, rel, tgt in sorted(edge_set):
        lines.append(f"  {src} ──[{rel}]──> {tgt}")
    
    return "\n".join(lines)


def generate_mermaid_graph(edges: List[Dict[str, Any]], 
                           direction: str = "LR",
                           title: str = "Causal Graph") -> str:
    """Generate Mermaid.js diagram code for the causal graph."""
    if not edges:
        return f"```mermaid\ngraph {direction}\n  %% Empty graph\n```"
    
    lines = [f"```mermaid", f"graph {direction}", f"  %% {title}"]
    
    edge_set = _build_edge_set(edges)
    # Define nodes with styling
    nodes = set()
    for src, _, tgt in edge_set:
        nodes.add(src)
        nodes.add(tgt)
    
    # Style definitions
    lines.append("  classDef perpetrator fill:#ff6b6b,color:#fff;")
    lines.append("  classDef intermediate fill:#ffd93d,color:#000;")
    lines.append("  classDef victim fill:#6bcb77,color:#fff;")
    lines.append("  classDef drug fill:#4d96ff,color:#fff;")
    lines.append("  classDef enzyme fill:#ffd93d,color:#000;")
    lines.append("  classDef transporter fill:#a8e6cf,color:#000;")
    lines.append("  classDef physiological fill:#ffaaa5,color:#000;")
    
    # Identify node types
    perpetrators = set()
    victims = set()
    for src, _, tgt in edge_set:
        # Perpetrators: sources that are never targets
        pass
    
    # Actually, let's use simpler classification
    for node in nodes:
        if any(x in node for x in ["CYP", "OAT", "HERG", "P-GP", "BCRP", "GLOMERULAR", "PROXIMAL", "VITAMIN_K"]):
            if "CYP" in node or "OAT" in node or "HERG" in node or "P-GP" in node or "BCRP" in node:
                lines.append(f"  class {node} enzyme;")
            elif "GLOMERULAR" in node or "PROXIMAL" in node:
                lines.append(f"  class {node} physiological;")
            elif "VITAMIN_K" in node:
                lines.append(f"  class {node} physiological;")
        elif node in ["RIVAROXABAN", "KETOCONAZOLE", "CLOPIDOGREL", "OMEPRAZOLE", "SOTALOL", 
                       "LEVOFLOXACIN", "METHOTREXATE", "NAPROXEN", "SIMVASTATIN", "AMLODIPINE",
                       "TACROLIMUS", "VORICONAZOLE", "WARFARIN", "METRONIDAZOLE", "LITHIUM",
                       "LISINOPRIL", "FUROSEMIDE", "ATORVASTATIN", "AZITHROMYCIN", "CEFTRIAXONE",
                       "S-WARFARIN", "R-WARFARIN"]:
            lines.append(f"  class {node} drug;")
        else:
            lines.append(f"  class {node} intermediate;")
    
    # Edges
    for src, rel, tgt in sorted(edge_set):
        # Sanitize for mermaid
        src_id = src.replace("-", "_").replace(".", "_")
        tgt_id = tgt.replace("-", "_").replace(".", "_")
        lines.append(f"  {src_id}[{src}] -->|{rel}| {tgt_id}[{tgt}]")
    
    lines.append("```")
    return "\n".join(lines)


def generate_diff_visualization(
    expected_edges: List[Dict[str, Any]], 
    predicted_edges: List[Dict[str, Any]],
    task_id: str = ""
) -> str:
    """Generate a visual diff between expected and predicted graphs."""
    expected_set = _build_edge_set(expected_edges)
    predicted_set = _build_edge_set(predicted_edges)
    
    matched = expected_set & predicted_set
    missing = expected_set - predicted_set
    extra = predicted_set - expected_set
    
    lines = [f"=== GRAPH DIFF: {task_id} ==="]
    lines.append(f"Matched edges ({len(matched)}):")
    for src, rel, tgt in sorted(matched):
        lines.append(f"  ✅ {src} ──[{rel}]──> {tgt}")
    
    lines.append(f"\nMissing edges ({len(missing)}):")
    for src, rel, tgt in sorted(missing):
        lines.append(f"  ❌ {src} ──[{rel}]──> {tgt}")
    
    lines.append(f"\nExtra/Hallucinated edges ({len(extra)}):")
    for src, rel, tgt in sorted(extra):
        lines.append(f"  ⚠️  {src} ──[{rel}]──> {tgt}")
    
    # Summary
    total_expected = len(expected_set)
    recall = len(matched) / max(1, total_expected)
    precision = len(matched) / max(1, len(predicted_set))
    f1 = 2 * precision * recall / max(0.001, precision + recall)
    
    lines.append(f"\n--- Metrics ---")
    lines.append(f"  Edge Recall:    {recall:.1%} ({len(matched)}/{total_expected})")
    lines.append(f"  Edge Precision: {precision:.1%} ({len(matched)}/{len(predicted_set)})")
    lines.append(f"  Edge F1:        {f1:.1%}")
    
    return "\n".join(lines)


def generate_side_by_side_comparison(
    expected_edges: List[Dict[str, Any]], 
    predicted_edges: List[Dict[str, Any]],
    task_id: str = ""
) -> str:
    """Generate a side-by-side comparison table."""
    expected_set = _build_edge_set(expected_edges)
    predicted_set = _build_edge_set(predicted_edges)
    
    all_edges = expected_set | predicted_set
    
    lines = [f"=== SIDE-BY-SIDE: {task_id} ==="]
    lines.append(f"{'Status':<10} {'Source':<25} {'Relation':<25} {'Target':<25}")
    lines.append("-" * 85)
    
    for src, rel, tgt in sorted(all_edges):
        in_exp = (src, rel, tgt) in expected_set
        in_pred = (src, rel, tgt) in predicted_set
        
        if in_exp and in_pred:
            status = "✅ MATCH"
        elif in_exp:
            status = "❌ MISSING"
        else:
            status = "⚠️  EXTRA"
        
        lines.append(f"{status:<10} {src:<25} {rel:<25} {tgt:<25}")
    
    return "\n".join(lines)


def generate_task_mermaid(task: Dict[str, Any], 
                          model_json: Dict[str, Any] = None,
                          show_diff: bool = True) -> str:
    """Generate complete Mermaid visualization for a task."""
    gt = task["ground_truth"]
    expected_edges = gt.get("causal_edges", [])
    
    sections = []
    sections.append(f"# {task['id']}: {task['title']}")
    sections.append("")
    
    # Ground Truth
    sections.append("## Ground Truth Causal Graph")
    sections.append(generate_mermaid_graph(expected_edges, "LR", "Ground Truth"))
    sections.append("")
    
    if model_json:
        predicted_edges = model_json.get("causal_graph", [])
        sections.append("## Model Prediction")
        sections.append(generate_mermaid_graph(predicted_edges, "LR", "Model Prediction"))
        sections.append("")
        
        if show_diff:
            sections.append("## Diff Analysis")
            sections.append("```")
            sections.append(generate_diff_visualization(expected_edges, predicted_edges, task["id"]))
            sections.append("```")
    
    return "\n".join(sections)


def print_terminal_comparison(task: Dict[str, Any], model_json: Dict[str, Any]):
    """Print a terminal-friendly comparison."""
    gt = task["ground_truth"]
    expected_edges = gt.get("causal_edges", [])
    predicted_edges = model_json.get("causal_graph", [])
    
    print("\n" + "=" * 70)
    print(f"TASK: {task['id']} - {task['title']}")
    print("=" * 70)
    
    print("\n📋 GROUND TRUTH:")
    print(generate_ascii_graph(expected_edges))
    
    print("\n🤖 MODEL PREDICTION:")
    print(generate_ascii_graph(predicted_edges))
    
    print("\n🔍 DIFF:")
    print(generate_diff_visualization(expected_edges, predicted_edges, task["id"]))


# ============================================================================
# Sankey Diagram Generation
# ============================================================================

def generate_sankey_data(
    expected_edges: List[Dict[str, Any]], 
    predicted_edges: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate Sankey diagram data for causal flow visualization.
    
    Returns dict with 'nodes' and 'links' suitable for Plotly/D3 Sankey.
    """
    expected_set = _build_edge_set(expected_edges)
    predicted_set = _build_edge_set(predicted_edges)
    
    # Combine all edges
    all_edges = expected_set | predicted_set
    
    # Build node list
    nodes = set()
    for src, _, tgt in all_edges:
        nodes.add(src)
        nodes.add(tgt)
    
    node_list = sorted(nodes)
    node_to_idx = {node: i for i, node in enumerate(node_list)}
    
    # Build links
    links = []
    for src, rel, tgt in all_edges:
        in_expected = (src, rel, tgt) in expected_set
        in_predicted = (src, rel, tgt) in predicted_set
        
        if in_expected and in_predicted:
            status = "matched"
            color = "rgba(107, 203, 119, 0.6)"  # Green
        elif in_expected:
            status = "missing"
            color = "rgba(255, 107, 107, 0.6)"  # Red
        else:
            status = "extra"
            color = "rgba(255, 217, 61, 0.6)"  # Yellow
        
        links.append({
            "source": node_to_idx[src],
            "target": node_to_idx[tgt],
            "value": 1,
            "label": rel,
            "status": status,
            "color": color
        })
    
    # Node colors based on type
    node_colors = []
    for node in node_list:
        if any(x in node for x in ["CYP", "OAT", "HERG", "P-GP", "BCRP", "CARBOXYLESTERASE", "UGT1A1", "TPMT", "HLA_B5701", "NKCC2"]):
            node_colors.append("rgba(255, 217, 61, 0.8)")  # Enzyme/transporter - yellow
        elif any(x in node for x in ["PROXIMAL", "GLOMERULAR", "RENAL", "SODIUM"]):
            node_colors.append("rgba(255, 170, 165, 0.8)")  # Physiological - pink
        elif node in ["RIVAROXABAN", "KETOCONAZOLE", "CLOPIDOGREL", "OMEPRAZOLE", "SOTALOL", 
                       "LEVOFLOXACIN", "METHOTREXATE", "NAPROXEN", "SIMVASTATIN", "AMLODIPINE",
                       "TACROLIMUS", "VORICONAZOLE", "WARFARIN", "METRONIDAZOLE", "LITHIUM",
                       "LISINOPRIL", "FUROSEMIDE", "ATORVASTATIN", "AZITHROMYCIN", "CEFTRIAXONE",
                       "S-WARFARIN", "R-WARFARIN", "CODEINE", "AZATHIOPRINE", "ABACAVIR", 
                       "IRINOTECAN", "SIMVASTATIN_LACTONE", "SIMVASTATIN_ACID", "CLOPIDOGREL_ACTIVE_THIOL_METABOLITE"]:
            node_colors.append("rgba(77, 150, 255, 0.8)")  # Drug - blue
        else:
            node_colors.append("rgba(168, 230, 207, 0.8)")  # Other - teal
    
    return {
        "nodes": [
            {"id": i, "label": node, "color": node_colors[i]} 
            for i, node in enumerate(node_list)
        ],
        "links": links
    }


def generate_sankey_html(
    expected_edges: List[Dict[str, Any]], 
    predicted_edges: List[Dict[str, Any]],
    task_id: str = "",
    output_path: str = None
) -> str:
    """
    Generate standalone HTML with Plotly Sankey diagram.
    
    Args:
        expected_edges: Ground truth edges
        predicted_edges: Model predicted edges
        task_id: Task identifier for title
        output_path: Optional path to save HTML file
    
    Returns:
        HTML string
    """
    sankey_data = generate_sankey_data(expected_edges, predicted_edges)
    
    # Convert to format for Plotly
    node_labels = [n["label"] for n in sankey_data["nodes"]]
    node_colors = [n["color"] for n in sankey_data["nodes"]]
    link_sources = [l["source"] for l in sankey_data["links"]]
    link_targets = [l["target"] for l in sankey_data["links"]]
    link_values = [l["value"] for l in sankey_data["links"]]
    link_labels = [l["label"] for l in sankey_data["links"]]
    link_colors = [l["color"] for l in sankey_data["links"]]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sankey Diagram - {task_id}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .legend {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 12px; border-radius: 2px; }}
    </style>
</head>
<body>
    <h2>Causal Flow Sankey Diagram: {task_id}</h2>
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: rgba(107, 203, 119, 0.6)"></div><span>Matched (Expected + Predicted)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: rgba(255, 107, 107, 0.6)"></div><span>Missing (Expected only)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: rgba(255, 217, 61, 0.6)"></div><span>Extra/Hallucinated (Predicted only)</span></div>
    </div>
    <div id="sankey" style="width: 100%; height: 600px;"></div>
    <script>
        var data = [{{
            type: 'sankey',
            orientation: 'h',
            node: {{
                label: {json.dumps(node_labels)},
                color: {json.dumps(node_colors)},
                pad: 20,
                thickness: 20,
                line: {{ color: 'black', width: 0.5 }}
            }},
            link: {{
                source: {json.dumps(link_sources)},
                target: {json.dumps(link_targets)},
                value: {json.dumps(link_values)},
                label: {json.dumps(link_labels)},
                color: {json.dumps(link_colors)}
            }}
        }}];
        
        var layout = {{
            title: 'Causal Graph Flow: {task_id}',
            font: {{ size: 12 }},
            margin: {{ l: 50, r: 50, t: 50, b: 50 }}
        }};
        
        Plotly.newPlot('sankey', data, layout);
    </script>
</body>
</html>"""
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(html)
    
    return html


# ============================================================================
# Spider Chart (Radar Chart) Generation
# ============================================================================

def generate_spider_chart_data(
    model_results: Dict[str, Any],
    metrics: List[str] = None
) -> Dict[str, Any]:
    """
    Generate spider chart data for multi-dimensional model comparison.
    
    Args:
        model_results: Benchmark results dict from run_eval.py
        metrics: List of metrics to include. Defaults to key metrics.
    
    Returns:
        Dict with chart data suitable for Chart.js/Plotly
    """
    if metrics is None:
        metrics = [
            "mean_score",
            "pass_rate_pct",
            "edge_accuracy",
            "atomic_accuracy",
            "cpcs_score"
        ]
    
    # Metric labels for display
    metric_labels = {
        "mean_score": "Mean Score",
        "pass_rate_pct": "Pass Rate (%)",
        "edge_accuracy": "Edge Accuracy (%)",
        "atomic_accuracy": "Atomic Accuracy (%)",
        "cpcs_score": "CPCS Score"
    }
    
    datasets = []
    colors = [
        "rgba(77, 150, 255, 0.6)",   # Blue
        "rgba(107, 203, 119, 0.6)",  # Green
        "rgba(255, 107, 107, 0.6)",  # Red
        "rgba(255, 217, 61, 0.6)",   # Yellow
        "rgba(168, 230, 207, 0.6)",  # Teal
        "rgba(255, 170, 165, 0.6)",  # Pink
    ]
    
    for idx, (model, data) in enumerate(model_results.get("results", {}).items()):
        values = []
        for metric in metrics:
            if metric == "mean_score":
                values.append(data.get("mean_score", 0))
            elif metric == "pass_rate_pct":
                values.append(data.get("pass_rate_pct", 0))
            elif metric == "edge_accuracy":
                # Average edge accuracy across tasks
                task_breakdown = data.get("task_breakdown", [])
                if task_breakdown:
                    avg_edge = sum(t.get("edge_accuracy", 0) for t in task_breakdown) / len(task_breakdown)
                    values.append(round(avg_edge, 1))
                else:
                    values.append(0)
            elif metric == "atomic_accuracy":
                task_breakdown = data.get("task_breakdown", [])
                if task_breakdown:
                    avg_atomic = sum(t.get("atomic_accuracy", 0) for t in task_breakdown) / len(task_breakdown)
                    values.append(round(avg_atomic, 1))
                else:
                    values.append(0)
            elif metric == "cpcs_score":
                task_breakdown = data.get("task_breakdown", [])
                if task_breakdown:
                    avg_cpcs = sum(t.get("cpcs_score", 0) for t in task_breakdown) / len(task_breakdown)
                    values.append(round(avg_cpcs * 100, 1))  # Convert to percentage
                else:
                    values.append(0)
            else:
                values.append(0)
        
        # Close the polygon
        values.append(values[0])
        
        datasets.append({
            "label": model,
            "data": values,
            "backgroundColor": colors[idx % len(colors)],
            "borderColor": colors[idx % len(colors)].replace("0.6", "1.0"),
            "pointBackgroundColor": colors[idx % len(colors)].replace("0.6", "1.0"),
            "pointBorderColor": "#fff",
            "pointHoverBackgroundColor": "#fff",
            "pointHoverBorderColor": colors[idx % len(colors)].replace("0.6", "1.0")
        })
    
    labels = [metric_labels.get(m, m) for m in metrics]
    labels.append(labels[0])  # Close the polygon
    
    return {
        "labels": labels,
        "datasets": datasets
    }


def generate_spider_chart_html(
    model_results: Dict[str, Any],
    metrics: List[str] = None,
    output_path: str = None
) -> str:
    """
    Generate standalone HTML with Chart.js spider chart.
    
    Args:
        model_results: Benchmark results dict from run_eval.py
        metrics: List of metrics to include
        output_path: Optional path to save HTML file
    
    Returns:
        HTML string
    """
    chart_data = generate_spider_chart_data(model_results, metrics)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Model Comparison - Spider Chart</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        canvas {{ max-height: 600px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Multi-Dimensional Model Comparison</h2>
        <p>Radar chart comparing models across key evaluation metrics</p>
        <canvas id="spiderChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('spiderChart').getContext('2d');
        new Chart(ctx, {{
            type: 'radar',
            data: {json.dumps(chart_data)},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                scales: {{
                    r: {{
                        angleLines: {{ display: true }},
                        suggestedMin: 0,
                        suggestedMax: 100,
                        pointLabels: {{ font: {{ size: 14 }} }},
                        ticks: {{ stepSize: 20, backdropColor: 'rgba(255,255,255,0.8)' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ font: {{ size: 14 }} }}
                    }},
                    title: {{
                        display: true,
                        text: 'Model Performance Radar',
                        font: {{ size: 18 }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(html)
    
    return html


def generate_task_spider_chart_data(
    task_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate spider chart data for a single task's detailed metrics.
    
    Args:
        task_result: Single task result from benchmark
    
    Returns:
        Dict with chart data
    """
    metrics = [
        "edge_accuracy",
        "edge_precision_pct",
        "cpcs_score",
        "atomic_accuracy"
    ]
    
    labels = ["Edge Recall", "Edge Precision", "CPCS Score", "Atomic Accuracy"]
    
    values = [
        task_result.get("edge_accuracy", 0),
        task_result.get("edge_precision_pct", 0),
        task_result.get("cpcs_score", 0) * 100,  # Convert to percentage
        task_result.get("atomic_accuracy", 0)
    ]
    
    return {
        "labels": labels,
        "datasets": [{
            "label": f"Task: {task_result.get('task_id', 'Unknown')}",
            "data": values + [values[0]],  # Close polygon
            "backgroundColor": "rgba(77, 150, 255, 0.3)",
            "borderColor": "rgba(77, 150, 255, 1.0)",
            "pointBackgroundColor": "rgba(77, 150, 255, 1.0)",
            "pointBorderColor": "#fff",
            "pointHoverBackgroundColor": "#fff",
            "pointHoverBorderColor": "rgba(77, 150, 255, 1.0)"
        }]
    }