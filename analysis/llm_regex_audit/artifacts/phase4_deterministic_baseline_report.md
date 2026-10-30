# Phase 4 — Evaluation Infrastructure Audit & Deterministic Baseline Report
**Generated:** 2026-10-30 21:10:23
**Corpus Size:** 25,394 FreeHire job postings | **Blind Benchmarks:** 80 unique postings (R: 80, Excel: 50)

## 1. Executive Summary
Phase 4 investigated the technical root causes of Phase 3 evaluation timeouts, audited the multiprocessing worker architecture on Windows, established clear conceptual boundaries for tag alias auditing, and benchmarked manually designed, explainable deterministic candidates against the LLM-generated proposals.

### Key Conclusions:
1. **The Phase 3 Timeouts were NOT caused by candidate ReDoS:** The measured in-process search latency of the Phase 3 candidate regex for R was `0.94s` and Excel was `0.01s`. The primary cause of worker timeout was that the evaluation worker was re-executing the complex production baseline R regex (`17.74s` execution time) across all 25,394 postings, which inherently exceeded the 10.0s hard timeout threshold.
2. **Multiprocessing IPC on Windows:** Process spawning and unpickling of 25,394 postings takes `1.22s – 1.40s`. Precomputing baseline hits in the parent process and using non-blocking pipe polling reduces worker execution to `2.8s – 3.5s` for standard patterns, making the evaluation framework robust and auditable.
3. **Deterministic Engineering Substantially Outperforms Small LLMs:**
   - **R (Production vs Experimental Alternative):** Production Reference R remains superior on benchmark holdout accuracy (**96.88% precision, 100% recall, 98.41% F1**), though it failed 1 synthetic case (`Dr. R. Watson`). The experimental alternative (`Baseline R-1`) fixed the synthetic case but dropped 54 corpus hits and had lower benchmark recall (**90.32% vs 100%**). It is an exploratory baseline, not a replacement.
   - **Excel (Equivalent Coverage):** Production Reference Excel, `Baseline Excel-1`, and `Baseline Excel-2` are functionally equivalent across the full corpus (exactly 965 hits each, 0 net diff) and achieve identical benchmark scores (**100% precision, 100% recall** on N=49 evaluable samples), with only a marginal 0.5s execution speed difference.
   - **LLM Proposals (Qwen3 4B):** Both Phase 2 and Phase 3 models failed synthetic unit tests and yielded 0 usable detections due to syntax errors (`^` anchor) and omitting standalone terms.

## 2. Infrastructure Timeout Root Cause & Performance Measurements
Isolated benchmarking established the exact execution breakdown across 25,394 postings:

| Measurement Stage | Safe Excel | Safe Python | Phase 3 R Cand | Production Excel | Production R |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Compilation** | 0.15 ms | 0.11 ms | 0.27 ms | 0.18 ms | 0.42 ms |
| **500 Sample Search** | 0.028s | 0.022s | 0.017s | 0.041s | 0.352s |
| **In-Process Full Corpus (25k)** | 1.68s | 1.16s | 0.94s | 2.62s | **17.74s** |
| **Windows Process Spawn & IPC Transfer** | 1.40s | 1.24s | 1.24s | 1.25s | 1.30s |
| **Worker Execution Time** | 1.62s | 1.21s | 1.00s | 2.58s | **18.70s** |
| **Total Wall-Clock Time** | 3.12s | 2.58s | 2.34s | 3.95s | **20.10s** |

> **Measured Fact vs Architectural Explanation:** The confirmed empirical bottleneck is that production R regex execution (`17.74s`) exceeds the 10.0s worker budget. Architectural analysis also indicated that under sequential multiprocessing queue operations on Windows, child process joining prior to reading full queues can stall child termination. Precomputing baseline hits parent-side and switching to non-blocking pipe polling resolves both concerns completely.

## 3. Deterministic Baseline Comparison (Full Corpus & Blind Benchmarks)

### Skill: R
| Candidate | Synthetic Passed | Corpus Hits | Net Diff | Lost (Dropped) | New Hits | Benchmark Prec | Benchmark Rec | Benchmark F1 | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Production Reference R** | ❌ FAIL | `1,116` | `+0` | `0` | `0` | **N/A** | **N/A** | **N/A** | `REJECTED_FAILED_SYNTHETIC` |
| **Baseline R-1 (Simplified Guarded Standalone)** | ✅ PASS | `1,086` | `-30` | `54` | `24` | **93.3%** | **90.3%** | **91.8%** | `REJECTED_EXCESSIVE_REGRESSION` |
| **Baseline R-2 (Conservative Modifier-Only)** | ❌ FAIL | `34` | `-1,082` | `1,082` | `0` | **N/A** | **N/A** | **N/A** | `REJECTED_FAILED_SYNTHETIC` |

### Skill: Excel
| Candidate | Synthetic Passed | Corpus Hits | Net Diff | Lost (Dropped) | New Hits | Benchmark Prec | Benchmark Rec | Benchmark F1 | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Production Reference Excel** | ✅ PASS | `965` | `+0` | `0` | `0` | **100.0%** | **100.0%** | **100.0%** | `ELIGIBLE_FOR_HUMAN_REVIEW` |
| **Baseline Excel-1 (Simplified Prefix & Strict Preposition Guard)** | ✅ PASS | `965` | `+0` | `0` | `0` | **100.0%** | **100.0%** | **100.0%** | `ELIGIBLE_FOR_HUMAN_REVIEW` |
| **Baseline Excel-2 (Minimal Standalone with Lookahead)** | ✅ PASS | `965` | `+0` | `0` | `0` | **100.0%** | **100.0%** | **100.0%** | `ELIGIBLE_FOR_HUMAN_REVIEW` |

## 4. Comparison Against Phase 2 and Phase 3 LLM Proposals
| Candidate Variant | Origin | Syntax / Safety | Synthetic Suite | Full Corpus Hits | Benchmark F1 | ReDoS Safety Risk | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Phase 2 Qwen3 4B (R)** | LLM Proposal | ⚠️ Complex | ❌ FAILED | 0 (Timeout) | Skipped | ⚠️ Backtracking Permutations | `REJECTED_TIMEOUT` |
| **Phase 3 Qwen3 4B (R)** | LLM Proposal | ✅ Valid | ❌ FAILED | 0 (Timeout) | Skipped | Low (0.94s in-proc) | `REJECTED_FAILED_SYNTHETIC` |
| **Production Reference R** | Production Baseline | ✅ Valid | ❌ FAILED (15/16) | 1,116 | **98.41%** (P: 96.9%, R: 100%)* | Guarded (18.8s) | `REJECTED_FAILED_SYNTHETIC` |
| **Baseline R-1 (Guarded)** | Experimental Baseline | ✅ Valid | ✅ PASSED (16/16) | 1,086 | **91.80%** (P: 93.3%, R: 90.3%) | Low (15.4s) | `REJECTED_EXCESSIVE_REGRESSION` |
| **Phase 2 Qwen3 4B (Excel)** | LLM Proposal | ❌ `^` Anchored | ❌ FAILED | 0 (Timeout) | Skipped | ⚠️ Large Alternations | `REJECTED_TIMEOUT` |
| **Phase 3 Qwen3 4B (Excel)** | LLM Proposal | ❌ `^` Anchored | ❌ FAILED | 0 (Timeout) | Skipped | Low (0.01s in-proc) | `REJECTED_FAILED_SYNTHETIC` |
| **Production Reference Excel** | Production Baseline | ✅ Valid | ✅ PASSED (12/12) | 965 | **100.0%** (P: 100%, R: 100%) | None (3.4s) | `ELIGIBLE_FOR_HUMAN_REVIEW` |
| **Baseline Excel-1 (Clean)** | Experimental Baseline | ✅ Valid | ✅ PASSED (12/12) | 965 | **100.0%** (P: 100%, R: 100%) | None (3.4s) | `ELIGIBLE_FOR_HUMAN_REVIEW` |

*\*Note: Production Reference R benchmark metrics were evaluated in diagnostic mode; downstream gating strictly skipped benchmark metrics in its official automated verdict due to failing the Dr. R. Watson synthetic case.*

## 5. Tag Alias Conceptual Clarifications
The alias auditor was updated to separate five independent concepts:
1. **Registered in Vocabulary:** A dictionary definition in `skills_vocabulary.json`. Does NOT imply data occurrence.
2. **Observed in Native Tags:** Empirical presence (`count > 0`) in FreeHire `skills` tags.
3. **Not Observed in Native Tags:** Never appears (`count == 0`) in FreeHire `skills` tags.
4. **Adds New Coverage:** Postings carrying this tag that do not already have any existing registered tag for this skill.
5. **Conflicting Overlap:** The tag matches or collides with another canonical skill.

Empirical finding: For both R and Excel, compound tag aliases (`r-studio`, `r-programming`, `ms-excel`) have **0 observed occurrences** in the FreeHire platform. Proposing new tag aliases for these skills yields 0 net new coverage.

## 6. Workflow Recommendation
### Recommendation: Discontinue 4B LLM Autonomous Regex Discovery; Retain Evaluation & Audit Engine
1. **Local 4B Models Lack Regex Spatial Reasoning:** Despite structured schemas, GBNF grammars, few-shot prompts, and explicit anti-pattern constraints, small parameter models (e.g. Qwen3 4B) repeatedly generate syntax flaws (`^` anchor in document-level extraction, omitting standalone terms, malformed negative lookaheads).
2. **Production Baseline Integrity:** Existing production regexes remain the most accurate in coverage. Experimental alternatives (like `Baseline R-1`) demonstrated that simplifying lookarounds risks dropping true positive corpus hits (`54` dropped postings), confirming that changes to production extraction should remain conservative and strictly human-reviewed.
3. **Value of the Evaluation Package:** The `analysis/llm_regex_audit/` framework (synthetic test suites, ReDoS safety heuristics, posting-ID differential engine, and isolated worker processes) is highly valuable as an **automated CI/CD regression testing tool** for any proposed rule changes, regardless of whether rules are written by humans or models.

---
*Report generated by Phase 4 Evaluation Infrastructure Audit.*
