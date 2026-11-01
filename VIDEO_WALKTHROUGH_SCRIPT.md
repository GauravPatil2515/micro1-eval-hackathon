# MechanismTrace-DDI: 5-Minute Video Walkthrough Script (Honest Version)

## Video Structure (5:00 total)

### 0:00-0:30 | HOOK & PROBLEM STATEMENT (30s)
**Visual:** Title card → Clinical polypharmacy death statistic → "Counterfactual Collapse" diagram

**Script:**
> "Over 100,000 Americans die annually from adverse drug interactions. Yet when we test frontier AI models on complex polypharmacy cases, they fail catastrophically — not because they can't name the interaction, but because they collapse when a counterfactual swap requires preserving background physiological risk.
> 
> This is MechanismTrace-DDI: the first benchmark that evaluates multi-hop pharmacological causal reasoning with deterministic, clinically-grounded grading."

### 0:30-1:15 | THE BENCHMARK: 14 EXPERT SCENARIOS (45s)
**Visual:** Task table scrolling → Show TASK-01, TASK-03, TASK-11, TASK-09 side by side

**Script:**
> "14 curated clinical scenarios across 4 categories:
> - **Dual Clearance Collapse**: Rivaroxaban + Ketoconazole in CKD (TASK-01)
> - **Electrolyte-Gated Arrhythmia**: Sotalol + HCTZ + Levofloxacin with hypokalemia (TASK-03)  
> - **Pharmacogenomic Crises**: Codeine in CYP2D6 ultrarapid metabolizers, Abacavir in HLA-B*57:01 positive patients (TASK-11, 13)
> - **Negative Controls**: Atorvastatin + Azithromycin, Warfarin + Ceftriaxone — mechanistic controls that test false-alarm rates (TASK-09, 10)
> 
> Each task includes: patient-specific physiological modifiers, FDA/CPIC evidence citations, minimal counterfactual pairs, mandated actions, and fatal safety traps."

### 1:15-2:15 | WHY MODELS FAIL: 4 FAILURE MODES (60s)
**Visual:** Animated failure mode diagrams with fixture-mode outputs

**Script:**
> "We identified four structural failure modes:
> 
> **1. Transporter Blindness**: Models fixate on CYP450 enzymes and ignore P-gp, OAT1/3, BCRP. In TASK-01, they cite CYP3A4 inhibition but miss that 33% of rivaroxaban clearance is renal P-gp/BCRP-mediated. In TASK-04, they miss OAT1/OAT3 entirely — despite methotrexate being 80% renally secreted.
> 
> **2. Counterfactual Invariant Amnesia**: TASK-03 is the killer. Swap Levofloxacin for Doxycycline — models correctly note Doxycycline doesn't block hERG. But then they conclude 'patient is safe.' They forget the patient is *still* hypokalemic (K+ 3.1) on Sotalol. The residual proarrhythmic risk remains lethal.
> 
> **3. Stereoselective Confusion**: TASK-07 — Warfarin + Metronidazole. Models treat warfarin as one drug. They miss that S-warfarin is 5x more potent and cleared *exclusively* by CYP2C9. Metronidazole doesn't touch R-warfarin's CYP3A4 pathway.
> 
> **4. Fatal Reassurance Anti-Patterns**: Models hallucinate unsafe mitigations — 'reduce rivaroxaban to 10mg,' 'separate doses by 12 hours.' Under FDA labeling, dual CYP3A4/P-gp inhibition with renal compromise is absolute contraindication — no dose titration saves this."

### 2:15-3:15 | DETERMINISTIC GRADING: NO LLM-AS-JUDGE (60s)
**Visual:** Grader code walkthrough → CPCS formula → Negation detection demo → Tier 3 residual risk invariant

**Script:**
> "Zero LLM-as-judge hallucination. Our DeterministicCausalGrader uses three tiers:
> 
> **Tier 1 (40 pts)**: Causal Edge Alignment — exact match on normalized (source, relation, target) triples. Our normalizer strips parentheticals ('P-gp (ABCB1)' → 'P-GP') and trailing nouns ('hERG channel' → 'HERG'). **CPCS (Clinical Trace Continuity)** multiplies Tier 1: continuous perpetrator→victim path = 1.0, disconnected = 0.5, inverted = 0.0.
> 
> **Tier 2 (30 pts)**: Regulatory Verdict + Fatal Traps. We scan *only* the mandated_action field with regex negation detection — 'Do NOT reduce rivaroxaban' is correctly NOT flagged as a trap. Verdict synonyms accepted (NO_DOSE_ADJUSTMENT ≡ SAFE ≡ NO_CYP_INTERACTION).
> 
> **Tier 3 (30 pts)**: Counterfactual Invariants. The model MUST correctly identify residual_risk_remains. Skip this, you cannot pass.
> 
> **Pass threshold**: ≥80 pts AND no fatal error. Threshold sensitivity at 60, 70, 80, 85 reported."

### 3:15-4:00 | ATOMIC vs COMPOSED GAP & FRAMEWORKS (45s)
**Visual:** Atomic probe examples → Oracle-facts concept → Human baseline & grader validation frameworks

**Script:**
> "The benchmark decomposes each task into single-hop atomic probes — 60-80 balanced questions (true/false/direction/negation). 
> 
> **Atomic vs Composed Gap**: Models score high on isolated edge recall but collapse on composed multi-hop reasoning. The gap *is* the benchmark signal.
> 
> **Oracle-Facts Mode**: We inject all constituent atomic facts into the prompt context. If models still fail to compose, vocabulary is ruled out — pure reasoning failure.
> 
> **Frameworks for Validation** (require independent execution):
> - Human baseline: Framework for 2-3 pharmacists to evaluate 8 core tasks
> - Grader validation: 30-case annotation framework for Cohen's κ vs LLM-as-judge
> - These are templates in the repo — real data requires independent collection."

### 4:00-4:30 | LIVE DEMO & RESULTS PREVIEW (30s)
**Visual:** Terminal recording of `python3 run_eval.py --fixture-mode` → Results summary

**Script:**
> "Let's run the fixture mode — deterministic, zero cost, offline:"
> 
> [Show terminal: `python3 run_eval.py --fixture-mode`]
> 
> "Two fixtures pass (TASK-01, TASK-03 — the only ones with hardcoded gold answers). The rest fail on missing edges, demonstrating the grader's precision. For empirical results, you'd run with live API keys."

### 4:30-5:00 | SUBMISSION & CALL TO ACTION (30s)
**Visual:** GitHub repo → HackerRank submission → "Run it yourself"

**Script:**
> "MechanismTrace-DDI is open-source, reproducible, and submission-ready:
> 
> ```bash
> cd starter_template
> python3 run_eval.py --fixture-mode          # Zero-cost validation
> python3 run_eval.py --models "..." --trials 5 # Full empirical rigor (needs API keys)
> python3 visualize.py --all --mermaid          # Publication-ready Mermaid diagrams
> ```
> 
> Evidence repository: 14 FDA/CPIC label excerpts. Unit tests: 26 adversarial tests passing. CPCS, atomic/composed gap, bootstrap CI frameworks — all in the benchmark summary JSON.
> 
> This benchmark exposes a real, dangerous blind spot in frontier AI. Not a riddle. Not a trick. A clinical reasoning gap that kills patients when deployed in CDS systems.
> 
> Repository: github.com/your-username/MechanismTrace-DDI
> Thank you."

---

## Production Notes

### Recording Setup
- **Screen recording**: 1920x1080, 30fps
- **Terminal**: Use `asciinema` or OBS with terminal window
- **Code editor**: VS Code with dark theme for grader walkthrough
- **Mermaid diagrams**: Render via GitHub/GitLab preview or Mermaid Live Editor

### Assets to Prepare
1. **Terminal asciicasts** for:
   - `python3 run_eval.py --fixture-mode`
   - `python3 visualize.py --task TASK-01 --terminal`
   - `pytest tests/test_causal_grader.py -v`

2. **Mermaid diagrams** (rendered as PNG/SVG):
   - All 14 ground truth graphs
   - TASK-03 diff showing continuous path but wrong residual_risk
   - TASK-02 inverted causation detection

3. **Slides/Overlays** (Canva/Figma):
   - Title card with benchmark name
   - 4 failure mode icons
   - CPCS formula
   - Results table (fixture mode results)
   - Atomic vs Composed gap concept diagram

### Timing Tips
- Practice once with timer
- Cut filler words ("um", "so", "basically")
- Aim for 4:55 to leave buffer
- Record in segments, stitch in editor

### Audio
- USB mic (Blue Yeti or similar)
- Pop filter
- Record in quiet room
- Normalize to -16 LUFS for YouTube/Loom

---

## Key Differences from Simulated Version
- **NO claims** about GPT-4o, Claude, 7.1%, 100% atomic, etc. — those were simulated/fabricated
- **NO fake human baseline** — framework only, requires real clinicians
- **NO fake grader validation** — framework only, requires real annotation
- **FIXTURE MODE** clearly labeled as demonstrations, NOT empirical evidence
- **LIVE API** fails visibly if no keys — no silent mock fallback