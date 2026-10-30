"""
analysis/llm_regex_audit/synthetic_suites.py

Independent, transparent, human-readable synthetic test suites for R and Excel.
Completely separate from blind holdout benchmark workbooks.
Tests positive skill expressions, confounding distractors, and domain edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SyntheticTestCase:
    input_text: str
    expected_match: bool
    explanation: str
    case_type: str  # 'positive', 'negative_distractor', 'ambiguous'


SYNTHETIC_SUITES: Dict[str, List[SyntheticTestCase]] = {
    "R": [
        # --- Positives: Genuine R Skill Mentions ---
        SyntheticTestCase(
            input_text="Proficient in Python and R for statistical data modeling.",
            expected_match=True,
            explanation="Standard list of data science languages (Python and R).",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Required skills: SQL, R, Tableau, and Git.",
            expected_match=True,
            explanation="Standalone R in a comma-separated technical skill list.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Strong background in R programming and Bayesian inference.",
            expected_match=True,
            explanation="Explicit 'R programming' phrase.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Experience building analytical dashboards in RStudio and tidyverse.",
            expected_match=True,
            explanation="Canonical R environment and ecosystem package mention.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Statistical analysis with R (ggplot2, dplyr, caret).",
            expected_match=True,
            explanation="R followed by parenthetical library specifications.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Experience deploying statistical models in R/Shiny.",
            expected_match=True,
            explanation="Compound R/Shiny application mention.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Expertise in Python/R scripting.",
            expected_match=True,
            explanation="Slash-delimited programming language variant (Python/R).",
            case_type="positive",
        ),

        # --- Negatives: Known Confounding Distractors ---
        SyntheticTestCase(
            input_text="Leading our European R&D initiatives across product lines.",
            expected_match=False,
            explanation="Research and Development (R&D) abbreviation.",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Responsible for processing invoices in our A/R department.",
            expected_match=False,
            explanation="Accounts Receivable (A/R) accounting abbreviation.",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Hardware diagnostics for server revision Model R-200.",
            expected_match=False,
            explanation="Hardware model revision identifier (Model R-200).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Tracking serial batch R/1204 in warehouse inventory.",
            expected_match=False,
            explanation="Logistics batch number with slash and digits (R/1204).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Refer to the System build R.10 release notes.",
            expected_match=False,
            explanation="Software build version number (R.10).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Compensation package: R$ 8,000 per month gross.",
            expected_match=False,
            explanation="Currency symbol prefix (Brazilian Real, R$).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="The applicant must maintain an active R.N. nursing license.",
            expected_match=False,
            explanation="Medical qualification abbreviation (Registered Nurse, R.N.).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Please submit your CV to Dr. R. Watson in administration.",
            expected_match=False,
            explanation="Human initial preceding surname (Dr. R. Watson).",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="We need energetic developers who excel in fast-paced teams.",
            expected_match=False,
            explanation="Ordinary English verb (excel in) containing no R skill.",
            case_type="negative_distractor",
        ),
    ],

    "Excel": [
        # --- Positives: Genuine Microsoft Excel Skill Mentions ---
        SyntheticTestCase(
            input_text="Advanced Microsoft Excel modeling for corporate financial forecasts.",
            expected_match=True,
            explanation="Explicit 'Microsoft Excel' with modeling context.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Strong command of MS Excel (pivot tables, VLOOKUP, XLOOKUP).",
            expected_match=True,
            explanation="Abbreviated 'MS Excel' followed by technical spreadsheet features.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Automating spreadsheet workflows using Excel VBA and macros.",
            expected_match=True,
            explanation="Compound technical usage ('Excel VBA').",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Proficient in SQL, Python, and Excel for business analytics.",
            expected_match=True,
            explanation="Standalone 'Excel' in standard analytics tool list.",
            case_type="positive",
        ),
        SyntheticTestCase(
            input_text="Building executive dashboards with Power BI and Excel.",
            expected_match=True,
            explanation="Excel alongside complementary BI tool.",
            case_type="positive",
        ),

        # --- Negatives: Known Confounding Distractors ---
        SyntheticTestCase(
            input_text="Candidates should excel in communication and leadership skills.",
            expected_match=False,
            explanation="Verbal usage ('excel in communication').",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="We are looking for individuals who excel at analytical problem solving.",
            expected_match=False,
            explanation="Verbal usage ('excel at problem solving').",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Engineers who excel within cross-functional distributed teams.",
            expected_match=False,
            explanation="Verbal usage ('excel within teams').",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Demonstrated ability to excel as a technical team lead.",
            expected_match=False,
            explanation="Verbal usage ('excel as a team lead').",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Software engineers who excel with complex microservice architectures.",
            expected_match=False,
            explanation="Verbal usage ('excel with architectures').",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Proficiency with Microsoft Office suite (Word, PowerPoint, Outlook).",
            expected_match=False,
            explanation="Office suite mention without explicit Excel skill requirement.",
            case_type="negative_distractor",
        ),
        SyntheticTestCase(
            input_text="Experience maintaining cloud spreadsheets in Google Workspace.",
            expected_match=False,
            explanation="Generic spreadsheet reference not establishing Microsoft Excel.",
            case_type="negative_distractor",
        ),
    ],
}


def evaluate_synthetic_suite(
    regex_compiled,
    canonical_skill: str,
) -> Tuple[bool, Dict[str, Dict[str, bool | str]]]:
    """
    Evaluates a compiled regular expression against the independent synthetic suite.
    Returns (all_passed, detailed_results_dict).
    """
    cases = SYNTHETIC_SUITES.get(canonical_skill, [])
    detailed: Dict[str, Dict[str, bool | str]] = {}
    all_passed = True

    for c in cases:
        matched = bool(regex_compiled.search(c.input_text))
        passed = (matched == c.expected_match)
        if not passed:
            all_passed = False

        detailed[c.input_text] = {
            "expected_match": c.expected_match,
            "actual_match": matched,
            "passed": passed,
            "case_type": c.case_type,
            "explanation": c.explanation,
        }

    return all_passed, detailed

