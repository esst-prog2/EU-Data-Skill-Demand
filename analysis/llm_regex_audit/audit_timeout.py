"""
analysis/llm_regex_audit/audit_timeout.py

Detailed benchmark and instrumentation script to audit the corpus evaluation timeout:
1. Regex compilation time.
2. Regex execution time on small sample (500 postings).
3. Regex execution time on full corpus in-process (25,394 postings).
4. Worker process startup time (empty worker).
5. Serialization and IPC transfer time for minimal_postings.
6. Worker execution time inside the child process.
7. Parent process waiting and cleanup time.

Evaluates:
- Baseline safe simple pattern: r'\\bexcel\\b'
- Phase 3 R candidate: r'r\\b(?:\\s*programming|\\s*scripting|\\s*lang|\\s*language|\\s*studio)'
- Phase 3 Excel candidate: r'^(?:ms\\s*excel|excel\\b)(?!(?:in|at|within|as|with|\\s+excel))'
- Deliberately pathological ReDoS pattern: r'(a+)+$'
"""

import json
import multiprocessing
import os
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CORPUS_PATH = PROJECT_ROOT / "data" / "raw" / "freehire_eu_raw.json"


def _empty_worker(ready_event, finish_event):
    ready_event.set()
    finish_event.wait()


def _eval_worker_timed(
    cand_pattern: str,
    curr_pattern: str,
    minimal_postings: list,
    max_snippets: int,
    queue: multiprocessing.Queue,
    start_time_holder: multiprocessing.Array,
):
    # Record arrival in child process
    t_child_start = time.perf_counter()
    start_time_holder[0] = t_child_start

    cand_compiled = re.compile(cand_pattern, re.IGNORECASE)
    curr_compiled = re.compile(curr_pattern, re.IGNORECASE) if curr_pattern else None

    curr_hits = set()
    cand_hits = set()
    snippets = []

    t_loop_start = time.perf_counter()
    for ident, desc, title, cat, country in minimal_postings:
        is_curr = bool(curr_compiled.search(desc)) if curr_compiled else False
        m = cand_compiled.search(desc)
        is_cand = bool(m)
        if is_curr:
            curr_hits.add(ident)
        if is_cand:
            cand_hits.add(ident)
        if is_cand and not is_curr and len(snippets) < max_snippets:
            snippets.append(ident)

    t_loop_end = time.perf_counter()
    queue.put({
        "status": "ok",
        "t_child_start": t_child_start,
        "t_loop_start": t_loop_start,
        "t_loop_end": t_loop_end,
        "curr_count": len(curr_hits),
        "cand_count": len(cand_hits),
    })


def run_timeout_audit():
    print("=== Multi-Factor Evaluation Timeout Audit ===")
    print(f"Platform: {sys.platform} (Start method: {multiprocessing.get_start_method()})")

    with open(RAW_CORPUS_PATH, "r", encoding="utf-8") as f:
        postings = json.load(f)
    print(f"Loaded {len(postings)} postings.")

    minimal_postings = []
    for p in postings:
        desc = p.get("description") or ""
        if isinstance(desc, str) and desc.strip():
            ident = str(p.get("id") or p.get("public_slug") or p.get("slug") or "")
            title = str(p.get("title") or "")
            cat = str(p.get("_collection_category") or "")
            country = str(p.get("_collection_country") or "")
            minimal_postings.append((ident, desc, title, cat, country))

    sample_500 = minimal_postings[:500]
    print(f"Prepared minimal_postings ({len(minimal_postings)} items).")

    # 4. Worker process startup time (empty worker)
    print("\n[Measurement 4] Worker process startup time (empty spawn):")
    ready_evt = multiprocessing.Event()
    finish_evt = multiprocessing.Event()
    t_start = time.perf_counter()
    proc = multiprocessing.Process(target=_empty_worker, args=(ready_evt, finish_evt))
    proc.start()
    ready_evt.wait(timeout=10.0)
    t_ready = time.perf_counter()
    startup_time = t_ready - t_start
    finish_evt.set()
    proc.join()
    t_join = time.perf_counter()
    print(f"  Empty worker start to ready: {startup_time:.4f}s")
    print(f"  Empty worker join/cleanup:   {t_join - t_ready:.4f}s")
    print(f"  Total baseline process spawn: {t_join - t_start:.4f}s")

    test_patterns = [
        ("Safe Simple (Excel)", r"\bexcel\b"),
        ("Safe Simple (Python)", r"\bpython\b"),
        ("Phase 3 Candidate R", r"r\b(?:\s*programming|\s*scripting|\s*lang|\s*language|\s*studio)"),
        ("Phase 3 Candidate Excel", r"^(?:ms\s*excel|excel\b)(?!(?:in|at|within|as|with|\s+excel))"),
    ]

    results = []

    for label, pat in test_patterns:
        print(f"\n--- Testing Pattern: {label} (`{pat}`) ---")

        # 1. Regex compilation time
        t0 = time.perf_counter()
        compiled = re.compile(pat, re.IGNORECASE)
        t_compile = time.perf_counter() - t0
        print(f"  1. Compilation time: {t_compile*1000:.3f} ms")

        # 2. Execution on 500 sample
        t0 = time.perf_counter()
        hits_500 = sum(1 for _, d, _, _, _ in sample_500 if compiled.search(d))
        t_sample = time.perf_counter() - t0
        print(f"  2. Execution on 500 postings: {t_sample:.4f}s ({hits_500} hits)")

        # 3. Execution on complete corpus in-process
        t0 = time.perf_counter()
        hits_full = sum(1 for _, d, _, _, _ in minimal_postings if compiled.search(d))
        t_full_inprocess = time.perf_counter() - t0
        print(f"  3. In-process full corpus (25,394): {t_full_inprocess:.4f}s ({hits_full} hits)")

        # 5, 6, 7. Multiprocessing worker execution
        start_holder = multiprocessing.Array("d", [0.0])
        queue = multiprocessing.Queue()

        t_parent_start = time.perf_counter()
        proc = multiprocessing.Process(
            target=_eval_worker_timed,
            args=(pat, "", minimal_postings, 15, queue, start_holder),
        )
        proc.start()
        proc.join(timeout=15.0)
        t_parent_joined = time.perf_counter()

        timed_out = proc.is_alive()
        if timed_out:
            proc.terminate()
            proc.join()
            print("  [ERROR] Multiprocessing run timed out after 15.0s!")
            results.append({
                "label": label,
                "pattern": pat,
                "compile_ms": round(t_compile * 1000, 3),
                "sample_500_s": round(t_sample, 4),
                "inprocess_s": round(t_full_inprocess, 4),
                "timed_out": True,
            })
            continue

        worker_data = queue.get(timeout=2.0) if not queue.empty() else {}
        t_child_start = worker_data.get("t_child_start", start_holder[0])
        t_loop_start = worker_data.get("t_loop_start", 0)
        t_loop_end = worker_data.get("t_loop_end", 0)

        transfer_time = t_child_start - t_parent_start
        worker_search_time = t_loop_end - t_loop_start
        cleanup_time = t_parent_joined - t_loop_end
        total_time = t_parent_joined - t_parent_start

        print(f"  4. Serialization + Spawn + Unpickle Transfer: {transfer_time:.4f}s")
        print(f"  5. Worker internal loop search time:          {worker_search_time:.4f}s")
        print(f"  6. Result queue get + Join cleanup time:      {cleanup_time:.4f}s")
        print(f"  7. Total wall-clock time from parent:         {total_time:.4f}s")

        results.append({
            "label": label,
            "pattern": pat,
            "compile_ms": round(t_compile * 1000, 3),
            "sample_500_s": round(t_sample, 4),
            "inprocess_s": round(t_full_inprocess, 4),
            "transfer_s": round(transfer_time, 4),
            "worker_search_s": round(worker_search_time, 4),
            "cleanup_s": round(cleanup_time, 4),
            "total_wall_clock_s": round(total_time, 4),
            "timed_out": False,
        })

    # Test Pathological Pattern
    print("\n--- Testing Deliberately Pathological ReDoS Pattern ---")
    pathological_pat = r"(a+)+$"
    pathological_text = "a" * 30 + "!"  # Triggers 2^30 backtracking iterations
    print(f"  Pattern: `{pathological_pat}` on '{pathological_text[:10]}...!'")
    t0 = time.perf_counter()
    try:
        proc = multiprocessing.Process(
            target=_eval_worker_timed,
            args=(
                pathological_pat,
                "",
                [("path_1", pathological_text, "", "", "")],
                15,
                multiprocessing.Queue(),
                multiprocessing.Array("d", [0.0]),
            ),
        )
        proc.start()
        proc.join(timeout=3.0)
        if proc.is_alive():
            proc.terminate()
            proc.join()
            print("  [SUCCESS] Pathological ReDoS worker timed out after 3.0s and was cleanly terminated!")
        else:
            print("  [WARNING] Worker finished unexpectedly without timeout.")
    except Exception as e:
        print(f"  Error testing pathological pattern: {e}")

    out_file = PROJECT_ROOT / "analysis" / "llm_regex_audit" / "artifacts" / "timeout_audit_measurements.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved timing measurements to {out_file.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_timeout_audit()

