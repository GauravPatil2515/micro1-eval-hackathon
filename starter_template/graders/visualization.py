"""
Graph Visualization for MechanismTrace-DDI
Generates terminal ASCII graphs, Mermaid diagrams, and diff visualizations
for model vs ground truth causal graph comparison.
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