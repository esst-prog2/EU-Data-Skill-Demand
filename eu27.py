"""
01_collect_jobs_eu.py

Collect data-related job postings from FreeHire across the EU-27.

The script:
1. Queries FreeHire's public search API.
2. Searches each EU country separately.
3. Searches the five target occupational categories.
4. Paginates through all matching results.
5. Preserves the FreeHire category and country used for collection.
6. Deduplicates postings across country/category queries.
7. Saves raw postings and collection statistics.

Target categories:
    data_analytics
    data_engineering
    data_science
    ml_ai
    ai_engineering

The resulting dataset should be interpreted as an observed
job-posting snapshot from FreeHire, not a census of the EU labor market.
"""

import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://freehire.me/api/v1/jobs/search"

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JOBS_OUTPUT = OUTPUT_DIR / "freehire_eu_raw.json"
METADATA_OUTPUT = OUTPUT_DIR / "collection_metadata_eu.json"

# FreeHire allows a maximum of 100 results per request.
PAGE_SIZE = 100

# Small pause between requests.
REQUEST_DELAY = 0.15

# Request timeout in seconds.
TIMEOUT = 30


# ============================================================
# EU-27 COUNTRY CODES
# ============================================================

EU_COUNTRIES = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
}


# ============================================================
# TARGET OCCUPATIONAL CATEGORIES
# ============================================================

CATEGORIES = [
    "data_analytics",
    "data_engineering",
    "data_science",
    "ml_ai",
    "ai_engineering",
]


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "EU-Data-Job-Skill-Analysis/"
            "1.0 "
            "(educational research project)"
        )
    }
)


# ============================================================
# HELPERS
# ============================================================

def get_jobs(country_code, category):
    """
    Retrieve all matching jobs for one country/category combination.
    """

    jobs = []
    offset = 0

    while True:
        params = {
            "countries": country_code,
            "category": category,
            "limit": PAGE_SIZE,
            "offset": offset,
            "sort": "posted_at",
            "order": "desc",
        }

        response = session.get(
            BASE_URL,
            params=params,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        # ----------------------------------------------------
        # Check whether FreeHire ignored any parameters.
        # ----------------------------------------------------

        meta = payload.get("meta", {})

        ignored_params = meta.get("ignored_params", [])

        if ignored_params:
            raise RuntimeError(
                f"FreeHire ignored parameters for "
                f"{country_code}/{category}: "
                f"{ignored_params}"
            )

        page = payload.get("data", [])

        if not page:
            break

        # Preserve the provenance of the query.
        for job in page:
            job["_collection_country"] = country_code
            job["_collection_category"] = category

        jobs.extend(page)

        total = meta.get("total")

        print(
            f"    {country_code} / {category}: "
            f"{len(jobs)}"
            + (f" / {total}" if total is not None else "")
        )

        # ----------------------------------------------------
        # Stop when all matching jobs have been retrieved.
        # ----------------------------------------------------

        if total is not None and len(jobs) >= total:
            break

        # Safety check.
        if len(page) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

        # FreeHire documents offset + limit <= 10000.
        if offset + PAGE_SIZE > 10000:
            raise RuntimeError(
                f"Pagination limit exceeded for "
                f"{country_code}/{category}. "
                f"More than 10,000 matching jobs."
            )

        time.sleep(REQUEST_DELAY)

    return jobs


def get_job_key(job):
    """
    Return the most stable available identifier.
    """

    return (
        job.get("public_slug")
        or job.get("slug")
        or job.get("id")
        or job.get("external_id")
    )


# ============================================================
# MAIN COLLECTION
# ============================================================

def main():

    print("=" * 70)
    print("FREEHIRE EU-27 DATA JOB COLLECTION")
    print("=" * 70)

    print(f"Countries: {len(EU_COUNTRIES)}")
    print(f"Categories: {len(CATEGORIES)}")
    print(f"Maximum country/category queries: "
          f"{len(EU_COUNTRIES) * len(CATEGORIES)}")

    print()

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    all_jobs = {}

    query_counts = defaultdict(int)
    country_counts = Counter()
    category_counts = Counter()

    query_totals = {}

    # --------------------------------------------------------
    # Country × category collection
    # --------------------------------------------------------

    for country_code, country_name in EU_COUNTRIES.items():

        print()
        print("-" * 70)
        print(f"{country_name} ({country_code})")
        print("-" * 70)

        for category in CATEGORIES:

            try:

                jobs = get_jobs(
                    country_code=country_code,
                    category=category,
                )

            except requests.RequestException as exc:

                print(
                    f"    ERROR: {country_code} / {category}: "
                    f"{exc}"
                )

                continue

            query_counts[(country_code, category)] = len(jobs)

            query_totals[(country_code, category)] = len(jobs)

            # ------------------------------------------------
            # Deduplicate
            # ------------------------------------------------

            for job in jobs:

                key = get_job_key(job)

                if key is None:
                    print(
                        "    WARNING: job without stable ID "
                        f"in {country_code}/{category}"
                    )
                    continue

                if key not in all_jobs:

                    all_jobs[key] = job

                else:

                    # ------------------------------------------------
                    # Preserve every FreeHire category matching the job.
                    # ------------------------------------------------

                    existing = all_jobs[key]

                    existing_categories = set(
                        existing.get(
                            "_freehire_matched_categories",
                            []
                        )
                    )

                    existing_categories.add(category)

                    existing["_freehire_matched_categories"] = sorted(
                        existing_categories
                    )

                    # ------------------------------------------------
                    # Preserve every collection country as well.
                    # Usually this will be one country, but keeping
                    # all observed values makes the deduplication
                    # transparent.
                    # ------------------------------------------------

                    existing_countries = set(
                        existing.get(
                            "_collection_countries",
                            []
                        )
                    )

                    existing_country = existing.get(
                        "_collection_country"
                    )

                    if existing_country:
                        existing_countries.add(existing_country)

                    existing_countries.add(country_code)

                    existing["_collection_countries"] = sorted(
                        existing_countries
                    )

            time.sleep(REQUEST_DELAY)

    # ========================================================
    # FINALIZE CATEGORY / COUNTRY METADATA
    # ========================================================

    for job in all_jobs.values():

        # First occurrence becomes the default category/country.
        category = job.get("_collection_category")
        country = job.get("_collection_country")

        matched_categories = set(
            job.get("_freehire_matched_categories", [])
        )

        if category:
            matched_categories.add(category)

        job["_freehire_matched_categories"] = sorted(
            matched_categories
        )

        collection_countries = set(
            job.get("_collection_countries", [])
        )

        if country:
            collection_countries.add(country)

        job["_collection_countries"] = sorted(
            collection_countries
        )

        # ----------------------------------------------------
        # If FreeHire itself provides countries, preserve that
        # separately rather than overwriting it.
        # ----------------------------------------------------

        job["_collection_source"] = "FreeHire"


    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    unique_jobs = list(all_jobs.values())

    for job in unique_jobs:

        # Country
        countries = job.get("_collection_countries", [])

        for country in countries:
            country_counts[country] += 1

        # Category
        categories = job.get(
            "_freehire_matched_categories",
            []
        )

        for category in categories:
            category_counts[category] += 1


    # ========================================================
    # SORT JOBS
    # ========================================================

    unique_jobs.sort(
        key=lambda job: (
            job.get("posted_at")
            or job.get("created_at")
            or ""
        ),
        reverse=True,
    )


    # ========================================================
    # SAVE RAW DATA
    # ========================================================

    with open(
        JOBS_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            unique_jobs,
            f,
            ensure_ascii=False,
            indent=2,
        )


    # ========================================================
    # QUERY COUNTS TABLE
    # ========================================================

    query_summary = []

    for country_code, country_name in EU_COUNTRIES.items():

        for category in CATEGORIES:

            query_summary.append(
                {
                    "country_code": country_code,
                    "country": country_name,
                    "category": category,
                    "jobs_returned": query_counts.get(
                        (country_code, category),
                        0,
                    ),
                }
            )


    # ========================================================
    # COLLECTION METADATA
    # ========================================================

    metadata = {
        "source": "FreeHire",
        "api_endpoint": BASE_URL,
        "collection_timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "geographic_scope": "European Union EU-27",

        "countries": EU_COUNTRIES,

        "categories": CATEGORIES,

        "country_count": len(EU_COUNTRIES),

        "category_count": len(CATEGORIES),

        "unique_jobs": len(unique_jobs),

        "category_distribution": dict(
            sorted(
                category_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

        "country_distribution": dict(
            sorted(
                country_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

        "query_summary": query_summary,
    }


    with open(
        METADATA_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2,
        )


    # ========================================================
    # PRINT FINAL RESULTS
    # ========================================================

    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)

    print()
    print(f"Unique postings: {len(unique_jobs)}")

    print()
    print("CATEGORY DISTRIBUTION")
    print("-" * 40)

    for category, count in sorted(
        category_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"{category:<25} {count:>6}")

    print()
    print("COUNTRY DISTRIBUTION")
    print("-" * 40)

    for country_code, count in sorted(
        country_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        country_name = EU_COUNTRIES[country_code]

        print(
            f"{country_code} "
            f"{country_name:<20} "
            f"{count:>6}"
        )

    print()
    print(f"Saved jobs:     {JOBS_OUTPUT}")
    print(f"Saved metadata: {METADATA_OUTPUT}")


if __name__ == "__main__":
    main()