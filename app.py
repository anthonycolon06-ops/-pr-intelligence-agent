from flask import Flask, request, jsonify

app = Flask(__name__)

# Demo dataset.
# Later this will be replaced/expanded with real job sources.
JOBS = [
    {
        "title": "Production Worker",
        "location": "Bayamon, PR",
        "salary_min": 16.00,
        "salary_max": 20.00,
        "industry": "Manufacturing"
    },
    {
        "title": "Aircraft Ground Operations",
        "location": "Carolina, PR",
        "salary_min": 15.00,
        "salary_max": 18.00,
        "industry": "Aviation"
    },
    {
        "title": "Warehouse Associate",
        "location": "Cataño, PR",
        "salary_min": 16.00,
        "salary_max": 19.00,
        "industry": "Logistics"
    }
]


@app.route("/")
def home():
    return jsonify({
        "agent": "PR Intelligence Agent",
        "status": "online",
        "version": "1.0.0",
        "description": "Puerto Rico employment intelligence service"
    })


@app.route("/.well-known/agent.json")
def agent_manifest():
    return jsonify({
        "name": "PR Intelligence Agent",
        "description": "Puerto Rico employment intelligence service for AI agents.",
        "version": "1.0.0",
        "capabilities": [
            "job_search",
            "salary_filtering",
            "location_filtering",
            "industry_filtering",
            "job_intelligence"
        ],
        "coverage": {
            "country": "Puerto Rico",
            "industries": "multiple",
            "locations": "Puerto Rico"
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
    min_salary = request.args.get("min_salary", type=float)

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

    if min_salary is not None:
        results = [
            job for job in results
            if job["salary_max"] >= min_salary
        ]

    return jsonify({
        "count": len(results),
        "jobs": results
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
