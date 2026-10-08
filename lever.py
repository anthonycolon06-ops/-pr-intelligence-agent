
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
    """Fetch and normalize public postings from one Lever board."""
    url = f"{LEVER_API}/{site}"

    response = requests.get(
        url,
        params={"mode": "json"},
        timeout=25,
        headers={
            "Accept": "application/json",
            "User-Agent": "PR-Intelligence-Agent/1.0",
        },
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        return []

    results = []
    for job in data:
        if not isinstance(job, dict):
            continue

        normalized = normalize_lever_job(job, site)
        if normalized:
            results.append(normalized)

    return results


def detect_location(raw_location):
    raw = str(raw_location or "").strip()
    lower = raw.lower()

    if not raw:
        return {
            "country": None,
            "municipality": "Location not specified",
            "raw": "",
            "region": None,
        }

    if "puerto rico" in lower:
        return {
            "country": "PR",
            "municipality": raw,
            "raw": raw,
            "region": "Puerto Rico",
        }

    # Recognize state names first.
    for state_name, code in STATE_CODES.items():
        if state_name in lower:
            municipality = re.sub(
                r",?\s*" + re.escape(state_name) + r"\b",
                "",
                raw,
                flags=re.IGNORECASE,
            ).strip(" ,")

            return {
                "country": "US",
                "municipality": municipality or raw,
                "raw": raw,
                "region": code,
            }

    # Recognize a state abbreviation as a separate token.
    for code in CODE_TO_STATE:
        if re.search(
            r"(?:,|\s)\s*" + re.escape(code) + r"\s*$",
            raw.upper(),
        ):
            municipality = re.sub(
                r",?\s*" + re.escape(code) + r"\s*$",
                "",
                raw,
                flags=re.IGNORECASE,
            ).strip(" ,")

            return {
                "country": "US",
                "municipality": municipality or raw,
                "raw": raw,
                "region": code,
            }

    if any(term in lower for term in (
        "united states",
        "united states of america",
        "remote - us",
        "remote, us",
        "remote (us)",
        "usa",
    )):
        return {
            "country": "US",
            "municipality": raw,
            "raw": raw,
            "region": None,
        }

    # Do not assume that an unrecognized location is in the US.
    return {
        "country": None,
        "municipality": raw,
        "raw": raw,
        "region": None,
    }


def normalize_lever_job(job, site):
    categories = job.get("categories") or {}

    all_locations = categories.get("allLocations") or []
    raw_location = (
        categories.get("location")
        or ", ".join(str(item) for item in all_locations)
        or "Location not specified"
    )

    location = detect_location(raw_location)
    lower_location = str(raw_location).lower()

    if "remote" in lower_location:
        work_mode = "Remote"
    elif "hybrid" in lower_location:
        work_mode = "Hybrid"
    else:
        work_mode = "On-site"

    commitment = str(categories.get("commitment") or "")
    commitment_lower = commitment.lower()

    if "full" in commitment_lower:
        employment_type = "Full-time"
    elif "part" in commitment_lower:
        employment_type = "Part-time"
    elif "contract" in commitment_lower or "temporary" in commitment_lower:
        employment_type = "Contract"
    elif "intern" in commitment_lower:
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

    if created_at is not None:
        try:
            timestamp = float(created_at)
            # Lever timestamps are generally milliseconds.
            if timestamp > 10_000_000_000:
                timestamp /= 1000

            posted_date = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            ).date().isoformat()
        except (ValueError, TypeError, OverflowError, OSError):
            posted_date = None

    title = job.get("text") or "Untitled position"
    description = job.get("descriptionPlain") or ""

    if not description and job.get("description"):
        description = re.sub(
            r"<[^>]+>",
            " ",
            str(job["description"]),
        )
        description = re.sub(r"\s+", " ", description).strip()

    hosted_url = job.get("hostedUrl")
    apply_url = job.get("applyUrl") or hosted_url
    job_id = job.get("id") or title

    return {
        "company": site,
        "title": title,
        "job_id": f"lever-{site}-{job_id}",
        "description": description,
        "location": location,
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
