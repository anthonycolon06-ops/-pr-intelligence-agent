from flask import Flask, request, jsonify

app = Flask(__name__)

JOBS = [
    {
        "id": "demo-001",
        "title": "Production Worker",
        "company": "Demo Manufacturing",
        "location": "Bayamon, PR",
        "salary_min": 16.00,
        "salary_max": 20.00,
        "salary_period": "hour",
        "salary_published": True,
        "industry": "Manufacturing",
        "employment_type": "Full-time",
        "posted_date": "2026-10-06",
        "source": "demo",
        "application_url": None,
        "verified": False
    },
    {
        "id": "demo-002",
        "title": "Aircraft Ground Operations",
        "company": "Demo Aviation",
        "location": "Carolina, PR",
        "salary_min": 15.00,
        "salary_max": 18.00,
        "salary_period": "hour",
        "salary_published": True,
        "industry": "Aviation",
        "employment_type": "Full-time",
        "posted_date": "2026-10-06",
        "source": "demo",
        "application_url": None,
        "verified": False
    },
    {
        "id": "demo-003",
        "title": "Warehouse Associate",
        "company": "Demo Logistics",
        "location": "Catano, PR",
        "salary_min": 16.00,
        "salary_max": 19.00,
        "salary_period": "hour",
        "salary_published": True,
        "industry": "Logistics",
        "employment_type": "Full-time",
        "posted_date": "2026-10-06",
        "source": "demo",
        "application_url": None,
        "verified": False
    }
]


@app.route("/")
def home():
    return jsonify({
        "agent": "PR Intelligence Agent",
        "status": "online",
        "version": "1.1.0",
        "description": "Puerto Rico employment intelligence service"
    })


@app.route("/.well-known/agent.json")
def agent_manifest():
    return jsonify({
        "name": "PR Intelligence Agent",
        "description": "Puerto Rico employment intelligence service for AI agents.",
        "version": "1.1.0",
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

    location = request.args.get("location", "").lower()
    industry = request.args.get("industry", "").lower()
    employment_type = request.args.get(
        "employment_type", ""
    ).lower()

    min_salary = request.args.get("min_salary", type=float)
    max_salary = request.args.get("max_salary", type=float)

    results = JOBS

    if location:
        results = [
            job for job in results
            if location in job["location"].lower()
        ]

    if industry:
        results = [
            job for job in results
            if industry in job["industry"].lower()
        ]

    if employment_type:
        results = [
            job for job in results
            if employment_type in job["employment_type"].lower()
        ]

    if min_salary is not None:
        results = [
            job for job in results
            if (
                job["salary_max"] is not None
                and job["salary_max"] >= min_salary
            )
        ]

    if max_salary is not None:
        results = [
            job for job in results
            if (
                job["salary_min"] is not None
                and job["salary_min"] <= max_salary
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
