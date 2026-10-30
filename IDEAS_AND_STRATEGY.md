# Winning Ideas & Benchmark Strategy

## Why Do Most Evals Fail?
1. **The Model Already Scores 90%+:** If GPT-4o or Claude 3.5 Sonnet already solves the tasks, there's no benchmark value.
2. **Subjective "LLM-as-a-judge" Hallucinations:** When an LLM grades another LLM with loose criteria, it often gives passing scores to flawed or hallucinated answers.
3. **Cheap "Riddle" or "Trick" Questions:** micro1 explicitly notes: *"It should be a real limitation, not a trick question."*

---

## 4 High-Scoring Domain Ideas

### Track A: Software Concurrency, Memory & Async Edge Cases (Recommended)
* **The Gap:** Frontier LLMs excel at basic async/await syntax, but catastrophically fail at subtle concurrency bugs (e.g. asyncio event loop starvation, thread-safety violations in shared mutable structures, signal handling during non-reentrant syscalls, or Go channel deadlocks under specific buffer capacity).
* **The Tasks (5–8 Scenarios):**
  - Provide a seemingly working async Python/Go service with an undetected race condition or event loop blocking call.
  - Ask the model to identify the bug, write the patch, and verify safety.
* **Deterministic Grader:**
  - Run the model's generated fix against a dedicated stress test with race-condition detection (`pytest-asyncio` with high concurrency simulation or thread sanitizer). If it deadlocks or drops events, it fails automatically.
* **Why it wins:** 100% objective, code-verified, zero false passes.

---

### Track B: PostgreSQL / Database Isolation & Lock Contention Pitfalls
* **The Gap:** LLMs write standard SQL queries well, but fail when asked to resolve subtle multi-transaction isolation anomalies (e.g. Write Skew in Repeatable Read, Phantom Reads, Lock Upgrade deadlocks in Postgres, or Advisory Lock lifecycle leakage).
* **The Tasks (5–8 Scenarios):**
  - Concrete financial ledger / seat booking / balance transfer transactions executing simultaneously.
  - Require the model to write SQL/PLpgSQL transactions that guarantee 100% correctness without deadlocking or allowing balance overdrafts under Concurrent Repeatable Read.
* **Deterministic Grader:**
  - Spin up a test database or run a simulated transaction sequence in Python with concurrent workers testing race conditions.

---

### Track C: Web Security / API Authorization Logic Bypasses
* **The Gap:** LLMs know textbook vulnerabilities (SQL injection, basic XSS), but fail on complex authorization & token exchange logic (e.g., OAuth 2.0 PKCE downgrade attacks, JWT Algorithm Confusion with asymmetric public keys, IDOR with compound tenant IDs).
* **The Tasks (5–8 Scenarios):**
  - Code review / patch challenge where standard linters pass, but a domain security architect immediately spots an authorization flaw.
* **Deterministic Grader:**
  - Automated test harness that sends exploit payloads to the model-secured implementation.

---

### Track D: FinTech & Accounting Regulations (Multi-Jurisdiction Tax & Ledger)
* **The Gap:** Tax law, cross-border VAT/GST rules, or compound interest ledger calculations have strict legal edge cases that general LLMs blur or generalize.
* **The Tasks (5–10 Scenarios):**
  - Complex case studies with exact numbers and multi-step tax treaty rules.
* **Deterministic Grader:**
  - Strict numeric/formula evaluation checking exact financial figures and cited statute clauses.

---

## Benchmark Design Blueprint

```
micro1-eval-hackathon/
│
├── README.md                      # Complete 8 mandatory sections
├── requirements.txt               # e.g., openai, anthropic, google-genai, pydantic, rich
├── .env.example                   # API keys template
├── run_eval.py                    # Main evaluation CLI runner
│
├── dataset/
│   └── tasks.json                 # 5 to 10 structured challenge definitions
│
├── graders/
│   ├── base.py                    # Base grader interface
│   ├── code_sandbox_grader.py     # Deterministic code execution / unit tests
│   └── test_suites/               # Unit tests run against model outputs
│
└── results/
    ├── raw_runs.json              # Raw responses from candidate models
    └── summary_report.md          # Formatted comparison tables & charts
```
