
import re
import requests
from datetime import datetime, timezone


LEVER_API = "https://api.lever.co/v0/postings"

STATE_CODES = {
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

CODE_TO_STATE = {
    code: name.title()
    for name, code in STATE_CODES.items()
}


def get_lever_jobs(site):
    url = f"{LEVER_API}/{site}"

    response = requests.get(
        url,
        params={"mode": "json"},
        timeout=25,
        headers={"User-Agent": "PR-Intelligence-Agent/1.0"}
    )

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        return []

    return [
        normalize_lever_job(job, site)
        for job in data
        if isinstance(job, dict)
    ]


def normalize_lever_job(job, site):
    categories = job.get("categories") or {}

    raw_location = (
        categories.get("location")
        or ", ".join(categories.get("allLocations") or [])
        or "Location not specified"
    )

    location_text = str(raw_location).strip()
    lower_location = location_text.lower()

    country = None
    region = None
    municipality = location_text

    if "puerto rico" in lower_location:
        country = "PR"
        region = "Puerto Rico"

    else:
        for state_name, code in STATE_CODES.items():
            if (
                state_name in lower_location
                or re.search(
                    r"\b" + re.escape(code) + r"\b",
                    location_text.upper()
                )
            ):
                country = "US"
                region = code

                municipality = re.sub(
                    r",?\s*" + re.escape(state_name) + r"\b",
                    "",
                    municipality,
                    flags=re.IGNORECASE
                ).strip(" ,")

                municipality = re.sub(
                    r",?\s*" + re.escape(code) + r"\b",
                    "",
                    municipality,
                    flags=re.IGNORECASE
                ).strip(" ,")

                break

        if any(x in lower_location for x in [
            "united states", "usa", "remote - us",
            "remote, us", "remote (us)"
        ]):
            country = "US"

    if "remote" in lower_location:
        work_mode = "Remote"
    elif "hybrid" in lower_location:
        work_mode = "Hybrid"
    else:
        work_mode = "On-site"

    commitment = str(categories.get("commitment") or "")
    if "full" in commitment.lower():
        employment_type = "Full-time"
    elif "part" in commitment.lower():
        employment_type = "Part-time"
    elif "contract" in commitment.lower():
        employment_type = "Contract"
    elif "intern" in commitment.lower():
        employment_type = "Internship"
    else:
        employment_type = commitment or "Unknown"

    salary_data = job.get("salaryRange") or {}

    salary_min = salary_data.get("min")
    salary_max = salary_data.get("max")
    salary_currency = salary_data.get("currency") or "USD"
    salary_period = salary_data.get("interval") or "unknown"

    created_at = job.get("createdAt")
    posted_date = None

    if created_at:
        try:
            posted_date = datetime.fromtimestamp(
                float(created_at) / 1000,
                tz=timezone.utc
            ).date().isoformat()
        except (ValueError, TypeError, OverflowError):
            pass

    title = job.get("text") or "Untitled position"
    description = job.get("descriptionPlain") or ""

    if not description and job.get("description"):
        description = re.sub(
            r"<[^>]+>",
            " ",
            str(job["description"])
        )

    hosted_url = job.get("hostedUrl")
    apply_url = job.get("applyUrl") or hosted_url

    return {
        "company": site,
        "title": title,
        "job_id": f"lever-{site}-{job.get('id', title)}",
        "description": description,
        "location": {
            "country": country,
            "municipality": municipality or location_text,
            "raw": location_text,
            "region": region,
        },
        "salary": {
            "min": salary_min,
            "max": salary_max,
            "currency": salary_currency,
            "period": salary_period,
        },
        "employment_type": employment_type,
        "industry": "Other",
        "work_mode": work_mode,
        "requirements": {
            "education": [],
            "experience": None,
            "licenses": [],
        },
        "posted_date": posted_date,
        "updated_date": None,
        "source": {
            "name": "Lever",
            "url": hosted_url,
            "application_url": apply_url,
            "board": site,
        },
        "verification": {
            "source_type": "public_company_job_board",
            "verified": bool(hosted_url),
        },
    }
