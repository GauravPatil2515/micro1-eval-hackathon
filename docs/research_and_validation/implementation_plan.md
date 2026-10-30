# MechanismTrace-DDI: Scientific Redesign & Implementation Plan
**Frontier AI Evaluation Benchmark for Multi-Hop Pharmacological Reasoning**  
*Competition: micro1 Eval Hackathon (Deadline: November 9, 2026)*

---

## 1. Goal Description

This plan establishes a scientifically rigorous, defensible, and reproducible research plan for **MechanismTrace-DDI**, directly resolving the six critical vulnerabilities identified in the initial review:
1. **Clinical Ground-Truth Inaccuracies:** Replacing ambiguous or misquoted labeling (such as the Rivaroxaban + Clarithromycin eGFR error) with verified, versioned FDA Prescribing Information, DailyMed records, and CPIC guidelines.
2. **Superficial Difficulty vs. Format Constraint:** Shifting the evaluation from broad textbook essays to **evidence-linked causal graph reconstruction, counterfactual perturbation consistency, and multi-source contradiction detection**.
3. **Flawed Grader Vulnerability:** Replacing brittle keyword and anti-pattern matching with a **Deterministic Causal Path & Evidence Evaluator** that verifies entity attribution, edge directionality, intermediate causal hops, and evidence citation integrity.
4. **Weak Pilot Sample & Missing Frontier Evidence:** Establishing an 8-task stratified benchmark tested across commercial frontier APIs (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 1.5/2.0 Pro) alongside local/open-weight models over multiple repeated runs with exact seeds.
5. **Separation of Scientific Mechanism vs. Clinical Policy:** Explicitly decoupling (a) biochemical mechanism correctness, (b) evidence/regulatory interpretation, and (c) clinical action appropriateness.
6. **Defensible Strategic Positioning:** Elevating MechanismTrace-DDI beyond conventional 2-drug classification benchmarks (RxSafeBench, Rx-LLM, MARD) by testing multi-variable physiological interaction cascades that cannot be resolved via memorized pairwise tables.

---

## 2. User Review Required

> [!IMPORTANT]
> **Key Ground-Truth Corrections Applied to Pilot Scenarios:**
> - **M01 (Rivaroxaban Cascade Redesign):** Replaced Clarithromycin with **Ketoconazole/Itraconazole** (unequivocal, black-and-white FDA Section 7.1 contraindication: combined strong CYP3A + P-gp inhibitor increasing Rivaroxaban AUC by >160%) or paired Rivaroxaban with **Erythromycin in Cockcroft-Gault CrCl <50 mL/min** (where the FDA label explicitly mandates avoidance). We will not use the flawed Clarithromycin eGFR claim.
> - **Cockcroft-Gault CrCl Standard:** All renal drug dosing scenarios will explicitly supply age, sex, weight (kg), and serum creatinine (mg/dL) alongside the calculated CrCl, eliminating eGFR/CrCl ambiguity.
> - **M02 (Clopidogrel + PPI):** Decoupled pharmacodynamic active-metabolite inhibition from clinical stent thrombosis (which is probabilistic, not universal). The grader will reward models that identify the intermediate surrogate marker ($PRU$ increase) while properly qualifying clinical event risk.

> [!WARNING]
> **Hardware & API Requirements:**
> Live frontier testing will require candidate model API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`). For zero-cost local execution and reproducibility checks, the harness maintains deterministic replay logs and mock fallback execution.

---

## 3. The 4 Distinct Benchmark Capabilities (Scientific Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MECHANISMTRACE-DDI ARCHITECTURE                      │
├────────────────────────────────┬───────────────────────────────────────┤
│  Capability 1: Causal Trace    │  Capability 2: Physiological Modifiers │
│  - Multi-hop biochemical hops  │  - Renal CrCl / Hepatic Child-Pugh     │
│  - Enzyme & Transporter fluxes │  - Serum Electrolytes (K+, Mg2+)       │
├────────────────────────────────┼───────────────────────────────────────┤
│  Capability 3: Counterfactuals │  Capability 4: Evidence Contradiction │
│  - Single-variable mutation    │  - Discordant labeling (FDA vs EMA)   │
│  - Invariant preservation      │  - Missing PGx genotype uncertainty    │
└────────────────────────────────┴───────────────────────────────────────┘
```

1. **Multi-Hop Pharmacological Mechanism Reconstruction:**  
   The model must trace: $Drug_A \rightarrow [Inhibits/Induces] \rightarrow Target/Transporter \rightarrow [\Delta Clearance/Exposure] \rightarrow Drug_B \rightarrow Clinical\_Risk$.
2. **Causal Attribution Across Physiological Modifiers:**  
   Evaluating whether models recognize when non-drug patient variables (CrCl < 50 mL/min, $K^+ < 3.5\text{ mEq/L}$, CYP2C19 *2/*2 loss-of-function) gate or multiply an otherwise benign exposure.
3. **Counterfactual Consistency (Single-Variable Mutations):**  
   Testing whether replacing a perpetrator drug (e.g. Omeprazole $\rightarrow$ Pantoprazole; Levofloxacin $\rightarrow$ Doxycycline) selectively updates only the affected causal path while correctly preserving unresolved background risks.
4. **Contradiction Detection & Grounded Uncertainty:**  
   Presenting cases with incomplete pharmacogenomic data or conflicting regional labels (e.g., FDA vs. EMA recommendations) and testing whether the model identifies the conflict rather than hallucinating false certainty.

---

## 4. Evidence-Linked Causal Graph Grader (The Grader Redesign)

To solve the keyword-grading vulnerability, candidate models will be required to return a structured causal claim graph:

```json
{
  "causal_graph": [
    {
      "source": "perpetrator_drug",
      "target": "enzyme_or_transporter",
      "relation": "INHIBITS | INDUCES | SUBSTRATE_OF",
      "evidence_id": "REF_01"
    },
    {
      "source": "enzyme_or_transporter",
      "target": "victim_exposure",
      "relation": "INCREASES_AUC | DECREASES_AUC | BLOCKS_ACTIVATION",
      "evidence_id": "REF_02"
    }
  ],
  "physiological_gate": {
    "modifier_present": true,
    "parameter": "CrCl | K_SERUM | CYP2C19_GENOTYPE",
    "clinical_impact": "TRANSFORMS_TO_CONTRAINDICATION | AMPLIFIES_ARRHYTHMIA"
  },
  "counterfactual_analysis": {
    "proposed_substitute": "drug_name",
    "resolves_interaction": true,
    "unresolved_residual_risks": ["risk_1"]
  },
  "uncertainties_or_contradictions": [
    "description of missing patient data or conflicting labeling"
  ]
}
```

### Grader Verification Pipeline:
- **Graph Topology Check:** Compares the predicted directed graph against the gold-standard causal DAG using exact edge matching (Entity $\times$ Relation $\times$ Target).
- **Attribution Guard:** Verifies that enzymes/transporters are attributed to the exact perpetrator (prevents inverted causation).
- **Three-Tier Scoring:**
  - $S_{mech}$ (0–40 pts): Mechanical path accuracy (CYP, transporters, metabolites).
  - $S_{reg}$ (0–30 pts): Regulatory/labeling fidelity (FDA/EMA/CPIC citations and contraindication tiers).
  - $S_{cf}$ (0–30 pts): Counterfactual validity and residual risk retention.

---

## 5. The 8 Validated Benchmark Scenarios (Curated Dataset)

| Task ID | Domain / Interaction | Core Pharmacological Mechanism | Patient Modifier | Counterfactual & Negative Control | Versioned Evidence Source |
|---|---|---|---|---|---|
| **TASK-01** | **Rivaroxaban + Ketoconazole** | Strong dual CYP3A4 + P-gp inhibition causing >160% AUC spike | Moderate renal impairment (CrCl 45 mL/min) | Swap to **Fluconazole** (moderate inhibitor: requires risk/benefit analysis, not absolute contraindication) | FDA Xarelto Label §7.1, DailyMed 2026 |
| **TASK-02** | **Clopidogrel + Omeprazole** | Mechanism-based CYP2C19 suicide inhibition blocking active thiol metabolite | CYP2C19 *1/*2 Intermediate Metabolizer | Swap to **Pantoprazole** (mitigated); Control: **Ticagrelor** (not CYP2C19 prodrug) | FDA Drug Safety Comm 2011; CPIC 2022 |
| **TASK-03** | **Sotalol + HCTZ + Fluoroquinolone** | Additive $I_{Kr}$ (hERG) pore blockade | Hypokalemia ($3.1\text{ mEq/L}$) + Hypomagnesemia ($1.4\text{ mg/dL}$) | Swap to **Doxycycline** (clears antibiotic QT risk, but sotalol + hypokalemia remains dangerous) | CredibleMeds List 1; Vandenberg 2006 |
| **TASK-04** | **Methotrexate + NSAID (Naproxen)** | Inhibition of renal OAT1/OAT3 and P-gp secretion causing toxic MTX accumulation | Elderly patient with dehydration (CrCl 35 mL/min) | Swap to **Acetaminophen** (spares renal OAT clearance); Control: low-dose vs high-dose MTX | FDA Trexall Prescribing Info; EMA MTX SmPC |
| **TASK-05** | **Simvastatin + Amlodipine** | CYP3A4 substrate competition elevating Simvastatin lactone AUC ($>2\times$) | Genetic variant SLCO1B1 (OATP1B1 uptake transporter) | Dose cap at 20 mg daily OR swap to **Rosuvastatin** (minimal CYP3A4 involvement) | FDA Simvastatin Safety Labeling 2011; CPIC 2022 |
| **TASK-06** | **Tacrolimus + Voriconazole** | Potent CYP3A4/5 and P-gp inhibition causing nephrotoxic calcineurin inhibitor surge | Post-renal transplant patient on stable trough target | Mandated empiric 66%–75% Tacrolimus dose reduction with therapeutic drug monitoring (TDM) | CPIC Tacrolimus/CYP3A5 Guideline; Astellas Prograf Label |
| **TASK-07** | **Warfarin + Metronidazole** | Stereo-selective CYP2C9 inhibition of S-warfarin active enantiomer | Baseline INR 2.3 | Control: R-warfarin vs S-warfarin metabolism; INR spike within 48–72h | Coumadin Label §7; Holbrook et al., *Chest* 2012 |
| **TASK-08** | **Lithium + Lisinopril + Furosemide** | ACE-inhibitor + loop diuretic altering proximal tubule sodium reabsorption $\rightarrow$ toxic Li+ retention | Stage 3 CKD with hyponatremia ($Na^+ = 131\text{ mEq/L}$) | Swap ACEi/Diuretic vs mandatory serum lithium monitoring | FDA Eskalith Label; British National Formulary (BNF) |

---

## 6. Implementation Workflow & Milestones

### Phase 1: Ground Truth & Evidence Codification
- Formulate the 8 reference causal DAGs with explicit node/edge schemas and cited section texts from FDA/CPIC.
- Save to `starter_template/dataset/pharmacology_tasks.json`.

### Phase 2: Causal Graph & Invariant Grader (`graders/evaluator.py`)
- Implement `GraphMatcher` comparing model causal outputs against expected DAGs.
- Implement `CounterfactualValidator` checking invariant preservation.
- Implement `SafetyPenalty` punishing false reassurances or dangerous misattributions.

### Phase 3: Benchmark Harness Execution (`run_eval.py`)
- Adapt `runner.py` from TigerGraph and `openrouter.py` from GearShift to support:
  - Multi-provider calls (Groq, OpenAI, Anthropic, Gemini).
  - Pinned seeds, `temperature=0.0`, structured schema prompts.
  - Multi-run consistency testing (3 trials per task).
  - Rich CLI dashboard logging latency, cost, and edge-accuracy breakdowns.

### Phase 4: Baseline Benchmarking & Evaluation Logging
- Run evaluation across available models:
  - Local/Open-weight: `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`.
  - Frontier APIs (when keys provided): `gpt-4o`, `claude-3-5-sonnet`, `gemini-1.5-pro`.
- Generate timestamped run artifacts in `results/`.

### Phase 5: Hackathon Documentation Package
- Write `README.md` fulfilling all 8 mandatory hackathon sections.
- Document failure analysis, prior-work comparisons, and setup commands.

---

## 7. Verification Plan

### Automated Testing
```bash
# 1. Run unit test suite on the new deterministic causal grader
pytest starter_template/graders/test_evaluator.py -v

# 2. Run benchmark harness dry-run with mock models (zero API cost)
python3 starter_template/run_eval.py --dry-run --tasks starter_template/dataset/pharmacology_tasks.json

# 3. Execute live benchmark against baseline models with 3 repeated trials
python3 starter_template/run_eval.py --models openai/gpt-oss-120b,qwen/qwen3.8-27b --trials 3
```

### Manual Verification
- Review generated `results/benchmark_run_*.json` to verify:
  1. No model scores 100% due to causal edge precision and counterfactual residual risk traps.
  2. Latency, tokens, and cost are calculated accurately.
  3. Grader logs exact reasons for edge, modifier, or counterfactual failures.
