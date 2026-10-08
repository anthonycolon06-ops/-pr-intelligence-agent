import re
import html
from datetime import datetime, timezone


# ============================================================
# US STATES
# ============================================================

US_STATES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
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
    Identifica ubicaciones de Puerto Rico, Estados Unidos
    y otros países. Nunca asume que una ubicación desconocida
    pertenece a Estados Unidos.
    """

    location = job.get("location")
    raw = ""
    country_hint = ""

    if isinstance(location, dict):
        raw = location.get("name") or location.get("raw") or ""
        country_hint = str(
            location.get("country") or ""
        ).strip()

    elif isinstance(location, str):
        raw = location

    if not raw:
        offices = job.get("offices", [])

        if isinstance(offices, list):
            names = [
                str(office["name"])
                for office in offices
                if isinstance(office, dict)
                and office.get("name")
            ]

            if names:
                raw = ", ".join(names)

    raw = normalize_space(raw) or ""
    lowered = raw.lower()
    hint = country_hint.lower()

    country = None
    region = None
    municipality = raw or None

    # --------------------------------------------------------
    # PUERTO RICO
    # --------------------------------------------------------

    if (
        "puerto rico" in lowered
        or hint in {"pr", "pri", "puerto rico"}
        or re.search(
            r",\s*PR$",
            raw,
            re.IGNORECASE
        )
    ):
        country = "PR"
        region = "Puerto Rico"

        match = re.search(
            r"^(.+?),\s*(?:Puerto Rico|PR)$",
            raw,
            re.IGNORECASE,
        )

        municipality = (
            match.group(1).strip()
            if match
            else "Puerto Rico"
        )

    else:

        # ----------------------------------------------------
        # ESTADOS DE EE. UU.
        # ----------------------------------------------------

        state_codes = set(
            US_STATES.values()
        )

        # Austin, TX
        state_match = re.fullmatch(
            r"(.+?),\s*([A-Z]{2})"
            r"(?:,\s*(?:United States|USA|US))?",
            raw,
        )

        # Austin, Texas
        for state_name in sorted(
            US_STATES,
            key=len,
            reverse=True
        ):

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

            state_code = (
                state_match.group(2).upper()
            )

            if state_code in state_codes:

                country = "US"
                region = state_code
                municipality = (
                    state_match.group(1).strip()
                )

        # ----------------------------------------------------
        # REMOTO EN ESTADOS UNIDOS
        # ----------------------------------------------------

        if country is None and re.fullmatch(
            r"(?:United States|USA|U\.S\.A\.?)"
            r"\s*(?:\(\s*Remote\s*\))?",
            raw,
            re.IGNORECASE,
        ):
            country = "US"
            municipality = "United States (Remote)"

        if country is None and re.fullmatch(
            r"(?:US|U\.S\.)\s*"
            r"\(\s*Remote\s*\)",
            raw,
            re.IGNORECASE,
        ):
            country = "US"
            municipality = "United States (Remote)"

        # ----------------------------------------------------
        # PAÍSES INTERNACIONALES
        # ----------------------------------------------------

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
            "us": "US",
            "usa": "US",
            "united states": "US",
            "in": "IN",
            "ind": "IN",
            "pl": "PL",
            "pol": "PL",
            "ca": "CA",
            "can": "CA",
            "gb": "GB",
            "gbr": "GB",
            "au": "AU",
            "aus": "AU",
            "de": "DE",
            "deu": "DE",
            "fr": "FR",
            "fra": "FR",
            "es": "ES",
            "esp": "ES",
            "mx": "MX",
            "mex": "MX",
        }

        if country is None:

            if hint in country_codes:

                country = country_codes[hint]

            else:

                for country_name in sorted(
                    countries,
                    key=len,
                    reverse=True
                ):

                    if re.search(
                        r"\b"
                        + re.escape(country_name)
                        + r"\b",
                        lowered,
                    ):

                        country = countries[
                            country_name
                        ]

                        break

            if country is not None:

                parts = [
                    part.strip()
                    for part in raw.split(",")
                    if part.strip()
                ]

                if (
                    parts
                    and parts[-1].lower()
                    in countries
                ):

                    municipality = (
                        ", ".join(parts[:-1])
                        or raw
                    )

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
    Detecta dónde puede residir el candidato para ser elegible.

    Ejemplo:

    "BOLD can hire full-time residents of the following
    U.S. States & Territories: Arizona, California, Texas,
    Puerto Rico..."

    Produce:

    {
        "countries": ["US"],
        "states": ["AZ", "CA", "TX"],
        "territories": ["PR"]
    }

    Importante:
    Esto NO cambia la ubicación física del empleo.
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

    states_found = []
    territories_found = []

    # --------------------------------------------------------
    # Detectar si el texto habla explícitamente de elegibilidad
    # --------------------------------------------------------

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

    marker_positions = []

    for marker in eligibility_markers:

        position = lowered.find(marker)

        if position >= 0:
            marker_positions.append(position)

    # Si no encontramos una sección de elegibilidad,
    # no intentamos convertir cualquier mención de Texas
    # en elegibilidad.
    if not marker_positions:
        return empty

    start = min(marker_positions)

    # --------------------------------------------------------
    # Extraer una ventana después del marcador
    # --------------------------------------------------------

    eligibility_text = normalized[start:]

    # Generalmente la lista termina antes de:
    # California Residents / Benefits / Individual pay / etc.
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

        match = re.search(
            pattern,
            eligibility_text,
            re.IGNORECASE
        )

        if match:
            stop_positions.append(
                match.start()
            )

    if stop_positions:

        eligibility_text = (
            eligibility_text[
                :min(stop_positions)
            ]
        )

    lowered_eligibility = (
        eligibility_text.lower()
    )

    # --------------------------------------------------------
    # Estados
    # --------------------------------------------------------

    for state_name, state_code in US_STATES.items():

        if re.search(
            r"\b"
            + re.escape(state_name)
            + r"\b",
            lowered_eligibility,
        ):

            states_found.append(
                state_code
            )

    # --------------------------------------------------------
    # Códigos estatales explícitos
    # --------------------------------------------------------

    for state_code in STATE_CODE_TO_NAME:

        if re.search(
            r"(?<![A-Za-z])"
            + re.escape(state_code)
            + r"(?![A-Za-z])",
            lowered_eligibility,
        ):

            code_upper = state_code.upper()

            if code_upper not in states_found:

                states_found.append(
                    code_upper
                )

    # --------------------------------------------------------
    # Puerto Rico
    # --------------------------------------------------------

    if re.search(
        r"\bpuerto rico\b",
        lowered_eligibility
    ):

        territories_found.append(
            "PR"
        )

    # --------------------------------------------------------
    # Otros territorios estadounidenses
    # --------------------------------------------------------

    territory_patterns = {
        "guam": "GU",
        "u\.s\. virgin islands": "VI",
        "us virgin islands": "VI",
        "virgin islands": "VI",
        "american samoa": "AS",
        "northern mariana islands": "MP",
    }

    for pattern, code in territory_patterns.items():

        if re.search(
            r"\b" + pattern + r"\b",
            lowered_eligibility
        ):

            if code not in territories_found:

                territories_found.append(
                    code
                )

    # --------------------------------------------------------
    # Determinar país
    # --------------------------------------------------------

    countries_found = []

    if (
        states_found
        or territories_found
        or re.search(
            r"\bu\.?s\.?\b"
            r"|\bunited states\b"
            r"|\bu\.?s\.?\s+states\b",
            lowered_eligibility,
        )
    ):

        countries_found.append(
            "US"
        )

    return {
        "countries": sorted(
            set(countries_found)
        ),
        "states": sorted(
            set(states_found)
        ),
        "territories": sorted(
            set(territories_found)
        ),
    }


# ============================================================
# SALARY
# ============================================================

def normalize_salary_period(period):
    if not period:
        return "unknown"

    period = period.lower()

    if period in {
        "hour",
        "hr",
        "hourly"
    }:
        return "hour"

    if period in {
        "year",
        "annual",
        "annually"
    }:
        return "year"

    if period in {
        "month",
        "monthly"
    }:
        return "month"

    return "unknown"


def extract_salary(text):

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
        text.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    number = (
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
    )

    period_pattern = (
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?"
    )

    patterns = [

        re.compile(
            r"\$\s*" + number
            + r"\s*-\s*\$?\s*" + number
            + r"\s*" + period_pattern,
            re.IGNORECASE,
        ),

        re.compile(
            r"\bUSD\s*" + number
            + r"\s*-\s*USD?\s*" + number
            + r"\s*" + period_pattern,
            re.IGNORECASE,
        ),

    ]

    for pattern in patterns:

        match = pattern.search(
            normalized
        )

        if match:

            minimum = float(
                match.group(1)
                .replace(",", "")
            )

            maximum = float(
                match.group(2)
                .replace(",", "")
            )

            return {
                "currency": "USD",
                "max": maximum,
                "min": minimum,
                "period": normalize_salary_period(
                    match.group(3)
                ),
                "published": True,
            }

    single_patterns = [

        re.compile(
            r"\$\s*" + number
            + r"\s*" + period_pattern,
            re.IGNORECASE,
        ),

        re.compile(
            r"\bUSD\s*" + number
            + r"\s*" + period_pattern,
            re.IGNORECASE,
        ),

    ]

    for pattern in single_patterns:

        match = pattern.search(
            normalized
        )

        if match:

            amount = float(
                match.group(1)
                .replace(",", "")
            )

            return {
                "currency": "USD",
                "max": amount,
                "min": amount,
                "period": normalize_salary_period(
                    match.group(2)
                ),
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

    if re.search(
        r"\bfull[- ]time\b",
        lowered
    ):
        return "Full-time"

    if re.search(
        r"\bpart[- ]time\b",
        lowered
    ):
        return "Part-time"

    if re.search(
        r"\binternship\b"
        r"|\bintern position\b"
        r"|\bintern role\b",
        lowered,
    ):
        return "Internship"

    if re.search(
        r"\btemporary position\b"
        r"|\btemporary role\b"
        r"|\btemporary job\b",
        lowered,
    ):
        return "Temporary"

    if re.search(
        r"\bcontract position\b"
        r"|\bcontract role\b"
        r"|\bcontractor position\b",
        lowered,
    ):
        return "Contract"

    return "Unknown"


# ============================================================
# INDUSTRY
# ============================================================

def extract_industry(text, job=None):

    title = str(
        (job or {}).get("title") or ""
    ).lower()

    department = str(
        (job or {}).get("department") or ""
    ).lower()

    content = (
        text or ""
    ).lower()

    technology_terms = [
        "software",
        "developer",
        "engineer",
        "engineering",
        "artificial intelligence",
        "machine learning",
        "data scientist",
        "data engineer",
        "systems analyst",
        "systems administrator",
        "information technology",
        "technology",
        "technical",
        "devops",
        "cloud",
        "cybersecurity",
        "software architect",
    ]

    if any(
        term in title
        for term in technology_terms
    ):
        return "Technology"

    if any(
        term in department
        for term in [
            "technology",
            "engineering",
            "software",
            "data"
        ]
    ):
        return "Technology"

    design_terms = [
        "visual designer",
        "graphic designer",
        "ui designer",
        "ux designer",
        "ux/ui designer",
        "product designer",
        "brand designer",
        "digital designer",
        "marketing designer",
        "content designer",
        "creative designer",
        "web designer",
    ]

    if any(
        term in title
        for term in design_terms
    ):
        return "Marketing & Design"

    if any(
        term in department
        for term in [
            "marketing & design",
            "marketing and design",
            "creative",
            "brand",
            "visual design",
            "graphic design",
            "ux/ui",
        ]
    ):
        return "Marketing & Design"

    categories = [

        ("Aviation", [
            "aviation",
            "aircraft",
            "airline",
            "airport",
            "aerospace",
            "flight operations",
            "air cargo",
        ]),

        ("Manufacturing", [
            "manufacturing",
            "production",
            "assembly",
            "fabrication",
            "machine operator",
            "production operator",
        ]),

        ("Logistics", [
            "logistics",
            "warehouse",
            "supply chain",
            "inventory",
            "shipping",
            "receiving",
            "distribution",
        ]),

        ("Healthcare", [
            "nurse",
            "nursing",
            "medical assistant",
            "medical technician",
            "healthcare",
            "health care",
            "clinical",
            "pharmacy",
            "pharmacist",
            "therapist",
            "physician",
            "doctor",
            "radiology",
            "patient care",
        ]),

        ("Construction", [
            "construction",
            "carpenter",
            "electrician",
            "plumber",
            "welder",
            "concrete",
            "mason",
            "roofer",
        ]),

        ("Maintenance", [
            "maintenance",
            "mechanic",
            "industrial technician",
            "equipment technician",
        ]),

        ("Transportation", [
            "driver",
            "delivery driver",
            "transportation",
            "truck driver",
            "courier",
            "dispatcher",
        ]),

        ("Retail", [
            "retail",
            "store associate",
            "sales associate",
            "cashier",
            "store manager",
        ]),

        ("Restaurants", [
            "restaurant",
            "server",
            "waiter",
            "waitress",
            "cook",
            "chef",
            "food service",
            "line cook",
            "dishwasher",
        ]),

        ("Hospitality", [
            "hotel",
            "resort",
            "hospitality",
            "front desk",
            "guest services",
            "housekeeping",
        ]),

        ("Security", [
            "security",
            "security officer",
            "security guard",
        ]),

        ("Sales", [
            "sales",
            "account executive",
            "sales representative",
            "business development",
        ]),

        ("Customer Service", [
            "customer service",
            "customer support",
            "call center",
            "contact center",
        ]),

        ("Finance", [
            "accountant",
            "accounting",
            "finance",
            "financial analyst",
            "financial",
            "bookkeeper",
            "banking",
        ]),

        ("Administrative", [
            "administrative",
            "administration",
            "office assistant",
            "receptionist",
            "executive assistant",
            "office coordinator",
        ]),

        ("Education", [
            "teacher",
            "professor",
            "instructor",
            "education",
            "school counselor",
            "academic",
        ]),

        ("Government", [
            "government",
            "federal",
            "municipal",
            "public sector",
        ]),
    ]

    for category, terms in categories:

        if any(
            term in title
            for term in terms
        ):
            return category

    strong_technology_content = [
        "software engineering",
        "software development",
        "javascript",
        "typescript",
        "python",
        "sql",
        "llm",
        "large language model",
        "machine learning",
        "artificial intelligence",
        "rest api",
        "soap api",
        "ci/cd",
        "database modeling",
        "data modeling",
        "cloud infrastructure",
        "devops",
    ]

    score = sum(
        1
        for term in strong_technology_content
        if term in content
    )

    if score >= 2:
        return "Technology"

    return "Other"


# ============================================================
# WORK MODE
# ============================================================

def extract_work_mode(text):

    if not text:
        return "Unknown"

    lowered = text.lower()

    if (
        "li-hybrid" in lowered
        or re.search(
            r"\bhybrid\b",
            lowered
        )
    ):
        return "Hybrid"

    if (
        "li-remote" in lowered
        or re.search(
            r"\bremote\b",
            lowered
        )
        or "work from home" in lowered
    ):
        return "Remote"

    if (
        "li-onsite" in lowered
        or re.search(
            r"\bon[- ]site\b",
            lowered
        )
        or "onsite" in lowered
        or "on site" in lowered
    ):
        return "On-site"

    return "Unknown"


# ============================================================
# EDUCATION
# ============================================================

def extract_education(text):

    if not text:
        return []

    lowered = text.lower()
    education = []

    if re.search(
        r"\bhigh school\b"
        r"|\bhigh-school\b"
        r"|\bsecondary school\b",
        lowered,
    ):
        education.append(
            "High school"
        )

    if re.search(
        r"\bassociate'?s?\b"
        r"|\bassociates degree\b",
        lowered,
    ):
        education.append(
            "Associate degree"
        )

    if re.search(
        r"\bundergraduate degree\b"
        r"|\bbachelor'?s?\b"
        r"|\bbachelor degree\b",
        lowered,
    ):
        education.append(
            "Bachelor's degree"
        )

    if re.search(
        r"\bmaster'?s?\b"
        r"|\bmaster degree\b",
        lowered,
    ):
        education.append(
            "Master's degree"
        )

    if re.search(
        r"\bph\.?d\.?\b"
        r"|\bdoctorate\b",
        lowered
    ):
        education.append(
            "Doctorate"
        )

    if re.search(
        r"\btechnical degree\b"
        r"|\btechnical diploma\b",
        lowered,
    ):
        education.append(
            "Technical degree"
        )

    return education


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(text):

    if not text:
        return None, []

    normalized = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    matches = []

    patterns = [

        re.compile(
            r"\b(\d+)\s*-\s*(\d+)\s+years?\b",
            re.IGNORECASE,
        ),

        re.compile(
            r"\b(\d+)\s*\+\s*years?\b",
            re.IGNORECASE,
        ),

        re.compile(
            r"\b(?:minimum of|at least)"
            r"\s+(\d+)\s+years?\b",
            re.IGNORECASE,
        ),

    ]

    for index, pattern in enumerate(
        patterns
    ):

        for match in pattern.finditer(
            normalized
        ):

            if index == 0:

                value = (
                    f"{match.group(1)}"
                    f"-{match.group(2)} years"
                )

            else:

                value = (
                    f"{match.group(1)}+ years"
                )

            start = max(
                0,
                match.start() - 80
            )

            end = min(
                len(normalized),
                match.end() + 120
            )

            matches.append({

                "start":
                    match.start(),

                "value":
                    value,

                "context":
                    normalize_space(
                        normalized[
                            start:end
                        ]
                    ),

            })

    if not matches:
        return None, []

    unique = []
    seen = set()

    for item in sorted(
        matches,
        key=lambda x: x["start"]
    ):

        key = (
            item["start"],
            item["value"]
        )

        if key not in seen:

            unique.append(
                item
            )

            seen.add(key)

    primary = unique[0]["value"]

    details = []
    seen_values = set()

    for item in unique:

        if item["value"] in seen_values:
            continue

        details.append({

            "experience":
                item["value"],

            "context":
                item["context"],

        })

        seen_values.add(
            item["value"]
        )

    return primary, details


# ============================================================
# LICENSES
# ============================================================

def extract_licenses(text):

    if not text:
        return []

    lowered = text.lower()
    licenses = []

    patterns = [

        ("A&P", [
            "a&p",
            "airframe and powerplant",
        ]),

        ("Driver's license", [
            "driver's license",
            "drivers license",
            "valid driver's license",
            "valid drivers license",
        ]),

        ("FAA certification", [
            "faa certification",
            "faa license",
        ]),

        ("CPA", [
            "cpa license",
            "certified public accountant",
        ]),

        ("PMP", [
            "pmp certification",
            "project management professional",
        ]),

    ]

    for name, keywords in patterns:

        if any(
            keyword in lowered
            for keyword in keywords
        ):

            licenses.append(
                name
            )

    return licenses


# ============================================================
# REQUIREMENTS
# ============================================================

def extract_requirements(text):

    experience, experience_details = (
        extract_experience(text)
    )

    return {

        "education":
            extract_education(text),

        "experience":
            experience,

        "experience_details":
            experience_details,

        "licenses":
            extract_licenses(text),

    }


# ============================================================
# DATES
# ============================================================

def parse_date_value(value):

    if value is None:
        return None

    if isinstance(
        value,
        datetime
    ):

        dt = value

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.isoformat()

    value = str(value).strip()

    if not value:
        return None

    try:

        dt = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.isoformat()

    except ValueError:
        pass

    for date_format in [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]:

        try:

            dt = datetime.strptime(
                value,
                date_format
            )

            dt = dt.replace(
                tzinfo=timezone.utc
            )

            return dt.isoformat()

        except ValueError:
            continue

    return value


def extract_dates(job):

    posted_candidates = [

        "first_published_at",
        "first_published",
        "published_at",
        "published",
        "date_posted",
        "datePosted",
        "created_at",
        "createdAt",
        "opened_at",
        "opening_date",

    ]

    updated_candidates = [

        "updated_at",
        "updatedAt",
        "last_updated_at",
        "last_updated",
        "modified_at",
        "modifiedAt",

    ]

    posted_date = None
    updated_date = None

    for field in posted_candidates:

        value = job.get(field)

        if value:

            posted_date = parse_date_value(
                value
            )

            break

    for field in updated_candidates:

        value = job.get(field)

        if value:

            updated_date = parse_date_value(
                value
            )

            break

    return posted_date, updated_date


# ============================================================
# SOURCE
# ============================================================

def build_source(
    job,
    company,
    board_token
):

    job_id = job.get("id")

    absolute_url = (
        job.get("absolute_url")
        or job.get("url")
    )

    if not absolute_url and job_id:

        absolute_url = (
            f"https://boards.greenhouse.io/"
            f"{board_token}/jobs/{job_id}"
        )

    return {

        "name":
            "Greenhouse",

        "type":
            "job_board_api",

        "url":
            absolute_url,

        "application_url":
            absolute_url,

    }


# ============================================================
# NORMALIZER
# ============================================================

def normalize_greenhouse_job(
    job,
    company,
    board_token
):

    content = get_job_content(
        job
    )

    location = extract_location(
        job
    )

    eligibility = extract_eligibility(
        content
    )

    salary = extract_salary(
        content
    )

    requirements = extract_requirements(
        content
    )

    posted_date, updated_date = (
        extract_dates(job)
    )

    job_id = job.get("id")
    title = job.get("title") or ""

    return {

        "company":
            company,

        "title":
            title,

        "job_id":
            (
                f"greenhouse-{board_token}-{job_id}"
                if job_id
                else f"greenhouse-{board_token}"
            ),

        "description":
            content,

        "location":
            location,

        "eligibility":
            eligibility,

        "salary":
            salary,

        "employment_type":
            extract_employment_type(
                content
            ),

        "industry":
            extract_industry(
                content,
                job
            ),

        "work_mode":
            extract_work_mode(
                content
            ),

        "requirements":
            requirements,

        "posted_date":
            posted_date,

        "updated_date":
            updated_date,

        "source":
            build_source(
                job,
                company,
                board_token
            ),

        "verification": {

            "status":
                "source_verified",

            "checked_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        },

    }
