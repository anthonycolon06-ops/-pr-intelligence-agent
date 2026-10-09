
import requests
from datetime import datetime, timezone

SMARTRECRUITERS_API = (
    "https://api.smartrecruiters.com/v1/companies"
)


def parse_date(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.date().isoformat()
    except (ValueError, TypeError):
        return None


def normalize_job(job, company):
    location = job.get("location") or {}

    city = location.get("city") or ""
    region = location.get("region") or ""
    country = str(location.get("country") or "").lower()
    remote = location.get("remote") is True

    raw_location = ", ".join(
        part for part in (city, region, country.upper()) if part
    )

    if country in ("pr", "puerto rico"):
        normalized_location = {
            "country": "PR",
            "municipality": city or raw_location,
            "region": "Puerto Rico",
            "raw": raw_location,
        }
    elif country in ("us", "usa", "united states"):
        normalized_location = {
            "country": "US",
            "municipality": city or raw_location,
            "region": region or None,
            "raw": raw_location,
        }
    else:
        normalized_location = {
            "country": None,
            "municipality": city or raw_location or "Location not specified",
            "region": region or None,
            "raw": raw_location,
        }

    employment = str(job.get("typeOfEmployment") or "Unknown")
    employment_lower = employment.lower()

    if "full" in employment_lower:
        employment_type = "Full-time"
    elif "part" in employment_lower:
        employment_type = "Part-time"
    elif "contract" in employment_lower:
        employment_type = "Contract"
    elif "intern" in employment_lower:
        employment_type = "Internship"
    else:
        employment_type = employment

    job_id = job.get("id") or job.get("uuid") or job.get("name")

    salary_data = job.get("salary") or {}
    salary_min = salary_data.get("min")
    salary_max = salary_data.get("max")
    salary_currency = salary_data.get("currency") or "USD"
    salary_period = salary_data.get("period") or "unknown"

    return {
        "company": (
            (job.get("company") or {}).get("name")
            or company
        ),
        "title": job.get("name") or "Untitled position",
        "job_id": f"smartrecruiters-{company}-{job_id}",
        "description": job.get("jobAd") or "",
        "location": normalized_location,
        "salary": {
            "min": salary_min,
            "max": salary_max,
            "currency": salary_currency,
            "period": salary_period,
        },
        "employment_type": employment_type,
        "industry": "Other",
        "work_mode": "Remote" if remote else "On-site",
        "requirements": {
            "education": [],
            "experience": None,
            "licenses": [],
        },
        "posted_date": parse_date(
            job.get("releasedDate") or job.get("releasedDateTime")
        ),
        "updated_date": parse_date(job.get("releasedDate")),
        "source": {
            "name": "SmartRecruiters",
            "url": job.get("ref"),
            "application_url": (
                job.get("applyUrl")
                or job.get("jobAdUrl")
            ),
            "board": company,
        },
        "verification": {
            "source_type": "public_company_job_board",
            "verified": bool(job.get("applyUrl") or job.get("jobAdUrl")),
        },
    }


def get_smartrecruiters_jobs(company):
    results = []
    limit = 100
    offset = 0

    for _ in range(10):
        response = requests.get(
            f"{SMARTRECRUITERS_API}/{company}/postings",
            params={"limit": limit, "offset": offset},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()

        if isinstance(payload, list):
            jobs = payload
            total = len(payload)
        elif isinstance(payload, dict):
            jobs = (
                payload.get("content")
                or payload.get("postings")
                or payload.get("jobs")
                or []
            )
            total = payload.get("totalFound", len(jobs))
        else:
            break

        if not jobs:
            break

        for job in jobs:
            if isinstance(job, dict):
                results.append(normalize_job(job, company))

        offset += len(jobs)

        if len(jobs) < limit or offset >= int(total):
            break

    return results
