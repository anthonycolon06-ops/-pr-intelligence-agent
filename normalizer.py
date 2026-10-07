from datetime import datetime


def normalize_greenhouse_job(job, company_name, board_token):

    location_name = job.get("location", {}).get("name", "")

    location_lower = location_name.lower()

    is_puerto_rico = (
        "puerto rico" in location_lower
        or ", pr" in location_lower
        or location_lower == "pr"
        or "san juan" in location_lower
        or "bayamon" in location_lower
        or "carolina" in location_lower
        or "caguas" in location_lower
        or "ponce" in location_lower
        or "mayaguez" in location_lower
    )

    if is_puerto_rico:
        country = "PR"
        region = "Puerto Rico"
    else:
        country = None
        region = None

    return {
        "job_id": f"greenhouse-{board_token}-{job.get('id')}",

        "title": job.get("title"),

        "company": company_name,

        "location": {
            "raw": location_name,
            "municipality": location_name,
            "region": region,
            "country": country
        },

        "industry": "Other",

        "salary": {
            "min": None,
            "max": None,
            "currency": "USD",
            "period": "unknown",
            "published": False
        },

        "employment_type": "Unknown",

        "work_mode": "Unknown",

        "posted_date": None,

        "updated_date": job.get("updated_at"),

        "source": {
            "name": "Greenhouse",
            "type": "job_board_api",
            "url": job.get("absolute_url"),
            "application_url": job.get("absolute_url")
        },

        "verification": {
            "status": "source_verified",
            "checked_at": datetime.utcnow().isoformat()
        },

        "requirements": {
            "education": [],
            "experience": None,
            "licenses": []
        }
    }
