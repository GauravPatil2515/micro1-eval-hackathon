#!/usr/bin/env python3
"""
Causal DAG Diff Visualizer for MechanismTrace-DDI
Generates side-by-side Mermaid.js flowcharts comparing gold vs predicted causal graphs.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from graders.normalizer import normalize_entity, normalize_relation

# Node type classification for color coding
NODE_TYPE_COLORS = {
    "drug": "#1f77b4",           # Blue
    "enzyme_transporter": "#ff7f0e",  # Orange
    "exposure": "#9467bd",       # Purple
    "risk": "#d62728",           # Red
    "modifier": "#2ca02c",       # Green
    "unknown": "#7f7f7f",        # Gray
}

# Keywords for node type detection
DRUG_KEYWORDS = {"RIVAROXABAN", "KETOCONAZOLE", "CLOPIDOGREL", "OMEPRAZOLE", "SOTALOL", 
                 "LEVOFLOXACIN", "METHOTREXATE", "NAPROXEN", "SIMVASTATIN", "AMLODIPINE",
                 "TACROLIMUS", "VORICONAZOLE", "WARFARIN", "METRONIDAZOLE", "LITHIUM",
                 "LISINOPRIL", "FUROSEMIDE", "ATORVASTATIN", "AZITHROMYCIN", "CEFTRIAXONE",
                 "CODEINE", "AZATHIOPRINE", "ABACAVIR", "IRINOTECAN", "FLUCONAZOLE",
                 "PANTOPRAZOLE", "DOXYCYCLINE", "TMP_SMX", "CLARITHROMYCIN", "ERYTHROMYCIN"}

ENZYME_TRANSPORTER_KEYWORDS = {"CYP3A4", "CYP2C19", "CYP2C9", "CYP2D6", "CYP3A5", "P-GP", "P-GLYCOPROTEIN",
                               "OAT1", "OAT3", "HERG", "NKCC2", "ACE", "UGT1A1", "TPMT", "HLA_B5701",
                               "CARBOXYLESTERASE", "CES", "VKORC1", "BCRP", "UGT2B7", "DHFR",
                               "PROXIMAL_TUBULE_REABSORPTION", "GLOMERULAR_FILTRATION", "RENAL_PERFUSION",
                               "SODIUM_REABSORPTION_TAL", "CALCINEURIN", "COX1", "COX2", "MU_OPIOID_RECEPTOR",
                               "BETA_RECEPTOR", "CALCIUM_CHANNEL", "SODIUM_CHANNEL", "DISTAL_CONVOLUTED_TUBULE",
                               "SERUM_POTASSIUM", "TOP1", "REVERSE_TRANSCRIPTASE", "ALCOHOL_DEHYDROGENASE",
                               "BACTERIAL_RIBOSOME", "PBP", "GUT_MICROBIOME", "VITAMIN_K_FLORA",
                               "XANTHINE_OXIDASE", "DNA_SYNTHESIS", "NORCODEINE", "6_MERCAPTOPURINE",
                               "6_THIOGUANINE_NUCLEOTIDES", "SN38", "SN38_GLUCURONIDE", "MORPHINE",
                               "MU_OPIOID_RECEPTOR", "P2Y12", "CD8_T_CELL_ACTIVATION", "HYPERSENSITIVITY_SYNDROME",
                               "BONE_MARROW", "MYELOID_LINEAGE", "CLOPIDOGREL_ACTIVE_THIOL_METABOLITE",
                               "SIMVASTATIN_LACTONE", "SIMVASTATIN_ACID", "R-WARFARIN", "S-WARFARIN",
                               "6_TGN"}

EXPOSURE_KEYWORDS = {"INCREASES_EXPOSURE", "DECREASES_EXPOSURE", "ELEVATES_AUC", "ELEVATES_INR",
                     "NO_CHANGE_IN_EXPOSURE", "INCREASES", "DECREASES", "ELEVATES"}

RISK_KEYWORDS = {"TORSADES", "BLEEDING", "TOXICITY", "MYELOSUPPRESSION", "NEPHROTOXICITY",
                 "NEUROTOXICITY", "HYPERSENSITIVITY", "INR", "TDM", "MONITORING"}

MODIFIER_KEYWORDS = {"CRCL", "CREATININE", "K+", "POTASSIUM", "HYPOKALEMIA", "HYPERKALEMIA",
                     "GENOTYPE", "ULTRARAPID", "POOR", "INTERMEDIATE", "EXPRESSOR", "NON_EXPRESSOR",
                     "CYP2D6", "CYP2C19", "CYP3A5", "TPMT", "UGT1A1", "HLA_B5701", "HLA-B*57:01"}

def classify_node_type(node: str) -> str:
    """Classify node type for color coding."""
    node_upper = node.upper()
    
    if any(kw in node_upper for kw in DRUG_KEYWORDS):
        return "drug"
    if any(kw in node_upper for kw in ENZYME_TRANSPORTER_KEYWORDS):
        return "enzyme_transporter"
    if any(kw in node_upper for kw in EXPOSURE_KEYWORDS):
        return "exposure"
    if any(kw in node_upper for kw in RISK_KEYWORDS):
        return "risk"
    if any(kw in node_upper for kw in MODIFIER_KEYWORDS):
        return "modifier"
    return "unknown"

def get_node_color(node: str) -> str:
    """Get color for node based on type."""
    return NODE_TYPE_COLORS.get(classify_node_type(node), NODE_TYPE_COLORS["unknown"])

def build_edge_set(edges: List[Dict[str, Any]]) -> set:
    """Build normalized edge set from edge list."""
    edge_set = set()
    for e in edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        rel = normalize_relation(e.get("relation", ""))
        if src and tgt:
            edge_set.add((src, rel, tgt))
    return edge_set

def compare_edges(gold_edges: List[Dict], pred_edges: List[Dict]) -> Tuple[set, set, set]:
    """Compare gold and predicted edges. Returns (matched, missing, spurious)."""
    gold_set = build_edge_set(gold_edges)
    pred_set = build_edge_set(pred_edges)
    
    matched = gold_set & pred_set
    missing = gold_set - pred_set
    spurious = pred_set - gold_set
    
    return matched, missing, spurious

def generate_mermaid_graph(edges: List[Dict], title: str, 
                           matched: set = None, missing: set = None, spurious: set = None) -> str:
    """Generate Mermaid.js flowchart for a causal graph."""
    lines = []
    lines.append(f"```mermaid")
    lines.append(f"flowchart LR")
    lines.append(f'    title["{title}"]')
    lines.append(f"    style title fill:#f0f0f0,stroke:#333,stroke-width:2px")
    
    # Collect all nodes
    all_nodes = set()
    for e in edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        if src: all_nodes.add(src)
        if tgt: all_nodes.add(tgt)
    
    # Add subgraphs for node types (optional styling)
    for node in sorted(all_nodes):
        node_type = classify_node_type(node)
        color = get_node_color(node)
        # Escape special characters for Mermaid
        node_id = node.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "").replace("/", "_").replace("*", "_").replace("+", "_")
        node_label = node.replace('"', '\\"')
        lines.append(f'    {node_id}["{node_label}"]')
        lines.append(f'    style {node_id} fill:{color},stroke:#333,stroke-width:2px,color:#fff')
    
    # Add edges
    for e in edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        rel = normalize_relation(e.get("relation", ""))
        
        if not src or not tgt:
            continue
            
        src_id = src.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "").replace("/", "_").replace("*", "_").replace("+", "_")
        tgt_id = tgt.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "").replace("/", "_").replace("*", "_").replace("+", "_")
        
        # Determine edge style
        edge_key = (src, rel, tgt)
        if matched and edge_key in matched:
            # Solid green for matched
            lines.append(f'    {src_id} -->|{rel}| {tgt_id}')
            lines.append(f'    style {src_id} --> {tgt_id} stroke:#2ca02c,stroke-width:3px')
        elif missing and edge_key in missing:
            # Dashed red for missing (should not appear in pred graph)
            pass
        elif spurious and edge_key in spurious:
            # Dashed red for spurious/hallucinated
            lines.append(f'    {src_id} -.->|{rel}| {tgt_id}')
            lines.append(f'    style {src_id} -.-> {tgt_id} stroke:#d62728,stroke-width:2px,stroke-dasharray: 5 5')
        else:
            # Normal edge
            lines.append(f'    {src_id} -->|{rel}| {tgt_id}')
    
    lines.append("```")
    return "\n".join(lines)

def generate_comparison_mermaid(gold_edges: List[Dict], pred_edges: List[Dict], 
                                 task_id: str, task_title: str) -> str:
    """Generate side-by-side comparison with gold and predicted graphs."""
    matched, missing, spurious = compare_edges(gold_edges, pred_edges)
    
    lines = []
    lines.append(f"## {task_id}: {task_title}")
    lines.append("")
    
    # Gold standard
    lines.append("### Gold Standard (Ground Truth)")
    lines.append(generate_mermaid_graph(gold_edges, "Ground Truth Causal DAG", 
                                         matched=matched, missing=missing, spurious=set()))
    lines.append("")
    
    # Predicted
    lines.append("### Model Prediction")
    lines.append(generate_mermaid_graph(pred_edges, "Predicted Causal DAG",
                                         matched=matched, missing=missing, spurious=spurious))
    lines.append("")
    
    # Summary
    lines.append("### Edge Comparison Summary")
    lines.append(f"- **Matched**: {len(matched)} edges")
    lines.append(f"- **Missing (False Negatives)**: {len(missing)} edges")
    for src, rel, tgt in sorted(missing):
        lines.append(f"  - {src} --{rel}--> {tgt}")
    lines.append(f"- **Spurious/Hallucinated (False Positives)**: {len(spurious)} edges")
    for src, rel, tgt in sorted(spurious):
        lines.append(f"  - {src} --{rel}--> {tgt}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)

def load_gold_edges(task_id: str) -> List[Dict]:
    """Load ground truth edges from tasks.json."""
    tasks_path = BASE_DIR / "dataset" / "tasks.json"
    with open(tasks_path) as f:
        tasks = json.load(f)
    
    for task in tasks:
        if task["id"] == task_id:
            return task.get("ground_truth", {}).get("causal_edges", [])
    return []

def load_predicted_edges(task_id: str, model: str = "nousresearch/hermes-4-405b") -> List[Dict]:
    """Load predicted edges from raw model output."""
    raw_runs_dir = BASE_DIR / "results" / "raw_runs"
    # Model name in filename uses underscore instead of slash
    model_prefix = model.replace("/", "_")
    
    # Find the raw run file for this task
    for filepath in sorted(raw_runs_dir.glob(f"{model_prefix}_{task_id}_trial*.json")):
        with open(filepath) as f:
            data = json.load(f)
        raw_output = data.get("raw_output", "")
        try:
            # Parse the JSON output - handle markdown code blocks
            text = raw_output.strip()
            if text.startswith("```json"):
                text = text[7:]  # Remove ```json
            elif text.startswith("```"):
                text = text[3:]  # Remove ```
            if text.endswith("```"):
                text = text[:-3]  # Remove trailing ```
            text = text.strip()
            parsed = json.loads(text)
            return parsed.get("causal_graph", [])
        except Exception as e:
            print(f"  Parse error for {filepath.name}: {e}")
            pass
    
    return []

def main():
    print("=" * 70)
    print("🧬 MECHANISMTRACE-DDI: CAUSAL DAG DIFF VISUALIZER")
    print("=" * 70)
    
    # Configuration
    model = "nousresearch/hermes-4-405b"
    task_ids = ["TASK-01", "TASK-02", "TASK-03"]
    
    # Load tasks for titles
    tasks_path = BASE_DIR / "dataset" / "tasks.json"
    with open(tasks_path) as f:
        all_tasks = json.load(f)
    task_map = {t["id"]: t.get("title", "") for t in all_tasks}
    
    output_lines = []
    output_lines.append("# MechanismTrace-DDI: Causal DAG Diff Visualizations")
    output_lines.append("")
    output_lines.append(f"Model: `{model}`")
    output_lines.append(f"Generated: 2026-11-07")
    output_lines.append("")
    output_lines.append("## Color Legend")
    output_lines.append("- 🔵 **Blue**: Drug / Compound")
    output_lines.append("- 🟠 **Orange**: Enzyme / Transporter / Target")
    output_lines.append("- 🟣 **Purple**: Exposure / PK Change")
    output_lines.append("- 🔴 **Red**: Clinical Risk / Outcome")
    output_lines.append("- 🟢 **Green**: Patient Modifier / Physiological State")
    output_lines.append("")
    output_lines.append("## Edge Styles")
    output_lines.append("- **Solid**: Normal predicted edge")
    output_lines.append("- **Dashed Red**: Spurious / Hallucinated edge (False Positive)")
    output_lines.append("- *Note: Missing edges (False Negatives) only shown in Gold Standard*")
    output_lines.append("")
    output_lines.append("---")
    output_lines.append("")
    
    for task_id in task_ids:
        task_title = task_map.get(task_id, "")
        print(f"Processing {task_id}...")
        
        gold_edges = load_gold_edges(task_id)
        pred_edges = load_predicted_edges(task_id, model)
        
        if not gold_edges:
            print(f"  WARNING: No gold edges found for {task_id}")
            continue
        if not pred_edges:
            print(f"  WARNING: No predicted edges found for {task_id}")
            pred_edges = []
        
        comparison = generate_comparison_mermaid(gold_edges, pred_edges, task_id, task_title)
        output_lines.append(comparison)
    
    # Write output
    output_path = BASE_DIR / "DAG_VISUALIZATIONS.md"
    with open(output_path, "w") as f:
        f.write("\n".join(output_lines))
    
    print(f"\n✅ Visualizations written to: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()