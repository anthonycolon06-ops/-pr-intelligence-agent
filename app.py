
from flask import Flask, request, jsonify
import json
import os
import time
import threading

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

VERSION = "1.8.0"
CACHE_SECONDS = 300

_cache = {
    "jobs": [],
    "sources": [],
    "timestamp": 0,
}
_cache_lock = threading.Lock()

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
    code.lower(): name
    for name, code in US_STATES.items()
}


def load_jobs():
    try:
        with open("jobs.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            jobs = data.get("jobs", [])
            return jobs if isinstance(jobs, list) else []

        return data if isinstance(data, list) else []

    except (OSError, ValueError, TypeError):
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
        (
            "SmartRecruiters",
            SMARTRECRUITERS_BOARDS,
            get_smartrecruiters_jobs,
        ),
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


def load_all_jobs(force_refresh=False):
    now = time.time()

    with _cache_lock:
        cache_is_valid = (
            _cache["timestamp"] > 0
            and now - _cache["timestamp"] < CACHE_SECONDS
        )

        if cache_is_valid and not force_refresh:
            return _cache["jobs"], _cache["sources"]

        jobs, statuses = fetch_all_jobs()

        _cache["jobs"] = jobs
        _cache["sources"] = statuses
        _cache["timestamp"] = time.time()

        return jobs, statuses


def location_matches(job, requested_location):
    query = str(requested_location or "").strip().lower()

    if not query:
        return True

    location = job.get("location", {})

    if not isinstance(location, dict):
        return query in str(location).lower()

    municipality = str(location.get("municipality") or "").lower()
    region = str(location.get("region") or "").lower()
    country = str(location.get("country") or "").lower()
    raw = str(location.get("raw") or "").lower()
    location_text = " ".join(
        [municipality, region, country, raw]
    )

    if query in {"puerto rico", "puerto-rico", "pr"}:
        return (
            country == "pr"
            or region == "puerto rico"
            or "puerto rico" in location_text
        )

    if query in {
        "united states", "united states of america",
        "usa", "us", "u.s.", "u.s.a.",
    }:
        return (
            country in {"us", "usa", "united states"}
            or "united states" in location_text
            or "usa" in location_text
        )

    state_code = US_STATES.get(query)

    if not state_code and query in STATE_NAMES:
        state_code = query.upper()

    if state_code:
        state_name = STATE_NAMES.get(state_code.lower(), "").lower()
        raw_tokens = raw.replace(",", " ").split()

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
            state_query = parts[-1]
            requested_code = US_STATES.get(state_query)

            if not requested_code and state_query in STATE_NAMES:
                requested_code = state_query.upper()

            city_matches = (
                city_query in municipality or city_query in raw
            )

            if requested_code:
                state_name = STATE_NAMES.get(
                    requested_code.lower(), ""
                ).lower()

                state_matches = (
                    region == requested_code.lower()
                    or requested_code.lower() in raw.split()
                    or state_name in location_text
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
):
    results = list(jobs)

    if location:
        results = [
            job for job in results
            if location_matches(job, location)
        ]

    if industry:
        query = industry.strip().lower()
        results = [
            job for job in results
            if query in str(job.get("industry") or "").lower()
        ]

    if employment_type:
        query = employment_type.strip().lower()
        results = [
            job for job in results
            if query in str(job.get("employment_type") or "").lower()
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
            "/jobs",
            "/sources-test",
            "/greenhouse-test",
            "/.well-known/agent.json",
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
    min_salary = request.args.get("min_salary", type=float)
    max_salary = request.args.get("max_salary", type=float)

    results = filter_jobs(
        all_jobs,
        location=location,
        industry=industry,
        employment_type=employment_type,
        min_salary=min_salary,
        max_salary=max_salary,
    )

    return jsonify({
        "version": VERSION,
        "count": len(results),
        "total_loaded": len(all_jobs),
        "filters": {
            "location": location or None,
            "industry": industry or None,
            "employment_type": employment_type or None,
            "min_salary": min_salary,
            "max_salary": max_salary,
        },
        "sources": source_status,
        "jobs": results,
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
            1 for item in statuses if item["status"] == "ok"
        ),
        "failed_sources": sum(
            1 for item in statuses if item["status"] == "error"
        ),
        "cache_seconds": CACHE_SECONDS,
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

        return jsonify({
            "source": "Greenhouse",
            "board": board,
            "count": len(normalized_jobs),
            "filters": {
                "location": requested_location or None,
            },
            "jobs": normalized_jobs,
        })

    except Exception as error:
        return jsonify({
            "error": str(error),
            "source": "Greenhouse",
            "board": board,
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
