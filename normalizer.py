
import re
import html
from datetime import datetime, timezone


US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia"
}

STATE_CODE_TO_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "U.S. Virgin Islands",
    "AS": "American Samoa", "MP": "Northern Mariana Islands"
}

COUNTRY_ALIASES = {
    "us": "United States", "usa": "United States",
    "u.s.": "United States", "u.s.a.": "United States",
    "united states of america": "United States",
    "united states": "United States",
    "pr": "Puerto Rico", "pri": "Puerto Rico",
    "puerto rico": "Puerto Rico",
    "uk": "United Kingdom", "u.k.": "United Kingdom",
    "gb": "United Kingdom", "great britain": "United Kingdom",
    "uae": "United Arab Emirates", "ksa": "Saudi Arabia",
    "in": "India", "pl": "Poland", "ca": "Canada",
    "au": "Australia", "nz": "New Zealand", "de": "Germany",
    "fr": "France", "es": "Spain", "it": "Italy",
    "nl": "Netherlands", "br": "Brazil", "mx": "Mexico",
    "sg": "Singapore", "ph": "Philippines", "ie": "Ireland",
    "jp": "Japan", "kr": "South Korea", "cn": "China",
    "za": "South Africa", "ch": "Switzerland", "se": "Sweden",
    "no": "Norway", "dk": "Denmark", "fi": "Finland",
    "pt": "Portugal", "be": "Belgium", "at": "Austria",
    "cz": "Czechia", "ro": "Romania", "gr": "Greece",
    "tr": "Turkey", "il": "Israel", "ar": "Argentina",
    "cl": "Chile", "co": "Colombia", "cr": "Costa Rica"
}


def normalize_space(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def decode_greenhouse_content(content):
    if not content:
        return ""
    return html.unescape(str(content))


def html_to_text(value):
    if not value:
        return ""
    value = str(value)
    value = re.sub(r"(?is)<(script|style)\b.*?>.*?</\1>", " ", value)
    value = re.sub(
        r"(?i)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>",
        "\n", value
    )
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return normalize_space(html.unescape(value))


def get_job_content(job):
    if not isinstance(job, dict):
        return ""
    for key in (
        "content", "description", "descriptionPlain", "descriptionText",
        "jobDescription", "job_description", "jobAd"
    ):
        value = job.get(key)
        if isinstance(value, dict):
            value = value.get("text") or value.get("description") or ""
        if value:
            return html_to_text(value)
    return ""


def _location_raw(job):
    if isinstance(job, str):
        return normalize_space(job)
    if not isinstance(job, dict):
        return ""

    location = job.get("location")
    if isinstance(location, dict):
        raw = normalize_space(location.get("raw"))
        if raw:
            return raw
        parts = []
        for key in ("name", "city", "municipality", "region", "state", "country"):
            value = normalize_space(location.get(key))
            if value and value not in parts:
                parts.append(value)
        if parts:
            return ", ".join(parts)
    elif location:
        return normalize_space(location)

    offices = job.get("offices") or job.get("locations") or []
    if isinstance(offices, list):
        names = []
        for office in offices:
            if isinstance(office, dict):
                name = office.get("name") or office.get("location") or office.get("city")
            else:
                name = office
            name = normalize_space(name)
            if name and name not in names:
                names.append(name)
        if names:
            return ", ".join(names)

    for key in ("locationName", "location_name", "workplace", "address"):
        value = job.get(key)
        if isinstance(value, dict):
            value = ", ".join(
                normalize_space(value.get(k))
                for k in ("city", "region", "country")
                if value.get(k)
            )
        if value:
            return normalize_space(value)
    return ""


def extract_location(job):
    raw = _location_raw(job)
    low = raw.lower()
    result = {
        "country": None,
        "municipality": None,
        "raw": raw,
        "region": None
    }
    if not raw:
        return result

    # Do not invent a physical location for remote jobs.
    if re.search(r"\b(remote|work from home|distributed|anywhere)\b", low):
        if re.search(r"\b(united states|u\.s\.|usa|us only|remote - us)\b", low):
            result["country"] = "United States"
        elif "puerto rico" in low or re.search(r"\bremote\s*[-,]\s*pr\b", low):
            result["country"] = "Puerto Rico"
        return result

    if "puerto rico" in low or re.search(r"(?:,\s*|\b)PR$", raw.strip(), re.I):
        result["country"] = "Puerto Rico"
        parts = [normalize_space(p) for p in raw.split(",") if normalize_space(p)]
        for part in parts:
            if part.lower() not in {
                "puerto rico", "pr", "pri", "united states", "usa", "us",
                "remote", "hybrid"
            }:
                result["municipality"] = part
                break
        return result

    # Prefer structured location data when the source provides it.
    if isinstance(job, dict) and isinstance(job.get("location"), dict):
        loc = job["location"]
        country = normalize_space(loc.get("country") or loc.get("countryCode"))
        region = normalize_space(loc.get("region") or loc.get("state"))
        city = normalize_space(loc.get("city") or loc.get("municipality"))

        if country:
            result["country"] = COUNTRY_ALIASES.get(country.lower(), country)
        if region:
            result["region"] = STATE_CODE_TO_NAME.get(region.upper(), region)
        if city:
            result["municipality"] = city

        if country or region or city:
            return result

    parts = [normalize_space(p) for p in raw.split(",") if normalize_space(p)]
    last = parts[-1] if parts else raw
    last_low = last.lower()

    # City, State, Country
    if last_low in {"united states", "usa", "us", "u.s.", "u.s.a."} and len(parts) >= 2:
        state = parts[-2]
        if state.lower() in US_STATES or state.upper() in STATE_CODE_TO_NAME:
            result["country"] = "United States"
            result["region"] = STATE_CODE_TO_NAME.get(state.upper(), state.title())
            result["municipality"] = parts[0] if len(parts) >= 3 else None
            return result

    if last_low in COUNTRY_ALIASES:
        result["country"] = COUNTRY_ALIASES[last_low]
        if len(parts) >= 2:
            result["municipality"] = parts[0]
        if len(parts) >= 3:
            result["region"] = parts[-2]
        return result

    # City, state name or abbreviation.
    if len(parts) >= 2:
        state = parts[-1]
        if state.lower() in US_STATES or state.upper() in STATE_CODE_TO_NAME:
            result["country"] = "United States"
            result["region"] = STATE_CODE_TO_NAME.get(state.upper(), state.title())
            result["municipality"] = parts[0]
            return result

    # A country name anywhere in the raw location.
    for alias, canonical in sorted(
        COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", low):
            result["country"] = canonical
            if len(parts) >= 2:
                result["municipality"] = parts[0]
            if len(parts) >= 3:
                result["region"] = parts[-2]
            return result

    # Preserve unknown locations without claiming a country.
    if len(parts) >= 2:
        result["municipality"] = parts[0]
        result["region"] = parts[1]
    else:
        result["municipality"] = raw
    return result


def extract_eligibility(text):
    content = normalize_space(text)
    result = {"countries": [], "states": [], "territories": []}
    if not content:
        return result

    low = content.lower()
    markers = (
        "eligible locations", "eligible location", "must be located in",
        "locations:", "location:", "work authorization",
        "authorized to work in", "candidates must reside in",
        "must reside in", "based in", "remote in", "remote within",
        "available in"
    )
    relevant = low
    for marker in markers:
        idx = low.find(marker)
        if idx >= 0:
            relevant = low[idx:idx + 1500]
            break

    if "puerto rico" in relevant:
        result["territories"].append("Puerto Rico")

    territory_aliases = {
        "guam": "Guam",
        "u.s. virgin islands": "U.S. Virgin Islands",
        "us virgin islands": "U.S. Virgin Islands",
        "american samoa": "American Samoa",
        "northern mariana islands": "Northern Mariana Islands"
    }
    for alias, canonical in territory_aliases.items():
        if alias in relevant and canonical not in result["territories"]:
            result["territories"].append(canonical)

    if re.search(r"\b(united states|u\.s\.|usa|us-based|within the us)\b", relevant):
        result["countries"].append("United States")
    if "canada" in relevant:
        result["countries"].append("Canada")
    if "united kingdom" in relevant:
        result["countries"].append("United Kingdom")

    for state in US_STATES:
        if re.search(r"(?<!\w)" + re.escape(state) + r"(?!\w)", relevant):
            result["states"].append(state.title())

    for code, name in STATE_CODE_TO_NAME.items():
        if code in {"PR", "GU", "VI", "AS", "MP"}:
            continue
        if re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", relevant):
            result["states"].append(name)

    result["countries"] = sorted(set(result["countries"]))
    result["states"] = sorted(set(result["states"]))
    result["territories"] = sorted(set(result["territories"]))
    return result


def normalize_salary_period(period):
    value = normalize_space(period).lower().replace(".", "")
    if not value:
        return "unknown"

    if any(term in value for term in (
        "hour", "hourly", "per hour", "/hr", " hr", "hrly"
    )) or value in {"h", "hr", "hrs"}:
        return "hour"
    if any(term in value for term in (
        "biweekly", "bi-weekly", "every two weeks", "per pay period"
    )):
        return "biweekly"
    if any(term in value for term in (
        "day", "daily", "per diem", "/day"
    )) or value in {"d", "dy"}:
        return "day"
    if any(term in value for term in (
        "week", "weekly", "per week", "/wk"
    )) or value in {"w", "wk", "wks"}:
        return "week"
    if any(term in value for term in (
        "month", "monthly", "per month", "/mo"
    )) or value in {"mo", "mos"}:
        return "month"
    if any(term in value for term in (
        "year", "yearly", "annual", "annually", "per annum", "/yr"
    )) or value in {"yr", "yrs", "y"}:
        return "year"
    return "unknown"


def _salary_number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = normalize_space(value).replace(",", "")
    match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", text)
    return float(match.group(1)) if match else None


def extract_salary(text):
    """
    Extract salary only when a plausible salary phrase is present.
    Unknown pay periods remain unknown; no period is invented.
    """
    content = html_to_text(text)
    empty = {
        "min": None, "max": None, "currency": None,
        "period": "unknown", "display": None
    }
    if not content:
        return empty

    patterns = [
        r"(?is)(?:salary|pay|compensation|wage|rate|earnings|base pay|base salary|salary range|pay range)"
        r"[^.\n]{0,100}?"
        r"((?:USD\s*)?\$?\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:k|K)?"
        r"(?:\s*(?:-|–|—|to)\s*(?:USD\s*)?\$?\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:k|K)?)?)"
        r"\s*(per\s+hour|per\s+day|per\s+week|per\s+month|per\s+year|hourly|daily|weekly|monthly|annually|annual|yearly|hour|day|week|month|year|/hr|/hour|/year)?",
        r"(?is)((?:USD\s*)?\$\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:k|K)?"
        r"\s*(?:-|–|—|to)\s*(?:USD\s*)?\$?\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:k|K)?)"
        r"\s*(per\s+hour|per\s+day|per\s+week|per\s+month|per\s+year|hourly|daily|weekly|monthly|annually|annual|yearly|hour|day|week|month|year|/hr|/hour|/year)"
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if not match:
            continue

        amounts_text = match.group(1)
        period_text = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
        numbers = []
        for number, suffix in re.findall(
            r"\$?\s*(\d[\d,]*(?:\.\d{1,2})?)\s*([kK]?)",
            amounts_text
        ):
            try:
                parsed = float(number.replace(",", ""))
                if suffix.lower() == "k":
                    parsed *= 1000
                numbers.append(parsed)
            except (ValueError, TypeError):
                continue

        if numbers:
            minimum = min(numbers)
            maximum = max(numbers) if len(numbers) > 1 else minimum
            return {
                "min": minimum,
                "max": maximum,
                "currency": "USD" if "$" in amounts_text or "USD" in amounts_text.upper() else None,
                "period": normalize_salary_period(period_text),
                "display": normalize_space(match.group(0))[:240]
            }

    return empty


def _salary_from_job_fields(job):
    if not isinstance(job, dict):
        return None

    for key in ("salary", "salary_range", "salaryRange", "compensation", "payRange"):
        value = job.get(key)
        if not value:
            continue

        if isinstance(value, dict):
            minimum = _salary_number(
                value.get("min") or value.get("minimum") or value.get("minValue")
            )
            maximum = _salary_number(
                value.get("max") or value.get("maximum") or value.get("maxValue")
            )
            currency = value.get("currency") or value.get("currencyCode")
            period = normalize_salary_period(
                value.get("period") or value.get("interval") or
                value.get("unit") or value.get("payFrequency")
            )
            display = value.get("display") or value.get("description") or value.get("text")

            if minimum is not None or maximum is not None:
                if minimum is None:
                    minimum = maximum
                if maximum is None:
                    maximum = minimum
                if maximum < minimum:
                    minimum, maximum = maximum, minimum
                return {
                    "min": minimum,
                    "max": maximum,
                    "currency": currency or ("USD" if "$" in str(display or "") else None),
                    "period": period,
                    "display": normalize_space(display) or None
                }

        elif isinstance(value, (int, float)):
            return {
                "min": float(value), "max": float(value),
                "currency": None, "period": "unknown", "display": str(value)
            }
        else:
            parsed = extract_salary(value)
            if parsed["min"] is not None:
                return parsed

    return None


def extract_employment_type(text):
    value = normalize_space(text).lower()
    if not value:
        return "Unknown"
    if re.search(r"\b(full[\s-]?time|full time employment)\b", value):
        return "Full-time"
    if re.search(r"\b(part[\s-]?time|part time employment)\b", value):
        return "Part-time"
    if re.search(r"\b(internship|intern\b|interns\b)", value):
        return "Internship"
    if re.search(r"\b(temporary|temp position|seasonal)\b", value):
        return "Temporary"
    if re.search(r"\b(contractor|contract position|fixed[\s-]?term contract|contract employment)\b", value):
        return "Contract"
    if re.search(r"\b(permanent position|regular employee)\b", value):
        return "Permanent"
    return "Unknown"


def extract_industry(text, job=None):
    if isinstance(text, dict) and job is None:
        job = text
        text = get_job_content(job)

    title = ""
    department = ""
    if isinstance(job, dict):
        title = normalize_space(job.get("title") or job.get("name"))
        departments = job.get("departments") or job.get("department") or job.get("team") or ""
        if isinstance(departments, list):
            department = " ".join(
                normalize_space(item.get("name") if isinstance(item, dict) else item)
                for item in departments
            )
        elif isinstance(departments, dict):
            department = normalize_space(departments.get("name"))
        else:
            department = normalize_space(departments)

    combined = f"{title} {department} {normalize_space(text)}".lower()

    rules = [
        ("Healthcare", r"\b(nurse|nursing|physician|doctor|medical|clinical|patient|pharmacy|therapist|hospital|healthcare|health care|dental)\b"),
        ("Aviation", r"\b(aircraft|aviation|airline|airport|flight crew|pilot|avionics|a&p mechanic|ground handling|ramp agent|line service technician|air cargo)\b"),
        ("Manufacturing", r"\b(manufactur\w*|production operator|production worker|assembly line|fabrication|machinist|quality inspector|plant operator)\b"),
        ("Logistics", r"\b(warehouse|inventory|fulfillment|distribution center|shipping|receiving|freight|cargo|supply chain|material handler|picker|packer)\b"),
        ("Construction", r"\b(construction|carpenter|concrete|electrician|plumber|welder|mason|heavy equipment|jobsite)\b"),
        ("Maintenance", r"\b(maintenance|facilities technician|building engineer|repair technician|mechanic|hvac|refrigeration|groundskeeper)\b"),
        ("Transportation", r"\b(truck driver|delivery driver|fleet|transportation|bus driver|courier|dispatcher|driver\b)\b"),
        ("Restaurants", r"\b(cook|chef|line cook|dishwasher|server|waiter|waitress|restaurant|food prep|barista)\b"),
        ("Hospitality", r"\b(hotel|resort|guest services|housekeeping|front desk|concierge|event staff|tourism)\b"),
        ("Retail", r"\b(retail|cashier|sales associate|store associate|merchandis|stock associate|store manager)\b"),
        ("Security", r"\b(security guard|security officer|loss prevention|protective services|surveillance)\b"),
        ("Customer Service", r"\b(customer service|call center|contact center|client support|customer care|help desk)\b"),
        ("Finance", r"\b(accountant|accounting|bookkeep|financial analyst|banking|investment|payroll|accounts payable|accounts receivable|auditor)\b"),
        ("Government", r"\b(government|public sector|municipal|federal agency|civil service|public administration)\b"),
        ("Education", r"\b(teacher|educator|school|university|professor|instructor|tutor|curriculum|academic)\b"),
        ("Sales", r"\b(sales representative|account executive|business development|sales manager|account manager|\bsales\b)\b"),
        ("Marketing & Design", r"\b(marketing|graphic design|designer|creative director|copywriter|brand|communications|social media)\b"),
        ("Administrative", r"\b(administrative assistant|office assistant|receptionist|office manager|executive assistant|data entry|clerical)\b"),
        ("Technology", r"\b(software|developer|programmer|information technology|cybersecurity|data engineer|machine learning|artificial intelligence|cloud engineer|devops|systems analyst|product manager|ux designer|it support)\b"),
        ("Engineering", r"\b(civil engineer|mechanical engineer|electrical engineer|industrial engineer|chemical engineer|aerospace engineer|engineering technician)\b"),
    ]

    for industry, pattern in rules:
        if re.search(pattern, combined):
            return industry
    return "Other"


def extract_work_mode(text):
    value = normalize_space(text).lower()
    if not value:
        return "Unknown"
    if re.search(r"\b(hybrid|partially remote|remote and on[- ]site|mix of remote and office)\b", value):
        return "Hybrid"
    if re.search(r"\b(fully remote|100% remote|remote position|remote role|work from home|work remotely|remote[- ]first|distributed team|anywhere in the world|remote)\b", value):
        return "Remote"
    if re.search(r"\b(on[- ]site|onsite|in[- ]person|in office|office based|office-based|must be present at|work at our facility)\b", value):
        return "On-site"
    return "Unknown"


def extract_education(text):
    value = normalize_space(text).lower()
    requirements = []
    patterns = [
        (r"\b(ph\.?d\.?|doctorate|doctoral degree)\b", "Doctorate"),
        (r"\b(master'?s degree|master of|mba)\b", "Master's degree"),
        (r"\b(bachelor'?s degree|bachelor of|undergraduate degree)\b", "Bachelor's degree"),
        (r"\b(associate'?s degree|associate degree)\b", "Associate degree"),
        (r"\b(high school diploma|high school degree|ged)\b", "High school diploma or equivalent"),
        (r"\b(technical diploma|vocational diploma|trade school)\b", "Technical/vocational education"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, value):
            requirements.append(label)
    return requirements


def extract_experience(text):
    value = normalize_space(text).lower()
    details = []
    patterns = [
        r"\b(?:minimum of|at least|min\.?)\s*(\d{1,2})\+?\s+years?(?:\s+of)?\s+(?:relevant\s+)?experience\b",
        r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s+years?(?:\s+of)?\s+(?:relevant\s+)?experience\b",
        r"\b(\d{1,2})\+?\s+years?(?:\s+of)?\s+(?:relevant\s+)?experience\b",
        r"\bexperience\s+of\s+(\d{1,2})\+?\s+years?\b",
    ]
    years = None
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            years = int(match.group(1))
            details.append(normalize_space(match.group(0)))
            break
    return {"years": years, "details": details}


def extract_licenses(text):
    value = normalize_space(text).lower()
    licenses = []
    patterns = [
        (r"\ba&p\b|airframe and powerplant", "A&P license"),
        (r"\bfaa\b.{0,30}\b(certificate|license|licence)\b", "FAA certificate/license"),
        (r"\b(cdl|commercial driver'?s license)\b", "Commercial driver's license (CDL)"),
        (r"\b(valid driver'?s license|driver'?s license required)\b", "Driver's license"),
        (r"\b(rn license|registered nurse license|licensed registered nurse)\b", "Registered Nurse license"),
        (r"\b(cpa license|certified public accountant)\b", "CPA license"),
        (r"\b(epa 608|epa certification)\b", "EPA certification"),
        (r"\b(osha 10|osha 30)\b", "OSHA certification"),
        (r"\b(license|licence|certification|certified)\b", "Other license/certification (details in description)"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, value) and label not in licenses:
            licenses.append(label)
    return licenses


def parse_date_value(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        try:
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return None

    raw = normalize_space(value)
    if not raw:
        return None

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y",
        "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y",
        "%Y/%m/%d", "%Y.%m.%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def extract_dates(job):
    """Only use publication/creation fields; don't mistake update dates for posting dates."""
    if not isinstance(job, dict):
        return None

    fields = (
        "posted_date", "postedDate", "first_published", "firstPublished",
        "published_at", "publishedAt", "date_posted", "datePosted",
        "releasedDate", "releasedDateTime", "created_at", "createdAt"
    )
    for field in fields:
        value = job.get(field)
        if value is not None:
            parsed = parse_date_value(value)
            if parsed:
                return parsed
    return None


def build_source(job, board=None, company=None):
    if not isinstance(job, dict):
        job = {}

    source = job.get("source")
    result = dict(source) if isinstance(source, dict) else {}
    result.setdefault("board", board or job.get("board") or job.get("board_token"))
    result.setdefault("company", company or job.get("company") or job.get("companyName"))
    result.setdefault(
        "url",
        job.get("absolute_url") or job.get("hostedUrl") or
        job.get("jobUrl") or job.get("url")
    )
    return result


def normalize_greenhouse_job(job, company=None, board="greenhouse"):
    """
    Normalize a Greenhouse-style job and preserve the fields expected by app.py.
    """
    if not isinstance(job, dict):
        job = {}

    title = normalize_space(job.get("title") or job.get("name") or job.get("jobTitle"))
    description = get_job_content(job)
    location = extract_location(job)

    departments = job.get("departments") or job.get("department") or job.get("team") or []
    if isinstance(departments, list):
        department = ", ".join(
            normalize_space(item.get("name") if isinstance(item, dict) else item)
            for item in departments
            if normalize_space(item.get("name") if isinstance(item, dict) else item)
        )
    elif isinstance(departments, dict):
        department = normalize_space(departments.get("name"))
    else:
        department = normalize_space(departments)

    salary = _salary_from_job_fields(job)
    if salary is None:
        salary_text = " ".join(
            normalize_space(job.get(key))
            for key in ("salary", "salary_range", "salaryRange", "compensation", "payRange")
            if isinstance(job.get(key), str)
        )
        salary = extract_salary(salary_text or description)

    posted_date = extract_dates(job)

    employment_type = normalize_space(
        job.get("employment_type") or job.get("employmentType") or
        job.get("typeOfEmployment") or job.get("commitment")
    ) or extract_employment_type(" ".join([title, description]))

    employment_map = {
        "fulltime": "Full-time", "full time": "Full-time",
        "parttime": "Part-time", "part time": "Part-time",
        "intern": "Internship", "internship": "Internship",
        "temporary": "Temporary", "temp": "Temporary",
        "contract": "Contract"
    }
    employment_type = employment_map.get(employment_type.lower(), employment_type or "Unknown")

    mode_source = " ".join([
        title,
        normalize_space(job.get("work_mode") or job.get("workMode") or job.get("workplaceType")),
        location.get("raw") or "",
        description[:5000]
    ])
    work_mode = normalize_space(
        job.get("work_mode") or job.get("workMode") or job.get("workplaceType")
    )
    if work_mode.lower() in {"remote", "hybrid", "on-site", "onsite", "on site"}:
        mode_map = {"onsite": "On-site", "on site": "On-site"}
        work_mode = mode_map.get(work_mode.lower(), work_mode.title() if work_mode.lower() != "on-site" else "On-site")
    else:
        work_mode = extract_work_mode(mode_source)

    source_url = (
        job.get("absolute_url") or job.get("hostedUrl") or job.get("applyUrl") or
        job.get("jobUrl") or job.get("url") or job.get("ref")
    )
    job_id = (
        job.get("job_id") or job.get("id") or job.get("requisition_id") or
        job.get("requisitionId") or job.get("external_id")
    )
    if job_id is None or normalize_space(job_id) == "":
        job_id = source_url or f"{board}-{title or 'unknown-job'}"

    actual_company = (
        job.get("companyName") or job.get("company_name") or
        (job.get("company") if isinstance(job.get("company"), str) else None) or
        company
    )

    source = build_source(job, board=board, company=actual_company)
    if source_url:
        source["url"] = source_url
    source["board"] = source.get("board") or board
    source["company"] = source.get("company") or actual_company

    content = " ".join([title, description])
    experience = extract_experience(content)

    return {
        "job_id": str(job_id),
        "title": title or "Unknown",
        "company": actual_company or "Unknown",
        "board": board,
        "location": location,
        "salary": salary,
        "posted_date": posted_date,
        "industry": extract_industry(
            description,
            job={**job, "title": title, "department": department}
        ),
        "work_mode": work_mode or "Unknown",
        "employment_type": employment_type or "Unknown",
        "requirements": {
            "education": extract_education(content),
            "experience": experience,
            "licenses": extract_licenses(content)
        },
        "eligibility": extract_eligibility(description),
        "description": description,
        "source": source,
        "url": source_url,
        "department": department
    }
