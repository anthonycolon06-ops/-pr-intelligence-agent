
from flask import Flask, request, jsonify
import json
import os
import re
import time
import threading
import unicodedata

from greenhouse import get_greenhouse_jobs
from normalizer import normalize_greenhouse_job
from lever import get_lever_jobs
from ashby import get_ashby_jobs
from smartrecruiters import get_smartrecruiters_jobs
from sources import (
    GREENHOUSE_BOARDS,
    LEVER_BOARDS,
    ASHBY_BOARDS,
    SMARTRECRUITERS_BOARDS,
)

app = Flask(__name__)

VERSION = "1.9.0"
CACHE_SECONDS = 300

_cache = {"jobs": [], "sources": [], "timestamp": 0}
_cache_lock = threading.Lock()
_refresh_lock = threading.Lock()

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ",
    "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

STATE_NAMES = {
    code.lower(): name for name, code in US_STATES.items()
}

PR_ALIASES = {
    "pr", "p r", "puerto rico", "puerto-rico",
    "puertorico", "commonwealth of puerto rico",
    "puerto rico usa", "puerto rico us",
}


def clean_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text).strip()


def normalize_location_query(value):
    query = clean_text(value).strip(" \t\r\n.,;:!?")
    query = re.sub(r"\s+", " ", query)

    if query in PR_ALIASES:
        return "puerto rico"

    if query in {
        "united states of america", "usa", "u s a",
        "u.s.a", "u.s.a.", "u s", "u.s", "u.s.",
        "us", "united states",
    }:
        return "united states"

    return query


def load_jobs():
    try:
        with open("jobs.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            jobs = data.get("jobs", [])
            return jobs if isinstance(jobs, list) else []

        return data if isinstance(data, list) else []

    except (OSError, ValueError, TypeError) as error:
        print(f"Could not load jobs.json: {error}")
        return []


def normalize_greenhouse_board(board):
    raw_jobs = get_greenhouse_jobs(board)
    normalized = []

    for job in raw_jobs:
        try:
            item = normalize_greenhouse_job(job, board, board)
            if item:
                normalized.append(item)
        except Exception as error:
            print(f"Greenhouse normalization failed: {error}")

    return normalized


def source_result(source_name, board, getter):
    try:
        jobs = getter(board)
        if not isinstance(jobs, list):
            raise TypeError("Source did not return a list")

        return jobs, {
            "source": source_name,
            "board": board,
            "status": "ok",
            "count": len(jobs),
        }

    except Exception as error:
        print(f"{source_name} board {board} failed: {error}")
        return [], {
            "source": source_name,
            "board": board,
            "status": "error",
            "error": str(error)[:300],
            "count": 0,
        }


def fetch_all_jobs():
    combined = []
    statuses = []

    source_groups = [
        ("Greenhouse", GREENHOUSE_BOARDS, normalize_greenhouse_board),
        ("Lever", LEVER_BOARDS, get_lever_jobs),
        ("Ashby", ASHBY_BOARDS, get_ashby_jobs),
        ("SmartRecruiters", SMARTRECRUITERS_BOARDS,
         get_smartrecruiters_jobs),
    ]

    for source_name, boards, getter in source_groups:
        for board in boards:
            jobs, status = source_result(source_name, board, getter)
            combined.extend(jobs)
            statuses.append(status)

    combined.extend(load_jobs())

    unique_jobs = []
    seen_ids = set()

    for job in combined:
        if not isinstance(job, dict):
            continue

        job_id = job.get("job_id")
        if job_id:
            key = str(job_id).strip().lower()
            if key in seen_ids:
                continue
            seen_ids.add(key)

        unique_jobs.append(job)

    return unique_jobs, statuses


def refresh_cache():
    try:
        print("Starting background job refresh...")
        jobs, statuses = fetch_all_jobs()

        successful_sources = sum(
            1 for item in statuses
            if item.get("status") == "ok"
        )

        if statuses and successful_sources == 0:
            print("All external sources failed. Keeping previous cache.")
            with _cache_lock:
                if not _cache["jobs"]:
                    _cache["jobs"] = load_jobs()
                _cache["sources"] = statuses
            return

        with _cache_lock:
            _cache["jobs"] = jobs
            _cache["sources"] = statuses
            _cache["timestamp"] = time.time()

        print(
            f"Background refresh complete: {len(jobs)} jobs, "
            f"{successful_sources}/{len(statuses)} source boards successful."
        )

    except Exception as error:
        print(f"Background cache refresh failed: {error}")

    finally:
        _refresh_lock.release()


def start_background_refresh():
    if not _refresh_lock.acquire(blocking=False):
        return False

    try:
        thread = threading.Thread(
            target=refresh_cache,
            name="job-cache-refresh",
            daemon=True,
        )
        thread.start()
        return True

    except Exception as error:
        print(f"Could not start cache refresh: {error}")
        _refresh_lock.release()
        return False


def load_all_jobs(force_refresh=False):
    now = time.time()

    with _cache_lock:
        if _cache["timestamp"] == 0 and not _cache["jobs"]:
            _cache["jobs"] = load_jobs()

        cache_is_valid = (
            _cache["timestamp"] > 0
            and now - _cache["timestamp"] < CACHE_SECONDS
        )

        jobs = list(_cache["jobs"])
        statuses = list(_cache["sources"])

    if force_refresh or not cache_is_valid:
        start_background_refresh()

    return jobs, statuses


def get_location_parts(job):
    location = job.get("location", {})

    if isinstance(location, dict):
        municipality = clean_text(location.get("municipality") or "")
        region = clean_text(location.get("region") or "")
        country = clean_text(location.get("country") or "")
        raw = clean_text(location.get("raw") or "")
    else:
        municipality = ""
        region = ""
        country = ""
        raw = clean_text(location)

    return municipality, region, country, raw


def get_pr_eligibility(job):
    eligibility = job.get("eligibility") or {}
    if not isinstance(eligibility, dict):
        return False

    territories = eligibility.get("territories", [])
    if not isinstance(territories, (list, tuple, set)):
        territories = [territories]

    return any(
        normalize_location_query(item) == "puerto rico"
        for item in territories
        if item is not None
    )


def is_remote_job(job):
    work_mode = clean_text(job.get("work_mode") or "")
    _, _, _, raw = get_location_parts(job)

    return (
        "remote" in work_mode
        or "(remote)" in raw
        or "(fully remote)" in raw
    )


def is_physical_pr_job(job):
    _, region, country, raw = get_location_parts(job)

    if country in {"pr", "pri", "puerto rico"}:
        return True

    if region in {"pr", "puerto rico"}:
        return True

    if is_remote_job(job):
        return False

    return (
        "puerto rico" in raw
        or bool(re.search(
            r"(^|[\s,(/-])pr($|[\s,)/-])",
            raw,
        ))
    )


def get_pr_match_type(job):
    if is_physical_pr_job(job):
        return "physical_in_puerto_rico"

    if is_remote_job(job) and get_pr_eligibility(job):
        return "remote_eligible_in_puerto_rico"

    return None


def location_matches(job, requested_location):
    query = normalize_location_query(requested_location)

    if not query:
        return True

    municipality, region, country, raw = get_location_parts(job)
    location_text = " ".join([municipality, region, country, raw])

    if query == "puerto rico":
        return get_pr_match_type(job) is not None

    if query == "united states":
        return (
            country in {"us", "usa", "united states"}
            or "united states" in location_text
            or "usa" in location_text
        )

    state_code = US_STATES.get(query)
    if not state_code and query in STATE_NAMES:
        state_code = query.upper()

    if state_code:
        state_name = clean_text(STATE_NAMES.get(state_code.lower(), ""))
        raw_tokens = set(re.findall(r"[a-z]+", raw))

        return (
            region == state_code.lower()
            or region == state_name
            or state_name in location_text
            or state_code.lower() in raw_tokens
        )

    if "," in query:
        parts = [part.strip() for part in query.split(",") if part.strip()]

        if len(parts) >= 2:
            city_query = parts[0]
            state_query = normalize_location_query(parts[-1])
            city_matches = city_query in municipality or city_query in raw

            if state_query == "puerto rico":
                return city_matches and is_physical_pr_job(job)

            requested_code = US_STATES.get(state_query)
            if not requested_code and state_query in STATE_NAMES:
                requested_code = state_query.upper()

            if requested_code:
                state_name = clean_text(
                    STATE_NAMES.get(requested_code.lower(), "")
                )
                raw_tokens = set(re.findall(r"[a-z]+", raw))
                state_matches = (
                    region == requested_code.lower()
                    or state_name in location_text
                    or requested_code.lower() in raw_tokens
                )
                return city_matches and state_matches

    return query in location_text


def salary_value(job, key):
    salary = job.get("salary") or {}
    if not isinstance(salary, dict):
        return None

    try:
        value = salary.get(key)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def filter_jobs(
    jobs,
    location="",
    industry="",
    employment_type="",
    min_salary=None,
    max_salary=None,
    pr_match_type="",
):
    results = list(jobs)

    if location:
        results = [
            job for job in results
            if location_matches(job, location)
        ]

    if industry:
        query = clean_text(industry)
        results = [
            job for job in results
            if query in clean_text(job.get("industry") or "")
        ]

    if employment_type:
        query = clean_text(employment_type)
        results = [
            job for job in results
            if query in clean_text(job.get("employment_type") or "")
        ]

    if min_salary is not None:
        results = [
            job for job in results
            if salary_value(job, "max") is not None
            and salary_value(job, "max") >= min_salary
        ]

    if max_salary is not None:
        results = [
            job for job in results
            if salary_value(job, "min") is not None
            and salary_value(job, "min") <= max_salary
        ]

    if pr_match_type:
        requested_type = clean_text(pr_match_type)

        if requested_type in {
            "physical", "physical_in_puerto_rico",
            "local", "onsite", "on-site",
        }:
            results = [
                job for job in results
                if is_physical_pr_job(job)
            ]

        elif requested_type in {
            "remote", "remote_eligible_in_puerto_rico",
            "remote-eligible",
        }:
            results = [
                job for job in results
                if is_remote_job(job) and get_pr_eligibility(job)
            ]

    return results


@app.route("/")
def home():
    return jsonify({
        "agent": "PR Intelligence Agent",
        "status": "online",
        "version": VERSION,
        "description": "Multi-source employment intelligence API",
        "coverage": ["Puerto Rico", "United States"],
        "sources": [
            "Greenhouse", "Lever", "Ashby",
            "SmartRecruiters", "jobs.json",
        ],
        "endpoints": [
            "/jobs", "/sources-test",
            "/greenhouse-test", "/.well-known/agent.json",
        ],
    })


@app.route("/.well-known/agent.json")
def agent_manifest():
    return jsonify({
        "name": "PR Intelligence Agent",
        "description": (
            "Multi-source employment intelligence with normalized "
            "job data, source links and location filters."
        ),
        "version": VERSION,
        "capabilities": [
            "job_search",
            "salary_filtering",
            "location_filtering",
            "industry_filtering",
            "employment_type_filtering",
            "multi_source_ingestion",
            "job_intelligence",
            "remote_eligibility_filtering",
        ],
        "coverage": {
            "primary_market": "Puerto Rico",
            "secondary_market": "United States",
            "countries": ["Puerto Rico", "United States"],
            "industries": "multiple",
        },
        "api": {
            "base_path": "/",
            "endpoints": {
                "health": "/",
                "jobs": "/jobs",
                "sources_test": "/sources-test",
                "greenhouse_test": "/greenhouse-test",
            },
        },
        "pricing": {
            "model": "per_query",
            "target_price_usd": 0.10,
        },
    })


@app.route("/jobs")
def jobs_endpoint():
    all_jobs, source_status = load_all_jobs()

    location = request.args.get("location", "").strip()
    industry = request.args.get("industry", "").strip()
    employment_type = request.args.get("employment_type", "").strip()
    pr_match_type = request.args.get("pr_match_type", "").strip()

    min_salary = request.args.get("min_salary", type=float)
    max_salary = request.args.get("max_salary", type=float)

    results = filter_jobs(
        all_jobs,
        location=location,
        industry=industry,
        employment_type=employment_type,
        min_salary=min_salary,
        max_salary=max_salary,
        pr_match_type=pr_match_type,
    )

    normalized_query = normalize_location_query(location)
    annotated_results = []

    for original_job in results:
        job = dict(original_job)

        if normalized_query == "puerto rico":
            job["pr_match_type"] = get_pr_match_type(job)

        annotated_results.append(job)

    with _cache_lock:
        cache_timestamp = _cache["timestamp"]

    cache_age = (
        int(time.time() - cache_timestamp)
        if cache_timestamp > 0 else None
    )

    return jsonify({
        "version": VERSION,
        "count": len(annotated_results),
        "total_loaded": len(all_jobs),
        "cache_age_seconds": cache_age,
        "refresh_in_progress": _refresh_lock.locked(),
        "filters": {
            "location": location or None,
            "normalized_location": normalized_query or None,
            "industry": industry or None,
            "employment_type": employment_type or None,
            "pr_match_type": pr_match_type or None,
            "min_salary": min_salary,
            "max_salary": max_salary,
        },
        "sources": source_status,
        "jobs": annotated_results,
    })


@app.route("/sources-test")
def sources_test():
    refresh = request.args.get("refresh", "").lower() in {
        "1", "true", "yes"
    }

    jobs, statuses = load_all_jobs(force_refresh=refresh)

    return jsonify({
        "version": VERSION,
        "total_loaded": len(jobs),
        "source_count": len(statuses),
        "successful_sources": sum(
            1 for item in statuses
            if item.get("status") == "ok"
        ),
        "failed_sources": sum(
            1 for item in statuses
            if item.get("status") == "error"
        ),
        "cache_seconds": CACHE_SECONDS,
        "refresh_requested": refresh,
        "refresh_in_progress": _refresh_lock.locked(),
        "sources": statuses,
    })


@app.route("/greenhouse-test")
def greenhouse_test():
    board = request.args.get("board", "").strip()
    requested_location = request.args.get("location", "").strip()

    if not board:
        return jsonify({
            "error": "Missing board parameter",
            "example": "/greenhouse-test?board=livecareer",
        }), 400

    try:
        raw_jobs = get_greenhouse_jobs(board)
        normalized_jobs = []

        for job in raw_jobs:
            try:
                item = normalize_greenhouse_job(job, board, board)
                if item:
                    normalized_jobs.append(item)
            except Exception as error:
                print(f"Greenhouse normalization failed: {error}")

        if requested_location:
            normalized_jobs = [
                job for job in normalized_jobs
                if location_matches(job, requested_location)
            ]

        if normalize_location_query(requested_location) == "puerto rico":
            for job in normalized_jobs:
                job["pr_match_type"] = get_pr_match_type(job)

        return jsonify({
            "version": VERSION,
            "source": "Greenhouse",
            "board": board,
            "count": len(normalized_jobs),
            "filters": {
                "location": requested_location or None,
                "normalized_location": (
                    normalize_location_query(requested_location) or None
                ),
            },
            "jobs": normalized_jobs,
        })

    except Exception as error:
        print(f"Greenhouse test failed for {board}: {error}")
        return jsonify({
            "error": str(error)[:300],
            "source": "Greenhouse",
            "board": board,
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
