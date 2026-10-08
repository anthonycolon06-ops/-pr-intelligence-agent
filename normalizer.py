import re
import html
from datetime import datetime, timezone


# ============================================================
# GREENHOUSE CONTENT
# ============================================================

def decode_greenhouse_content(content):
    """
    Decodifica contenido HTML/Unicode proveniente de Greenhouse.
    """

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
    """
    Convierte HTML de Greenhouse a texto limpio.
    """

    if not content:
        return ""

    text = decode_greenhouse_content(content)

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</p\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</div\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</li\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = html.unescape(text)

    text = text.replace("\xa0", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text,
    )

    return text.strip()


def get_job_content(job):
    """
    Obtiene la descripción/contenido completo.
    """

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
    """
    Normaliza espacios.
    """

    if value is None:
        return None

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# LOCATION
# ============================================================

def extract_location(job):
    """
    Extrae ubicación de Greenhouse.
    """

    location = job.get("location")

    raw = ""

    if isinstance(location, dict):
        raw = (
            location.get("name")
            or location.get("raw")
            or ""
        )

    elif isinstance(location, str):
        raw = location

    if not raw:
        offices = job.get("offices", [])

        if isinstance(offices, list):
            names = []

            for office in offices:
                if not isinstance(office, dict):
                    continue

                name = office.get("name")

                if name:
                    names.append(str(name))

            if names:
                raw = ", ".join(names)

    raw = normalize_space(raw) or ""

    lowered = raw.lower()

    country = None
    region = None
    municipality = None

    # --------------------------------------------------------
    # PUERTO RICO
    # --------------------------------------------------------

    if (
        "puerto rico" in lowered
        or re.search(r"\bpr\b", lowered)
    ):
        country = "PR"
        region = "Puerto Rico"

        municipality_match = re.search(
            r"([A-Za-zÁÉÍÓÚáéíóúÑñ .'-]+),\s*Puerto Rico",
            raw,
            flags=re.IGNORECASE,
        )

        if municipality_match:
            municipality = (
                municipality_match.group(1).strip()
            )
        else:
            municipality = "Puerto Rico"

    # --------------------------------------------------------
    # UNITED STATES
    # --------------------------------------------------------

    else:
        country = "US"

        us_match = re.search(
            r"([A-Za-z .'-]+),\s*([A-Z]{2})(?:,?\s*United States)?$",
            raw,
        )

        if us_match:
            municipality = (
                us_match.group(1).strip()
            )

            region = (
                us_match.group(2).upper()
            )

        else:
            municipality = raw or None

    return {
        "country": country,
        "municipality": municipality,
        "raw": raw,
        "region": region,
    }


# ============================================================
# SALARY
# ============================================================

def extract_salary(text):
    """
    Extrae salarios publicados.

    IMPORTANTE:
    Nunca interpreta '3-5 years' o '5+ years' como salario.

    Requiere un indicador monetario real como:
    $
    USD
    USD 50,000
    $20/hour
    $50,000-$70,000/year
    """

    if not text:
        return {
            "currency": "USD",
            "max": None,
            "min": None,
            "period": "unknown",
            "published": False,
        }

    # --------------------------------------------------------
    # Normalización
    # --------------------------------------------------------

    normalized = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    # --------------------------------------------------------
    # RANGOS CON SIGNO $
    # --------------------------------------------------------

    range_dollar = re.compile(
        r"\$\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*-\s*"
        r"\$?\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    match = range_dollar.search(normalized)

    if match:
        minimum = float(
            match.group(1).replace(",", "")
        )

        maximum = float(
            match.group(2).replace(",", "")
        )

        period = normalize_salary_period(
            match.group(3)
        )

        return {
            "currency": "USD",
            "max": maximum,
            "min": minimum,
            "period": period,
            "published": True,
        }

    # --------------------------------------------------------
    # USD RANGES
    # --------------------------------------------------------

    range_usd = re.compile(
        r"\bUSD\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*-\s*"
        r"USD?\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    match = range_usd.search(normalized)

    if match:
        minimum = float(
            match.group(1).replace(",", "")
        )

        maximum = float(
            match.group(2).replace(",", "")
        )

        period = normalize_salary_period(
            match.group(3)
        )

        return {
            "currency": "USD",
            "max": maximum,
            "min": minimum,
            "period": period,
            "published": True,
        }

    # --------------------------------------------------------
    # SINGLE SALARY CON $
    # --------------------------------------------------------

    single_dollar = re.compile(
        r"\$\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    match = single_dollar.search(normalized)

    if match:
        amount = float(
            match.group(1).replace(",", "")
        )

        period = normalize_salary_period(
            match.group(2)
        )

        return {
            "currency": "USD",
            "max": amount,
            "min": amount,
            "period": period,
            "published": True,
        }

    # --------------------------------------------------------
    # SINGLE USD
    # --------------------------------------------------------

    single_usd = re.compile(
        r"\bUSD\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    match = single_usd.search(normalized)

    if match:
        amount = float(
            match.group(1).replace(",", "")
        )

        period = normalize_salary_period(
            match.group(2)
        )

        return {
            "currency": "USD",
            "max": amount,
            "min": amount,
            "period": period,
            "published": True,
        }

    # --------------------------------------------------------
    # NADA PUBLICADO
    # --------------------------------------------------------

    return {
        "currency": "USD",
        "max": None,
        "min": None,
        "period": "unknown",
        "published": False,
    }


def normalize_salary_period(period):
    """
    Normaliza período salarial.
    """

    if not period:
        return "unknown"

    period = period.lower()

    if period in {
        "hour",
        "hr",
        "hourly",
    }:
        return "hour"

    if period in {
        "year",
        "annual",
        "annually",
    }:
        return "year"

    if period in {
        "month",
        "monthly",
    }:
        return "month"

    return "unknown"


# ============================================================
# EMPLOYMENT TYPE
# ============================================================

def extract_employment_type(text):
    """
    Detecta tipo de empleo solamente cuando aparece
    explícitamente.
    """

    if not text:
        return "Unknown"

    lowered = text.lower()

    # Full-time
    if re.search(
        r"\bfull[- ]time\b",
        lowered,
    ):
        return "Full-time"

    # Part-time
    if re.search(
        r"\bpart[- ]time\b",
        lowered,
    ):
        return "Part-time"

    # Internship
    if re.search(
        r"\binternship\b|\bintern position\b|\bintern role\b",
        lowered,
    ):
        return "Internship"

    # Temporary
    if re.search(
        r"\btemporary position\b|\btemporary role\b|\btemporary job\b",
        lowered,
    ):
        return "Temporary"

    # Contract
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
    """
    Determina la industria del puesto.

    Prioridad:
    1. Título
    2. Departamento
    3. Señales fuertes del contenido
    4. Señales generales

    Esto evita que beneficios como healthcare/medical
    conviertan un puesto tecnológico en Healthcare.
    """

    title = ""

    department = ""

    if job:
        title = str(
            job.get("title") or ""
        )

        department = str(
            job.get("department") or ""
        )

    title_lower = title.lower()
    department_lower = department.lower()

    content_lower = (
        text or ""
    ).lower()

    # --------------------------------------------------------
    # TECHNOLOGY - PRIORIDAD MUY ALTA
    # --------------------------------------------------------

    technology_title_terms = [
        "software",
        "developer",
        "engineer",
        "engineering",
        "ai",
        "artificial intelligence",
        "machine learning",
        "data scientist",
        "data engineer",
        "systems analyst",
        "systems administrator",
        "information technology",
        "it ",
        "technology",
        "technical",
        "devops",
        "cloud",
        "cybersecurity",
        "web developer",
        "ux engineer",
        "software architect",
    ]

    if any(
        term in title_lower
        for term in technology_title_terms
    ):
        return "Technology"

    if any(
        term in department_lower
        for term in [
            "technology",
            "engineering",
            "product technology",
            "information technology",
            "software",
            "data",
        ]
    ):
        return "Technology"

    # --------------------------------------------------------
    # MARKETING & DESIGN
    # --------------------------------------------------------

    design_title_terms = [
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
        term in title_lower
        for term in design_title_terms
    ):
        return "Marketing & Design"

    if any(
        term in department_lower
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

    # --------------------------------------------------------
    # AVIATION
    # --------------------------------------------------------

    aviation_terms = [
        "aviation",
        "aircraft",
        "airline",
        "airport",
        "aerospace",
        "flight operations",
        "air cargo",
    ]

    if any(
        term in title_lower
        for term in aviation_terms
    ):
        return "Aviation"

    # --------------------------------------------------------
    # MANUFACTURING
    # --------------------------------------------------------

    manufacturing_terms = [
        "manufacturing",
        "production",
        "assembly",
        "fabrication",
        "machine operator",
        "production operator",
    ]

    if any(
        term in title_lower
        for term in manufacturing_terms
    ):
        return "Manufacturing"

    # --------------------------------------------------------
    # LOGISTICS
    # --------------------------------------------------------

    logistics_terms = [
        "logistics",
        "warehouse",
        "supply chain",
        "inventory",
        "shipping",
        "receiving",
        "distribution",
    ]

    if any(
        term in title_lower
        for term in logistics_terms
    ):
        return "Logistics"

    # --------------------------------------------------------
    # HEALTHCARE
    # --------------------------------------------------------

    healthcare_title_terms = [
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
        "laboratory technician",
        "patient care",
    ]

    if any(
        term in title_lower
        for term in healthcare_title_terms
    ):
        return "Healthcare"

    # --------------------------------------------------------
    # CONSTRUCTION
    # --------------------------------------------------------

    construction_terms = [
        "construction",
        "carpenter",
        "electrician",
        "plumber",
        "welder",
        "concrete",
        "mason",
        "roofer",
    ]

    if any(
        term in title_lower
        for term in construction_terms
    ):
        return "Construction"

    # --------------------------------------------------------
    # MAINTENANCE
    # --------------------------------------------------------

    maintenance_terms = [
        "maintenance",
        "mechanic",
        "maintenance technician",
        "maintenance mechanic",
        "industrial technician",
        "equipment technician",
    ]

    if any(
        term in title_lower
        for term in maintenance_terms
    ):
        return "Maintenance"

    # --------------------------------------------------------
    # TRANSPORTATION
    # --------------------------------------------------------

    transportation_terms = [
        "driver",
        "delivery driver",
        "transportation",
        "truck driver",
        "courier",
        "dispatcher",
    ]

    if any(
        term in title_lower
        for term in transportation_terms
    ):
        return "Transportation"

    # --------------------------------------------------------
    # RETAIL
    # --------------------------------------------------------

    retail_terms = [
        "retail",
        "store associate",
        "sales associate",
        "cashier",
        "store manager",
    ]

    if any(
        term in title_lower
        for term in retail_terms
    ):
        return "Retail"

    # --------------------------------------------------------
    # RESTAURANTS / FOOD SERVICE
    # --------------------------------------------------------

    restaurant_terms = [
        "restaurant",
        "server",
        "waiter",
        "waitress",
        "cook",
        "chef",
        "food service",
        "line cook",
        "dishwasher",
    ]

    if any(
        term in title_lower
        for term in restaurant_terms
    ):
        return "Restaurants"

    # --------------------------------------------------------
    # HOSPITALITY
    # --------------------------------------------------------

    hospitality_terms = [
        "hotel",
        "resort",
        "hospitality",
        "front desk",
        "guest services",
        "housekeeping",
    ]

    if any(
        term in title_lower
        for term in hospitality_terms
    ):
        return "Hospitality"

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    security_terms = [
        "security",
        "security officer",
        "security guard",
    ]

    if any(
        term in title_lower
        for term in security_terms
    ):
        return "Security"

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    sales_terms = [
        "sales",
        "account executive",
        "sales representative",
        "business development",
    ]

    if any(
        term in title_lower
        for term in sales_terms
    ):
        return "Sales"

    # --------------------------------------------------------
    # CUSTOMER SERVICE
    # --------------------------------------------------------

    customer_service_terms = [
        "customer service",
        "customer support",
        "call center",
        "contact center",
    ]

    if any(
        term in title_lower
        for term in customer_service_terms
    ):
        return "Customer Service"

    # --------------------------------------------------------
    # FINANCE
    # --------------------------------------------------------

    finance_terms = [
        "accountant",
        "accounting",
        "finance",
        "financial analyst",
        "financial",
        "bookkeeper",
        "banking",
    ]

    if any(
        term in title_lower
        for term in finance_terms
    ):
        return "Finance"

    # --------------------------------------------------------
    # ADMINISTRATIVE
    # --------------------------------------------------------

    administrative_terms = [
        "administrative",
        "administration",
        "office assistant",
        "receptionist",
        "executive assistant",
        "office coordinator",
    ]

    if any(
        term in title_lower
        for term in administrative_terms
    ):
        return "Administrative"

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    education_terms = [
        "teacher",
        "professor",
        "instructor",
        "education",
        "school counselor",
        "academic",
    ]

    if any(
        term in title_lower
        for term in education_terms
    ):
        return "Education"

    # --------------------------------------------------------
    # GOVERNMENT
    # --------------------------------------------------------

    government_terms = [
        "government",
        "federal",
        "municipal",
        "public sector",
    ]

    if any(
        term in title_lower
        for term in government_terms
    ):
        return "Government"

    # --------------------------------------------------------
    # ENGINEERING
    # --------------------------------------------------------

    engineering_terms = [
        "engineer",
        "engineering",
    ]

    if any(
        term in title_lower
        for term in engineering_terms
    ):
        return "Engineering"

    # --------------------------------------------------------
    # CONTENT-BASED TECHNOLOGY
    # --------------------------------------------------------

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

    technology_score = sum(
        1
        for term in strong_technology_content
        if term in content_lower
    )

    if technology_score >= 2:
        return "Technology"

    return "Other"


# ============================================================
# WORK MODE
# ============================================================

def extract_work_mode(text):
    """
    Detecta modalidad de trabajo.
    """

    if not text:
        return "Unknown"

    lowered = text.lower()

    # Hybrid tiene prioridad si aparece explícitamente.
    if (
        "li-hybrid" in lowered
        or re.search(
            r"\bhybrid\b",
            lowered,
        )
    ):
        return "Hybrid"

    if (
        "li-remote" in lowered
        or re.search(
            r"\bremote\b",
            lowered,
        )
        or "work from home" in lowered
    ):
        return "Remote"

    if (
        "li-onsite" in lowered
        or re.search(
            r"\bon[- ]site\b",
            lowered,
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
    """
    Extrae niveles educativos.
    """

    if not text:
        return []

    lowered = text.lower()

    education = []

    if re.search(
        r"\bhigh school\b|\bhigh-school\b|\bsecondary school\b",
        lowered,
    ):
        education.append("High school")

    if re.search(
        r"\bassociate'?s?\b|\bassociates degree\b",
        lowered,
    ):
        education.append("Associate degree")

    if re.search(
        r"\bundergraduate degree\b|\bbachelor'?s?\b|\bbachelor degree\b",
        lowered,
    ):
        education.append("Bachelor's degree")

    if re.search(
        r"\bmaster'?s?\b|\bmaster degree\b",
        lowered,
    ):
        education.append("Master's degree")

    if re.search(
        r"\bph\.?d\.?\b|\bdoctorate\b",
        lowered,
    ):
        education.append("Doctorate")

    if re.search(
        r"\btechnical degree\b|\btechnical diploma\b",
        lowered,
    ):
        education.append("Technical degree")

    return education


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(text):
    """
    Extrae experiencia requerida.

    Ejemplos:

    3–5 years
    -> 3-5 years

    5+ years
    -> 5+ years

    También conserva requisitos adicionales.
    """

    if not text:
        return None, []

    normalized = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    matches = []

    # --------------------------------------------------------
    # RANGOS
    # --------------------------------------------------------

    range_pattern = re.compile(
        r"\b(\d+)\s*-\s*(\d+)\s+years?\b",
        flags=re.IGNORECASE,
    )

    for match in range_pattern.finditer(
        normalized
    ):
        minimum = match.group(1)
        maximum = match.group(2)

        start = max(
            0,
            match.start() - 80,
        )

        end = min(
            len(normalized),
            match.end() + 120,
        )

        context = normalize_space(
            normalized[start:end]
        )

        matches.append(
            {
                "start": match.start(),
                "value": (
                    f"{minimum}-{maximum} years"
                ),
                "context": context,
            }
        )

    # --------------------------------------------------------
    # X+ YEARS
    # --------------------------------------------------------

    plus_pattern = re.compile(
        r"\b(\d+)\s*\+\s*years?\b",
        flags=re.IGNORECASE,
    )

    for match in plus_pattern.finditer(
        normalized
    ):
        amount = match.group(1)

        start = max(
            0,
            match.start() - 80,
        )

        end = min(
            len(normalized),
            match.end() + 120,
        )

        context = normalize_space(
            normalized[start:end]
        )

        matches.append(
            {
                "start": match.start(),
                "value": f"{amount}+ years",
                "context": context,
            }
        )

    # --------------------------------------------------------
    # MINIMUM / AT LEAST
    # --------------------------------------------------------

    minimum_pattern = re.compile(
        r"\b(?:minimum of|at least)\s+"
        r"(\d+)\s+years?\b",
        flags=re.IGNORECASE,
    )

    for match in minimum_pattern.finditer(
        normalized
    ):
        amount = match.group(1)

        start = max(
            0,
            match.start() - 80,
        )

        end = min(
            len(normalized),
            match.end() + 120,
        )

        context = normalize_space(
            normalized[start:end]
        )

        matches.append(
            {
                "start": match.start(),
                "value": f"{amount}+ years",
                "context": context,
            }
        )

    if not matches:
        return None, []

    # Eliminar duplicados por posición/valor.
    unique = []

    seen = set()

    for item in sorted(
        matches,
        key=lambda x: x["start"],
    ):
        key = (
            item["start"],
            item["value"],
        )

        if key not in seen:
            unique.append(item)
            seen.add(key)

    # El primer requisito explícito suele ser
    # el requisito principal.
    primary = unique[0]["value"]

    details = []

    seen_values = set()

    for item in unique:
        value = item["value"]

        if value in seen_values:
            continue

        details.append(
            {
                "experience": value,
                "context": item["context"],
            }
        )

        seen_values.add(value)

    return primary, details


# ============================================================
# LICENSES
# ============================================================

def extract_licenses(text):
    """
    Extrae licencias/certificaciones.
    """

    if not text:
        return []

    lowered = text.lower()

    licenses = []

    patterns = [
        (
            "A&P",
            [
                "a&p",
                "airframe and powerplant",
            ],
        ),
        (
            "Driver's license",
            [
                "driver's license",
                "drivers license",
                "valid driver's license",
                "valid drivers license",
            ],
        ),
        (
            "FAA certification",
            [
                "faa certification",
                "faa license",
            ],
        ),
        (
            "CPA",
            [
                "cpa license",
                "certified public accountant",
            ],
        ),
        (
            "PMP",
            [
                "pmp certification",
                "project management professional",
            ],
        ),
    ]

    for license_name, keywords in patterns:
        if any(
            keyword in lowered
            for keyword in keywords
        ):
            licenses.append(license_name)

    return licenses


# ============================================================
# REQUIREMENTS
# ============================================================

def extract_requirements(text):
    """
    Construye requisitos estructurados.
    """

    experience, experience_details = (
        extract_experience(text)
    )

    return {
        "education": extract_education(
            text
        ),
        "experience": experience,
        "experience_details": experience_details,
        "licenses": extract_licenses(
            text
        ),
    }


# ============================================================
# DATES
# ============================================================

def parse_date_value(value):
    """
    Convierte fechas a ISO cuando es posible.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.isoformat()

    value = str(value).strip()

    if not value:
        return None

    # ISO 8601
    try:
        normalized = value.replace(
            "Z",
            "+00:00",
        )

        dt = datetime.fromisoformat(
            normalized
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.isoformat()

    except ValueError:
        pass

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]

    for date_format in date_formats:
        try:
            dt = datetime.strptime(
                value,
                date_format,
            )

            dt = dt.replace(
                tzinfo=timezone.utc
            )

            return dt.isoformat()

        except ValueError:
            continue

    return value


def extract_dates(job):
    """
    Recupera fechas publicadas por Greenhouse.
    """

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
    board_token,
):
    """
    Construye información de la fuente.
    """

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
        "name": "Greenhouse",
        "type": "job_board_api",
        "url": absolute_url,
        "application_url": absolute_url,
    }


# ============================================================
# NORMALIZER
# ============================================================

def normalize_greenhouse_job(
    job,
    company,
    board_token,
):
    """
    Convierte una vacante Greenhouse al esquema estándar
    del PR Intelligence Agent.
    """

    content = get_job_content(
        job
    )

    location = extract_location(
        job
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

    title = (
        job.get("title")
        or ""
    )

    normalized = {
        "company": company,

        "title": title,

        "job_id": (
            f"greenhouse-{board_token}-{job_id}"
            if job_id
            else f"greenhouse-{board_token}"
        ),

        "description": content,

        "location": location,

        "salary": salary,

        "employment_type": (
            extract_employment_type(
                content
            )
        ),

        "industry": (
            extract_industry(
                content,
                job,
            )
        ),

        "work_mode": (
            extract_work_mode(
                content
            )
        ),

        "requirements": requirements,

        "posted_date": posted_date,

        "updated_date": updated_date,

        "source": build_source(
            job,
            company,
            board_token,
        ),

        "verification": {
            "status": "source_verified",
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    }

    return normalized
