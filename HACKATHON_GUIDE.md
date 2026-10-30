# micro1 Eval Hackathon: Complete Participant & Execution Guide

## Overview
* **Organizer:** micro1 & HackerRank
* **Core Goal:** Build an **Eval Benchmark** that identifies and exposes a blind spot in frontier AI models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5/2.0 Pro) within your area of domain expertise.
* **Duration:** 14,280 minutes (~10 Days)
* **Deadline:** **November 9, 2026, at 05:15 GMT (10:45 AM IST / Nov 8, 9:15 PM PT)**
* **Format:** Take-home challenge. You can log in, inspect, work locally, and submit anytime before the deadline.
* **Participation:** Solo participation only; 1 submission per participant.

---

## What is an "Eval"?
An eval is an automated test showing where AI models quietly fail. Frontier models can generate convincing answers in seconds, but fail when tasks demand:
1. Niche domain expertise.
2. Counter-intuitive edge cases.
3. Complex multi-step reasoning.
4. Exact precision where being "close" is completely wrong.

### The 3 Hallmarks of a Winning Submission:
1. **A Real Gap:** A problem an expert in your field can solve reliably, but current frontier models fail at (target failure rate: 60%–90%).
2. **A Rigorous Grader:** Clear expected answers with a deterministic or high-integrity scoring logic that avoids false positives and false negatives.
3. **Reproducibility:** A clean codebase where anyone can clone, run `pip install -r requirements.txt`, execute one command (e.g. `python run_eval.py`), and reproduce identical evaluation scores.

---

## Submission Checklist

### Question 1: File Upload (`.zip` file, max 50 MB)
Only code and small supporting data files. **No videos or gigabyte datasets inside the zip.**

Your zip file must include:
- [ ] `README.md` at root covering all 8 mandatory sections.
- [ ] `tasks/` (5 to 10 deeply engineered, expert-level scenarios).
- [ ] `graders/` (Scoring logic — automated code grading, unit test execution, or calibrated LLM judge).
- [ ] `run_eval.py` (One-command evaluation execution script).
- [ ] `results/` (Raw model outputs, scores, and timestamps from your actual run).
- [ ] `requirements.txt` or `pyproject.toml` (All dependencies pinned).
- [ ] `.env.example` (API key placeholders with NO actual secrets).

### Question 2: Subjective Text Response
In the HackerRank text box, submit:
1. **Short Description:** Domain, the gap identified, and key benchmark findings.
2. **Video Walkthrough Link:** Public URL (Loom, YouTube Unlisted, Google Drive).
   - Max 5 minutes.
   - Covers: Problem context, why models fail, how eval runs, and results.
   - You don't need to show your face; AI-generated voiceover is permitted.
3. **Public GitHub Repository Link:** (Highly recommended for transparency).

---

## Mandatory `README.md` Sections (Strict 8-Point Checklist)
Your `README.md` will be directly scored based on these 8 sections:
1. **Short description:** A few sentences on the domain, the gap you found, and your key finding.
2. **Video walkthrough link:** Direct link (Loom/YouTube/Drive) accessible without login restrictions.
3. **Domain and expertise:** Your domain and the specific real-world expertise this benchmark tests.
4. **What it tests and why it matters:** What the eval measures, who relies on this in production, and why AI failures here are dangerous or costly.
5. **Setup and run instructions:** Exact steps to run from a clean machine in 1 command, including environment variables, runtime, and cost.
6. **Models tested and results:** Model IDs (e.g., `gpt-4o-2024-08-06`, `claude-3-5-sonnet-20241022`, `gemini-1.5-pro-latest`), temperature, number of trials, and exact score table.
7. **Failure analysis:** Deep dive into the failure modes (e.g., hallucinated assumptions, pattern-matching shortcuts, off-by-one reasoning).
8. **Prior work and sources:** Any academic papers, official specifications, or existing benchmarks you referenced.

---

## Scoring Rubric (Out of 100 Points)
Submissions are evaluated on:
- **Eligibility & Integrity (Gatekeeper):** Original work, no leaked confidential data, runs cleanly.
- **Novelty & Severity of Gap (30%):** Is this a genuine blind spot or a cheap trick?
- **Grader Rigor (25%):** Is scoring deterministic and defensible? No false passes.
- **Reproducibility (20%):** Does the script run out of the box with clear instructions?
- **Analysis Depth (15%):** Quality of failure mode explanation in the README and video.
- **Clarity & Engineering Polish (10%):** Clean code structure, typing, error handling, CLI UX.
