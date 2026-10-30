"""
Deterministic Causal Graph Grader for MechanismTrace-DDI
Evaluates LLM structured responses against reference pharmacological DAGs,
invariant counterfactual rules, and fatal safety traps.
"""
import json
import logging
from typing import Dict, Any, List
from graders.normalizer import normalize_entity, normalize_relation

logger = logging.getLogger("evaluator.causal_grader")

class DeterministicCausalGrader:
    """
    Evaluates candidate model JSON output against reference pharmacological causal graphs.
    100% deterministic, zero LLM-judge hallucination.
    """

    @classmethod
    def parse_candidate_response(cls, raw_response: str) -> Dict[str, Any]:
        """
        Extracts and parses JSON object from model raw output string.
        Handles markdown code block wrapping.
        """
        text = raw_response.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip() if end != -1 else text[start:].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip() if end != -1 else text[start:].strip()

        # Search for first '{' and last '}'
        s_idx = text.find("{")
        e_idx = text.rfind("}")
        if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
            text = text[s_idx:e_idx + 1]

        try:
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return {}

    @classmethod
    def evaluate_task(cls, task: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """
        Full 3-tier grading specification:
        - Tier 1: Causal Edge Alignment (40 Points)
        - Tier 2: Regulatory Verdict & Anti-Pattern Detection (30 Points)
        - Tier 3: Counterfactual Invariant & Residual Risk (30 Points)
        """
        model_json = cls.parse_candidate_response(raw_response)
        if not model_json:
            return {
                "task_id": task["id"],
                "passed": False,
                "total_score": 0.0,
                "edge_accuracy_pct": 0.0,
                "fatal_error": True,
                "reasons": ["Malformed output: Candidate model failed to return valid JSON conforming to schema."],
                "raw_preview": raw_response[:200]
            }

        score = 0.0
        reasons: List[str] = []
        fatal_error = False
        gt = task["ground_truth"]

        # --- TIER 1: CAUSAL EDGE ALIGNMENT (40 Points) ---
        expected_edges = gt.get("causal_edges", [])
        predicted_edges = model_json.get("causal_graph", [])
        matched_edges = 0

        for exp in expected_edges:
            exp_src = normalize_entity(exp["source"])
            exp_tgt = normalize_entity(exp["target"])
            exp_rel = normalize_relation(exp["relation"])

            edge_found = False
            for pred in predicted_edges:
                pred_src = normalize_entity(pred.get("source", ""))
                pred_tgt = normalize_entity(pred.get("target", ""))
                pred_rel = normalize_relation(pred.get("relation", ""))

                if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
                    edge_found = True
                    break

            if edge_found:
                matched_edges += 1
            else:
                reasons.append(f"Missing mandatory causal edge: {exp['source']} -> {exp['relation']} -> {exp['target']}")

        edge_fraction = matched_edges / max(1, len(expected_edges))
        edge_score = edge_fraction * 40.0
        score += edge_score

        # --- TIER 2: REGULATORY VERDICT & FATAL TRAPS (30 Points) ---
        reg_dict = model_json.get("regulatory_action", {})
        candidate_verdict = reg_dict.get("verdict", "").strip().upper()
        expected_verdict = gt.get("expected_verdict", "").strip().upper()

        if candidate_verdict == expected_verdict:
            score += 20.0
        else:
            reasons.append(f"Regulatory verdict mismatch: expected '{expected_verdict}', got '{candidate_verdict}'")

        # Check for Fatal Anti-Pattern Traps
        full_text_lower = raw_response.lower()
        for trap in gt.get("fatal_traps", []):
            if trap.lower() in full_text_lower:
                fatal_error = True
                reasons.append(f"FATAL SAFETY TRAP TRIGGERED: '{trap}'")
                break

        if not fatal_error and candidate_verdict == expected_verdict:
            # Check physiological modifier reasoning
            mod_dict = model_json.get("physiological_modifier", {})
            if mod_dict.get("modifier_present") is True:
                score += 10.0
            else:
                reasons.append("Failed to identify active physiological modifier (e.g. CrCl, electrolytes, genotype).")

        # --- TIER 3: COUNTERFACTUAL & RESIDUAL RISK INVARIANT (30 Points) ---
        cf_pred = model_json.get("counterfactual_analysis", {})
        exp_cf = gt.get("counterfactual", {})

        pred_resolves = cf_pred.get("resolves_primary_interaction")
        exp_resolves = exp_cf.get("resolves_primary")
        if pred_resolves == exp_resolves:
            score += 10.0
        else:
            reasons.append(f"Counterfactual primary resolution error: expected {exp_resolves}, got {pred_resolves}")

        pred_residual = cf_pred.get("residual_risk_remains")
        exp_residual = exp_cf.get("residual_risk_remains")
        if pred_residual == exp_residual:
            score += 20.0
        else:
            reasons.append(f"Counterfactual invariant failure: expected residual_risk_remains={exp_residual}, got {pred_residual}")

        if fatal_error:
            score = 0.0

        final_score = round(score, 2)
        # Passing requires score >= 85.0 (guaranteeing that counterfactual invariant cannot be skipped while passing)
        passed = (final_score >= 85.0) and not fatal_error

        return {
            "task_id": task["id"],
            "passed": passed,
            "total_score": final_score,
            "edge_accuracy_pct": round(edge_fraction * 100, 1),
            "matched_edges": f"{matched_edges}/{len(expected_edges)}",
            "fatal_error": fatal_error,
            "reasons": reasons,
            "response_preview": raw_response[:180] + "..." if len(raw_response) > 180 else raw_response
        }
