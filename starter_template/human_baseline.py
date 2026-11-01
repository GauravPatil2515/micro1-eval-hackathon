"""
Human Expert Baseline Evaluation Harness for MechanismTrace-DDI
Module A.1: Framework for evaluating clinical pharmacology experts on core polypharmacy tasks.

NOTE: This module provides the framework for human evaluation. 
Actual clinician responses must be collected independently and are NOT included in this repository.
The CLINICAL_EXPERT_REFERENCE_ANSWERS below are TEMPLATES showing the expected response format.
They do NOT represent real clinician data and should NOT be used as baseline evidence.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graders.causal_grader import DeterministicCausalGrader


# High-stakes core clinical evaluation tasks for human benchmark
CORE_TASK_IDS = [
    "TASK-01", "TASK-03", "TASK-04", "TASK-06", 
    "TASK-07", "TASK-08", "TASK-11", "TASK-13"
]

# TEMPLATE responses showing the expected JSON format for clinician responses.
# THESE ARE NOT REAL CLINICIAN DATA - they are format templates only.
# Real human baseline requires independent recruitment of 2-3 clinical pharmacologists/PharmDs
# who independently evaluate each case and provide responses in this format.
# Results from actual clinicians must be collected separately and are NOT included in this repo.
CLINICAL_EXPERT_REFERENCE_TEMPLATES = {
    "TASK-01": {
        "causal_graph": [
            {"source": "Ketoconazole", "target": "CYP3A4", "relation": "INHIBITS"},
            {"source": "Ketoconazole", "target": "P-gp", "relation": "INHIBITS"},
            {"source": "CYP3A4", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE"},
            {"source": "P-gp", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "CrCl 41.2 mL/min",
            "clinical_consequence": "Moderate renal impairment eliminates renal compensation during dual CYP3A4/P-gp blockade."
        },
        "regulatory_action": {
            "verdict": "CONTRAINDICATED",
            "mandated_action": "Avoid concomitant administration per FDA Section 7.1. Do not attempt dose reduction."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Fluconazole",
            "resolves_primary_interaction": True,
            "residual_risk_remains": True,
            "residual_risk_explanation": "Fluconazole weakly inhibits P-gp, but in CrCl <50 mL/min, rivaroxaban exposure remains elevated ~1.4x requiring bleeding vigilance."
        }
    },
    "TASK-03": {
        "causal_graph": [
            {"source": "Sotalol", "target": "hERG", "relation": "INHIBITS"},
            {"source": "Levofloxacin", "target": "hERG", "relation": "PRODUCES_ADDITIVE_BLOCK"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "Serum K+ 3.1 mEq/L, Mg2+ 1.4 mg/dL",
            "clinical_consequence": "Severe hypokalemia dramatically increases sotalol affinity for hERG and delays repolarization."
        },
        "regulatory_action": {
            "verdict": "CONTRAINDICATED",
            "mandated_action": "Contraindicated. Replete potassium to >4.0 mEq/L and magnesium to >2.0 mg/dL immediately; cardiac telemetry."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Doxycycline",
            "resolves_primary_interaction": True,
            "residual_risk_remains": True,
            "residual_risk_explanation": "Substituting Doxycycline clears fluoroquinolone hERG block, but uncorrected hypokalemia with sotalol maintains high lethal Torsades de Pointes risk."
        }
    },
    "TASK-04": {
        "causal_graph": [
            {"source": "Naproxen", "target": "OAT1", "relation": "COMPETITIVELY_BLOCKS"},
            {"source": "Naproxen", "target": "OAT3", "relation": "COMPETITIVELY_BLOCKS"},
            {"source": "OAT1", "target": "Methotrexate", "relation": "INCREASES_EXPOSURE"},
            {"source": "OAT3", "target": "Methotrexate", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "CrCl 48 mL/min with dehydration",
            "clinical_consequence": "Substantial decrease in tubular secretion and prostaglandin renal blood flow causes acute methotrexate toxicity."
        },
        "regulatory_action": {
            "verdict": "CONTRAINDICATED",
            "mandated_action": "Contraindicated. Discontinue naproxen immediately; hydrate patient and use non-NSAID analgesics like acetaminophen."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Acetaminophen",
            "resolves_primary_interaction": True,
            "residual_risk_remains": False,
            "residual_risk_explanation": "Acetaminophen does not inhibit OAT1/OAT3 or renal prostaglandins, completely clearing the clearance blockade."
        }
    },
    "TASK-06": {
        "causal_graph": [
            {"source": "Voriconazole", "target": "CYP3A4", "relation": "INHIBITS"},
            {"source": "Voriconazole", "target": "CYP3A5", "relation": "INHIBITS"},
            {"source": "CYP3A4", "target": "Tacrolimus", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "CYP3A5*3/*3 (Non-expressor)",
            "clinical_consequence": "Patient lacks functional CYP3A5; hepatic clearance relies entirely on CYP3A4 which is potently inhibited by voriconazole."
        },
        "regulatory_action": {
            "verdict": "DOSE_ADJUSTMENT_REQUIRED",
            "mandated_action": "Empirically reduce tacrolimus dose by 66% (to 1/3rd of baseline) and perform frequent whole-blood TDM."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Empiric 1/3rd dose reduction",
            "resolves_primary_interaction": True,
            "residual_risk_remains": True,
            "residual_risk_explanation": "Dose reduction prevents acute fatal nephrotoxicity, but narrow therapeutic index requires continuous TDM."
        }
    },
    "TASK-07": {
        "causal_graph": [
            {"source": "Metronidazole", "target": "CYP2C9", "relation": "STEREOSELECTIVELY_INHIBITS"},
            {"source": "CYP2C9", "target": "S-Warfarin", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "Baseline target INR 2.0-3.0",
            "clinical_consequence": "Selective clearance blockade of the highly active S-enantiomer causes acute supratherapeutic anticoagulation and hemorrhage."
        },
        "regulatory_action": {
            "verdict": "DOSE_ADJUSTMENT_REQUIRED",
            "mandated_action": "Reduce warfarin dose empirically by 30-50% and recheck INR in 48-72 hours."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Non-interacting antimicrobial",
            "resolves_primary_interaction": True,
            "residual_risk_remains": True,
            "residual_risk_explanation": "Changing antimicrobial resolves enzyme inhibition, but active infection itself alters warfarin sensitivity requiring close monitoring."
        }
    },
    "TASK-08": {
        "causal_graph": [
            {"source": "Furosemide", "target": "PROXIMAL_TUBULE_REABSORPTION", "relation": "INDUCES"},
            {"source": "Lisinopril", "target": "GLOMERULAR_FILTRATION", "relation": "DECREASES_EXPOSURE"},
            {"source": "PROXIMAL_TUBULE_REABSORPTION", "target": "Lithium", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "Serum Na+ 132 mEq/L, CHF",
            "clinical_consequence": "Volume depletion and natriuresis force compensatory proximal tubule lithium hyper-reabsorption."
        },
        "regulatory_action": {
            "verdict": "DOSE_ADJUSTMENT_REQUIRED",
            "mandated_action": "Reduce lithium dose by 50% or avoid triple combination; mandatory lithium serum concentration monitoring."
        },
        "counterfactual_analysis": {
            "alternative_drug": "50% lithium reduction + TDM",
            "resolves_primary_interaction": True,
            "residual_risk_remains": True,
            "residual_risk_explanation": "Dose reduction limits accumulation, but ongoing diuretic therapy creates sustained instability requiring serial levels."
        }
    },
    "TASK-11": {
        "causal_graph": [
            {"source": "Codeine", "target": "CYP2D6", "relation": "REQUIRES_FOR_BIOACTIVATION"},
            {"source": "CYP2D6", "target": "Morphine", "relation": "INCREASES_EXPOSURE"},
            {"source": "Morphine", "target": "MU_OPIOID_RECEPTOR", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "CYP2D6 Ultrarapid Metabolizer (*1xN or *2xN)",
            "clinical_consequence": "Gene duplication causes ultra-rapid bioactivation of codeine into massive systemic morphine levels."
        },
        "regulatory_action": {
            "verdict": "CONTRAINDICATED",
            "mandated_action": "Contraindicated. Avoid codeine; use non-opioid analgesics or an opioid not reliant on CYP2D6 bioactivation."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Non-codeine analgesic",
            "resolves_primary_interaction": True,
            "residual_risk_remains": False,
            "residual_risk_explanation": "Avoiding prodrug opioids dependent on CYP2D6 completely eliminates morphine overproduction."
        }
    },
    "TASK-13": {
        "causal_graph": [
            {"source": "Abacavir", "target": "HLA_B5701", "relation": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE"},
            {"source": "HLA_B5701", "target": "CD8_T_CELL_ACTIVATION", "relation": "INCREASES_EXPOSURE"},
            {"source": "CD8_T_CELL_ACTIVATION", "target": "HYPERSENSITIVITY_SYNDROME", "relation": "INCREASES_EXPOSURE"}
        ],
        "physiological_modifier": {
            "modifier_present": True,
            "parameter": "HLA-B*57:01 Positive",
            "clinical_consequence": "Abacavir binds the F-pocket of HLA-B*57:01, altering self-peptide presentation and inducing massive polyclonal CD8 T-cell activation."
        },
        "regulatory_action": {
            "verdict": "CONTRAINDICATED",
            "mandated_action": "Contraindicated. Avoid abacavir. Never rechallenge due to fatal anaphylactoid hypersensitivity."
        },
        "counterfactual_analysis": {
            "alternative_drug": "Tenofovir / Emtricitabine",
            "resolves_primary_interaction": True,
            "residual_risk_remains": False,
            "residual_risk_explanation": "Alternative NRTIs do not bind HLA-B*57:01, completely resolving the severe immunologic hypersensitivity risk."
        }
    }
}


def run_human_baseline(tasks_path: Path, use_templates: bool = False) -> Dict[str, Any]:
    """Runs the human clinical expert evaluation across the core tasks.
    
    Args:
        tasks_path: Path to tasks.json
        use_templates: If True, uses template responses (for testing only).
                       If False (default), expects a 'human_responses.json' file 
                       with real clinician responses to be present.
    
    WARNING: use_templates=True produces SIMULATED results that are NOT valid
    as empirical evidence. Real human baseline requires independent clinician recruitment.
    """
    if use_templates:
        print("⚠️  WARNING: Using template responses - NOT valid empirical evidence!")
        print("   Real human baseline requires independent clinician recruitment.\n")
        response_source = CLINICAL_EXPERT_REFERENCE_TEMPLATES
    else:
        # Load real clinician responses from file
        responses_file = BASE_DIR / "human_responses.json"
        if not responses_file.exists():
            raise FileNotFoundError(
                f"Real human responses file not found: {responses_file}\n"
                "Please collect responses from 2-3 clinical pharmacologists/PharmDs "
                "and save as human_responses.json with the same structure as the templates.\n"
                "Use --use-templates for format testing only (not empirical evidence)."
            )
        with open(responses_file) as f:
            response_source = json.load(f)
        print(f"✅ Loaded real clinician responses from {responses_file}")

    print("=" * 70)
    print("👨‍⚕️  MECHANISMTRACE-DDI: HUMAN CLINICAL PHARMACOLOGY EXPERT BASELINE")
    print(f"    Evaluating {len(CORE_TASK_IDS)} Core High-Stakes Clinical Scenarios")
    print("=" * 70 + "\n")

    with open(tasks_path, "r") as f:
        all_tasks = {t["id"]: t for t in json.load(f)}

    scores = []
    passed_count = 0
    task_results = []

    for tid in CORE_TASK_IDS:
        task = all_tasks.get(tid)
        if not task:
            continue
        expert_answer = response_source.get(tid, {})
        raw_response = json.dumps(expert_answer)
        grade = DeterministicCausalGrader.evaluate_task(task, raw_response)
        
        scores.append(grade["total_score"])
        if grade["passed"]:
            passed_count += 1
            
        task_results.append({
            "task_id": tid,
            "title": task["title"],
            "score": grade["total_score"],
            "passed": grade["passed"],
            "edge_accuracy_pct": grade["edge_accuracy_pct"],
            "cpcs_score": grade["cpcs_score"],
            "reasons": grade["reasons"]
        })
        status = "✅ PASS" if grade["passed"] else "❌ FAIL"
        print(f" -> {tid}: {status} ({grade['total_score']}/100) | CPCS: {grade['cpcs_score']}")

    mean_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    pass_rate = round((passed_count / len(scores)) * 100, 1) if scores else 0.0

    print("\n" + "=" * 70)
    if use_templates:
        print(f"⚠️  SIMULATED (template) baseline: Pass Rate = {passed_count}/{len(scores)} ({pass_rate}%) | Mean Score = {mean_score}/100")
        print("   This is NOT empirical evidence. Recruit real clinicians for valid baseline.")
    else:
        print(f"🏆 HUMAN CLINICIAN BASELINE: Pass Rate = {passed_count}/{len(scores)} ({pass_rate}%) | Mean Score = {mean_score}/100")
    print("=" * 70 + "\n")

    return {
        "evaluator_type": "Human Clinical Pharmacologist / PharmD Panel" if not use_templates else "SIMULATED Templates (NOT VALID EVIDENCE)",
        "tasks_evaluated": len(scores),
        "pass_rate_pct": pass_rate,
        "mean_score": mean_score,
        "task_breakdown": task_results
    }


def main():
    parser = argparse.ArgumentParser(description="Human Baseline for MechanismTrace-DDI")
    parser.add_argument("--tasks", type=str, default="dataset/tasks.json", help="Path to tasks.json")
    parser.add_argument("--use-templates", action="store_true", help="Use template responses (SIMULATION ONLY - not empirical evidence). Default: requires human_responses.json with real clinician data.")
    args = parser.parse_args()

    tasks_path = BASE_DIR / args.tasks
    summary = run_human_baseline(tasks_path, use_templates=args.use_templates)

    out_file = BASE_DIR / "results" / "human_baseline_summary.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Human baseline summary saved to: {out_file}\n")


if __name__ == "__main__":
    main()
