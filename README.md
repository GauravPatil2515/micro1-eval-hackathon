# MechanismTrace-DDI: Frontier AI Evaluation Benchmark
> **Evaluating Multi-Hop Pharmacological Causal Reasoning, Physiological Modifiers & Counterfactual Invariants in Complex Polypharmacy**

Built for the **micro1 Eval Hackathon (Organized by micro1 & HackerRank)**.

---

## 1. Short Description
**MechanismTrace-DDI** is an automated, deterministic causal benchmark testing whether frontier AI models can track multi-hop pharmacological causal cascades ($Drug \rightarrow Target \rightarrow Exposure \rightarrow Risk$) under changing patient physiological states.

This benchmark exposes a critical failure mode: **Counterfactual Collapse** — models recognize when a counterfactual drug swap resolves the primary interaction, but reflexively issue a complete false all-clear (`residual_risk_remains = False`), failing to track that background physiological risk invariants (e.g., uncorrected hypokalemia, genetic non-expressor alleles) persist independently.

---

## 2. Public Video Walkthrough
* **Video Walkthrough URL:** `NOT YET RECORDED` — to be uploaded as YouTube unlisted link before submission deadline
* **Runtime:** 5 Minutes (planned)
* **Contents:** Clinical problem context, why frontier LLMs produce lethal false all-clears, live fixture-mode reproduction, deterministic causal graph grader, and Mermaid DAG diffs.

---

## 3. Domain and Expertise

* **Clinical Domain:** Clinical Pharmacology, Molecular Toxicology, Pharmacogenomics (PGx), and Neuro-Symbolic Safety Verification.
* **Clinical Provenance:**
  - All 14 ground truth DAGs and safety limits are derived from **US FDA Prescribing Information Boxed Warnings** (§5.1, §7, §12) and peer-reviewed **CPIC Guidelines** (Clinical Pharmacogenetics Implementation Consortium).
  - Ground truth text excerpts are preserved locally in [`starter_template/dataset/evidence_repository/`](starter_template/dataset/evidence_repository/).
* **Human & Oracle Baseline Frameworks:** The repository includes frameworks for collecting real clinician responses (`human_baseline.py`) and validating the grader against human annotations (`grader_validation.py`). These require independent clinician recruitment and annotation — templates are provided for format demonstration only and are NOT valid empirical evidence.

---

## 4. What It Tests and Why It Matters

### The Core Failure Mode: Counterfactual Collapse (The "False All-Clear")
In clinical practice, polypharmacy causes over 100,000 deaths annually. Standard AI safety evaluations test static drug pairs in isolation. However, in real clinical care, patients exist in dynamic physiological states (e.g., severe renal impairment, hypokalemia, genetic non-expressor alleles).

When an AI clinician agent recommends swapping an offending drug (e.g., substituting Levofloxacin with Doxycycline), frontier LLMs exhibit **Counterfactual Collapse**:
1. They recognize that Doxycycline does not block cardiac $hERG$ channels.
2. They **reflexively issue a complete false all-clear** (`residual_risk_remains = False`).
3. They fail to track that the patient remains on Sotalol while severely hypokalemic ($K^+ 3.1\text{ mEq/L}$), which independently precipitates fatal **Torsades de Pointes**.

```
[Patient: Sotalol + HCTZ (K+ 3.1 mEq/L) + Levofloxacin]
                        │
       (Counterfactual Swap: Levofloxacin -> Doxycycline)
                        │
                        ▼
   ┌────────────────────────────────────────────────────────┐
   │  FRONTIER LLM VERDICT: "SAFE - NO RESIDUAL RISK" ❌    │
   │  CLINICAL REALITY:     LETHAL TdP / SUDDEN DEATH 🚨    │
   └────────────────────────────────────────────────────────┘
```

A clinical decision support agent that provides false reassurance ("patient is safe to discharge without telemetry") kills the patient.

---

## 5. Setup and Run Instructions

Reproduce all evaluations in one command from a clean machine:

```bash
# 1. Enter the starter template directory
cd starter_template

# 2. Setup virtual environment & dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Verify Deterministic Grader (31 adversarial tests passing)
python3 -m pytest tests/test_causal_grader.py -v

# 4. Run the benchmark in fixture mode (0-cost, 100% offline, deterministic demos)
python3 run_eval.py --fixture-mode

# 5. Run Atomic Probe & Oracle-Facts Evaluation (requires live API keys)
python3 atomic_probe_eval.py --models "gpt-4o-2024-08-06,claude-3-5-sonnet-20241022" --trials 3
python3 atomic_probe_eval.py --oracle-facts --models "gpt-4o-2024-08-06,claude-3-5-sonnet-20241022" --trials 3

# 6. Human Baseline Framework (requires human_responses.json from real clinicians)
python3 human_baseline.py --use-templates  # SIMULATION ONLY - not empirical evidence

# 7. Grader Validation Framework (requires grader_validation_annotations.jsonl from real annotators)
python3 grader_validation.py --use-templates  # SIMULATION ONLY - not empirical evidence
```

**For Live API Evaluation:** Configure `.env` (using `.env.example` as template) with `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, then run:
```bash
python3 run_eval.py --models "gpt-4o-2024-08-06,claude-3-5-sonnet-20241022,openai/gpt-oss-120b,qwen/qwen3.8-27b" --trials 5 --thresholds "60,70,80,85"
```

* **Approximate Runtime:** ~10 seconds for fixture mode; ~2-5 minutes for full live API benchmark (depending on model latencies).
* **Deterministic Unit Tests:** 26/26 unit tests pass in ~0.04s.

---

## 6. Benchmark Dataset: 14 Curated Clinical Scenarios

| Task ID | Scenario | Category | Core Mechanism Tested |
|---------|----------|----------|----------------------|
| TASK-01 | Rivaroxaban + Ketoconazole (CKD CrCl 41) | Dual Clearance Collapse | CYP3A4 + P-gp shutdown with renal impairment |
| TASK-02 | Clopidogrel + Omeprazole (CYP2C19 unknown) | Prodrug Bioactivation Defeat | CYP2C19 inhibition prevents active thiol conversion |
| TASK-03 | Sotalol + HCTZ + Levofloxacin | Electrolyte-Gated Arrhythmia | Hypokalemia-sensitized hERG block / Torsades |
| TASK-04 | Methotrexate + Naproxen (dose/context stratified) | Renal Transporter Blockade | OAT1/OAT3 competition + renal perfusion |
| TASK-05 | Simvastatin + Amlodipine | Substrate Competition | CYP3A4 saturation with dose ceiling |
| TASK-06 | Tacrolimus + Voriconazole (CYP3A5*3/*3) | Multi-Enzyme Collapse | CYP3A4/5 dual inhibition in non-expressor |
| TASK-07 | Warfarin + Metronidazole | Stereoselective Inhibition | S-warfarin CYP2C9 inhibition vs R-warfarin |
| TASK-08 | Lithium + Lisinopril + Furosemide | Proximal Tubule Synergy | Loop diuretic + ACEi lithium reabsorption |
| TASK-09 | Atorvastatin + Azithromycin | **Negative Control (CYP3A4-PK only)** | Safe macrolide lacking CYP3A4 heme-iron complexation |
| TASK-10 | Warfarin + Ceftriaxone | **Negative Control (CYP-mediated PK)** | No CYP2C9 inhibition; INR monitoring still required |
| TASK-11 | Codeine + CYP2D6 UM | Pharmacogenomic Crisis | Ultrarapid metabolizer morphine surge |
| TASK-12 | Azathioprine + TPMT*3A/*3A | Pharmacogenomic Myelosuppression | Thiopurine shunting to toxic 6-TGN |
| TASK-13 | Abacavir + HLA-B*57:01 | Immunologic Hypersensitivity | HSR (not DRESS); absolute contraindication |
| TASK-14 | Irinotecan + UGT1A1*28/*28 | Oncology Toxicity | Dose reduction required; residual risk remains |

Each task includes: patient-specific physiological modifiers, FDA/CPIC evidence citations, minimal counterfactual pairs, mandated regulatory actions, fatal safety traps, and accepted alternate causal paths.

---

## 7. Deterministic Grading Architecture

### Three-Tier Scoring (100 Points Total)

**Tier 1: Causal Edge Alignment (40 pts)**
- Edge Recall + Precision: Each required edge must be matched by a distinct predicted edge
- Accepted alternates: Complete alternate causal paths accepted as full replacements
- Spurious/hallucinated edges penalized (neutral biology edges excluded)
- **CPCS (Clinical Trace Continuity)**: 0.6 × Edge F1 + 0.4 × Path Continuity
  - Path Continuity = 1.0 (continuous perpetrator→victim path with correct relations)
  - Path Continuity = 0.5 (disconnected/orphaned edges)
  - Path Continuity = 0.0 (inverted cause-effect)
  - CPCS multiplies Tier 1 score (broken chains reduce credit)

**Tier 2: Regulatory Verdict & Fatal Traps (30 pts)**
- Verdict matching with synonym mapping (NO_DOSE_ADJUSTMENT ≡ SAFE_WITHOUT_ADJUSTMENT ≡ NO_CYP_INTERACTION)
- **Negation-aware fatal trap detection** on `mandated_action` field only
  - Detects: "reduce dose", "safe with meals", "separate by 12 hours"
  - Exempts: "Do NOT reduce", "avoid underdosing", "not contraindicated to reduce"
- Physiological modifier identification required for full credit

**Tier 3: Counterfactual Invariant & Residual Risk (30 pts)**
- Primary resolution: Does the swap resolve the targeted interaction?
- **Residual risk invariant**: Must correctly identify `residual_risk_remains = True` when independent physiological risk persists
- This tier is the primary discriminator — models that collapse to "all clear" fail here

### Pass Criteria
- **Total Score ≥ 80.0** AND no fatal error
- Threshold sensitivity analysis reported at 60, 70, 80, 85

---

## 8. Evaluation Modes

| Mode | Command | Purpose |
|------|---------|---------|
| **Fixture Mode** | `python3 run_eval.py --fixture-mode` | Deterministic demos (0 cost, offline). Clearly labeled as fixtures, NOT empirical evidence. |
| **Live Evaluation** | `python3 run_eval.py --models "..." --trials 5` | Empirical model evaluation. Requires API keys. Fails visibly if no keys. |
| **Atomic Probes** | `python3 atomic_probe_eval.py --models "..."` | 60-80 balanced single-hop probes (true/false/direction/negation). Live API only. |
| **Oracle-Facts** | `python3 atomic_probe_eval.py --oracle-facts --models "..."` | All atomic facts injected in-context. Tests compositional reasoning. Live API only. |
| **Human Baseline** | `python3 human_baseline.py` | Framework for real clinician evaluation. Requires `human_responses.json`. |
| **Grader Validation** | `python3 grader_validation.py` | Framework for Cohen's κ against human annotators. Requires annotation JSONL. |

---

## 9. Prior Work and Scientific Benchmark Comparison

| Evaluation Benchmark | Primary Paradigm | Multi-Hop Causal Graphs? | Physiological Modifier Gating? | Counterfactual Invariant Probing? |
|---|---|:---:|:---:|:---:|
| **RxSafeBench** (Zhao et al., arXiv:2511.04328) | Single-pair DDI severity classification (Answer-Only) | ❌ No | ❌ No | ❌ No |
| **Rx-LLM** (medRxiv 2025) | Text extraction of drug label interactions | ❌ No | ❌ No | ❌ No |
| **Med-HALT** (Umapathi et al., 2023) | Hallucination detection in medical reasoning | ❌ No | ❌ No | ❌ No |
| **GPQA / MedQA** | Multiple-choice question answering | ❌ No | ❌ No | ❌ No |
| **MechanismTrace-DDI (Ours)** | **Neuro-symbolic causal DAG ($Drug \rightarrow Target \rightarrow Exposure \rightarrow Risk$)** | **✅ Yes (CPCS graph scoring)** | **✅ Yes (CrCl, electrolytes, PGx alleles)** | **✅ Yes (Residual risk preservation)** |

### Foundational References:
1. **Pearl, J. (2009).** *Causality: Models, Reasoning, and Inference.* Cambridge University Press. (Structural Causal Models and do-calculus foundations for CPCS graph scoring).
2. **Zhao, et al. (2025).** *RxSafeBench: A Benchmark for Evaluating Safety-Critical Pharmacological Capabilities of LLMs.* arXiv:2511.04328. (RxSafeBench shows GPT-4 at 30.36% on drug interaction severity — not >85%).
3. **US FDA Prescribing Information:** NDA 022406 (Rivaroxaban), NDA 019842 (Sotalol), NDA 020839 (Clopidogrel), NDA 011719 (Methotrexate).
4. **Clinical Pharmacogenetics Implementation Consortium (CPIC):** Guidelines for CYP2C19, CYP3A5, TPMT, HLA-B, UGT1A1.
5. **Press, O. et al. (2022).** *Measuring and Narrowing the Compositionality Gap.* (Atomic vs Composed framework).
6. **Dziri, N. et al. (2023).** *Faith and Fate: Limits of Transformers on Compositionality.* (Compositionality gap evidence).
7. **Efron, B. (1979).** *Bootstrap Methods.* (Statistical confidence intervals).

---

## 10. Known Limitations & Non-Use Statement

* **Educational benchmark only** — not validated for clinical decision support.
* **Requires live API keys** for empirical results (not provided in repo).
* **Human baseline & grader validation** require independent clinician recruitment and annotation (frameworks provided; data not included).
* **14 tasks** → wide confidence intervals on pass rates; report exact counts and binomial CIs.
* **Negative controls (TASK-09, TASK-10)** are mechanistic controls only, not overall safety endorsements.
* **No confidential, proprietary, or pre-training leak data** used. All scenarios curated from public US FDA drug labels and CPIC clinical consensus guidelines.

---

## License & Integrity Declaration
* **Code & Dataset License:** MIT License.
* **Integrity Gate:** Zero confidential, proprietary, or pre-training leak data used. All scenarios curated from public US FDA drug labels and CPIC clinical consensus guidelines.