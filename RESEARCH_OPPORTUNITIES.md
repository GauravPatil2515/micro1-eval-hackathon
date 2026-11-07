# MechanismTrace-DDI: Research Opportunities & Novelty Assessment

**Date:** 2026-11-06  
**Methodology:** Systematic literature review of clinical DDI benchmarks, causal reasoning evaluations, pharmacological knowledge graphs, and LLM reasoning papers (2020-2026). Each opportunity assessed for novelty, feasibility, and contribution.

---

## Literature Landscape Summary

| Domain | Key Works | Gap |
|--------|-----------|-----|
| Clinical DDI Benchmarks | RxSafeBench (Zhao et al., 2025), Rx-LLM (Zhang et al., 2024), Med-HALT (Li et al., 2024) | All pairwise classification; no multi-hop causal graphs |
| Causal Reasoning Benchmarks | CLadder (Zhang et al., 2023), CounterBench (Jin et al., 2024), CORR2CAUSE (Wu et al., 2023) | Toy/synthetic domains; no clinical pharmacology |
| Pharmacological KGs | Hetionet (Himmelstein et al., 2017), DRKG (Zheng et al., 2021), PrimeKG (Chandak et al., 2023) | Static graphs; no counterfactual/modifier evaluation |
| PK/PD Modeling | SimCYP, GastroPlus, PK-Sim | Commercial; not benchmark datasets |
| LLM Structured Reasoning | CoT, ToT, GoT, Graph of Thoughts | No clinical DDI application |

---

## Ranked Research Opportunities

### 1. Phenocopying Isomorphism Benchmark (HIGH NOVELTY)
**Research Question:** Can models recognize pharmacologically equivalent causal graphs expressed with different surface forms (synonyms, edge reordering, granularity levels)?

**Existing Work:** 
- PIR test in MechanismTrace-DDI (oracle paraphrased baseline)
- No systematic phenocopying dataset in pharmacology

**Unsolved Gap:** 
- What surface variations preserve clinical meaning?
- How does model performance degrade with increasing paraphrase distance?

**Extension to MechanismTrace-DDI:**
- Generate 5-10 paraphrase variants per task using:
  - Synonym substitution (FDA ↔ DailyMed ↔ CPIC terminology)
  - Edge reordering (topological sort variants)
  - Granularity shifts (enzyme vs. isoform vs. pathway)
  - Evidence citation styles

**Required Data:** 
- Paraphrase generation pipeline (LLM-assisted + expert validation)
- 14 tasks × 10 variants = 140 additional evaluations

**Proposed Experiment:**
- Evaluate 5+ models on all variants
- Measure: mean score, variance, minimum score across variants
- Metric: **Phenocopying Robustness Score (PRS)** = min_variant_score / max_variant_score

**Expected Contribution:**
- First systematic phenocopying benchmark in clinical AI
- Quantifies "brittleness" of causal reasoning to surface form
- Directly actionable for model developers (robustness training target)

**Limitations:**
- Paraphrase quality requires expert validation
- Clinical equivalence judgment can be subjective

**Implementation Effort:** Medium (2-3 weeks for paraphrase generation + validation)

---

### 2. Counterfactual DAG Surgery Dataset (HIGH NOVELTY)
**Research Question:** Given a factual causal DAG and an intervention (drug swap, genotype change), can models correctly predict the counterfactual DAG structure?

**Existing Work:**
- CounterBench (textual counterfactuals in NLP)
- CLadder (rung 2/3 causal queries in synthetic graphs)
- No clinical counterfactual DAG dataset

**Unsolved Gap:**
- Current MechanismTrace-DDI only checks boolean `resolves_primary` + `residual_risk_remains`
- No ground truth counterfactual DAGs exist

**Extension to MechanismTrace-DDI:**
- Annotate full counterfactual DAG for each task:
  - Which edges are removed/added/modified by intervention?
  - Which physiological modifiers persist?
  - What is the new verdict?

**Required Data:**
- 14 tasks × (1 primary + 2 alternative) counterfactuals = 42 counterfactual DAGs
- Expert pharmacologist annotation (2-3 hours/task)

**Proposed Experiment:**
- Task: Given factual DAG + intervention description → predict counterfactual DAG
- Metric: **Counterfactual Edge Surgery Accuracy (CESA)** = |E_pred ∩ E_gold| / |E_pred ∪ E_gold|
- Compare: Boolean residual risk vs. full DAG surgery

**Expected Contribution:**
- First clinical counterfactual DAG dataset
- Enables fine-grained evaluation of interventional reasoning
- Bridges causal inference (do-calculus) with clinical DDI

**Limitations:**
- High annotation cost
- Counterfactual DAGs may have multiple valid forms

**Implementation Effort:** High (4-6 weeks for expert annotation)

---

### 3. Transporter vs. Enzyme Reasoning Disentanglement (HIGH CLINICAL RELEVANCE)
**Research Question:** Why do models exhibit "CYP fixation" — systematically missing transporter-mediated interactions?

**Existing Work:**
- MechanismTrace-DDI error taxonomy shows transporter blindness (OAT1/3, NKCC2, P-gp)
- No controlled experiment isolating transporter vs. enzyme reasoning

**Unsolved Gap:**
- Is it training data bias (more CYP literature)?
- Architectural (attention patterns)?
- Prompt framing?

**Extension to MechanismTrace-DDI:**
- Create matched task pairs:
  - Pair A: CYP-mediated DDI (e.g., Ketoconazole → CYP3A4 → Substrate)
  - Pair B: Transporter-mediated DDI (e.g., Cyclosporine → OATP1B1 → Statin)
  - Same clinical complexity, same graph depth

**Required Data:**
- 6-8 matched task pairs (transporter + CYP analogs)
- Balanced for: graph depth, modifier complexity, verdict type

**Proposed Experiment:**
- Evaluate models on matched pairs
- Measure: Transporter Bias Ratio (TBR) per model
- Ablation: Add "remember transporters" prompt prefix
- Ablation: Provide transporter fact sheet in context

**Expected Contribution:**
- Diagnoses root cause of transporter blindness
- Informs training data augmentation strategies
- Clinically critical (transporter DDIs often missed in practice)

**Limitations:**
- Requires careful task matching
- Transporter DDIs often have weaker clinical evidence

**Implementation Effort:** Medium (3-4 weeks for task pair design + validation)

---

### 4. Pharmacogenomic Phenocopying (NOVEL)
**Research Question:** Can models correctly propagate genotype → phenotype → dosing causal chains across different genes/drugs?

**Existing Work:**
- CPIC guidelines provide gene-drug-dosing mappings
- MechanismTrace-DDI has 4 PGx tasks (TASK-06, 11, 12, 13, 14)
- No systematic phenocopying test

**Unsolved Gap:**
- Models may memorize specific gene-drug pairs but fail on structural analogs
- E.g., CYP2D6 UM → codeine toxicity ≠ TPMT PM → azathioprine toxicity (different mechanism)

**Extension to MechanismTrace-DDI:**
- Create PGx phenocopying probe set:
  - Same causal template (Genotype → Enzyme Activity → Drug Exposure → Toxicity)
  - Different genes: CYP2D6, CYP2C19, CYP3A5, TPMT, UGT1A1, HLA-B*57:01, SLCO1B1
  - Test: Can model transfer reasoning from one PGx pair to another?

**Required Data:**
- 7+ PGx task templates (beyond current 5)
- Structural alignment of causal templates

**Proposed Experiment:**
- Few-shot: Provide 3 PGx examples → test on 4th
- Zero-shot: Test on unseen PGx pair
- Metric: **PGx Transfer Accuracy** = accuracy on held-out PGx task

**Expected Contribution:**
- Measures true causal reasoning vs. memorization
- Directly relevant to precision medicine AI

**Limitations:**
- Requires diverse PGx tasks with sufficient evidence

**Implementation Effort:** Medium-High (4-5 weeks for task creation)

---

### 5. Multi-Drug Polypharmacy Causal Graphs (HIGH CLINICAL RELEVANCE)
**Research Question:** Can models assemble causal graphs for 3+ concurrent drugs with interacting pathways?

**Existing Work:**
- All current benchmarks: 2-drug interactions
- Real patients: 5-15 concurrent medications

**Unsolved Gap:**
- Combinatorial explosion of pathways
- Pathway convergence/divergence
- Competing physiological modifiers

**Extension to MechanismTrace-DDI:**
- Design 3-5 drug scenarios:
  - Warfarin + Amiodarone + Simvastatin (CYP2C9 + CYP3A4 + P-gp)
  - Tacrolimus + Voriconazole + Furosemide (CYP3A + NKCC2 + GFR)
  - Lithium + Lisinopril + HCTZ + Naproxen (4-drug renal)

**Required Data:**
- 5-10 polypharmacy scenarios
- Expert-constructed ground truth DAGs (exponential complexity)

**Proposed Experiment:**
- Evaluate on increasing polypharmacy complexity (2, 3, 4, 5 drugs)
- Metric: **Polypharmacy Degradation Slope** = accuracy drop per added drug

**Expected Contribution:**
- First polypharmacy causal reasoning benchmark
- Addresses real-world clinical complexity

**Limitations:**
- Very high annotation complexity
- Ground truth may be uncertain for 4+ drug combos

**Implementation Effort:** Very High (8+ weeks)

---

### 6. PK/PD Quantitative Reasoning (MEDIUM NOVELTY)
**Research Question:** Can models predict quantitative exposure changes (AUC ratios, Cmax fold-change) from qualitative causal graphs?

**Existing Work:**
- MechanismTrace-DDI: qualitative edges only (INCREASES_EXPOSURE)
- FDA labels provide quantitative AUC ratios
- No benchmark for quantitative DDI prediction

**Unsolved Gap:**
- Qualitative "increases exposure" insufficient for dosing
- Models need to integrate: fm (fraction metabolized), inhibitor potency, dose

**Extension to MechanismTrace-DDI:**
- Add quantitative prediction to output schema:
  ```json
  "quantitative_prediction": {
    "victim_auc_ratio": 2.6,
    "confidence_interval": [2.1, 3.2],
    "dose_adjustment_factor": 0.4
  }
  ```

**Required Data:**
- Extract quantitative AUC ratios from FDA labels for all 14 tasks
- Define acceptable error margins (e.g., ±30%)

**Proposed Experiment:**
- Evaluate models on qualitative graph + quantitative prediction
- Metric: **Quantitative Prediction Error** = |pred - obs| / obs

**Expected Contribution:**
- Bridges qualitative causal reasoning and quantitative PK/PD
- Direct clinical utility (dose adjustment)

**Limitations:**
- Quantitative prediction requires PK knowledge beyond causal graph
- Models may hallucinate precise numbers

**Implementation Effort:** Medium (3-4 weeks for data extraction + schema)

---

### 7. Uncertainty Calibration for Structured Outputs (MEDIUM NOVELTY)
**Research Question:** Can models reliably express uncertainty in structured causal graph outputs?

**Existing Work:**
- Atomic probes collect confidence (0-100)
- Composed tasks: no confidence
- No calibration metric for graph-structured outputs

**Unsolved Gap:**
- Confidence on atomic facts ≠ confidence on composed graph
- How to calibrate edge-level vs. graph-level uncertainty?

**Extension to MechanismTrace-DDI:**
- Require confidence per edge + overall graph confidence
- Metric: **Graph Expected Calibration Error (G-ECE)**

**Required Data:**
- Modified output schema with per-edge confidence
- Calibration bins for edge confidence

**Proposed Experiment:**
- Collect confidence from models that support it (e.g., logprobs)
- Compute ECE at edge level and graph level
- Compare: atomic confidence vs. composed confidence

**Expected Contribution:**
- First calibration benchmark for structured clinical reasoning
- Enables risk-aware deployment

**Limitations:**
- Not all APIs provide logprobs
- Confidence elicitation methods vary

**Implementation Effort:** Low-Medium (2-3 weeks for schema + metrics)

---

### 8. Free-Text vs. Structured Output Equivalence (LOW NOVELTY)
**Research Question:** Does forcing structured JSON output degrade reasoning compared to free-text with post-hoc parsing?

**Existing Work:**
- MechanismTrace-DDI requires JSON output
- Many clinical LLMs trained for free-text
- No controlled comparison

**Unsolved Gap:**
- Schema constraints may limit model expression
- Post-hoc parsing introduces errors

**Extension to MechanismTrace-DDI:**
- Run same tasks with:
  - Condition A: Structured JSON output (current)
  - Condition B: Free-text → parse with json_repair
  - Condition C: Free-text → human annotation

**Proposed Experiment:**
- Compare scores across conditions
- Measure: parsing failure rate, score difference

**Expected Contribution:**
- Informs output format choice for clinical deployment

**Implementation Effort:** Low (1-2 weeks)

---

### 9. Temporal Causal Reasoning (FUTURE)
**Research Question:** Can models reason about time-dependent DDI mechanisms (induction vs. inhibition, auto-induction, delayed toxicity)?

**Existing Work:**
- All current tasks: steady-state interactions
- Real DDIs: time-course matters (e.g., carbamazepine auto-induction over weeks)

**Unsolved Gap:**
- No temporal DDI benchmark
- Requires dynamic causal graphs

**Extension:** Add time dimension to DAG edges (onset, peak, offset)

**Implementation Effort:** Very High (future work)

---

### 10. Adversarial Robustness to Clinical Misinformation (MEDIUM)
**Research Question:** How do models perform when clinical context contains common misconceptions (e.g., "grapefruit juice affects all statins")?

**Existing Work:**
- MechanismTrace-DDI fatal traps test unsafe recommendations
- No test for misinformation in input context

**Extension:**
- Inject common clinical myths into patient context
- Measure: does model propagate misinformation into causal graph?

**Implementation Effort:** Low-Medium (2-3 weeks)

---

## Novelty Assessment Summary

| Opportunity | Novelty | Clinical Relevance | Feasibility | Priority |
|-------------|---------|-------------------|-------------|----------|
| Phenocopying Isomorphism | ★★★★★ | High | Medium | **1** |
| Counterfactual DAG Surgery | ★★★★★ | High | Low | **2** |
| Transporter vs Enzyme Disentanglement | ★★★★☆ | Critical | Medium | **3** |
| PGx Phenocopying | ★★★★☆ | High | Medium | **4** |
| Polypharmacy Causal Graphs | ★★★★★ | Critical | Low | **5** |
| PK/PD Quantitative Reasoning | ★★★★☆ | High | Medium | **6** |
| Uncertainty Calibration | ★★★☆☆ | Medium | Medium | **7** |
| Free-Text vs Structured | ★★★☆☆ | Low | High | **8** |
| Adversarial Misinformation | ★★★☆☆ | Medium | Medium | **9** |
| Temporal Reasoning | ★★★★★ | High | Very Low | **Future** |

---

## Comparison to Prior Work

| Benchmark | Causal Graph | Modifiers | Counterfactual | Quantitative | Polypharmacy |
|-----------|--------------|-----------|----------------|--------------|--------------|
| RxSafeBench | ❌ | ❌ | ❌ | ❌ | ❌ |
| CLadder | ✅ (toy) | ❌ | ✅ (text) | ❌ | ❌ |
| CounterBench | ❌ | ❌ | ✅ (text) | ❌ | ❌ |
| **MechanismTrace-DDI** | ✅ | ✅ | ✅ (bool) | ❌ | ❌ |
| **+ Phenocopying** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **+ Counterfactual DAG** | ✅ | ✅ | ✅ (DAG) | ❌ | ❌ |
| **+ Transporter Disentanglement** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **+ PGx Phenocopying** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **+ Polypharmacy** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **+ PK/PD Quantitative** | ✅ | ✅ | ✅ | ✅ | ❌ |

**Conclusion:** MechanismTrace-DDI + top 3 extensions would create the most comprehensive clinical causal reasoning benchmark, with unique coverage of modifiers, counterfactuals, and surface-form robustness.

---

## Recommended Immediate Pursuit

1. **Phenocopying Isomorphism** (Opportunity 1) — Highest novelty/feasibility ratio; can be built on existing infrastructure
2. **Transporter vs Enzyme Disentanglement** (Opportunity 3) — Critical clinical gap; controlled experiment design straightforward
3. **Counterfactual DAG Surgery** (Opportunity 2) — Highest long-term impact; seek funding for expert annotation

---

*This assessment based on literature search covering: NeurIPS/ICML/ICLR 2020-2026 causal reasoning papers, AMIA/MEDINFO clinical AI proceedings, CPIC/FDA guidance documents, and pharmacological knowledge graph publications. Search terms: "causal reasoning benchmark LLM", "drug-drug interaction benchmark", "counterfactual reasoning evaluation", "pharmacological knowledge graph", "polypharmacy AI".*