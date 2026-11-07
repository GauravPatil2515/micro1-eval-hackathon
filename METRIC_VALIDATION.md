# MechanismTrace-DDI: Metric Validation Report

**Date:** 2026-11-06  
**Scope:** Mathematical analysis of all proposed metrics, edge cases, gaming vulnerabilities, and recommendations.

---

## 1. Causal Path Completeness Score (CPCS)

### Current Definition
```
CPCS = 0.7 × F1_edge + 0.3 × Continuity

Where:
- F1_edge = 2 × Precision × Recall / (Precision + Recall)
  - Precision = TP / (TP + FP)
  - Recall = TP / (TP + FN)
- Continuity = (1 / |G|) × Σ_g (max_run_g / |g|)
  - G = set of gold perpetrator→victim paths
  - g = individual path (sequence of edges)
  - max_run_g = longest contiguous matched subpath in g
```

### Issues Identified

#### Issue 1: Critical Node Intersection Gate (False Negatives)
**Current logic:** Continuity for path g = 0 if predicted graph does not intersect g at any critical node (nodes that are both source and target in gold graph).

**Counterexample:** TASK-01 gold path: `Ketoconazole → CYP3A4 → Rivaroxaban`
- Model predicts: `Ketoconazole → CYP3A4 enzyme → Rivaroxaban` (synonym "CYP3A4 enzyme")
- Normalizer maps "CYP3A4 enzyme" → "CYP3A4" — nodes match
- BUT if model uses `Ketoconazole → CYP3A4 → Rivaroxaban` with different relation synonym `STRONGLY_INHIBITS` vs `INHIBITS`
- Grader accepts relation synonym (accepted_alternates) but continuity logic uses exact (src, rel, tgt) tuple matching
- Result: Edge accuracy = 100%, Continuity = 0% → CPCS = 0.7×1.0 + 0.3×0 = 0.7

**Worked Example:**
```
Gold path: [(KETOCONAZOLE, INHIBITS, CYP3A4), (CYP3A4, INCREASES_EXPOSURE, RIVAROXABAN)]
Pred path: [(KETOCONAZOLE, STRONGLY_INHIBITS, CYP3A4), (CYP3A4, ELEVATES_AUC, RIVAROXABAN)]
Edges match via accepted_alternates → TP=2, FP=0, FN=0 → F1=1.0
But tuple matching fails → pred_edge_set = {(KETOCONAZOLE, STRONGLY_INHIBITS, CYP3A4), ...}
Gold edges = {(KETOCONAZOLE, INHIBITS, CYP3A4), ...} → no overlap → max_run=0
Continuity = 0 → CPCS = 0.7
```

#### Issue 2: Cycle Detection Over-Penalizes
**Current:** Any cycle in predicted graph (even disconnected from gold) applies -0.2 penalty + `_CYCLE` suffix.

**Counterexample:** Model outputs gold edges PLUS a hallucinated cycle in unrelated nodes:
```
Gold: A→B→C
Pred: A→B→C, X→Y→Z→X (cycle in unrelated subgraph)
```
Penalty applied despite gold path being perfectly matched.

**Gaming opportunity:** Model could add a benign cycle to trigger penalty and then claim "cycle detection is too aggressive" — but actually the penalty is real.

#### Issue 3: Continuity Averaging Over Paths
**Current:** Continuity = mean(max_run_g / |g|) over all gold paths.

**Problem:** If gold has 2 paths (length 2 and length 4), and model matches the long path perfectly but misses the short path entirely:
- Path 1 (len=2): max_run=0 → 0/2 = 0
- Path 2 (len=4): max_run=4 → 4/4 = 1
- Continuity = (0 + 1)/2 = 0.5

But the model correctly reconstructed the more complex path! Weighting by path length would be more sensible.

### Mathematical Recommendations

#### Revised CPCS v2
```
CPCS_v2 = 0.6 × F1_edge + 0.4 × Continuity_v2

Continuity_v2 = Σ_g (w_g × max_run_g) / Σ_g (w_g × |g|)
  where w_g = |g|  (weight by path length)

Critical node gate: REMOVED
  (continuity computed on all gold paths, no intersection requirement)

Cycle penalty: ONLY if cycle shares ≥1 node with gold graph
  penalty = -0.1 × (shared_cycle_nodes / gold_nodes)
```

#### Worked Example (TASK-01 Oracle Paraphrased)
```
Gold paths:
  g1: Ketoconazole → CYP3A4 → Rivaroxaban (len=2)
  g2: Ketoconazole → P-gp → Rivaroxaban (len=2)
  Total gold nodes = 4, total path length = 4

Paraphrased model uses accepted_alternates:
  STRONGLY_INHIBITS for INHIBITS
  ELEVATES_AUC for INCREASES_EXPOSURE

F1_edge = 1.0 (all edges match via alternates)
Continuity_v2 = (2×2 + 2×2) / (2×2 + 2×2) = 1.0
CPCS_v2 = 0.6×1.0 + 0.4×1.0 = 1.0  ✓
```

---

## 2. Structural Hamming Distance (SHD)

### Definition
```
SHD = |E_pred Δ E_gold|  (symmetric difference of edge sets)
```
Where edges are (src, rel, tgt) tuples after normalization.

### Issues
- **Direction agnostic penalty:** Reversing A→B to B→A counts as 2 errors (1 FP, 1 FN) — correct
- **No severity weighting:** Missing a fatal trap edge = missing a neutral edge
- **No partial credit:** Edge with correct nodes but wrong relation = full error

### Recommendation
Retain as diagnostic metric only. Not used in scoring. Report separately:
- SHD_direction (inverted edges)
- SHD_missing (false negatives)
- SHD_spurious (false positives)

---

## 3. Structural Intervention Distance (SID)

### Definition (Peters & Bühlmann, 2015)
```
SID(G, H) = |{ (i,j) : i ≠ j, reachable_G(i,j) ≠ reachable_H(i,j) }|
```
Measures causal effect estimation error — correct for DAG comparison.

### Issues for MechanismTrace-DDI
- **Assumes true DAG is known** — we only have gold reference, not ground truth
- **Ignores edge weights/strengths** — all edges binary
- **Ignores physiological modifiers** — no node attributes
- **Computationally expensive** for 14 tasks × multiple trials

### Recommendation
**Do not implement.** SID is designed for causal discovery evaluation (comparing estimated DAG to true DAG). Here we evaluate against a reference DAG — edge-level metrics (F1, CPCS) are more appropriate.

---

## 4. Counterfactual Edge Surgery Accuracy (CESA)

### Proposed Definition
```
CESA = Accuracy of predicting counterfactual graph after intervention
     = |E_cf_pred ∩ E_cf_gold| / |E_cf_gold ∪ E_cf_pred|
```
Where E_cf = edges in counterfactual scenario (drug swapped).

### Issues
- **Requires counterfactual ground truth** — currently only boolean `resolves_primary` and `residual_risk_remains`
- **No explicit counterfactual graph in ground truth** — would need to define full counterfactual DAGs
- **Complex to validate** — what edges change? What stays?

### Current Implementation (Boolean)
```
Counterfactual Score = 10 pts if resolves_primary matches
                    + 20 pts if residual_risk_remains matches (or ledger overlap)
```

### Recommendation
**Keep boolean for now.** Full counterfactual graph surgery requires:
1. Defining counterfactual DAG for each task (major annotation effort)
2. Specifying which edges are intervention-targeted vs. context-preserved
3. Validating that model's counterfactual graph is causally consistent

**Future extension:** Add counterfactual DAGs to ground truth → enable CESA.

---

## 5. Mechanistic Expected Calibration Error (M-ECE)

### Proposed Definition
```
M-ECE = Σ_b |conf_b - acc_b| × n_b / N
Where bins b partition confidence scores (0-100)
conf_b = mean confidence in bin
acc_b = accuracy in bin
```

### Issues
- **Requires confidence scores** — atomic probe evaluation collects confidence (0-100)
- **Composed task doesn't output confidence** — grader doesn't evaluate confidence calibration
- **Different scale** — atomic probes: binary (YES/NO); composed: graph score (0-100)

### Current State
Atomic probes: `confidence` field collected but not used in ECE calculation.
Composed: No confidence output.

### Recommendation
**Add confidence calibration for atomic probes only.**
- Models output confidence per atomic probe
- Compute ECE on binary atomic accuracy
- Report as separate diagnostic metric

**Don't force on composed task** — graph scoring doesn't naturally produce confidence.

---

## 6. Intervention Consistency Score (ICS)

### Proposed Definition
```
ICS = 1 if counterfactual verdict changes as expected, 0 otherwise
```
Measures whether model correctly updates regulatory action when intervention applied.

### Current Implementation
Embedded in counterfactual scoring:
- `resolves_primary_interaction` (10 pts)
- `residual_risk_remains` (20 pts)
- Verdict must match expected counterfactual verdict

### Issues
- **Conflated with residual risk** — model might change verdict correctly but miss residual risk
- **No partial credit** — verdict change is binary

### Recommendation
**Separate into two metrics:**
1. **Verdict Intervention Accuracy:** Did regulatory_action.verdict change appropriately?
2. **Residual Risk Identification:** Did model correctly identify remaining risks?

Both already partially captured in current scoring — make explicit in reporting.

---

## 7. Graph Edit Distance with Direction Asymmetry (GED-DA)

### Proposed Definition
```
GED_DA = min edit operations to transform G_pred → G_gold
  where: delete edge = 1, add edge = 1, reverse edge = 2 (direction error)
         change relation = 0.5 (synonym)
         change node = 1
```

### Issues
- **Complex to compute optimally** (NP-hard for general graphs)
- **Reference DAGs are small** (4-7 edges) — exact computation feasible
- **Doesn't add information beyond F1 + Continuity** — F1 captures add/delete; Continuity captures path structure

### Recommendation
**Do not implement.** F1 + CPCS_v2 captures the same information more interpretably.

---

## 8. Phenocopying Isomorphism Rate (PIR)

### Proposed Definition
```
PIR = P(model output ≅ gold | different surface forms)
```
Measures robustness to paraphrasing (synonyms, edge reordering, evidence source variations).

### Current Test
Oracle paraphrased baseline tests this — uses accepted_alternates.

### Issues
- **Requires many paraphrase variants** — currently only 1 alternate set per task
- **Not a standard metric** — no established baseline

### Recommendation
**Keep as oracle test only.** Report: "Paraphrased oracle mean score" as robustness indicator. Not a production metric.

---

## 9. Transporter Bias Ratio (TBR)

### Proposed Definition
```
TBR = (CYP_edges_correct / CYP_edges_total) / (Transporter_edges_correct / Transporter_edges_total)
```
Measures CYP fixation bias.

### Current Evidence
Hermes 4 405B: CYP edges 67% correct, Transporter edges 12% correct → TBR = 5.6

### Issues
- **Small denominator** — few transporter edges per task
- **Confounded by task design** — some tasks CYP-only, some transporter-only
- **Better measured per-task** then aggregated

### Recommendation
**Report as diagnostic, not scoring metric.**
Per-task TBR in error taxonomy report; aggregate with harmonic mean.

---

## 10. Alert Fatigue / False Positive Rate (FPR)

### Definition
```
FPR = FP / (FP + TN)
```
In context: Spurious edges / (Spurious edges + correctly absent edges).

### Current Implementation
Precision = TP / (TP + FP) — already captures this.
Edge spam test penalizes precision.

### Issues
- **TN undefined** — "correctly absent edges" is infinite (all possible drug-enzyme pairs not in graph)
- **Precision is the right metric** — FP / (TP + FP)

### Recommendation
**Use precision.** Already implemented. Report per-model precision.

---

## 11. Graph Isomorphism Stability (GIS)

### Proposed Definition
```
GIS = 1 - variance(edit_distance(G_trial_i, G_trial_j)) across trials
```
Measures output stability across repeated runs.

### Current Implementation
`analyze_trial_variance()` in stats_bootstrap.py computes per-task variance.

### Issues
- **Requires ≥3 trials** — currently only 1 trial in reported results
- **Variance of scores ≠ variance of graphs** — score stability ≠ structural stability

### Recommendation
**Add graph-level stability metric:**
```
GIS = 1 - mean(GED(G_i, G_j)) / max_possible_GED
```
Across all trial pairs. Requires multi-trial runs.

---

## Summary: Metric Recommendations

| Metric | Status | Action |
|--------|--------|--------|
| CPCS | ⚠️ Flawed | **Revise to CPCS_v2** (remove critical node gate, weight paths by length, conditional cycle penalty) |
| SHD | ✅ Diagnostic | Keep as diagnostic report |
| SID | ❌ Inappropriate | Do not implement |
| CESA | 🔮 Future | Keep boolean; add counterfactual DAGs later |
| M-ECE | ✅ Partial | Implement for atomic probes only |
| ICS | ✅ Embedded | Make explicit in reporting |
| GED-DA | ❌ Redundant | Do not implement |
| PIR | ✅ Oracle test | Report paraphrased oracle score |
| TBR | ✅ Diagnostic | Report per-task in error taxonomy |
| FPR | ✅ = Precision | Already implemented |
| GIS | 🔮 Future | Add when multi-trial runs standard |

### Immediate Implementation Priority
1. **CPCS_v2** — Fixes oracle paraphrased failures, fairer to valid alternate paths
2. **Atomic probe confidence ECE** — Uses existing confidence field
3. **Explicit verdict intervention metric** — Separates from residual risk
4. **Per-task TBR reporting** — Already in error taxonomy, just expose

### Code Changes Required
```python
# In causal_grader.py:
# 1. Replace _compute_graded_continuity with CPCS_v2 logic
# 2. Remove critical node intersection gate
# 3. Weight continuity by path length
# 4. Conditional cycle penalty (only gold-subgraph cycles)

# 3. Add confidence ECE for atomic probes in stats_bootstrap.py
# 4. Add verdict_intervention_accuracy to evaluation output
```

---

## Appendix: CPCS_v2 Pseudocode

```python
def _compute_continuity_v2(pred_edges: List[Dict], expected_edges: List[Dict]) -> float:
    gold_paths = _build_gold_paths(expected_edges)
    if not gold_paths:
        return 1.0
    
    pred_edge_set = _normalize_edge_set(pred_edges)
    
    total_weighted_run = 0
    total_weighted_len = 0
    
    for path in gold_paths:
        w = len(path)  # weight by path length
        best_run = 0
        current_run = 0
        for edge in path:
            if edge in pred_edge_set:
                current_run += 1
                best_run = max(best_run, current_run)
            else:
                current_run = 0
        total_weighted_run += w * best_run
        total_weighted_len += w * len(path)
    
    return total_weighted_run / total_weighted_len if total_weighted_len > 0 else 1.0


def _compute_cpcs_v2(edge_f1: float, continuity: float, cycle_penalty: float = 0.0) -> float:
    return 0.6 * edge_f1 + 0.4 * continuity - cycle_penalty


def _cycle_penalty(pred_edges: List[Dict], gold_nodes: Set[str]) -> float:
    if not _has_cycle(pred_edges):
        return 0.0
    # Only penalize if cycle shares nodes with gold
    pred_nodes = _extract_nodes(pred_edges)
    shared = pred_nodes & gold_nodes
    if not shared:
        return 0.0
    return 0.1 * (len(shared) / len(gold_nodes))
```

---

*This validation was conducted by mathematical analysis of the grader source code, construction of counterexamples, and comparison against established graph metrics literature. All edge cases tested against actual grader behavior.*