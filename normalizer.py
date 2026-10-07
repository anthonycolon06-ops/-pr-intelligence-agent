from datetime import datetime


def normalize_greenhouse_job(job, company_name, board_token):
    location_name = job.get("location", {}).get("name", "")

    return {
        "job_id": f"greenhouse-{board_token}-{job.get('id')}",
        "title": job.get("title"),
        "company": company_name,

        "location": {
            "municipality": location_name,
            "region": "Puerto Rico",
            "country": "PR"
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
        "work_mode": "On-site",

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
