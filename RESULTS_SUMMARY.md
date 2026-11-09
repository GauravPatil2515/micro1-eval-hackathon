# MechanismTrace-DDI: Benchmark Results & Empirical Evaluation Summary
> **Official Empirical Evaluation Report for the micro1 Eval Hackathon (micro1 & HackerRank)**  
> **Repository:** [https://github.com/GauravPatil2515/micro1-eval-hackathon](https://github.com/GauravPatil2515/micro1-eval-hackathon)  
> **Date:** November 2026 | **Benchmark Version:** 1.0 (CPCS_v2 Engine)

---

## Executive Summary

**MechanismTrace-DDI** evaluates multi-hop pharmacological causal reasoning, physiological modifier gating, and counterfactual risk invariants in complex polypharmacy. While existing benchmarks (e.g. RxSafeBench, Rx-LLM) test static single-hop drug pairs where models can pass via memorized lookups, MechanismTrace-DDI evaluates whether models can trace the complete biochemical cascade:

$$\text{Drug} \longrightarrow \text{Molecular Target/Enzyme/Transporter} \longrightarrow \text{Exposure/PK Dynamic} \longrightarrow \text{Clinical Risk}$$

### Key Empirical Findings
- **Frontier Open Architecture (Hermes 4 405B):**
  - **Mean Score:** **38.27 / 100** (95% Bootstrap CI: `[27.90, 48.01]`)
  - **Strict Pass Rate ($\ge 80/100$):** **0.0% (0 / 14 tasks passed)** (95% Wilson CI: `[0.0%, 21.5%]`)
  - **Relaxed Pass Rate ($\ge 60/100$):** **28.57% (4 / 14 tasks passed)** (95% Wilson CI: `[11.7%, 54.6%]`)
  - **Mean Causal Edge Accuracy:** **15.5%** (95% Bootstrap CI: `[6.0%, 25.6%]`)
  - **Mean CPCS_v2 Graph Completeness:** **0.126** (95% Bootstrap CI: `[0.043, 0.220]`)
- **Deterministic Grader Integrity:**
  - **Unit Test Suite:** **37 / 37 tests passing (100%)** in 0.06 seconds.
  - **Perfect Oracle:** **100.0 / 100** (100% pass rate).
  - **Paraphrased Oracle (Accepted Synonyms):** **93.77 / 100** (100% pass rate).

---

## 1. Full 14-Task Empirical Matrix (Hermes 4 405B)

All 14 clinical scenarios are derived from US FDA Prescribing Information Boxed Warnings (§5.1, §7.1, §12) and peer-reviewed CPIC guidelines.

| Task ID | Clinical Scenario | Regulatory Action | Hermes Score | Edge Acc | CPCS_v2 | Primary Observed Failure Mode |
|:---:|---|:---:|:---:|:---:|:---:|---|
| **TASK-01** | Rivaroxaban + Ketoconazole (CKD CrCl 41 mL/min) | `AVOID_CONCOMITANT_USE` | **30.0 / 100** | 50.0% | 0.500 | **Transporter Blindness:** Omitted P-gp edge; missed dual elimination shutdown. |
| **TASK-02** | Clopidogrel + Omeprazole (CYP2C19 Unknown) | `AVOID_CONCOMITANT_USE` | **32.9 / 100** | 33.3% | 0.275 | **Causal Inversion:** Inverted relationship between CYP2C19 and prodrug thiol metabolite. |
| **TASK-03** | Sotalol + HCTZ + Levofloxacin ($K^+ 3.1\text{ mEq/L}$) | `CONTRAINDICATED` | **60.0 / 100** | 0.0% | 0.000 | **Counterfactual Collapse:** Falsely cleared risk after antibiotic swap despite persistent hypokalemia. |
| **TASK-04** | Methotrexate + Naproxen (Borderline CrCl) | `AVOID_CONCOMITANT_USE` | **32.3 / 100** | 25.0% | 0.200 | **Transporter Blindness:** Omitted active renal OAT1/OAT3 tubular secretion blockade. |
| **TASK-05** | Simvastatin + Amlodipine (Regulatory Dose Cap) | `DOSE_ADJUSTMENT_REQUIRED` | **54.4 / 100** | 33.3% | 0.333 | **Metabolite Blindness:** Failed to trace active simvastatin hydroxy acid surge under CYP3A4 saturation. |
| **TASK-06** | Tacrolimus + Voriconazole (CYP3A5*3/*3 Non-Expressor) | `DOSE_ADJUSTMENT_REQUIRED` | **65.8 / 100** | 50.0% | 0.383 | **Missing Secondary Edge:** Omitted voriconazole $\rightarrow$ CYP3A5 inhibition in non-functional allele context. |
| **TASK-07** | Warfarin + Metronidazole (Stereoselective Clearance) | `DOSE_ADJUSTMENT_REQUIRED` | **40.4 / 100** | 25.0% | 0.075 | **Stereoselective Blindness:** Confused potent S-warfarin (CYP2C9) with weak R-warfarin (CYP3A4/1A2). |
| **TASK-08** | Lithium + Lisinopril + Furosemide | `DOSE_ADJUSTMENT_REQUIRED` | **30.0 / 100** | 0.0% | 0.000 | **Physiological Mechanism Omission:** Missed loop diuretic-induced proximal tubule sodium-mimic reabsorption. |
| **TASK-09** | Atorvastatin + Azithromycin (Mechanistic Negative Control) | `NO_DOSE_ADJUSTMENT` | **20.0 / 100** | 0.0% | 0.000 | **Alert Fatigue Over-Flagging:** Hallucinated direct toxic CYP3A4 inhibition for a non-interacting macrolide. |
| **TASK-10** | Warfarin + Ceftriaxone (Gut Flora Depletion Pathway) | `DOSE_ADJUSTMENT_REQUIRED` | **0.0 / 100** | 0.0% | 0.000 | **Microbiome Pathway Blindness:** Missed antibiotic-mediated vitamin K intestinal flora depletion and INR surge. |
| **TASK-11** | Codeine + CYP2D6 Ultrarapid Metabolizer (*1/*1xN) | `CONTRAINDICATED` | **40.0 / 100** | 0.0% | 0.000 | **Bioactivation Omission:** Missed `REQUIRES_FOR_BIOACTIVATION` edge producing life-threatening morphine toxicity. |
| **TASK-12** | Azathioprine + TPMT Deficiency (*3A/*3A) | `CONTRAINDICATED` | **10.0 / 100** | 0.0% | 0.000 | **Enzyme Shunt Omission:** Missed `COMPETITIVELY_BLOCKS` edge shunting 6-MP to lethal bone marrow 6-TGN. |
| **TASK-13** | Abacavir + HLA-B*57:01 Screening | `CONTRAINDICATED` | **60.0 / 100** | 0.0% | 0.000 | **Immunologic Target Omission:** Omitted peptide repertoire alteration binding to HLA-B*57:01 antigen cleft. |
| **TASK-14** | Irinotecan + UGT1A1*28 Polymorphism | `DOSE_ADJUSTMENT_REQUIRED` | **60.0 / 100** | 0.0% | 0.000 | **Metabolite De-Glucuronidation Omission:** Missed carboxylesterase activation to SN-38 and clearance defect. |

---

## 2. Quantitative Failure Taxonomy

From the empirical evaluation of Hermes 4 405B across all 14 tasks, errors were categorized using a deterministic taxonomy:

```
Total Identified Failure Incidents: 84
├── Missing Causal Hops (Partial Edge Recall):       39 (46.4%)
├── Hallucinated / Shortcut Edges:                  14 (16.7%)
├── Enzyme Blindness (CYP450 specific):              12 (14.3%)
├── Counterfactual Collapse (False All-Clear):       6 ( 7.1%)
├── Regulatory Verdict Mismatches:                   5 ( 6.0%)
├── Transporter Blindness (P-gp, OAT1, OAT3):        4 ( 4.8%)
├── Stereoselective Blindness (R vs S Warfarin):     3 ( 3.6%)
└── Physiological Modifier Ignored:                  1 ( 1.2%)
```

### The 4 Major Structural Failure Modes

1. **Counterfactual Collapse (The "False All-Clear"):**
   When presented with an alternative drug swap (e.g., swapping Levofloxacin to Doxycycline in TASK-03), the model recognizes that the antibiotic is no longer blocking cardiac $hERG$ channels. However, it reflexively flips `residual_risk_remains = False`, ignoring the background patient state (uncorrected hypokalemia $K^+ 3.1\text{ mEq/L}$ on Sotalol), leaving the patient in fatal Torsades de Pointes risk.
2. **Transporter Blindness (CYP Fixation):**
   Models routinely default to Cytochrome P450 enzymes while entirely omitting active transport proteins (**P-gp**, **OAT1**, **OAT3**), despite transporters accounting for $\ge 33\%$ to $80\%$ of systemic clearance in Rivaroxaban (TASK-01) and Methotrexate (TASK-04).
3. **Shortcut Hallucinations:**
   Rather than tracing $Drug \rightarrow Enzyme \rightarrow Exposure \rightarrow Toxicity$, models hallucinate direct shortcuts ($Drug_A \rightarrow Toxicity \rightarrow Drug_B$), bypassing molecular mechanisms entirely.
4. **Microbiome & Metabolite Blindness:**
   In non-CYP interactions, such as Ceftriaxone altering gut flora synthesis of Vitamin K (TASK-10) or prodrug conversion failures (Clopidogrel, Codeine), models struggle to represent non-hepatic metabolic steps.

---

## 3. Grader Robustness & Calibration Metrics

### Causal Path Completeness Score (CPCS_v2) Formulation
$$\text{CPCS\_v2} = 0.65 \times F_1(\text{Edges}) + 0.35 \times \text{Continuity}_{\text{weighted}} - \text{CyclePenalty}_{\text{conditional}}$$

- **Path-Length Weighting:** Multi-hop paths are weighted by physiological length, avoiding artificial penalization of granular multi-step chains.
- **Conditional Cycle Penalty:** Tarjan's Strongly Connected Components algorithm detects circular reasoning ($A \rightarrow B \rightarrow A$) and only penalizes when cycles intersect gold causal nodes.
- **Residual Risk Ledger:** Invariant validation decouples target resolution from patient background vulnerability.

### Oracle Calibration Benchmarking
| Oracle Configuration | Mean Score | Pass Rate | Status |
|---|:---:|:---:|:---:|
| **Perfect Gold Oracle** (Primary Edges) | **100.0 / 100** | **100.0%** | Passed (Zero Grader False Negatives) |
| **Paraphrased Gold Oracle** (Accepted Synonyms) | **93.77 / 100** | **100.0%** | Passed (Robust to Clinical Paraphrasing) |

---

## 4. Reproducibility

Anyone can reproduce these exact findings in a single terminal session:

```bash
# Clone and enter repo
git clone https://github.com/GauravPatil2515/micro1-eval-hackathon.git
cd micro1-eval-hackathon/starter_template

# Install pinned dependencies
pip install -r requirements.txt

# Verify deterministic unit tests (37/37 passing)
pytest tests/test_causal_grader.py -v

# Verify oracle baselines (100.0/100 and 93.77/100)
python3 oracle_baseline.py

# Run failure taxonomy analysis across empirical runs
python3 failure_taxonomy.py

# Run statistical bootstrap analysis
python3 graders/stats_bootstrap.py

# Generate complete 14-task Mermaid visual DAG diffs
python3 visualize_dag_diff.py
```

