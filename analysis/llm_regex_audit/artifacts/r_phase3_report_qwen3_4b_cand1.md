# Regex Audit Report: R
**Evaluated on:** Snapshot Corpus (0 evaluated postings)
**Execution Time:** 11.441s

> ### Validation Verdict: ⛔ **REJECTED: WORKER TIMEOUT (ReDoS Risk)**

> ⛔ **SAFETY ABORT: WORKER TIMEOUT**
> Candidate regular expression evaluation exceeded the safety timeout threshold on an isolated worker process. Execution was aborted to prevent catastrophic backtracking (ReDoS).

## 1. Candidate Proposal Overview
- **Canonical Skill:** `R`
- **Validation Verdict:** `REJECTED_TIMEOUT`
- **Confidence Score:** `0.95`
- **Synthetic Tests Passed:** `NO`
- **ReDoS Safety Check:** `WARNINGS FLAGGED`

### Proposed Regular Expression
```regex
r\b(?:\s*programming|\s*scripting|\s*lang|\s*language|\s*studio)
```

### Current Production Regular Expression
```regex
\b[Rr]\s*(?:programming|scripting|studio|lang|language)\b|(?<!\.)(?<!-)(?<!\b[A-Za-z]/)(?<!\b[A-Za-z]\.\s)(?:(?<![\(\[])\bR\b|(?<=[\(\[])\bR\b(?!\s*[\)\]]))(?!\s*&)(?!\.\s*\d)(?!\.[A-Za-z])(?!\.\s*[A-Z]\.)(?!-\d)(?!/\d)(?![\$€£])
```

### Technical Rationale
> The regex isolates standalone 'r' followed by optional whitespace and one of the technical context modifiers (programming/scripting/lang/language/studio). It avoids false positives from R&D, A/R, hardware models, etc. by using word boundaries and excluding common distractors through context.

## 2. Empirical Tag Alias Audit (FreeHire Native Platform Tags)
### Native Tag Alias Audit: R
**Evaluated Candidates:** 5 | **Supported:** 0 | **Unsupported (0 count):** 2 | **Conflicts:** 0

| Proposed Alias | Native Count | Net New Hits | Conflict | Audit Verdict | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `r-programming` | `0` | `0` | None | **ℹ️ EXISTING** | Alias is already registered for this canonical skill in skills_vocabulary.json. |
| `r-scripting` | `0` | `0` | None | **❌ UNSUPPORTED (0)** | Alias never appears in native FreeHire skill tags (0 observed occurrences). |
| `r-lang` | `0` | `0` | None | **ℹ️ EXISTING** | Alias is already registered for this canonical skill in skills_vocabulary.json. |
| `r-language` | `0` | `0` | None | **ℹ️ EXISTING** | Alias is already registered for this canonical skill in skills_vocabulary.json. |
| `r-studio` | `0` | `0` | None | **❌ UNSUPPORTED (0)** | Alias never appears in native FreeHire skill tags (0 observed occurrences). |


## 3. ReDoS & Syntactic Safety Analysis
- ⚠️ **Safety Warning:** Corpus evaluation timed out after 10.0s. Process terminated to prevent catastrophic backtracking.

## 4. Synthetic Test Suite Results
### Independent Domain Synthetic Suite (Positives & Confounders)
| Test Phrase | Expected | Actual | Status | Type | Note |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `Proficient in Python and R for statistical data modeling.` | `True` | `False` | **❌ FAIL** | `positive` | Standard list of data science languages (Python and R). |
| `Required skills: SQL, R, Tableau, and Git.` | `True` | `False` | **❌ FAIL** | `positive` | Standalone R in a comma-separated technical skill list. |
| `Strong background in R programming and Bayesian inference.` | `True` | `True` | **✅ PASS** | `positive` | Explicit 'R programming' phrase. |
| `Experience building analytical dashboards in RStudio and tidyverse.` | `True` | `False` | **❌ FAIL** | `positive` | Canonical R environment and ecosystem package mention. |
| `Statistical analysis with R (ggplot2, dplyr, caret).` | `True` | `False` | **❌ FAIL** | `positive` | R followed by parenthetical library specifications. |
| `Experience deploying statistical models in R/Shiny.` | `True` | `False` | **❌ FAIL** | `positive` | Compound R/Shiny application mention. |
| `Expertise in Python/R scripting.` | `True` | `True` | **✅ PASS** | `positive` | Slash-delimited programming language variant (Python/R). |
| `Leading our European R&D initiatives across product lines.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Research and Development (R&D) abbreviation. |
| `Responsible for processing invoices in our A/R department.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Accounts Receivable (A/R) accounting abbreviation. |
| `Hardware diagnostics for server revision Model R-200.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Hardware model revision identifier (Model R-200). |
| `Tracking serial batch R/1204 in warehouse inventory.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Logistics batch number with slash and digits (R/1204). |
| `Refer to the System build R.10 release notes.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Software build version number (R.10). |
| `Compensation package: R$ 8,000 per month gross.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Currency symbol prefix (Brazilian Real, R$). |
| `The applicant must maintain an active R.N. nursing license.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Medical qualification abbreviation (Registered Nurse, R.N.). |
| `Please submit your CV to Dr. R. Watson in administration.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Human initial preceding surname (Dr. R. Watson). |
| `We need energetic developers who excel in fast-paced teams.` | `False` | `False` | **✅ PASS** | `negative_distractor` | Ordinary English verb (excel in) containing no R skill. |

### Proposal-Declared Test Cases
**Positive Cases (Must Match):**
- `❌ FAIL`: 'Proficiency in data analysis tools and languages such as Python or R'
- `❌ FAIL`: 'Experience with data extraction/wrangling * Experience using analytic tools such as: Databricks, SQL, R, Python, PySpark, Power BI or Tableau'
- `❌ FAIL`: 'Knowledge of programming languages such as Python or R for data analysis and statistical modeling'

**Negative Cases (Must Reject):**
- `✅ PASS`: 'Diagnostics for hardware revision Model R-200'
- `✅ PASS`: 'Tracking serial batch R/1204 in logistics'
- `✅ PASS`: 'System build R.10 release notes'
- `✅ PASS`: 'Compensation: R$ 8,000 per month gross'
- `✅ PASS`: 'The applicant must have an R.N. nursing license'
- `✅ PASS`: 'Contact Dr. R. Watson in the administrative office'

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
- ⚠️ R in compound words (e.g., 'RStudio') - requires human review
- ⚠️ R as part of a larger word (e.g., 'R&D') - excluded by \b
- ⚠️ R with non-technical modifiers (e.g., 'R.10') - excluded by \b

### Cases Requiring Human Decision
- 🔍 RStudio
- 🔍 R in technical contexts with modifiers

---
*Audit generated by offline llm_regex_audit package. Production vocabulary is unchanged.*