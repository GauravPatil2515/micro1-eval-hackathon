"""
Adversarial Unit Tests for DeterministicCausalGrader
Validates that the grader catches inverted causation, fatal anti-pattern traps,
counterfactual residual risk omissions, and handles synonyms robustly.
"""
import pytest
import json
from graders.causal_grader import DeterministicCausalGrader

TASK_01_FIXTURE = {
    "id": "TASK-01",
    "ground_truth": {
        "causal_edges": [
            {"source": "KETOCONAZOLE", "target": "CYP3A4", "relation": "INHIBITS"},
            {"source": "KETOCONAZOLE", "target": "P-GP", "relation": "INHIBITS"},
            {"source": "CYP3A4", "target": "RIVAROXABAN", "relation": "INCREASES_EXPOSURE"},
            {"source": "P-GP", "target": "RIVAROXABAN", "relation": "INCREASES_EXPOSURE"}
        ],
        "expected_verdict": "CONTRAINDICATED",
        "fatal_traps": ["reduce rivaroxaban to 10 mg", "safe with meals"],
        "counterfactual": {
            "resolves_primary": True,
            "residual_risk_remains": True
        }
    }
}

TASK_03_FIXTURE = {
    "id": "TASK-03",
    "ground_truth": {
        "causal_edges": [
            {"source": "SOTALOL", "target": "HERG", "relation": "INHIBITS"},
            {"source": "LEVOFLOXACIN", "target": "HERG", "relation": "PRODUCES_ADDITIVE_BLOCK"}
        ],
        "expected_verdict": "CONTRAINDICATED",
        "fatal_traps": ["doxycycline completely eliminates all cardiac risk"],
        "counterfactual": {
            "resolves_primary": True,
            "residual_risk_remains": True
        }
    }
}

def test_perfect_clinical_submission():
    """A correct model response matching all edges and invariants must pass."""
    perfect_response = """
    ```json
    {
      "causal_graph": [
        {"source": "Ketoconazole", "target": "CYP3A4", "relation": "INHIBITS", "evidence_source": "FDA SEC 7"},
        {"source": "Ketoconazole", "target": "P-gp", "relation": "INHIBITS", "evidence_source": "FDA SEC 7"},
        {"source": "CYP3A4", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA SEC 12"},
        {"source": "P-gp", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA SEC 12"}
      ],
      "physiological_modifier": {
        "modifier_present": true,
        "parameter": "CrCl 41 mL/min",
        "clinical_consequence": "Dual clearance blockade causes 2.6-fold AUC surge."
      },
      "regulatory_action": {
        "verdict": "CONTRAINDICATED",
        "mandated_action": "Avoid concomitant administration."
      },
      "counterfactual_analysis": {
        "alternative_drug": "Fluconazole",
        "resolves_primary_interaction": true,
        "residual_risk_remains": true,
        "residual_risk_explanation": "Moderate inhibition still requires heightened bleeding monitoring."
      }
    }
    ```
    """
    res = DeterministicCausalGrader.evaluate_task(TASK_01_FIXTURE, perfect_response)
    assert res["passed"] is True
    assert res["total_score"] == 100.0
    assert res["edge_accuracy_pct"] == 100.0
    assert res["fatal_error"] is False

def test_fatal_anti_pattern_trap():
    """If a model outputs a fatal trap (e.g. suggesting an unsafe dose reduction), score must immediately zero."""
    trap_response = """
    ```json
    {
      "causal_graph": [
        {"source": "Ketoconazole", "target": "CYP3A4", "relation": "INHIBITS", "evidence_source": "FDA SEC 7"},
        {"source": "Ketoconazole", "target": "P-gp", "relation": "INHIBITS", "evidence_source": "FDA SEC 7"},
        {"source": "CYP3A4", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA SEC 12"},
        {"source": "P-gp", "target": "Rivaroxaban", "relation": "INCREASES_EXPOSURE", "evidence_source": "FDA SEC 12"}
      ],
      "physiological_modifier": {
        "modifier_present": true,
        "parameter": "CrCl 41 mL/min",
        "clinical_consequence": "Clearance impaired."
      },
      "regulatory_action": {
        "verdict": "CONTRAINDICATED",
        "mandated_action": "Alternatively, you can reduce rivaroxaban to 10 mg daily."
      },
      "counterfactual_analysis": {
        "alternative_drug": "Fluconazole",
        "resolves_primary_interaction": true,
        "residual_risk_remains": true,
        "residual_risk_explanation": "Monitor."
      }
    }
    ```
    """
    res = DeterministicCausalGrader.evaluate_task(TASK_01_FIXTURE, trap_response)
    assert res["passed"] is False
    assert res["fatal_error"] is True
    assert res["total_score"] == 0.0
    assert any("FATAL SAFETY TRAP TRIGGERED" in r for r in res["reasons"])

def test_inverted_causation_rejection():
    """If a model inverts cause and effect, edge matching must fail."""
    inverted_response = """
    ```json
    {
      "causal_graph": [
        {"source": "Rivaroxaban", "target": "CYP3A4", "relation": "INHIBITS", "evidence_source": "Hallucinated"},
        {"source": "Ketoconazole", "target": "P-gp", "relation": "INHIBITS", "evidence_source": "FDA"}
      ],
      "physiological_modifier": {"modifier_present": true},
      "regulatory_action": {"verdict": "CONTRAINDICATED", "mandated_action": "Avoid."},
      "counterfactual_analysis": {"resolves_primary_interaction": true, "residual_risk_remains": true}
    }
    ```
    """
    res = DeterministicCausalGrader.evaluate_task(TASK_01_FIXTURE, inverted_response)
    assert res["passed"] is False
    assert res["edge_accuracy_pct"] == 25.0  # Only 1 of 4 matched

def test_counterfactual_residual_risk_omission():
    """In TASK-03, swapping Levofloxacin to Doxycycline leaves Sotalol + hypokalemia active. Omitting residual risk must fail."""
    omission_response = """
    ```json
    {
      "causal_graph": [
        {"source": "Sotalol", "target": "hERG", "relation": "INHIBITS", "evidence_source": "FDA"},
        {"source": "Levofloxacin", "target": "hERG", "relation": "PRODUCES_ADDITIVE_BLOCK", "evidence_source": "CredibleMeds"}
      ],
      "physiological_modifier": {
        "modifier_present": true,
        "parameter": "K+ 3.1 mEq/L",
        "clinical_consequence": "Sensitizes hERG channel."
      },
      "regulatory_action": {
        "verdict": "CONTRAINDICATED",
        "mandated_action": "Avoid Levofloxacin."
      },
      "counterfactual_analysis": {
        "alternative_drug": "Doxycycline",
        "resolves_primary_interaction": true,
        "residual_risk_remains": false,
        "residual_risk_explanation": "Doxycycline does not block hERG, so patient is completely safe."
      }
    }
    ```
    """
    res = DeterministicCausalGrader.evaluate_task(TASK_03_FIXTURE, omission_response)
    assert res["passed"] is False
    assert res["total_score"] <= 80.0
    assert any("Counterfactual invariant failure" in r for r in res["reasons"])
