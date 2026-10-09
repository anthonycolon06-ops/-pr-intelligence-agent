
import re
import requests
from datetime import datetime, timezone

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board"


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


def parse_compensation(value):
    text = str(value or "")
    numbers = re.findall(
        r"(?<![A-Za-z])\$\s*([\d,]+(?:\.\d+)?)",
        text,
    )

    values = []
    for number in numbers[:2]:
        try:
            values.append(float(number.replace(",", "")))
        except ValueError:
            pass

    return {
        "min": values[0] if values else None,
        "max": values[1] if len(values) > 1 else (
            values[0] if values else None
        ),
        "currency": "USD",
        "period": "unknown",
        "display": text or None,
    }


def get_ashby_jobs(board):
    response = requests.get(
        f"{ASHBY_API}/{board}",
        params={"includeCompensation": "true"},
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()

    payload = response.json()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

    results = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        if job.get("isListed") is False:
            continue

        location_text = job.get("location") or ""
        secondary = job.get("secondaryLocations") or []

        if not location_text and secondary:
            location_text = ", ".join(
                str(item.get("location") or "")
                if isinstance(item, dict)
                else str(item)
                for item in secondary
            )

        address = job.get("address") or {}
        postal = address.get("postalAddress") or {}

        city = postal.get("addressLocality")
        region = postal.get("addressRegion")
        country = postal.get("addressCountry")

        if not location_text:
            location_text = ", ".join(
                str(part) for part in (city, region, country) if part
            )

        lower_location = location_text.lower()

        if "puerto rico" in lower_location or country in ("PR", "pr"):
            normalized_location = {
                "country": "PR",
                "municipality": city or location_text,
                "region": "Puerto Rico",
                "raw": location_text,
            }
        elif country and str(country).lower() in (
            "us", "usa", "united states", "united states of america"
        ):
            normalized_location = {
                "country": "US",
                "municipality": city or location_text,
                "region": region,
                "raw": location_text,
            }
        else:
            normalized_location = {
                "country": None,
                "municipality": city or location_text or "Location not specified",
                "region": region,
                "raw": location_text,
            }

        if "remote" in lower_location:
            work_mode = "Remote"
        elif "hybrid" in lower_location:
            work_mode = "Hybrid"
        else:
            work_mode = "On-site"

        employment = str(job.get("employmentType") or "Unknown")
        employment_map = {
            "fulltime": "Full-time",
            "parttime": "Part-time",
            "intern": "Internship",
            "contract": "Contract",
            "temporary": "Temporary",
        }
        employment_type = employment_map.get(
            employment.lower(), employment
        )

        compensation = job.get("compensation") or {}
        salary_text = (
            compensation.get("scrapeableCompensationSalarySummary")
            or compensation.get("compensationTierSummary")
            or ""
        )

        salary = parse_compensation(salary_text)

        results.append({
            "company": board,
            "title": job.get("title") or "Untitled position",
            "job_id": f"ashby-{board}-{job.get('id') or job.get('jobUrl')}",
            "description": (
                job.get("descriptionPlain")
                or job.get("descriptionHtml")
                or ""
            ),
            "location": normalized_location,
            "salary": salary,
            "employment_type": employment_type,
            "industry": "Other",
            "work_mode": work_mode,
            "requirements": {
                "education": [],
                "experience": None,
                "licenses": [],
            },
            "posted_date": parse_date(
                job.get("publishedAt") or job.get("updatedAt")
            ),
            "updated_date": parse_date(job.get("updatedAt")),
            "source": {
                "name": "Ashby",
                "url": job.get("jobUrl"),
                "application_url": job.get("applyUrl") or job.get("jobUrl"),
                "board": board,
            },
            "verification": {
                "source_type": "public_company_job_board",
                "verified": bool(job.get("jobUrl")),
            },
        })

    return results
