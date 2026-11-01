"""
Deterministic Causal Graph Grader for MechanismTrace-DDI
Evaluates LLM structured responses against reference pharmacological DAGs,
invariant counterfactual rules, and fatal safety traps.
"""
import json
import re
import logging
from typing import Dict, Any, List, Set, Tuple
from graders.normalizer import normalize_entity, normalize_relation

logger = logging.getLogger("evaluator.causal_grader")

# Negation patterns for fatal trap detection - hardened with token-window approach
_NEGATION_PATTERNS = [
    r"\bdo\s+not\b",
    r"\bdoes\s+not\b",
    r"\bdon'?t\b",
    r"\bavoid\b",
    r"\bnever\b",
    r"\bcontraindicat\w*\b",
    r"\bunsafe\b",
    r"\bnot\s+recommended\b",
    r"\bnot\s+safe\b",
    r"\bmust\s+not\b",
    r"\bshould\s+not\b",
    r"\brefrain\s+from\b",
    r"\bprohibit\w*\b",
]

# Token window for negation detection (number of tokens before target)
_NEGATION_WINDOW_TOKENS = 10


def _tokenize(text: str) -> List[str]:
    """Simple tokenization for negation window."""
    return re.findall(r"\b\w+(?:'\w+)?\b", text.lower())


def _contains_negation(text: str, target_phrase: str) -> bool:
    """
    Check if target_phrase appears in text WITHOUT negation context.
    Returns True if the phrase appears in a positive/affirmative context.
    Returns False if the phrase appears within a negated context.
    
    Uses token-window approach: checks up to NEGATION_WINDOW_TOKENS tokens before target.
    """
    text_lower = text.lower()
    target_lower = target_phrase.lower()
    
    # Find all occurrences of the target phrase
    start = 0
    while True:
        idx = text_lower.find(target_lower, start)
        if idx == -1:
            break
        
        # Get text before the phrase
        context_before = text_lower[:idx]
        tokens_before = _tokenize(context_before)
        
        # Check last N tokens for negation patterns
        window_tokens = tokens_before[-_NEGATION_WINDOW_TOKENS:]
        window_text = " ".join(window_tokens)
        
        # Check if any negation pattern appears in the token window
        negated = any(re.search(pattern, window_text) for pattern in _NEGATION_PATTERNS)
        
        if not negated:
            return True  # Found affirmative occurrence
        
        start = idx + 1
    
    return False  # All occurrences were negated, or phrase not found


def _build_adjacency(edges: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, str]]]:
    """Build adjacency list from normalized edges."""
    adj = {}
    for e in edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        rel = normalize_relation(e.get("relation", ""))
        if src and tgt:
            adj.setdefault(src, []).append((tgt, rel))
    return adj


def _find_perpetrators_and_victims(expected_edges: List[Dict[str, Any]]) -> Tuple[Set[str], Set[str]]:
    """Identify perpetrator (source) and victim (target) nodes from expected edges."""
    sources = {normalize_entity(e["source"]) for e in expected_edges}
    targets = {normalize_entity(e["target"]) for e in expected_edges}
    # Perpetrators are sources that are never targets
    perpetrators = sources - targets
    # Victims are targets that are never sources (exposure endpoints)
    victims = targets - sources
    return perpetrators, victims


def _has_continuous_path(pred_edges: List[Dict[str, Any]], 
                          expected_edges: List[Dict[str, Any]]) -> bool:
    """
    Check if predicted graph contains at least one continuous directed path
    from any Perpetrator -> ... -> Victim Exposure with CORRECT RELATIONS.
    """
    pred_adj = _build_adjacency(pred_edges)
    perpetrators, victims = _find_perpetrators_and_victims(expected_edges)
    
    if not perpetrators or not victims:
        return False
    
    # Build expected adjacency with relations for verification
    expected_adj = _build_adjacency(expected_edges)
    
    # Build a set of valid (src, rel, tgt) from expected edges for relation verification
    expected_edge_set = set()
    for e in expected_edges:
        src = normalize_entity(e["source"])
        tgt = normalize_entity(e["target"])
        rel = normalize_relation(e["relation"])
        expected_edge_set.add((src, rel, tgt))
    
    # For each perpetrator, try to reach any victim via a path with CORRECT relations
    for perp in perpetrators:
        # BFS from perpetrator with relation tracking
        visited = set()
        queue = [(perp, [])]  # (node, path_edges) where path_edges = list of (src, rel, tgt)
        while queue:
            node, path_edges = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            if node in victims:
                # Verify the path relations are consistent with expected chain
                # Check that each edge in the path matches an expected edge (or its alternate)
                if path_edges:
                    all_edges_valid = True
                    for path_src, path_rel, path_tgt in path_edges:
                        if (path_src, path_rel, path_tgt) not in expected_edge_set:
                            all_edges_valid = False
                            break
                    if all_edges_valid:
                        return True
                else:
                    # Direct perpetrator->victim edge (no intermediates)
                    return True
            for neighbor, rel in pred_adj.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, path_edges + [(node, rel, neighbor)]))
    return False


def _has_cycle(edges: List[Dict[str, Any]]) -> bool:
    """
    Detect cycles in a directed graph using iterative DFS (no recursion limit).
    Returns True if a cycle exists.
    """
    pred_adj = _build_adjacency(edges)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}
    
    for root in pred_adj:
        if color.get(root, 0) != 0:  # WHITE = 0
            continue
        stack = [(root, iter(pred_adj.get(root, [])))]
        color[root] = 1  # GRAY
        while stack:
            node, it = stack[-1]
            for nxt in it:
                c = color.get(nxt, 0)
                if c == 1:  # GRAY - back edge found
                    return True
                if c == 0:  # WHITE
                    color[nxt] = 1  # GRAY
                    stack.append((nxt, iter(pred_adj.get(nxt, []))))
                    break
            else:
                color[node] = 2  # BLACK
                stack.pop()
    return False


def _check_cause_effect_inversion(pred_edges: List[Dict[str, Any]], 
                                   expected_edges: List[Dict[str, Any]]) -> bool:
    """Check if model inverts cause-effect (victim -> perpetrator or backwards along chain)."""
    pred_adj = _build_adjacency(pred_edges)
    perpetrators, victims = _find_perpetrators_and_victims(expected_edges)
    
    # Also get all nodes in expected causal chain
    expected_nodes = perpetrators | victims
    for e in expected_edges:
        expected_nodes.add(normalize_entity(e["source"]))
        expected_nodes.add(normalize_entity(e["target"]))
    
    # Check if any victim points to perpetrator
    for victim in victims:
        for neighbor, _ in pred_adj.get(victim, []):
            if neighbor in perpetrators:
                return True
    
    # Check for backward edges along expected chain (victim -> intermediate, intermediate -> perpetrator)
    # Build expected forward edges set
    expected_forward = set()
    for e in expected_edges:
        src = normalize_entity(e["source"])
        tgt = normalize_entity(e["target"])
        expected_forward.add((src, tgt))
    
    # Check predicted edges against expected direction
    for pred in pred_edges:
        pred_src = normalize_entity(pred.get("source", ""))
        pred_tgt = normalize_entity(pred.get("target", ""))
        if (pred_tgt, pred_src) in expected_forward:
            return True  # Exact reverse of an expected edge
    
    return False


def _build_gold_paths(expected_edges: List[Dict[str, Any]]) -> List[List[Tuple[str, str, str]]]:
    """
    Build all perpetrator->victim paths from expected edges.
    Returns list of paths, each path is a list of (src, rel, tgt) tuples.
    """
    adj = _build_adjacency(expected_edges)
    perpetrators, victims = _find_perpetrators_and_victims(expected_edges)
    
    if not perpetrators or not victims:
        return []
    
    gold_paths = []
    
    for perp in perpetrators:
        # DFS to find all paths from this perpetrator to any victim
        stack = [(perp, [])]  # (node, path_edges)
        visited_paths = set()
        
        while stack:
            node, path = stack.pop()
            path_key = (node, tuple(path))
            if path_key in visited_paths:
                continue
            visited_paths.add(path_key)
            
            if node in victims and path:
                gold_paths.append(path)
            
            for neighbor, rel in adj.get(node, []):
                new_path = path + [(node, rel, neighbor)]
                stack.append((neighbor, new_path))
    
    return gold_paths


def _compute_graded_continuity(pred_edges: List[Dict[str, Any]], 
                                expected_edges: List[Dict[str, Any]]) -> float:
    """
    Compute graded path continuity (0.0 to 1.0) based on longest matched run
    along each gold perpetrator->victim path.
    
    For each gold path, find the longest contiguous run of matched edges.
    Score = max_run_length / path_length for each path, averaged over all paths.
    """
    gold_paths = _build_gold_paths(expected_edges)
    
    if not gold_paths:
        return 1.0  # No paths to verify
    
    # Build set of predicted edges (normalized)
    pred_edge_set = set()
    for e in pred_edges:
        src = normalize_entity(e.get("source", ""))
        tgt = normalize_entity(e.get("target", ""))
        rel = normalize_relation(e.get("relation", ""))
        if src and tgt:
            pred_edge_set.add((src, normalize_relation(e.get("relation", "")), tgt))
    
    total_score = 0.0
    for path in gold_paths:
        if not path:
            continue
        best_run = 0
        current_run = 0
        for edge in path:
            if edge in pred_edge_set:
                current_run += 1
            else:
                current_run = 0
            best_run = max(best_run, current_run)
        path_score = best_run / len(path) if path else 1.0
        total_score += path_score
    
    return total_score / len(gold_paths) if gold_paths else 1.0


def _compute_cpcs(pred_edges: List[Dict[str, Any]], 
                  expected_edges: List[Dict[str, Any]],
                  edge_recall: float = None,
                  edge_precision: float = None) -> Tuple[float, str]:
    """
    Compute Causal Path Continuity Score (CPCS).
    CPCS = 0.7 * F1 + 0.3 * Graded_Continuity
    
    Where F1 = 2 * recall * precision / (recall + precision)
    Graded continuity = average longest matched run / path length across gold paths.
    """
    if edge_recall is None:
        matched = 0
        for exp in expected_edges:
            exp_src = normalize_entity(exp["source"])
            exp_tgt = normalize_entity(exp["target"])
            exp_rel = normalize_relation(exp["relation"])
            for pred in pred_edges:
                pred_src = normalize_entity(pred.get("source", ""))
                pred_tgt = normalize_entity(pred.get("target", ""))
                pred_rel = normalize_relation(pred.get("relation", ""))
                if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
                    matched += 1
                    break
        edge_recall = matched / max(1, len(expected_edges))
    
    # Use provided precision or default to recall if not provided
    if edge_precision is None:
        edge_precision = edge_recall
    
    # Compute F1
    if edge_recall + edge_precision > 0:
        f1 = 2 * edge_recall * edge_precision / (edge_recall + edge_precision)
    else:
        f1 = 0.0
    
    # Graded continuity (0.0 to 1.0)
    continuity = _compute_graded_continuity(pred_edges, expected_edges)
    
    # Check for inversion (hard penalty: continuity = 0)
    inverted = _check_cause_effect_inversion(pred_edges, expected_edges)
    if inverted:
        continuity = 0.0
    
    # CPCS = 0.7 * F1 + 0.3 * Continuity
    if edge_recall + edge_precision > 0:
        f1 = 2 * edge_recall * edge_precision / (edge_recall + edge_precision)
    else:
        f1 = 0.0
    
    cpcs = 0.7 * f1 + 0.3 * continuity
    
    # Determine description
    if continuity >= 0.9:
        desc = "CONTINUOUS"
    elif continuity >= 0.5:
        desc = "PARTIAL"
    elif continuity > 0:
        desc = "FRAGMENTED"
    elif inverted:
        desc = "INVERTED_CAUSATION"
    else:
        desc = "DISCONNECTED"
    
    return round(cpcs, 3), desc


def _match_edge_against_expected(pred_src: str, pred_tgt: str, pred_rel: str,
                                   expected_edges: List[Dict[str, Any]],
                                   accepted_alternates: List[List[Dict[str, Any]]]) -> bool:
    """Check if a predicted edge matches any expected edge or accepted alternate."""
    # Check primary expected edges
    for exp in expected_edges:
        exp_src = normalize_entity(exp["source"])
        exp_tgt = normalize_entity(exp["target"])
        exp_rel = normalize_relation(exp["relation"])
        if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
            return True
    
    # Check accepted alternates
    for alt_set in accepted_alternates:
        for exp in alt_set:
            exp_src = normalize_entity(exp["source"])
            exp_tgt = normalize_entity(exp["target"])
            exp_rel = normalize_relation(exp["relation"])
            if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
                return True
    
    return False


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
        - Tier 1: Causal Edge Alignment (40 Points) - recall + precision
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
        accepted_alternates = gt.get("accepted_alternates", [])
        predicted_edges = model_json.get("causal_graph", [])
        matched_edges = 0

        # Build normalized predicted edge set for precision calculation
        pred_normalized = set()
        for pred in predicted_edges:
            pred_src = normalize_entity(pred.get("source", ""))
            pred_tgt = normalize_entity(pred.get("target", ""))
            pred_rel = normalize_relation(pred.get("relation", ""))
            if pred_src and pred_tgt:
                pred_normalized.add((pred_src, pred_rel, pred_tgt))

        # Build normalized expected edge set (including alternates)
        expected_normalized = set()
        for exp in expected_edges:
            exp_src = normalize_entity(exp["source"])
            exp_tgt = normalize_entity(exp["target"])
            exp_rel = normalize_relation(exp["relation"])
            expected_normalized.add((exp_src, exp_rel, exp_tgt))
        for alt_set in accepted_alternates:
            for exp in alt_set:
                exp_src = normalize_entity(exp["source"])
                exp_tgt = normalize_entity(exp["target"])
                exp_rel = normalize_relation(exp["relation"])
                expected_normalized.add((exp_src, exp_rel, exp_tgt))

# Recall: how many expected edges were matched
        # Track which predicted edges have been used for matching to prevent double-counting
        used_pred_indices = set()
        
        # First, check if any complete alternate set is fully matched by distinct predicted edges
        # If so, ALL primary edges are considered matched (alternate set is a complete replacement)
        alternate_set_matched = False
        for alt_set in accepted_alternates:
            alt_matched = True
            alt_used_indices = set()
            for alt in alt_set:
                alt_src = normalize_entity(alt["source"])
                alt_tgt = normalize_entity(alt["target"])
                alt_rel = normalize_relation(alt["relation"])
                alt_found = False
                for pred_idx, pred in enumerate(predicted_edges):
                    if pred_idx in used_pred_indices or pred_idx in alt_used_indices:
                        continue
                    pred_src = normalize_entity(pred.get("source", ""))
                    pred_tgt = normalize_entity(pred.get("target", ""))
                    pred_rel = normalize_relation(pred.get("relation", ""))
                    if pred_src == alt_src and pred_tgt == alt_tgt and pred_rel == alt_rel:
                        alt_found = True
                        alt_used_indices.add(pred_idx)
                        break
                if not alt_found:
                    alt_matched = False
                    break
            if alt_matched:
                alternate_set_matched = True
                used_pred_indices.update(alt_used_indices)
                # All primary edges are satisfied by this alternate set
                matched_edges = len(expected_edges)
                break
        
        # If no complete alternate set matched, fall back to matching individual primary edges
        if not alternate_set_matched:
            for exp_idx, exp in enumerate(expected_edges):
                exp_src = normalize_entity(exp["source"])
                exp_tgt = normalize_entity(exp["target"])
                exp_rel = normalize_relation(exp["relation"])

                edge_found = False
                for pred_idx, pred in enumerate(predicted_edges):
                    if pred_idx in used_pred_indices:
                        continue
                    pred_src = normalize_entity(pred.get("source", ""))
                    pred_tgt = normalize_entity(pred.get("target", ""))
                    pred_rel = normalize_relation(pred.get("relation", ""))

                    if pred_src == exp_src and pred_tgt == exp_tgt and pred_rel == exp_rel:
                        edge_found = True
                        used_pred_indices.add(pred_idx)
                        break
                
                # Also check against accepted alternates for individual edges
                if not edge_found:
                    for alt_set in accepted_alternates:
                        for alt in alt_set:
                            alt_src = normalize_entity(alt["source"])
                            alt_tgt = normalize_entity(alt["target"])
                            alt_rel = normalize_relation(alt["relation"])
                            for pred_idx, pred in enumerate(predicted_edges):
                                if pred_idx in used_pred_indices:
                                    continue
                                pred_src = normalize_entity(pred.get("source", ""))
                                pred_tgt = normalize_entity(pred.get("target", ""))
                                pred_rel = normalize_relation(pred.get("relation", ""))
                                if pred_src == alt_src and pred_tgt == alt_tgt and pred_rel == alt_rel:
                                    edge_found = True
                                    used_pred_indices.add(pred_idx)
                                    break
                            if edge_found:
                                break
                
                if edge_found:
                    matched_edges += 1
                else:
                    reasons.append(f"Missing mandatory causal edge: {exp['source']} -> {exp['relation']} -> {exp['target']}")
        else:
            # All primary edges matched via alternate set
            pass

# Build normalized neutral edge set (neither rewarded nor penalized)
        neutral_edges = gt.get("neutral_edges", [])
        neutral_normalized = set()
        for neu in neutral_edges:
            neu_src = normalize_entity(neu.get("source", ""))
            neu_tgt = normalize_entity(neu.get("target", ""))
            neu_rel = normalize_relation(neu.get("relation", ""))
            if neu_src and neu_tgt:
                neutral_normalized.add((neu_src, neu_rel, neu_tgt))

        # Build set of all valid edges (expected + accepted alternates) for precision
        valid_edges = expected_normalized.copy()

        # Check predicted edges against expected + alternates + neutral for precision
        spurious_edges = []
        for pred in predicted_edges:
            pred_src = normalize_entity(pred.get("source", ""))
            pred_tgt = normalize_entity(pred.get("target", ""))
            pred_rel = normalize_relation(pred.get("relation", ""))
            if pred_src and pred_tgt:
                edge_tuple = (pred_src, pred_rel, pred_tgt)
                if edge_tuple in neutral_normalized:
                    continue  # Neutral edge: valid biology, not spurious
                # Check if this predicted edge matches any expected or alternate
                is_matched = _match_edge_against_expected(pred_src, pred_tgt, pred_rel, 
                                                          expected_edges, accepted_alternates)
                if not is_matched:
                    spurious_edges.append(f"{pred_src} -> {pred_rel} -> {pred_tgt}")

        edge_recall = matched_edges / max(1, len(expected_edges))
        
        # Denominator excludes neutral edges so precision measures non-neutral predictions
        non_neutral_pred = pred_normalized - neutral_normalized
        if len(non_neutral_pred) > 0:
            # Precision: fraction of non-neutral predictions that are valid (expected or alternate)
            edge_precision = len(valid_edges & non_neutral_pred) / len(non_neutral_pred)
        else:
            edge_precision = 1.0 if matched_edges > 0 else 0.0
        
        # Neutral edge cap: excess neutral edges count as noise
        neutral_hits = len(neutral_normalized & pred_normalized)
        neutral_cap = int(1.0 * len(expected_edges))  # Cap at 1x gold edges
        neutral_overage = max(0, neutral_hits - neutral_cap)
        if neutral_overage > 0:
            # Penalize excess neutral edges by reducing precision
            edge_precision = max(0.0, edge_precision - 0.1 * neutral_overage)
            reasons.append(f"Excess neutral edges ({neutral_hits} vs cap {neutral_cap}): precision penalty applied")
        
        # Check for cycles in predicted graph
        has_model_cycle = _has_cycle(predicted_edges)
        
        # --- CPCS: Causal Path Continuity Score (F1-based) ---
        cpcs_score, cpcs_desc = _compute_cpcs(
            predicted_edges, expected_edges, 
            edge_recall=edge_recall, edge_precision=edge_precision
        )
        
        # Cycle penalty: hard reduction if model graph has cycles
        if has_model_cycle:
            cpcs_score = max(0.0, cpcs_score - 0.2)
            cpcs_desc += "_CYCLE"
            reasons.append("Cyclic graph detected in predicted edges: CPCS penalty applied")
        
        # Tier 1 score: 0.5 * recall + 0.5 * precision * 40, modulated by CPCS (F1-based)
        # CPCS = 0.7 * F1 + 0.3 * Graded_Continuity
        edge_f1 = (2 * edge_recall * edge_precision / (edge_recall + edge_precision) 
                   if (edge_recall + edge_precision) > 0 else 0.0)
        edge_score = (0.5 * edge_recall + 0.5 * edge_precision) * 40.0
        # Apply CPCS as a continuity factor (cpcs_score ranges 0.0-1.0)
        edge_score *= cpcs_score
        score += edge_score

        if spurious_edges:
            reasons.append(f"Spurious/hallucinated edges ({len(spurious_edges)}): {', '.join(spurious_edges[:5])}{'...' if len(spurious_edges) > 5 else ''}")

        # --- TIER 2: REGULATORY VERDICT & FATAL TRAPS (30 Points) ---
        reg_dict = model_json.get("regulatory_action", {})
        candidate_verdict = reg_dict.get("verdict", "").strip().upper()
        expected_verdict = gt.get("expected_verdict", "").strip().upper()

        # Map equivalent verdict synonyms
        safe_synonyms = {"NO_DOSE_ADJUSTMENT", "SAFE_WITHOUT_ADJUSTMENT", "SAFE", "NO_ADJUSTMENT_REQUIRED", "NO_CYP_INTERACTION"}
        if candidate_verdict in safe_synonyms and expected_verdict in safe_synonyms:
            verdict_match = True
        else:
            verdict_match = (candidate_verdict == expected_verdict)

        if verdict_match:
            score += 20.0
        else:
            reasons.append(f"Regulatory verdict mismatch: expected '{expected_verdict}', got '{candidate_verdict}'")

        # Check for Fatal Anti-Pattern Traps in mandated_action field only
        mandated_action = reg_dict.get("mandated_action", "")
        for trap in gt.get("fatal_traps", []):
            if _contains_negation(mandated_action, trap):
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
        # Passing requires score >= 80.0 AND preserving the counterfactual residual risk invariant (no skipping lethal background risks)
        passed = (final_score >= 80.0) and (pred_residual == exp_residual) and not fatal_error

        return {
            "task_id": task["id"],
            "passed": passed,
            "total_score": final_score,
            "edge_accuracy_pct": round(edge_recall * 100, 1),
            "edge_precision_pct": round(edge_precision * 100, 1),
            "matched_edges": f"{matched_edges}/{len(expected_edges)}",
            "cpcs_score": cpcs_score,
            "cpcs_continuity": cpcs_desc,
            "fatal_error": fatal_error,
            "reasons": reasons,
            "response_preview": raw_response[:180] + "..." if len(raw_response) > 180 else raw_response
        }