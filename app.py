from flask import Flask, request, jsonify
import json
import os

from greenhouse import get_greenhouse_jobs
from normalizer import normalize_greenhouse_job

app = Flask(__name__)


def load_jobs():
    try:
        with open("jobs.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("jobs", [])
    except Exception:
        return []


def location_text(job):
    location = job.get("location", {})

    if isinstance(location, dict):
        return " ".join([
            str(location.get("municipality", "")),
            str(location.get("region", "")),
            str(location.get("country", ""))
        ]).lower()

    return str(location).lower()


@app.route("/")
def home():
    return jsonify({
        "agent": "PR Intelligence Agent",
        "status": "online",
        "version": "1.3.0",
        "description": "Puerto Rico employment intelligence service"
    })


@app.route("/.well-known/agent.json")
def agent_manifest():
    return jsonify({
        "name": "PR Intelligence Agent",
        "description": "Puerto Rico employment intelligence service for AI agents.",
        "version": "1.3.0",
        "capabilities": [
            "job_search",
            "salary_filtering",
            "location_filtering",
            "industry_filtering",
            "employment_type_filtering",
            "job_intelligence"
        ],
        "coverage": {
            "country": "Puerto Rico",
            "industries": "multiple",
            "locations": "Puerto Rico",
            "salary_ranges": "all"
        },
        "api": {
            "base_path": "/",
            "endpoints": {
                "health": "/",
                "jobs": "/jobs"
            }
        },
        "pricing": {
            "model": "per_query",
            "target_price_usd": 0.10
        }
    })


@app.route("/jobs", methods=["GET"])
def jobs():

    all_jobs = load_jobs()

    location = request.args.get("location", "").lower()
    industry = request.args.get("industry", "").lower()
    employment_type = request.args.get(
        "employment_type", ""
    ).lower()

    min_salary = request.args.get("min_salary", type=float)
    max_salary = request.args.get("max_salary", type=float)

    results = all_jobs

    if location:
        results = [
            job for job in results
            if location in location_text(job)
        ]

    if industry:
        results = [
            job for job in results
            if industry in job.get("industry", "").lower()
        ]

    if employment_type:
        results = [
            job for job in results
            if employment_type in job.get(
                "employment_type", ""
            ).lower()
        ]

    if min_salary is not None:
        results = [
            job for job in results
            if (
                job.get("salary", {}).get("max") is not None
                and job.get("salary", {}).get("max") >= min_salary
            )
        ]

    if max_salary is not None:
        results = [
            job for job in results
            if (
                job.get("salary", {}).get("min") is not None
                and job.get("salary", {}).get("min") <= max_salary
            )
        ]

    return jsonify({
        "count": len(results),
        "filters": {
            "location": location or None,
            "industry": industry or None,
            "employment_type": employment_type or None,
            "min_salary": min_salary,
            "max_salary": max_salary
        },
        "jobs": results
    })


@app.route("/greenhouse-test", methods=["GET"])
def greenhouse_test():

    board_token = request.args.get("board")

    if not board_token:
        return jsonify({
            "error": "Missing board parameter",
            "example": "/greenhouse-test?board=example"
        }), 400

    try:
        raw_jobs = get_greenhouse_jobs(board_token)

        normalized_jobs = [
            normalize_greenhouse_job(
                job,
                board_token,
                board_token
            )
            for job in raw_jobs
        ]

        return jsonify({
            "source": "Greenhouse",
            "board": board_token,
            "count": len(normalized_jobs),
            "jobs": normalized_jobs
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
