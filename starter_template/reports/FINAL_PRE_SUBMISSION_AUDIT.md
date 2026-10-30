# MechanismTrace-DDI: Final Pre-Submission Technical & Scientific Audit Report

**Lead Benchmark Engineer & Scientific Validation Coordinator Review**  
**Hackathon Target:** micro1 Eval Hackathon (Organized by micro1 & HackerRank)  
**Audit Date:** October 31, 2026  
**Current Repository State:** Complete 8-task specification, causal DAG grader, normalizer, and baseline results (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`).

---

## Executive Summary & Gate Decision

| Audit Category | Status | Summary Finding |
|---|:---:|---|
| **Audit 1: Implementation & Repo Consistency** | ⚠️ Minor Issues | Code and schemas are fully functional, but evidence directory is unpopulated and normalizer misses common entity tokenizations. |
| **Audit 2: Scientific Correctness** | ⚠️ Refinements Needed | 5 tasks are rock-solid; 3 tasks (TASK-01, TASK-05, TASK-08) require pharmacokinetic and regulatory clarifications. |
| **Audit 3: Grader Rigor & Vulnerabilities** | 🛑 Critical Flaw | Normalizer splits entities with parentheticals; edge matching uses strict equality causing false negatives on valid paths; fatal trap matching can be tripped by negated explanations. |
| **Audit 4: Experimental Protocol** | ⚠️ Gaps | Single trials currently logged; needs 5 repeated runs with seed stability, token/cost tracking, CPCS, and atomic-composed breakdown. |
| **Audit 5: Roadmap & Prioritization** | ✅ Complete | Concrete 9-step execution sequence established. |

### **EXPLICIT AUDIT VERDICT: CONDITIONAL GO**
*The benchmark concept, causal DAG design, and baseline failure rates are exceptionally strong. However, live frontier evaluations (GPT-4o, Claude 3.5 Sonnet) must NOT be executed until the three grader edge-matching flaws and task-specific labeling nuances identified below are corrected. Running frontier models on the unpatched grader will produce artificial failures due to syntax/normalizer mismatch rather than true reasoning gaps.*

---

## Audit 1: Repository & Implementation Inspection

### 1. File Inventory and Verification
- `starter_template/dataset/tasks.json` (21,401 bytes): Contains 8 structured task objects. Verified valid JSON conforming to the schema.
- `starter_template/graders/causal_grader.py` (6,536 bytes): Implements 3-tier grading logic.
- `starter_template/graders/normalizer.py` (3,616 bytes): Contains entity and relation synonym mappings.
- `starter_template/run_eval.py` (14,550 bytes): Implements CLI harness, Groq/OpenAI/Anthropic dispatchers, and JSON logging.
- `starter_template/tests/test_causal_grader.py` (6,783 bytes): 4 pytest unit tests passing.
- `starter_template/dataset/evidence_repository/`: **CRITICAL GAP:** Directory exists but is completely empty (`sizeBytes: 4096`, 0 files). The referenced FDA label text files have not been materialized locally.

### 2. Discrepancies Between Code and Documentation
1. **Pass Threshold Inconsistency:** `README.md` and report documentation cite a pass threshold of 80%, but `causal_grader.py:L149` enforces `score >= 85.0`.
2. **Entity Normalizer Parenthetical Bug:** Raw model output inspection reveals models emit `"P-gp (ABCB1)"` or `"BCRP (ABCG2)"`. The normalizer in `normalizer.py` matches exact keys (`"p-gp"`, `"abcb1"`). It does NOT strip parenthetical annotations, causing `"P-gp (ABCB1)"` to fail normalization and default to uppercase `"P-GP (ABCB1)"`, which fails exact edge comparison against expected `"P-GP"`. This single bug caused an artificial failure on `TASK-01` in trial runs.
3. **Missing Intermediate Exposure Node in Prompts:** In `tasks.json`, expected causal paths are structured as:  
   `KETOCONAZOLE -> INHIBITS -> CYP3A4` and `CYP3A4 -> INCREASES_EXPOSURE -> RIVAROXABAN`.  
   Models frequently emit direct exposure edges: `KETOCONAZOLE -> INCREASES_EXPOSURE -> RIVAROXABAN`. The current grader rejects direct edges if intermediate hops are mandated, without a transitive closure or path continuity check.

---

## Audit 2: Scientific Correctness Audit (Scenario-by-Scenario)

| Task ID | Interacting Pair & Target Mechanism | Primary Evidence Citation & Section | Causal Direction | Patient Modifier | Expected Regulatory Action | Counterfactual Outcome | Verified Status / Clinician Flags |
|---|---|---|---|---|---|---|---|
| **TASK-01** | Rivaroxaban + Ketoconazole | US FDA Xarelto Label (NDA 022406) §7.1, §7.2, §12.3 | `Ketoconazole -> INHIBITS -> CYP3A4`, `P-gp`<br>`CYP3A4, P-gp -> INCREASES_EXPOSURE -> Rivaroxaban` | CrCl 41.2 mL/min (Moderate CKD) | `CONTRAINDICATED` (Avoid concomitant use) | Swap to Fluconazole: Primary contraindication resolved, but residual bleeding surveillance required. | **VERIFIED WITH CLINICAL REFINEMENT:** Xarelto label explicitly states combined P-gp + strong CYP3A inhibitors are avoided. However, the label phrasing is *"avoid concomitant use"*; the prompt must clarify that *"avoid"* and *"contraindicated"* are functionally synonymous in this regulatory tier. |
| **TASK-02** | Clopidogrel + Omeprazole | US FDA Plavix Boxed Warning & §7.1; CPIC 2022 | `Omeprazole -> INHIBITS -> CYP2C19`<br>`CYP2C19 -> BLOCKS_BIOACTIVATION -> Clopidogrel` | CYP2C19 genotype unknown; Post-PCI DAPT | `CONTRAINDICATED` (Avoid concomitant use) | Swap to Pantoprazole: Resolves interaction (minimal CYP2C19 inhibition). | **VERIFIED:** Rock-solid evidence. Active thiol metabolite AUC drops 40–45%; PRU significantly elevated. |
| **TASK-03** | Sotalol + HCTZ + Levofloxacin | US FDA Betapace §5.1; CredibleMeds List 1 | `Sotalol -> INHIBITS -> hERG`<br>`Levofloxacin -> PRODUCES_ADDITIVE_BLOCK -> hERG` | $K^+ 3.1\text{ mEq/L}$, $Mg^{2+} 1.4\text{ mg/dL}$ | `CONTRAINDICATED` (Electrolyte repletion + telemetry required) | Swap to Doxycycline: Antimicrobial QT liability resolved, but **residual proarrhythmic risk remains lethal** due to Sotalol + uncorrected hypokalemia. | **VERIFIED:** Excellent electrophysiological trap. Vandenberg et al. (2006) confirms hypokalemia increases blocker binding affinity and slows unbinding kinetics. |
| **TASK-04** | Methotrexate + Naproxen | US FDA Trexall §5.1, §7; DailyMed | `Naproxen -> COMPETITIVELY_BLOCKS -> OAT1, OAT3`<br>`OAT1, OAT3 -> INCREASES_EXPOSURE -> Methotrexate` | Borderline CrCl 48 mL/min; Mild dehydration | `CONTRAINDICATED` (Avoid concurrent NSAIDs; switch to Acetaminophen) | Swap to Acetaminophen: Spares OAT1/OAT3; resolves renal clearance block. | **VERIFIED:** FDA Boxed Warning documents fatal pancytopenia and severe enteritis. Methotrexate elimination is >80% active renal tubular secretion via OAT1/OAT3. |
| **TASK-05** | Simvastatin + Amlodipine | US FDA Simvastatin Safety Labeling (2011) §2.2 | `Amlodipine -> INHIBITS -> CYP3A4`<br>`CYP3A4 -> INCREASES_EXPOSURE -> Simvastatin` | Baseline CK 110 U/L; Normal CrCl | `DOSE_ADJUSTMENT_REQUIRED` (Cap Simvastatin at max 20 mg daily) | Dose reduction to 20 mg OR swap to Rosuvastatin: Completely resolves CYP3A4 substrate competition. | **SCIENTIFIC REFINEMENT REQUIRED:** In clinical practice, clinicians frequently switch to Rosuvastatin or Atorvastatin rather than keeping Simvastatin at 20 mg. Grader must accept BOTH dose ceiling at 20 mg AND statin class switch as fully correct actions. |
| **TASK-06** | Tacrolimus + Voriconazole | US FDA Prograf §7.1; US FDA Vfend §7.1 | `Voriconazole -> INHIBITS -> CYP3A4, CYP3A5`<br>`CYP3A4 -> INCREASES_EXPOSURE -> Tacrolimus` | CYP3A5*3/*3 (Non-expressor); Stable graft | `DOSE_ADJUSTMENT_REQUIRED` (Empiric 66% reduction to 1/3rd dose + daily TDM) | Dose reduction to 1/3rd: Resolves acute surge, but **residual volatility requires continuous TDM**. | **SCIENTIFIC REFINEMENT REQUIRED:** Ground truth currently lists `VORICONAZOLE -> INHIBITS -> CYP3A5`. While voriconazole inhibits both, in a CYP3A5*3/*3 non-expressor, CYP3A5 enzyme is virtually absent. The prompt should evaluate whether models recognize that CYP3A4 inhibition is the primary driver in non-expressors. |
| **TASK-07** | Warfarin + Metronidazole | US FDA Coumadin §7; US FDA Flagyl §7.1 | `Metronidazole -> STEREOSELECTIVELY_INHIBITS -> CYP2C9`<br>`CYP2C9 -> INCREASES_EXPOSURE -> S-Warfarin` | Baseline stable INR 2.5; Normal hepatic function | `DOSE_ADJUSTMENT_REQUIRED` (Empiric 30–50% Warfarin reduction + INR check at 48–72h) | Swap to non-interacting antibiotic: Clears metabolic inhibition, but residual infection/diet monitoring remains. | **VERIFIED:** Enantiomer distinction is completely validated. S-warfarin is 3–5x more potent than R-warfarin and cleared exclusively by CYP2C9. |
| **TASK-08** | Lithium + Lisinopril + Furosemide | US FDA Lithobid / Eskalith §7; Zestril §7.4 | `Furosemide -> INDUCES -> PROXIMAL_TUBULE_REABSORPTION`<br>`Lisinopril -> DECREASES_EXPOSURE -> GLOMERULAR_FILTRATION`<br>`PROXIMAL_TUBULE_REABSORPTION -> INCREASES_EXPOSURE -> Lithium` | $Na^+ 132\text{ mEq/L}$, CHF comorbidity | `DOSE_ADJUSTMENT_REQUIRED` (Empiric 50% Lithium reduction or avoid triple combination) | Dose reduction to 50%: Minimizes toxic accumulation, but **residual GFR impairment requires mandatory TDM**. | **SCIENTIFIC REFINEMENT REQUIRED:** The relationship verb `Lisinopril -> DECREASES_EXPOSURE -> GLOMERULAR_FILTRATION` in ground truth is biologically inverted in terminology. Lisinopril *decreases glomerular filtration*, which *increases lithium exposure*. The DAG schema must clearly demarcate physiological targets from pharmacokinetic exposure consequences. |

---

## Audit 3: Grader Rigor & Vulnerabilities Audit

### 1. Mathematical Score Bounds Check
- Max score calculation in `causal_grader.py`:
  - Tier 1 (Causal Edges): 40.0 pts
  - Tier 2 (Regulatory Action & Modifier): 20.0 (Verdict) + 10.0 (Modifier) = 30.0 pts
  - Tier 3 (Counterfactual Invariants): 10.0 (Primary Resolution) + 20.0 (Residual Risk) = 30.0 pts
  - Total Maximum: **100.0 pts**.
- Pass Threshold: Currently set to 85.0.

### 2. Fatal Flaws Identified in Grader Implementation

#### A. The String Inversion / Negation Vulnerability in Fatal Traps
In `causal_grader.py:L113-117`:
```python
full_text_lower = raw_response.lower()
for trap in gt.get("fatal_traps", []):
    if trap.lower() in full_text_lower:
        fatal_error = True
        reasons.append(f"FATAL SAFETY TRAP TRIGGERED: '{trap}'")
        break
```
**CRITICAL VULNERABILITY:** Substring search does not check context or negation.  
If a model writes:  
> *"Do NOT reduce rivaroxaban to 10 mg because dose reduction is contraindicated in dual clearance block,"*  
the grader flags `"reduce rivaroxaban to 10 mg"`, sets `fatal_error = True`, and wipes the model's score to 0!  
**Fix Required:** Fatal traps must only inspect the `regulatory_action.mandated_action` field, not the entire response text, and must use regex negation matching (e.g. negative lookbehind for `do not`, `avoid`, `never`).

#### B. Normalizer Token Truncation Bug
Models routinely output chemical names with biological identifiers in parentheses:
- `"P-gp (ABCB1)"` $\rightarrow$ Normalizer returns `"P-GP (ABCB1)"`, failing match against `"P-GP"`.
- `"CYP3A4 enzyme"` $\rightarrow$ Normalizer returns `"CYP3A4 ENZYME"`, failing match against `"CYP3A4"`.
- `"hERG channel"` $\rightarrow$ Normalizer returns `"HERG CHANNEL"`, failing match against `"HERG"`.  
**Fix Required:** Add pre-processing regex to strip parentheticals and trailing nouns (`channel`, `enzyme`, `protein`, `transporter`, `receptor`) before dictionary lookup.

#### C. Edge Disconnection & The Missing Causal Path Continuity Score (CPCS)
Currently, edge accuracy is computed as flat set overlap: $\frac{\text{matched edges}}{\text{expected edges}}$.  
A model that predicts two disconnected edges:
`Ketoconazole -> INHIBITS -> CYP3A4` and `P-gp -> INCREASES_EXPOSURE -> Rivaroxaban` gets 50% edge credit, even though its causal graph is completely broken (no link from Ketoconazole to P-gp or CYP3A4 to Rivaroxaban).

### 3. Proposed Causal Path Continuity Score (CPCS) Formulation
We propose augmenting flat edge accuracy with **CPCS** without disrupting the 40-point tier:
$$\text{CPCS} = \alpha \cdot \text{Edge Recall} + \beta \cdot \text{Path Continuity}$$
Where:
- $\text{Path Continuity} = 1.0$ if there exists at least one continuous directed path from Perpetrator $\rightarrow$ Modifier/Target $\rightarrow$ Victim Exposure.
- If the predicted graph contains orphaned nodes or disconnected edges, $\text{Path Continuity} = 0.5$.
- If cause and effect are inverted ($Victim \rightarrow Perpetrator$), $\text{Path Continuity} = 0.0$.
- Weights: $\alpha = 0.6, \beta = 0.4$.

---

## Audit 4: Experimental Protocol & Reproducibility Standard

To establish defensible frontier-model failure rates that cannot be dismissed by hackathon judges:

### 1. Model Evaluation Matrix

| Model Tier | Model Name | Exact Identifier | API Provider | Reasoning / Evaluation Role |
|---|---|---|---|---|
| **Frontier Closed Tier** | GPT-4o | `gpt-4o-2024-08-06` | OpenAI API | Industry standard multimodal frontier baseline. |
| **Frontier Closed Tier** | Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` | Anthropic API | State-of-the-art reasoning benchmark leader. |
| **Frontier Closed Tier** | Gemini 1.5 Pro | `gemini-1.5-pro-002` | Google AI Studio | Long-context medical reasoning frontier baseline. |
| **Open-Weight Baseline** | LLaMA 3.3 70B | `llama-3.3-70b-versatile` | Groq API / Local | High-performance open-weight clinical baseline. |
| **Open-Weight Baseline** | Qwen 2.5 72B / 27B | `qwen/qwen3.8-27b` | Groq API / Local | Demonstrates open-source reasoning behavior. |

### 2. Multi-Trial Statistical Rigor
- **Trial Count:** $N = 5$ repeated trials per model per task (Total: $5 \text{ models} \times 8 \text{ tasks} \times 5 \text{ trials} = 200 \text{ execution runs}$).
- **Parameters:** `temperature = 0.0`, `seed = 42` (pinned where API supports), `top_p = 1.0`, `max_tokens = 2048`.
- **Statistical Uncertainty:** Report mean task score with 95% bootstrap confidence intervals ($CI_{95}$), and compute trial-to-trial variance to measure model output stability.
- **Data Integrity:** Store every raw completion, prompt, and execution timestamp in `results/raw_runs/` accompanied by SHA-256 integrity hashes to prevent tampering claims.

### 3. Multi-Metric Reporting Dashboard
1. **Schema Validity Rate:** % of runs returning valid Pydantic JSON.
2. **Causal Edge Precision & Recall:** Directed relationship accuracy.
3. **Causal Path Continuity Score (CPCS):** Graph connectivity metric.
4. **Fatal Recommendation Rate (%):** Frequency of triggering contraindicated dosing actions.
5. **Counterfactual Consistency (%):** Accurate identification of residual risk under single-variable swaps.
6. **Atomic vs. Composed Gap:** Performance degradation between isolated pairwise questions vs. complex multi-modifier cases.

---

## Audit 5: Prioritized Implementation Roadmap

### Phase 1: Critical Bug Fixes & Grader Hardening (Immediate)
1. **Fix Normalizer Regex:** Strip parentheticals and descriptors (`(ABCB1)`, `channel`, `enzyme`) in `normalizer.py`.
2. **Fix Fatal Trap Negation:** Scope fatal trap scanning strictly to `regulatory_action.mandated_action` with regex negation checking (`do not`, `avoid`, `never`).
3. **Adjust Pass Threshold:** Align `causal_grader.py` and `README.md` to `80.0` points.
4. **Implement CPCS:** Add path continuity checking to `causal_grader.py`.

### Phase 2: Scientific & Ground-Truth Refinements
1. **Materialize Evidence Repository:** Populate `dataset/evidence_repository/` with verified plaintext excerpts of US FDA Prescribing Information and CPIC tables.
2. **Refine TASK-05 & TASK-08 Ground Truth:** Update accepted alternative actions in TASK-05 (statin class switch) and clarify physiological directionality in TASK-08.
3. **Add 2 Safe-Control Negative Tasks:** Introduce control scenarios (e.g., Atorvastatin + Azithromycin, or Warfarin + Ceftriaxone) to measure model false-alarm / over-warning rates.

### Phase 3: Benchmark Execution & Frontier Testing
1. **Multi-Model 5-Trial Evaluation:** Run automated evaluation across GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, and Groq baselines.
2. **Generate Statistical Summary:** Output `benchmark_summary.json` containing confidence intervals and failure archetype distributions.
3. **Generate Visual Graph Diff:** Implement terminal ASCII/Rich graph visualization comparing model DAG against FDA ground truth.

### Phase 4: Submission Packaging
1. **Update README.md:** Populate final score tables, failure analysis, and live API cost metrics.
2. **Record 5-Minute Video Walkthrough:** Follow the 5-stage pitch blueprint.
3. **Package Submission Archive:** Verify ZIP file size (<50 MB) and clean `.env.example`.

---

## Final Pre-Submission Gate Decision

### **VERDICT: CONDITIONAL GO**

#### Conditions to Fulfill Before Live Frontier Execution:
- [ ] Grader entity normalizer must handle parentheticals and trailing nouns.
- [ ] Fatal trap scanning must not penalize negated warnings.
- [ ] Evidence text files must be populated in `dataset/evidence_repository/`.
- [ ] Safe-control tasks must be included to prove the benchmark does not merely reward models that shout "contraindicated" to everything.

Once these surgical adjustments are completed, MechanismTrace-DDI will represent one of the most scientifically rigorous and technically defensible evaluation benchmarks in the entire competition.
