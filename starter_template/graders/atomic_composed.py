"""
Atomic vs Composed Gap Analysis for MechanismTrace-DDI
Measures the performance degradation when models transition from isolated
pairwise queries to complex multi-modifier clinical scenarios.
"""
from typing import Dict, Any, List
from graders.normalizer import normalize_entity, normalize_relation


# Atomic (single-hop) sub-questions derived from each task
# Balanced: ~50% true relations, ~50% false relations
# Each probe includes: question, expected_answer (YES/NO), expected_edge (for validation)
ATOMIC_PROBES = {
    "TASK-01": [
        # True relations (positive)
        {"question": "Does ketoconazole inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("KETOCONAZOLE", "CYP3A4", "INHIBITS")},
        {"question": "Does ketoconazole inhibit P-gp?", "expected_answer": "YES", "expected_edge": ("KETOCONAZOLE", "P-GP", "INHIBITS")},
        {"question": "Does CYP3A4 inhibition increase rivaroxaban exposure?", "expected_answer": "YES", "expected_edge": ("CYP3A4", "RIVAROXABAN", "INCREASES_EXPOSURE")},
        {"question": "Does P-gp inhibition increase rivaroxaban exposure?", "expected_answer": "YES", "expected_edge": ("P-GP", "RIVAROXABAN", "INCREASES_EXPOSURE")},
        # False relations (negative)
        {"question": "Does ketoconazole induce CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does ketoconazole inhibit CYP2C9?", "expected_answer": "NO", "expected_edge": None},
        # Direction reversals
        {"question": "Does CYP3A4 inhibit ketoconazole?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does rivaroxaban inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        # Clinically irrelevant facts
        {"question": "Does ketoconazole inhibit CYP2D6?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-02": [
        {"question": "Does omeprazole inhibit CYP2C19?", "expected_answer": "YES", "expected_edge": ("OMEPRAZOLE", "CYP2C19", "INHIBITS")},
        {"question": "Does CYP2C19 inhibition block clopidogrel bioactivation?", "expected_answer": "YES", "expected_edge": ("CYP2C19", "CLOPIDOGREL", "BLOCKS_BIOACTIVATION")},
        {"question": "Does omeprazole induce CYP2C19?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does clopidogrel inhibit CYP2C19?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does omeprazole inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("OMEPRAZOLE", "CYP3A4", "INHIBITS")},
    ],
    "TASK-03": [
        {"question": "Does sotalol inhibit hERG?", "expected_answer": "YES", "expected_edge": ("SOTALOL", "HERG", "INHIBITS")},
        {"question": "Does levofloxacin produce additive hERG block?", "expected_answer": "YES", "expected_edge": ("LEVOFLOXACIN", "HERG", "PRODUCES_ADDITIVE_BLOCK")},
        {"question": "Does sotalol activate hERG?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does doxycycline produce additive hERG block?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does hypokalemia protect against hERG blockade?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-04": [
        {"question": "Does naproxen competitively block OAT1?", "expected_answer": "YES", "expected_edge": ("NAPROXEN", "OAT1", "COMPETITIVELY_BLOCKS")},
        {"question": "Does naproxen competitively block OAT3?", "expected_answer": "YES", "expected_edge": ("NAPROXEN", "OAT3", "COMPETITIVELY_BLOCKS")},
        {"question": "Does OAT1 inhibition increase methotrexate exposure?", "expected_answer": "YES", "expected_edge": ("OAT1", "METHOTREXATE", "INCREASES_EXPOSURE")},
        {"question": "Does OAT3 inhibition increase methotrexate exposure?", "expected_answer": "YES", "expected_edge": ("OAT3", "METHOTREXATE", "INCREASES_EXPOSURE")},
        {"question": "Does naproxen induce OAT1?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does methotrexate inhibit OAT1?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does naproxen inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-05": [
        {"question": "Does amlodipine inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("AMLODIPINE", "CYP3A4", "INHIBITS")},
        {"question": "Does CYP3A4 inhibition increase simvastatin exposure?", "expected_answer": "YES", "expected_edge": ("CYP3A4", "SIMVASTATIN", "INCREASES_EXPOSURE")},
        {"question": "Does amlodipine induce CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does simvastatin inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does amlodipine inhibit CYP2C9?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-06": [
        {"question": "Does voriconazole inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("VORICONAZOLE", "CYP3A4", "INHIBITS")},
        {"question": "Does voriconazole inhibit CYP3A5?", "expected_answer": "YES", "expected_edge": ("VORICONAZOLE", "CYP3A5", "INHIBITS")},
        {"question": "Does CYP3A4 inhibition increase tacrolimus exposure?", "expected_answer": "YES", "expected_edge": ("CYP3A4", "TACROLIMUS", "INCREASES_EXPOSURE")},
        {"question": "Does voriconazole induce CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does tacrolimus inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does voriconazole inhibit CYP2C9?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-07": [
        {"question": "Does metronidazole stereoselectively inhibit CYP2C9?", "expected_answer": "YES", "expected_edge": ("METRONIDAZOLE", "CYP2C9", "STEREOSELECTIVELY_INHIBITS")},
        {"question": "Does CYP2C9 inhibition increase S-warfarin exposure?", "expected_answer": "YES", "expected_edge": ("CYP2C9", "S-WARFARIN", "INCREASES_EXPOSURE")},
        {"question": "Does metronidazole inhibit R-warfarin clearance via CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does metronidazole induce CYP2C9?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does warfarin inhibit CYP2C9?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does metronidazole inhibit CYP1A2?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-08": [
        {"question": "Does furosemide induce proximal tubule reabsorption?", "expected_answer": "YES", "expected_edge": ("FUROSEMIDE", "PROXIMAL_TUBULE_REABSORPTION", "INDUCES")},
        {"question": "Does lisinopril decrease glomerular filtration?", "expected_answer": "YES", "expected_edge": ("LISINOPRIL", "GLOMERULAR_FILTRATION", "DECREASES_EXPOSURE")},
        {"question": "Does proximal tubule reabsorption increase lithium exposure?", "expected_answer": "YES", "expected_edge": ("PROXIMAL_TUBULE_REABSORPTION", "LITHIUM", "INCREASES_EXPOSURE")},
        {"question": "Does furosemide decrease proximal tubule reabsorption?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does lisinopril increase glomerular filtration?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does lithium inhibit proximal tubule reabsorption?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does furosemide inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-09": [
        {"question": "Does azithromycin inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": ("AZITHROMYCIN", "CYP3A4", "NO_INHIBITION")},
        {"question": "Does clarithromycin inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("CLARITHROMYCIN", "CYP3A4", "INHIBITS")},
        {"question": "Does azithromycin induce CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does azithromycin form metabolic intermediate complex with CYP3A4 heme iron?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-10": [
        {"question": "Does ceftriaxone inhibit CYP2C9?", "expected_answer": "NO", "expected_edge": ("CEFTRIAXONE", "CYP2C9", "NO_INHIBITION")},
        {"question": "Does ceftriaxone decrease vitamin K flora?", "expected_answer": "YES", "expected_edge": ("CEFTRIAXONE", "VITAMIN_K_FLORA", "MINIMAL_DECREASE")},
        {"question": "Does TMP-SMX inhibit CYP2C9?", "expected_answer": "YES", "expected_edge": None},
        {"question": "Does ceftriaxone displace warfarin from albumin?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does ceftriaxone induce CYP2C9?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-11": [
        {"question": "Does codeine require CYP2D6 for bioactivation to morphine?", "expected_answer": "YES", "expected_edge": ("CODEINE", "CYP2D6", "REQUIRES_FOR_BIOACTIVATION")},
        {"question": "Does CYP2D6 activity increase morphine exposure?", "expected_answer": "YES", "expected_edge": ("CYP2D6", "MORPHINE", "INCREASES_EXPOSURE")},
        {"question": "Does morphine increase mu-opioid receptor activation?", "expected_answer": "YES", "expected_edge": ("MORPHINE", "MU_OPIOID_RECEPTOR", "INCREASES_EXPOSURE")},
        {"question": "Does CYP2D6 inhibit codeine bioactivation?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does morphine inhibit CYP2D6?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does codeine activate mu-opioid receptor directly?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-12": [
        {"question": "Does azathioprine competitively block TPMT?", "expected_answer": "YES", "expected_edge": ("AZATHIOPRINE", "TPMT", "COMPETITIVELY_BLOCKS")},
        {"question": "Does TPMT deficiency increase 6-thioguanine nucleotides?", "expected_answer": "YES", "expected_edge": ("TPMT", "6_THIOGUANINE_NUCLEOTIDES", "INCREASES_EXPOSURE")},
        {"question": "Do 6-thioguanine nucleotides increase bone marrow toxicity?", "expected_answer": "YES", "expected_edge": ("6_THIOGUANINE_NUCLEOTIDES", "BONE_MARROW", "INCREASES_EXPOSURE")},
        {"question": "Does azathioprine induce TPMT?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does 6-TGN inhibit TPMT?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does azathioprine inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-13": [
        {"question": "Does abacavir interact with HLA-B*57:01?", "expected_answer": "YES", "expected_edge": ("ABACAVIR", "HLA_B5701", "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE")},
        {"question": "Does HLA-B*57:01 increase CD8 T-cell activation?", "expected_answer": "YES", "expected_edge": ("HLA_B5701", "CD8_T_CELL_ACTIVATION", "INCREASES_EXPOSURE")},
        {"question": "Does CD8 T-cell activation increase hypersensitivity?", "expected_answer": "YES", "expected_edge": ("CD8_T_CELL_ACTIVATION", "HYPERSENSITIVITY_SYNDROME", "INCREASES_EXPOSURE")},
        {"question": "Does abacavir bind HLA-B*57:01 directly?", "expected_answer": "YES", "expected_edge": None},
        {"question": "Does abacavir inhibit CYP3A4?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does HLA-B*57:01 inhibit abacavir metabolism?", "expected_answer": "NO", "expected_edge": None},
    ],
    "TASK-14": [
        {"question": "Does irinotecan convert to SN-38 via carboxylesterase?", "expected_answer": "YES", "expected_edge": ("IRINOTECAN", "CARBOXYLESTERASE", "INCREASES_EXPOSURE")},
        {"question": "Does carboxylesterase increase SN-38?", "expected_answer": "YES", "expected_edge": ("CARBOXYLESTERASE", "SN38", "INCREASES_EXPOSURE")},
        {"question": "Does SN-38 require UGT1A1 for glucuronidation?", "expected_answer": "YES", "expected_edge": ("SN38", "UGT1A1", "DECREASES_EXPOSURE")},
        {"question": "Does UGT1A1 increase SN-38 glucuronide?", "expected_answer": "YES", "expected_edge": ("UGT1A1", "SN38_GLUCURONIDE", "INCREASES_EXPOSURE")},
        {"question": "Does irinotecan directly inhibit UGT1A1?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does SN-38 inhibit carboxylesterase?", "expected_answer": "NO", "expected_edge": None},
        {"question": "Does irinotecan inhibit CYP3A4?", "expected_answer": "YES", "expected_edge": ("IRINOTECAN", "CYP3A4", "METABOLIZED_BY")},
    ],
}


def evaluate_atomic_accuracy(model_json: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """
    Evaluate how many atomic edges the model correctly identifies
    in its causal_graph, regardless of full composed reasoning.
    """
    predicted_edges = model_json.get("causal_graph", [])
    probes = ATOMIC_PROBES.get(task_id, [])
    
    if not probes:
        return {"atomic_accuracy": 1.0, "atomic_matched": 0, "atomic_total": 0}
    
    matched = 0
    for probe in probes:
        expected_edge = probe.get("expected_edge")
        # For probes with expected_edge, check if model predicted it
        if expected_edge and isinstance(expected_edge, (list, tuple)) and len(expected_edge) == 3:
            exp_src, exp_tgt, exp_rel = expected_edge
            for pred in predicted_edges:
                pred_src = normalize_entity(pred.get("source", ""))
                pred_tgt = normalize_entity(pred.get("target", ""))
                pred_rel = normalize_relation(pred.get("relation", ""))
                if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
                    matched += 1
                    break
        # For probes without expected_edge (false/negative probes), 
        # they're validated by absence in atomic probe evaluation mode
        # Not evaluated from causal_graph alone
    
    return {
        "atomic_accuracy": round(matched / len(probes), 3) if probes else 1.0,
        "atomic_matched": matched,
        "atomic_total": len(probes),
    }


def compute_atomic_vs_composed_gap(
    task_results: List[Dict[str, Any]], 
    task_id: str
) -> Dict[str, Any]:
    """
    Compute the gap between atomic (single-hop) accuracy and 
    composed (full multi-hop) performance.
    """
    # Find the task result
    task_result = None
    for tr in task_results:
        if tr["task_id"] == task_id:
            task_result = tr
            break
    
    if not task_result:
        return {"gap": 0.0, "atomic_accuracy": 0.0, "composed_score": 0.0}
    
    # Atomic accuracy is already in the eval_grade
    # We'll compute it from the raw model output
    return {
        "gap": 0.0,  # Will be computed externally
        "atomic_accuracy": task_result.get("atomic_accuracy", 0.0),
        "composed_score": task_result.get("total_score", 0.0) / 100.0,
    }


def analyze_atomic_composed_gap(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze atomic vs composed gap across all models and tasks.
    Returns summary statistics for the benchmark report.
    Gap is measured in percentage points (0-100 scale).
    """
    model_gaps = {}
    
    for model, model_data in all_results.get("results", {}).items():
        gaps = []
        for task in model_data.get("task_breakdown", []):
            atomic_acc_pct = task.get("atomic_accuracy", 0.0)  # 0-100
            composed_score_pct = task.get("avg_score", 0.0)  # 0-100
            gap = atomic_acc_pct - composed_score_pct
            gaps.append(gap)
        
        if gaps:
            model_gaps[model] = {
                "mean_gap_pct": round(sum(gaps) / len(gaps), 1),
                "max_gap_pct": round(max(gaps), 1),
                "task_gaps_pct": {t["task_id"]: round(t.get("atomic_accuracy", 0.0) - t.get("avg_score", 0.0), 1) 
                                  for t in model_data.get("task_breakdown", [])}
            }
    
    return {
        "model_gaps": model_gaps,
        "overall_mean_gap_pct": round(
            sum(g["mean_gap_pct"] for g in model_gaps.values()) / len(model_gaps), 1
        ) if model_gaps else 0.0,
    }