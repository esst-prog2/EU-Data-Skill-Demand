# Regex Audit Report: Excel
**Evaluated on:** Snapshot Corpus (0 evaluated postings)
**Execution Time:** 11.156s

> ### Validation Verdict: ⛔ **REJECTED: WORKER TIMEOUT (ReDoS Risk)**

> ⛔ **SAFETY ABORT: WORKER TIMEOUT**
> Candidate regular expression evaluation exceeded the safety timeout threshold on an isolated worker process. Execution was aborted to prevent catastrophic backtracking (ReDoS).

## 1. Candidate Proposal Overview
- **Canonical Skill:** `Excel`
- **Validation Verdict:** `REJECTED_TIMEOUT`
- **Confidence Score:** `0.95`
- **Synthetic Tests Passed:** `NO`
- **ReDoS Safety Check:** `WARNINGS FLAGGED`

### Proposed Regular Expression
```regex
^(?:ms\s*excel|excel\b)(?!(?:in|at|within|as|with|\s+excel))
```

### Current Production Regular Expression
```regex
\b(?:ms\s*|microsoft\s*)?excel\b(?!\s+(?:in|at|within|as|with)\b)
```

### Technical Rationale
> The regex now uses a negative lookahead to exclude common verb phrases like 'excel in', 'excel at', etc. It also avoids matching 'excel' as part of other terms like 'excel pricing lists' by ensuring it's not followed by a space and 'excel' (which would be a false positive). The pattern is concise and avoids ReDoS risks.

## 2. Empirical Tag Alias Audit (FreeHire Native Platform Tags)
### Native Tag Alias Audit: Excel
**Evaluated Candidates:** 2 | **Supported:** 0 | **Unsupported (0 count):** 0 | **Conflicts:** 0

| Proposed Alias | Native Count | Net New Hits | Conflict | Audit Verdict | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `excel` | `0` | `0` | None | **ℹ️ EXISTING** | Alias is already registered for this canonical skill in skills_vocabulary.json. |
| `ms-excel` | `0` | `0` | None | **ℹ️ EXISTING** | Alias is already registered for this canonical skill in skills_vocabulary.json. |


## 3. ReDoS & Syntactic Safety Analysis
- ⚠️ **Safety Warning:** Corpus evaluation timed out after 10.0s. Process terminated to prevent catastrophic backtracking.

## 4. Synthetic Test Suite Results
### Independent Domain Synthetic Suite (Positives & Confounders)
| Test Phrase | Expected | Actual | Status | Type | Note |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `Advanced Microsoft Excel modeling for corporate financial forecasts.` | `True` | `False` | **❌ FAIL** | `positive` | Explicit 'Microsoft Excel' with modeling context. |
| `Strong command of MS Excel (pivot tables, VLOOKUP, XLOOKUP).` | `True` | `False` | **❌ FAIL** | `positive` | Abbreviated 'MS Excel' followed by technical spreadsheet features. |
| `Automating spreadsheet workflows using Excel VBA and macros.` | `True` | `False` | **❌ FAIL** | `positive` | Compound technical usage ('Excel VBA'). |
| `Proficient in SQL, Python, and Excel for business analytics.` | `True` | `False` | **❌ FAIL** | `positive` | Standalone 'Excel' in standard analytics tool list. |
| `Building executive dashboards with Power BI and Excel.` | `True` | `False` | **❌ FAIL** | `positive` | Excel alongside complementary BI tool. |
| `Candidates should excel in communication and leadership skills.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Verbal usage ('excel in communication'). |
| `We are looking for individuals who excel at analytical problem solving.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Verbal usage ('excel at problem solving'). |
| `Engineers who excel within cross-functional distributed teams.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Verbal usage ('excel within teams'). |
| `Demonstrated ability to excel as a technical team lead.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Verbal usage ('excel as a team lead'). |
| `Software engineers who excel with complex microservice architectures.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Verbal usage ('excel with architectures'). |
| `Proficiency with Microsoft Office suite (Word, PowerPoint, Outlook).` | `False` | `False` | **✅ PASS** | `negative_distractor` | Office suite mention without explicit Excel skill requirement. |
| `Experience maintaining cloud spreadsheets in Google Workspace.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Generic spreadsheet reference not establishing Microsoft Excel. |

### Proposal-Declared Test Cases
**Positive Cases (Must Match):**
- `❌ FAIL`: 'Microsoft Excel'
- `✅ PASS`: 'Excel VBA'
- `❌ FAIL`: 'Advanced Excel modeling'
- `✅ PASS`: 'Excel for data analysis'
- `✅ PASS`: 'Excel in analytical tools'

**Negative Cases (Must Reject):**
- `❌ FAIL`: 'excel in communication'
- `❌ FAIL`: 'excel at analytical problem solving'
- `❌ FAIL`: 'excel within cross-functional teams'
- `❌ FAIL`: 'excel as a team lead'
- `❌ FAIL`: 'excel with complex architectures'

## 5. Corpus Posting-ID Differential Impact
| Metric | Count | Description |
| :--- | :---: | :--- |
| **Current Hits** | `0` | Postings matched by production regex |
| **Candidate Hits** | `0` | Postings matched by candidate regex |
| **Shared Hits** | `0` | Postings agreed upon by both rules |
| **Net Difference** | `+0` | Net detection change |
| **Current-Only (Lost)** | `0` | Postings detected by current but dropped by candidate |
| **Candidate-Only (New)** | `0` | New postings captured exclusively by candidate |

## 6. Human-Confirmed Benchmark Validation
> ℹ️ **GATING ACTIVE:** Blind benchmark holdout evaluation was skipped because this candidate was rejected during earlier validation (Verdict: `REJECTED_TIMEOUT`). This preserves holdout integrity and avoids misleading performance metrics.

## 8. Identified Risks & Expert Review Decision
### Identified False Positive Risks
- ⚠️ excel pricing lists

### Cases Requiring Human Decision
- 🔍 excel pricing lists

---
*Audit generated by offline llm_regex_audit package. Production vocabulary is unchanged.*