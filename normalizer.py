import re
import html
from datetime import datetime, timezone


# ============================================================
# US STATES
# ============================================================

US_STATES = {
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

STATE_CODE_TO_NAME = {
    code.lower(): name
    for name, code in US_STATES.items()
}


# ============================================================
# GREENHOUSE CONTENT
# ============================================================

def decode_greenhouse_content(content):
    if not content:
        return ""

    decoded = str(content)

    for _ in range(4):
        decoded = html.unescape(decoded)

    decoded = decoded.replace("\\u0026", "&")
    decoded = decoded.replace("\\u003c", "<")
    decoded = decoded.replace("\\u003e", ">")
    decoded = decoded.replace("\\/", "/")

    return decoded


def html_to_text(content):
    if not content:
        return ""

    text = decode_greenhouse_content(content)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def get_job_content(job):
    content = job.get("content")

    if content:
        return html_to_text(content)

    description = job.get("description")

    if description:
        return html_to_text(description)

    return ""


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_space(value):
    if value is None:
        return None

    return re.sub(r"\s+", " ", str(value)).strip()


# ============================================================
# LOCATION
# ============================================================

def extract_location(job):
    """
    Normaliza la ubicación sin asumir que una ubicación
    desconocida pertenece a Estados Unidos.
    """

    location = job.get("location")
    raw = ""
    country_hint = ""

    if isinstance(location, dict):
        raw = location.get("name") or location.get("raw") or ""
        country_hint = str(location.get("country") or "").strip()

    elif isinstance(location, str):
        raw = location

    if not raw:
        offices = job.get("offices", [])

        if isinstance(offices, list):
            names = [
                str(office["name"])
                for office in offices
                if isinstance(office, dict) and office.get("name")
            ]

            if names:
                raw = ", ".join(names)

    raw = normalize_space(raw) or ""
    lowered = raw.lower()
    hint = country_hint.lower()

    country = None
    region = None
    municipality = raw or None

    # Puerto Rico
    if (
        "puerto rico" in lowered
        or hint in {"pr", "pri", "puerto rico"}
        or re.search(r",\s*PR$", raw, re.IGNORECASE)
    ):
        country = "PR"
        region = "Puerto Rico"

        match = re.fullmatch(
            r"(.+?),\s*(?:Puerto Rico|PR)",
            raw,
            re.IGNORECASE,
        )

        if match:
            municipality = match.group(1).strip()
        elif lowered in {"puerto rico", "pr"}:
            municipality = "Puerto Rico"
        else:
            municipality = raw or "Puerto Rico"

    else:
        state_codes = set(US_STATES.values())

        state_match = re.fullmatch(
            r"(.+?),\s*([A-Z]{2})"
            r"(?:,\s*(?:United States|USA|US))?",
            raw,
        )

        for state_name in sorted(US_STATES, key=len, reverse=True):
            match = re.fullmatch(
                r"(.+?),\s*"
                + re.escape(state_name)
                + r"(?:,\s*(?:United States|USA|US))?",
                raw,
                re.IGNORECASE,
            )

            if match:
                country = "US"
                region = US_STATES[state_name]
                municipality = match.group(1).strip()
                break

        if country is None and state_match:
            state_code = state_match.group(2).upper()

            if state_code in state_codes:
                country = "US"
                region = state_code
                municipality = state_match.group(1).strip()

        # Remote explícitamente limitado a Estados Unidos
        if country is None and re.fullmatch(
            r"(?:United States|USA|U\.S\.A\.?)"
            r"\s*(?:\(\s*Remote\s*\))?",
            raw,
            re.IGNORECASE,
        ):
            country = "US"
            municipality = "United States (Remote)"

        if country is None and re.fullmatch(
            r"(?:US|U\.S\.)\s*\(\s*Remote\s*\)",
            raw,
            re.IGNORECASE,
        ):
            country = "US"
            municipality = "United States (Remote)"

        countries = {
            "india": "IN",
            "poland": "PL",
            "canada": "CA",
            "united kingdom": "GB",
            "england": "GB",
            "ireland": "IE",
            "australia": "AU",
            "new zealand": "NZ",
            "germany": "DE",
            "france": "FR",
            "spain": "ES",
            "italy": "IT",
            "portugal": "PT",
            "netherlands": "NL",
            "brazil": "BR",
            "mexico": "MX",
            "philippines": "PH",
            "singapore": "SG",
            "japan": "JP",
            "china": "CN",
            "israel": "IL",
            "united arab emirates": "AE",
            "south africa": "ZA",
            "colombia": "CO",
            "argentina": "AR",
            "chile": "CL",
        }

        country_codes = {
            "us": "US", "usa": "US", "united states": "US",
            "in": "IN", "ind": "IN", "pl": "PL", "pol": "PL",
            "ca": "CA", "can": "CA", "gb": "GB", "gbr": "GB",
            "au": "AU", "aus": "AU", "de": "DE", "deu": "DE",
            "fr": "FR", "fra": "FR", "es": "ES", "esp": "ES",
            "mx": "MX", "mex": "MX",
        }

        if country is None:
            if hint in country_codes:
                country = country_codes[hint]
            else:
                for country_name in sorted(countries, key=len, reverse=True):
                    if re.search(
                        r"\b" + re.escape(country_name) + r"\b",
                        lowered,
                    ):
                        country = countries[country_name]
                        break

            if country is not None:
                parts = [part.strip() for part in raw.split(",") if part.strip()]

                if parts and parts[-1].lower() in countries:
                    municipality = ", ".join(parts[:-1]) or raw

    return {
        "country": country,
        "municipality": municipality,
        "raw": raw,
        "region": region,
    }


# ============================================================
# ELIGIBILITY
# ============================================================

def extract_eligibility(text):
    """
    Detecta restricciones explícitas de elegibilidad geográfica.
    No confunde el lugar donde se puede contratar con la ubicación
    física del empleo.
    """

    empty = {
        "countries": [],
        "states": [],
        "territories": [],
    }

    if not text:
        return empty

    normalized = normalize_space(text)
    lowered = normalized.lower()

    eligibility_markers = [
        "eligible hiring locations",
        "eligible locations",
        "eligible to work",
        "eligible candidates",
        "can hire",
        "can hire full-time residents",
        "residents of the following",
        "hiring locations",
        "locations where we can hire",
    ]

    positions = [
        lowered.find(marker)
        for marker in eligibility_markers
        if lowered.find(marker) >= 0
    ]

    if not positions:
        return empty

    eligibility_text = normalized[min(positions):]

    stop_patterns = [
        r"\bCalifornia Residents:",
        r"\bBenefits\b",
        r"\bIndividual pay\b",
        r"\bStarting pay range\b",
        r"\bEqual Opportunity Employer\b",
        r"\bAbout Bold\b",
        r"\b#LI-",
    ]

    stop_positions = []

    for pattern in stop_patterns:
        match = re.search(pattern, eligibility_text, re.IGNORECASE)
        if match:
            stop_positions.append(match.start())

    if stop_positions:
        eligibility_text = eligibility_text[:min(stop_positions)]

    lowered_eligibility = eligibility_text.lower()
    states_found = []
    territories_found = []

    for state_name, state_code in US_STATES.items():
        if re.search(
            r"\b" + re.escape(state_name) + r"\b",
            lowered_eligibility,
        ):
            states_found.append(state_code)

    for state_code in STATE_CODE_TO_NAME:
        if re.search(
            r"(?<![A-Za-z])" + re.escape(state_code)
            + r"(?![A-Za-z])",
            lowered_eligibility,
        ):
            code_upper = state_code.upper()
            if code_upper not in states_found:
                states_found.append(code_upper)

    if re.search(r"\bpuerto rico\b", lowered_eligibility):
        territories_found.append("PR")

    territory_patterns = {
        r"guam": "GU",
        r"u\.s\. virgin islands": "VI",
        r"us virgin islands": "VI",
        r"virgin islands": "VI",
        r"american samoa": "AS",
        r"northern mariana islands": "MP",
    }

    for pattern, code in territory_patterns.items():
        if re.search(r"\b" + pattern + r"\b", lowered_eligibility):
            if code not in territories_found:
                territories_found.append(code)

    countries_found = []

    if (
        states_found
        or territories_found
        or re.search(
            r"\bu\.?s\.?\b|\bunited states\b|\bu\.?s\.?\s+states\b",
            lowered_eligibility,
        )
    ):
        countries_found.append("US")

    return {
        "countries": sorted(set(countries_found)),
        "states": sorted(set(states_found)),
        "territories": sorted(set(territories_found)),
    }


# ============================================================
# SALARY
# ============================================================

def normalize_salary_period(period):
    if not period:
        return "unknown"

    period = period.lower().strip()

    if period in {"hour", "hr", "hourly"}:
        return "hour"

    if period in {"year", "annual", "annually", "yearly"}:
        return "year"

    if period in {"month", "monthly"}:
        return "month"

    return "unknown"


def extract_salary(text):
    """
    Extrae rangos salariales y cantidades individuales.

    Ejemplos:
      $16 - $20 per hour
      $80,000 to $95,000
      USD 50,000 - USD 70,000 annually
      $100k - $150k
      $1.2m - $1.5m

    No supone que un salario sea anual u horario si la fuente
    no especifica el período.
    """

    empty = {
        "currency": "USD",
        "max": None,
        "min": None,
        "period": "unknown",
        "published": False,
    }

    if not text:
        return empty

    normalized = (
        str(text)
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    # Permite comas, decimales y sufijos k/m.
    amount = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kKmM])?"

    period_pattern = (
        r"(?:\s*(?:per|/)\s*)?"
        r"(hourly|hour|hr|hours|yearly|annual|annually|year|years|"
        r"monthly|month|months)"
        r"(?:\s+rate|\s+salary)?"
    )

    def parse_amount(number_text, suffix):
        value = float(number_text.replace(",", ""))

        if suffix:
            suffix = suffix.lower()

            if suffix == "k":
                value *= 1000
            elif suffix == "m":
                value *= 1000000

        return value

    # Rango con símbolo $, USD opcional y sufijos k/m.
    range_patterns = [
        re.compile(
            r"\$\s*" + amount
            + r"\s*(?:-|to|through)\s*\$?\s*" + amount
            + period_pattern + r"?",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bUSD\s*" + amount
            + r"\s*(?:-|to|through)\s*(?:USD\s*)?\$?\s*" + amount
            + period_pattern + r"?",
            re.IGNORECASE,
        ),
    ]

    for pattern in range_patterns:
        match = pattern.search(normalized)

        if not match:
            continue

        minimum = parse_amount(match.group(1), match.group(2))
        maximum = parse_amount(match.group(3), match.group(4))
        period = normalize_salary_period(match.group(5))

        if minimum > maximum:
            minimum, maximum = maximum, minimum

        return {
            "currency": "USD",
            "max": maximum,
            "min": minimum,
            "period": period,
            "published": True,
        }

    # Cantidad única. Solo se usa cuando no hay un rango.
    single_patterns = [
        re.compile(
            r"\$\s*" + amount + period_pattern + r"?",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bUSD\s*" + amount + period_pattern + r"?",
            re.IGNORECASE,
        ),
    ]

    for pattern in single_patterns:
        match = pattern.search(normalized)

        if not match:
            continue

        value = parse_amount(match.group(1), match.group(2))
        period = normalize_salary_period(match.group(3))

        return {
            "currency": "USD",
            "max": value,
            "min": value,
            "period": period,
            "published": True,
        }

    return empty


# ============================================================
# EMPLOYMENT TYPE
# ============================================================

def extract_employment_type(text):
    if not text:
        return "Unknown"

    lowered = text.lower()

    if re.search(r"\bfull[- ]time\b", lowered):
        return "Full-time"

    if re.search(r"\bpart[- ]time\b", lowered):
        return "Part-time"

    if re.search(
        r"\binternship\b|\bintern position\b|\bintern role\b",
        lowered,
    ):
        return "Internship"

    if re.search(
        r"\btemporary position\b|\btemporary role\b|\btemporary job\b",
        lowered,
    ):
        return "Temporary"

    if re.search(
        r"\bcontract position\b|\bcontract role\b|\bcontractor position\b",
        lowered,
    ):
        return "Contract"

    return "Unknown"


# ============================================================
# INDUSTRY
# ============================================================

def extract_industry(text, job=None):
    title = str((job or {}).get("title") or "").lower()
    department = str((job or {}).get("department") or "").lower()
    content = (text or "").lower()

    technology_terms = [
        "software", "developer", "engineer", "engineering",
        "artificial intelligence", "machine learning",
        "data scientist", "data engineer", "systems analyst",
        "systems administrator", "information technology",
        "technology", "technical", "devops", "cloud",
        "cybersecurity", "software architect",
    ]

    if any(term in title for term in technology_terms):
        return "Technology"

    if any(
        term in department
        for term in ["technology", "engineering", "software", "data"]
    ):
        return "Technology"

    design_terms = [
        "visual designer", "graphic designer", "ui designer",
        "ux designer", "ux/ui designer", "product designer",
        "brand designer", "digital designer", "marketing designer",
        "content designer", "creative designer", "web designer",
    ]

    if any(term in title for term in design_terms):
        return "Marketing & Design"

    if any(
        term in department
        for term in [
            "marketing & design", "marketing and design", "creative",
            "brand", "visual design", "graphic design", "ux/ui",
        ]
    ):
        return "Marketing & Design"

    categories = [
        ("Aviation", [
            "aviation", "aircraft", "airline", "airport", "aerospace",
            "flight operations", "air cargo",
        ]),
        ("Manufacturing", [
            "manufacturing", "production", "assembly", "fabrication",
            "machine operator", "production operator",
        ]),
        ("Logistics", [
            "logistics", "warehouse", "supply chain", "inventory",
            "shipping", "receiving", "distribution",
        ]),
        ("Healthcare", [
            "nurse", "nursing", "medical assistant", "medical technician",
            "healthcare", "health care", "clinical", "pharmacy",
            "pharmacist", "therapist", "physician", "doctor",
            "radiology", "patient care",
        ]),
        ("Construction", [
            "construction", "carpenter", "electrician", "plumber",
            "welder", "concrete", "mason", "roofer",
        ]),
        ("Maintenance", [
            "maintenance", "mechanic", "industrial technician",
            "equipment technician",
        ]),
        ("Transportation", [
            "driver", "delivery driver", "transportation",
            "truck driver", "courier", "dispatcher",
        ]),
        ("Retail", [
            "retail", "store associate", "sales associate",
            "cashier", "store manager",
        ]),
        ("Restaurants", [
            "restaurant", "server", "waiter", "waitress", "cook",
            "chef", "food service", "line cook", "dishwasher",
        ]),
        ("Hospitality", [
            "hotel", "resort", "hospitality", "front desk",
            "guest services", "housekeeping",
        ]),
        ("Security", ["security", "security officer", "security guard"]),
        ("Sales", [
            "sales", "account executive", "sales representative",
            "business development",
        ]),
        ("Customer Service", [
            "customer service", "customer support", "call center",
            "contact center",
        ]),
        ("Finance", [
            "accountant", "accounting", "finance", "financial analyst",
            "financial", "bookkeeper", "banking",
        ]),
        ("Administrative", [
            "administrative", "administration", "office assistant",
            "receptionist", "executive assistant", "office coordinator",
        ]),
        ("Education", [
            "teacher", "professor", "instructor", "education",
            "school counselor", "academic",
        ]),
        ("Government", [
            "government", "federal", "municipal", "public sector",
        ]),
    ]

    for category, terms in categories:
        if any(term in title for term in terms):
            return category

    strong_technology_content = [
        "software engineering", "software development", "javascript",
        "typescript", "python", "sql", "llm", "large language model",
        "machine learning", "artificial intelligence", "rest api",
        "soap api", "ci/cd", "database modeling", "data modeling",
        "cloud infrastructure", "devops",
    ]

    score = sum(1 for term in strong_technology_content if term in content)

    if score >= 2:
        return "Technology"

    return "Other"


# ============================================================
# WORK MODE
# ============================================================

def extract_work_mode(text):
    """
    Clasifica la modalidad usando señales explícitas.
    Evita detectar Remote solo porque se menciona un equipo remoto.
    Una indicación inequívoca de 100% presencial tiene prioridad.
    """

    if not text:
        return "Unknown"

    lowered = normalize_space(text).lower()

    # Una declaración inequívoca de presencialidad tiene prioridad.
    onsite_explicit_patterns = [
        r"\b100\s*%\s*(?:on[- ]?site|onsite|in[- ]person)\b",
        r"\bfully\s+on[- ]?site\b",
        r"\bstrictly\s+on[- ]?site\b",
        r"\bthis\s+is\s+an?\s+on[- ]?site\s+role\b",
        r"\bon[- ]?site\s+position\b",
        r"\bonsite\s+position\b",
        r"\bwork\s+must\s+be\s+performed\s+on[- ]?site\b",
    ]

    if any(
        re.search(pattern, lowered)
        for pattern in onsite_explicit_patterns
    ):
        return "On-site"

    # Hybrid solo se reconoce por una indicación de modalidad,
    # no por una mención incidental.
    hybrid_patterns = [
        r"\bhybrid\s+(?:work|schedule|role|position|model|arrangement)\b",
        r"\bhybrid[- ]work\b",
        r"\bhybrid\s+workplace\b",
        r"\bthis\s+is\s+a\s+hybrid\b",
        r"\bhybrid\b",
    ]

    if any(
        re.search(pattern, lowered)
        for pattern in hybrid_patterns
    ):
        return "Hybrid"

    # Requiere evidencia explícita de que el puesto es remoto.
    remote_patterns = [
        r"\bfully\s+remote\b",
        r"\b100\s*%\s+remote\b",
        r"\bthis\s+is\s+a\s+remote\s+(?:role|position|job)\b",
        r"\bremote\s+(?:role|position|job)\b",
        r"\bremote[- ]first\b",
        r"\bwork\s+remotely\b",
        r"\bwork\s+from\s+home\b",
        r"\bremote\s+work\s+arrangement\b",
        r"\bposition\s+is\s+remote\b",
        r"\bremote\s+eligible\b",
    ]

    if any(
        re.search(pattern, lowered)
        for pattern in remote_patterns
    ):
        return "Remote"

    # Presencialidad explícita sin ser necesariamente 100%.
    onsite_patterns = [
        r"\bon[- ]site\b",
        r"\bonsite\b",
        r"\bin[- ]person\s+at\s+(?:our|the)\s+office\b",
        r"\boffice[- ]based\b",
        r"\bin[- ]office\s+(?:role|position|work)\b",
        r"\bwork\s+from\s+(?:our|the)\s+office\b",
        r"\bmust\s+be
