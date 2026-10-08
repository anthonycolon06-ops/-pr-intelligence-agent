import re
import html
from datetime import datetime, timezone


def decode_greenhouse_content(content):
    """
    Decodifica el contenido HTML/Unicode que devuelve Greenhouse.
    """

    if not content:
        return ""

    decoded = str(content)

    for _ in range(3):
        decoded = html.unescape(decoded)

    decoded = decoded.replace("\\u0026", "&")
    decoded = decoded.replace("\\u003c", "<")
    decoded = decoded.replace("\\u003e", ">")
    decoded = decoded.replace("\\/", "/")

    return decoded


def html_to_text(content):
    """
    Convierte HTML a texto limpio.
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
    Obtiene el contenido completo de una vacante Greenhouse.
    """

    content = job.get("content")

    if content:
        return html_to_text(content)

    description = job.get("description")

    if description:
        return html_to_text(description)

    return ""


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

    # Puerto Rico
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

    else:
        # Estados Unidos
        country = "US"

        us_match = re.search(
            r"([A-Za-z .'-]+),\s*([A-Z]{2})(?:,?\s*United States)?$",
            raw,
        )

        if us_match:
            municipality = (
                us_match.group(1).strip()
            )
            region = us_match.group(2).upper()

        else:
            municipality = raw or None

    return {
        "country": country,
        "municipality": municipality,
        "raw": raw,
        "region": region,
    }


def extract_salary(text):
    """
    Extrae salario solamente cuando existe una cantidad numérica
    publicada en el texto.

    No inventa salario cuando el anuncio dice solamente
    'Competitive salary', etc.
    """

    if not text:
        return {
            "currency": "USD",
            "max": None,
            "min": None,
            "period": "unknown",
            "published": False,
        }

    salary_pattern = re.compile(
        r"\$?\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(?:-|–|to)"
        r"\s*"
        r"\$?\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    match = salary_pattern.search(text)

    if match:
        minimum = float(
            match.group(1).replace(",", "")
        )

        maximum = float(
            match.group(2).replace(",", "")
        )

        period = (
            match.group(3)
            or "unknown"
        ).lower()

        if period in {
            "hour",
            "hr",
            "hourly",
        }:
            period = "hour"

        elif period in {
            "year",
            "annual",
            "annually",
        }:
            period = "year"

        elif period in {
            "month",
            "monthly",
        }:
            period = "month"

        return {
            "currency": "USD",
            "max": maximum,
            "min": minimum,
            "period": period,
            "published": True,
        }

    single_pattern = re.compile(
        r"\$"
        r"\s*"
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        r"\s*"
        r"(hour|hr|hourly|year|annual|annually|month|monthly)?",
        flags=re.IGNORECASE,
    )

    single_match = single_pattern.search(text)

    if single_match:
        amount = float(
            single_match.group(1).replace(",", "")
        )

        period = (
            single_match.group(2)
            or "unknown"
        ).lower()

        if period in {
            "hour",
            "hr",
            "hourly",
        }:
            period = "hour"

        elif period in {
            "year",
            "annual",
            "annually",
        }:
            period = "year"

        elif period in {
            "month",
            "monthly",
        }:
            period = "month"

        return {
            "currency": "USD",
            "max": amount,
            "min": amount,
            "period": period,
            "published": True,
        }

    return {
        "currency": "USD",
        "max": None,
        "min": None,
        "period": "unknown",
        "published": False,
    }


def extract_employment_type(text):
    """
    Detecta el tipo de empleo cuando aparece explícitamente.
    """

    if not text:
        return "Unknown"

    lowered = text.lower()

    patterns = [
        (
            "Full-time",
            [
                "full-time",
                "full time",
                "fulltime",
            ],
        ),
        (
            "Part-time",
            [
                "part-time",
                "part time",
                "parttime",
            ],
        ),
        (
            "Contract",
            [
                "contract position",
                "contract role",
                "contractor position",
            ],
        ),
        (
            "Temporary",
            [
                "temporary position",
                "temporary role",
                "temporary job",
            ],
        ),
        (
            "Internship",
            [
                "internship",
                "intern position",
                "intern role",
            ],
        ),
    ]

    for employment_type, keywords in patterns:
        for keyword in keywords:
            if keyword in lowered:
                return employment_type

    return "Unknown"


def extract_industry(text, job=None):
    """
    Determina industria de forma conservadora.
    """

    combined = text or ""

    if job:
        combined += " "
        combined += str(
            job.get("title") or ""
        )

        combined += " "
        combined += str(
            job.get("department") or ""
        )

    lowered = combined.lower()

    industry_keywords = [
        (
            "Aviation",
            [
                "aviation",
                "aircraft",
                "airline",
                "airport",
                "aerospace",
            ],
        ),
        (
            "Manufacturing",
            [
                "manufacturing",
                "production",
                "factory",
            ],
        ),
        (
            "Logistics",
            [
                "logistics",
                "warehouse",
                "supply chain",
            ],
        ),
        (
            "Healthcare",
            [
                "healthcare",
                "hospital",
                "medical",
                "clinical",
            ],
        ),
        (
            "Hospitality",
            [
                "hospitality",
                "hotel",
                "resort",
            ],
        ),
        (
            "Restaurants",
            [
                "restaurant",
                "food service",
            ],
        ),
        (
            "Retail",
            [
                "retail",
                "store associate",
            ],
        ),
        (
            "Technology",
            [
                "software",
                "technology",
                "engineering",
                "developer",
                "developer",
                "data science",
                "artificial intelligence",
                "machine learning",
                "llm",
                "information systems",
                "systems analyst",
            ],
        ),
        (
            "Construction",
            [
                "construction",
                "carpentry",
                "concrete",
            ],
        ),
        (
            "Maintenance",
            [
                "maintenance",
                "mechanic",
                "technician",
            ],
        ),
        (
            "Transportation",
            [
                "transportation",
                "driver",
                "delivery",
                "trucking",
            ],
        ),
        (
            "Customer Service",
            [
                "customer service",
                "customer support",
            ],
        ),
        (
            "Administrative",
            [
                "administrative",
                "administration",
                "office assistant",
            ],
        ),
        (
            "Finance",
            [
                "finance",
                "financial",
                "accounting",
            ],
        ),
        (
            "Education",
            [
                "education",
                "teacher",
                "school",
                "university",
            ],
        ),
        (
            "Government",
            [
                "government",
                "federal",
                "municipal",
            ],
        ),
        (
            "Security",
            [
                "security",
                "security officer",
            ],
        ),
        (
            "Sales",
            [
                "sales",
                "sales representative",
            ],
        ),
        (
            "Engineering",
            [
                "engineering",
                "engineer",
            ],
        ),
    ]

    for industry, keywords in industry_keywords:
        for keyword in keywords:
            if keyword in lowered:
                return industry

    return "Other"


def extract_work_mode(text):
    """
    Detecta modalidad de trabajo.
    """

    if not text:
        return "Unknown"

    lowered = text.lower()

    if (
        "hybrid" in lowered
        or "li-hybrid" in lowered
    ):
        return "Hybrid"

    if (
        "remote" in lowered
        or "li-remote" in lowered
        or "work from home" in lowered
    ):
        return "Remote"

    if (
        "on-site" in lowered
        or "onsite" in lowered
        or "on site" in lowered
        or "li-onsite" in lowered
    ):
        return "On-site"

    return "Unknown"


def extract_education(text):
    """
    Extrae niveles educativos mencionados.
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


def extract_experience(text):
    """
    Extrae experiencia requerida sin convertir rangos en máximos.

    Ejemplos:

    3–5 years -> 3-5 years
    5+ years -> 5+ years

    También conserva detalles adicionales en experience_details.
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

    range_pattern = re.compile(
        r"\b(\d+)\s*-\s*(\d+)\s+years?\b",
        flags=re.IGNORECASE,
    )

    plus_pattern = re.compile(
        r"\b(\d+)\s*\+\s*years?\b",
        flags=re.IGNORECASE,
    )

    # Primero encontramos todos los rangos.
    for match in range_pattern.finditer(normalized):
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
                "value": f"{minimum}-{maximum} years",
                "context": context,
            }
        )

    # Después encontramos X+ years.
    for match in plus_pattern.finditer(normalized):
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
        # Caso adicional: "minimum of 5 years"
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

    matches.sort(
        key=lambda item: item["start"]
    )

    primary = matches[0]["value"]

    details = []

    seen = set()

    for match in matches:
        detail = match["value"]

        if detail not in seen:
            details.append(
                {
                    "experience": detail,
                    "context": match["context"],
                }
            )

            seen.add(detail)

    return primary, details


def extract_licenses(text):
    """
    Extrae licencias/certificaciones importantes.
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


def extract_requirements(text):
    """
    Construye requisitos estructurados.
    """

    experience, experience_details = (
        extract_experience(text)
    )

    return {
        "education": extract_education(text),
        "experience": experience,
        "experience_details": experience_details,
        "licenses": extract_licenses(text),
    }


def parse_date_value(value):
    """
    Convierte una fecha conocida a ISO cuando es posible.
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

    # Ya parece ISO.
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

    # Fechas simples.
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
    Recupera las fechas de publicación y actualización
    desde los diferentes nombres de campos que puede entregar
    Greenhouse.

    No genera fechas artificiales.
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


def build_source(job, company, board_token):
    """
    Construye la información de fuente.
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

    application_url = absolute_url

    return {
        "name": "Greenhouse",
        "type": "job_board_api",
        "url": absolute_url,
        "application_url": application_url,
    }


def normalize_greenhouse_job(
    job,
    company,
    board_token,
):
    """
    Convierte un job de Greenhouse al esquema estándar
    del PR Intelligence Agent.
    """

    content = get_job_content(job)

    location = extract_location(job)

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
        "employment_type": extract_employment_type(
            content
        ),
        "industry": extract_industry(
            content,
            job,
        ),
        "work_mode": extract_work_mode(
            content
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
