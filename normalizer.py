import re
import html
from datetime import datetime


def decode_greenhouse_content(value):
    """
    Decodifica contenido de Greenhouse que puede venir
    con Unicode escapado y entidades HTML.
    """

    if not value:
        return ""

    text = str(value)

    def replace_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)

    # Convierte secuencias como \u0026lt; en caracteres reales.
    text = re.sub(
        r"\\u([0-9a-fA-F]{4})",
        replace_unicode,
        text,
    )

    # Decodifica entidades HTML.
    for _ in range(4):
        decoded = html.unescape(text)

        if decoded == text:
            break

        text = decoded

    return text


def html_to_text(value):
    """
    Convierte HTML a texto limpio.
    """

    if not value:
        return ""

    text = decode_greenhouse_content(value)

    # Elimina scripts y estilos.
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Convierte algunos elementos HTML en saltos de línea.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</(?:p|div|li|ul|ol|h1|h2|h3|h4|h5|h6)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Elimina cualquier otro tag HTML.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Normaliza espacios.
    text = text.replace("\xa0", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text,
    )

    return text.strip()


def get_job_content(job):
    """
    Obtiene el contenido completo disponible de una vacante.
    """

    possible_fields = [
        "content",
        "description",
        "job_description",
        "description_html",
    ]

    for field in possible_fields:
        value = job.get(field)

        if value:
            text = html_to_text(value)

            if text:
                return text

    return ""


def normalize_space(value):
    """
    Normaliza espacios en un texto.
    """

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def extract_location(job):
    """
    Extrae la ubicación de Greenhouse.
    """

    raw_location = ""

    location = job.get("location")

    if isinstance(location, dict):
        raw_location = (
            location.get("name")
            or location.get("raw")
            or ""
        )

    elif isinstance(location, str):
        raw_location = location

    if not raw_location:
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
                raw_location = ", ".join(names)

    raw_location = normalize_space(raw_location)

    lowered = raw_location.lower()

    country = None
    region = None
    municipality = None

    if "puerto rico" in lowered or re.search(
        r"\bPR\b",
        raw_location,
        flags=re.IGNORECASE,
    ):
        country = "PR"
        region = "Puerto Rico"

        if "puerto rico" in lowered:
            municipality = "Puerto Rico"

    else:
        country = job.get("country")

        if isinstance(country, str):
            country = country.upper()

        region = job.get("region")
        municipality = job.get("municipality")

    return {
        "country": country,
        "municipality": municipality,
        "region": region,
        "raw": raw_location,
    }


def extract_salary(job, content=""):
    """
    Extrae salario estructurado o salario publicado en el texto.

    No inventa salario.
    """

    salary = job.get("salary")

    if isinstance(salary, dict):
        minimum = salary.get("min")
        maximum = salary.get("max")
        currency = salary.get("currency") or "USD"
        period = salary.get("period") or "unknown"

        if minimum is not None or maximum is not None:
            return {
                "currency": currency,
                "min": minimum,
                "max": maximum,
                "period": period,
                "published": True,
            }

    text = content or ""

    salary_patterns = [
        (
            r"\$\s*([\d,]+(?:\.\d+)?)\s*[-–]\s*"
            r"\$?\s*([\d,]+(?:\.\d+)?)\s*"
            r"(?:per\s+hour|/hour|hourly)",
            "hour",
        ),
        (
            r"\$\s*([\d,]+(?:\.\d+)?)\s*"
            r"(?:per\s+hour|/hour|hourly)",
            "hour",
        ),
        (
            r"\$\s*([\d,]+(?:\.\d+)?)\s*[-–]\s*"
            r"\$?\s*([\d,]+(?:\.\d+)?)\s*"
            r"(?:per\s+year|/year|annually|annual)",
            "year",
        ),
        (
            r"\$\s*([\d,]+(?:\.\d+)?)\s*"
            r"(?:per\s+year|/year|annually|annual)",
            "year",
        ),
    ]

    for pattern, period in salary_patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        values = []

        for group in match.groups():
            if group:
                values.append(
                    float(group.replace(",", ""))
                )

        if len(values) == 1:
            minimum = values[0]
            maximum = values[0]

        else:
            minimum = min(values)
            maximum = max(values)

        return {
            "currency": "USD",
            "min": minimum,
            "max": maximum,
            "period": period,
            "published": True,
        }

    return {
        "currency": "USD",
        "min": None,
        "max": None,
        "period": "unknown",
        "published": False,
    }


def extract_employment_type(job, content=""):
    """
    Determina Full-Time / Part-Time / Contract / Temporary
    cuando existe evidencia explícita.
    """

    fields = [
        job.get("employment_type"),
        job.get("employmentType"),
        job.get("type"),
    ]

    for value in fields:
        if not value:
            continue

        text = normalize_space(value).lower()

        if "full" in text and "time" in text:
            return "Full-Time"

        if "part" in text and "time" in text:
            return "Part-Time"

        if "contract" in text:
            return "Contract"

        if "temporary" in text or "temp" in text:
            return "Temporary"

    text = content or ""

    patterns = [
        (
            r"\bfull[\s-]?time\b",
            "Full-Time",
        ),
        (
            r"\bpart[\s-]?time\b",
            "Part-Time",
        ),
        (
            r"\bindependent contractor\b",
            "Contract",
        ),
        (
            r"\bcontract(?:or)?\b",
            "Contract",
        ),
        (
            r"\btemporary\b",
            "Temporary",
        ),
    ]

    for pattern, employment_type in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return employment_type

    return "Unknown"


def extract_industry(job, content=""):
    """
    Determina la industria usando campos estructurados
    y, cuando faltan, palabras clave del contenido.
    """

    candidates = []

    for field in [
        job.get("industry"),
        job.get("category"),
        job.get("department"),
    ]:
        if isinstance(field, str):
            candidates.append(field)

        elif isinstance(field, dict):
            name = field.get("name")

            if name:
                candidates.append(str(name))

        elif isinstance(field, list):
            for item in field:
                if isinstance(item, str):
                    candidates.append(item)

                elif isinstance(item, dict):
                    name = item.get("name")

                    if name:
                        candidates.append(str(name))

    structured = " ".join(candidates).lower()

    if structured:
        if any(
            word in structured
            for word in [
                "engineering",
                "technology",
                "software",
                "information technology",
                "it",
            ]
        ):
            return "Technology"

        if "aviation" in structured or "aerospace" in structured:
            return "Aviation"

        if "manufacturing" in structured:
            return "Manufacturing"

        if "logistics" in structured:
            return "Logistics"

        if "health" in structured or "medical" in structured:
            return "Healthcare"

        if "hospitality" in structured:
            return "Hospitality"

        if "restaurant" in structured or "food" in structured:
            return "Restaurants"

        if "retail" in structured:
            return "Retail"

        if "construction" in structured:
            return "Construction"

        if "maintenance" in structured:
            return "Maintenance"

        if "transportation" in structured:
            return "Transportation"

        if "customer service" in structured:
            return "Customer Service"

        if "administrative" in structured:
            return "Administrative"

        if "finance" in structured or "accounting" in structured:
            return "Finance"

        if "education" in structured:
            return "Education"

        if "government" in structured:
            return "Government"

        if "security" in structured:
            return "Security"

        if "sales" in structured:
            return "Sales"

        return candidates[0]

    text = (content or "").lower()

    scores = {
        "Technology": 0,
        "Aviation": 0,
        "Manufacturing": 0,
        "Logistics": 0,
        "Healthcare": 0,
        "Hospitality": 0,
        "Restaurants": 0,
        "Retail": 0,
        "Construction": 0,
        "Maintenance": 0,
        "Transportation": 0,
        "Customer Service": 0,
        "Administrative": 0,
        "Finance": 0,
        "Education": 0,
        "Government": 0,
        "Security": 0,
        "Sales": 0,
        "Engineering": 0,
    }

    keyword_groups = {
        "Technology": [
            "software",
            "software engineering",
            "developer",
            "programming",
            "javascript",
            "typescript",
            "python",
            "sql",
            "api",
            "llm",
            "artificial intelligence",
            "machine learning",
            "technology",
            "data",
            "cloud",
            "cybersecurity",
        ],
        "Aviation": [
            "aircraft",
            "aviation",
            "airline",
            "airport",
            "aerospace",
            "ramp",
            "flight",
            "hangar",
        ],
        "Manufacturing": [
            "manufacturing",
            "production",
            "assembly",
            "factory",
        ],
        "Logistics": [
            "logistics",
            "warehouse",
            "inventory",
            "shipping",
            "supply chain",
        ],
        "Healthcare": [
            "healthcare",
            "hospital",
            "clinical",
            "medical",
            "patient",
        ],
        "Hospitality": [
            "hotel",
            "hospitality",
            "guest services",
            "front desk",
        ],
        "Restaurants": [
            "restaurant",
            "server",
            "waiter",
            "food service",
            "kitchen",
        ],
        "Retail": [
            "retail",
            "store",
            "sales associate",
            "cashier",
        ],
        "Construction": [
            "construction",
            "carpenter",
            "electrician",
            "plumbing",
        ],
        "Maintenance": [
            "maintenance",
            "mechanic",
            "repair",
            "technician",
        ],
        "Transportation": [
            "transportation",
            "driver",
            "delivery",
            "fleet",
        ],
        "Customer Service": [
            "customer service",
            "customer support",
            "call center",
        ],
        "Administrative": [
            "administrative",
            "office administrator",
            "receptionist",
            "clerical",
        ],
        "Finance": [
            "finance",
            "financial",
            "accounting",
            "accountant",
            "banking",
        ],
        "Education": [
            "education",
            "teacher",
            "school",
            "university",
            "instructor",
        ],
        "Government": [
            "government",
            "federal",
            "municipal",
            "public sector",
        ],
        "Security": [
            "security",
            "security officer",
            "guard",
        ],
        "Sales": [
            "sales",
            "business development",
            "account executive",
        ],
        "Engineering": [
            "engineering",
            "engineer",
            "technical engineering",
        ],
    }

    for industry, keywords in keyword_groups.items():
        for keyword in keywords:
            if keyword in text:
                scores[industry] += 1

    best_industry = max(
        scores,
        key=scores.get,
    )

    if scores[best_industry] > 0:
        return best_industry

    return "Other"


def extract_work_mode(job, content="", raw_location=""):
    """
    Determina Remote / Hybrid / On-site.
    """

    text = " ".join(
        [
            str(job.get("work_mode") or ""),
            str(job.get("remote") or ""),
            str(job.get("remote_status") or ""),
            content or "",
            raw_location or "",
        ]
    ).lower()

    # Los tags de Greenhouse tienen alta confiabilidad.
    if "#li-remote" in text:
        return "Remote"

    if "#li-hybrid" in text:
        return "Hybrid"

    if re.search(
        r"\bfully remote\b|\b100% remote\b|\bremote role\b|\bremote position\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "Remote"

    if re.search(
        r"\bhybrid\b|\bhybrid role\b|\bhybrid position\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"\bon[- ]site\b|\bonsite\b|\bin[- ]office\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "On-site"

    return "Unknown"


def extract_education(content=""):
    """
    Extrae requisitos educativos comunes.
    """

    text = content or ""

    education = []

    patterns = [
        (
            r"\bbachelor(?:'s|’s)?\s+degree\b",
            "Bachelor's degree",
        ),
        (
            r"\bbachelor(?:'s|’s)?\b",
            "Bachelor's degree",
        ),
        (
            r"\bmaster(?:'s|’s)?\s+degree\b",
            "Master's degree",
        ),
        (
            r"\bmaster(?:'s|’s)?\b",
            "Master's degree",
        ),
        (
            r"\bassociate(?:'s|’s)?\s+degree\b",
            "Associate degree",
        ),
        (
            r"\bassociate(?:'s|’s)?\b",
            "Associate degree",
        ),
        (
            r"\bundergraduate degree\b",
            "Undergraduate degree",
        ),
        (
            r"\bhigh school diploma\b",
            "High school diploma",
        ),
        (
            r"\bged\b",
            "GED",
        ),
    ]

    for pattern, label in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            if label not in education:
                education.append(label)

    return education


def extract_experience(content=""):
    """
    Extrae experiencia profesional expresada en años.

    Ejemplos reconocidos:
    5+ years
    3-5 years
    3–5 years
    2+ years of experience
    """

    text = content or ""

    matches = []

    patterns = [
        r"\b(\d+)\s*\+\s*years?\s+(?:of\s+)?(?:professional\s+)?experience\b",

        r"\b(\d+)\s*[-–]\s*(\d+)\s+years?\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience\b",

        r"\bminimum\s+of\s+(\d+)\s+years?\s+(?:of\s+)?experience\b",

        r"\bat\s+least\s+(\d+)\s+years?\s+(?:of\s+)?experience\b",

        r"\b(\d+)\s+years?\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience\b",
    ]

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            numbers = []

            for group in match.groups():
                if group:
                    numbers.append(int(group))

            if numbers:
                matches.append(
                    max(numbers)
                )

    if not matches:
        return None

    highest = max(matches)

    return f"{highest}+ years"


def extract_licenses(content=""):
    """
    Extrae algunas licencias/certificaciones comunes.
    """

    text = content or ""

    licenses = []

    patterns = [
        (
            r"\bA&P\b",
            "A&P",
        ),
        (
            r"\bEPA\s+608\b",
            "EPA 608",
        ),
        (
            r"\bCDL\b",
            "CDL",
        ),
        (
            r"\bFAA\b",
            "FAA",
        ),
        (
            r"\bOSHA\b",
            "OSHA",
        ),
    ]

    for pattern, label in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            if label not in licenses:
                licenses.append(label)

    return licenses


def extract_requirements(job, content=""):
    """
    Construye requisitos usando los campos estructurados
    y el contenido completo.
    """

    structured = job.get("requirements")

    education = []
    experience = None
    licenses = []

    if isinstance(structured, dict):
        structured_education = structured.get(
            "education"
        )

        if isinstance(
            structured_education,
            list,
        ):
            education.extend(
                str(item)
                for item in structured_education
                if item
            )

        elif structured_education:
            education.append(
                str(structured_education)
            )

        experience = structured.get(
            "experience"
        )

        structured_licenses = structured.get(
            "licenses"
        )

        if isinstance(
            structured_licenses,
            list,
        ):
            licenses.extend(
                str(item)
                for item in structured_licenses
                if item
            )

    extracted_education = extract_education(
        content
    )

    for item in extracted_education:
        if item not in education:
            education.append(item)

    extracted_experience = extract_experience(
        content
    )

    if extracted_experience:
        experience = extracted_experience

    extracted_licenses = extract_licenses(
        content
    )

    for item in extracted_licenses:
        if item not in licenses:
            licenses.append(item)

    return {
        "education": education,
        "experience": experience,
        "licenses": licenses,
    }


def extract_dates(job):
    """
    Extrae fechas de publicación y actualización.
    """

    posted_date = (
        job.get("first_published_at")
        or job.get("published_at")
        or job.get("created_at")
        or job.get("date_posted")
    )

    updated_date = (
        job.get("updated_at")
        or job.get("last_updated_at")
        or job.get("updated_date")
    )

    return posted_date, updated_date


def build_source(job, board_token):
    """
    Construye la información de fuente.
    """

    job_id = job.get("id")

    application_url = (
        job.get("absolute_url")
        or job.get("url")
    )

    if not application_url and job_id:
        application_url = (
            f"https://boards.greenhouse.io/"
            f"{board_token}/jobs/{job_id}"
        )

    if not application_url and job_id:
        application_url = (
            f"https://www.bold.com/"
            f"job-description/{job_id}"
            f"?gh_jid={job_id}"
        )

    return {
        "name": "Greenhouse",
        "type": "job_board_api",
        "url": application_url,
        "application_url": application_url,
    }


def normalize_greenhouse_job(
    job,
    company,
    board_token,
):
    """
    Convierte un job de Greenhouse al formato estándar
    del PR Intelligence Agent.
    """

    content = get_job_content(job)

    location = extract_location(job)

    raw_location = location.get(
        "raw",
        "",
    )

    salary = extract_salary(
        job,
        content,
    )

    employment_type = extract_employment_type(
        job,
        content,
    )

    industry = extract_industry(
        job,
        content,
    )

    work_mode = extract_work_mode(
        job,
        content,
        raw_location,
    )

    requirements = extract_requirements(
        job,
        content,
    )

    posted_date, updated_date = extract_dates(
        job
    )

    job_id = job.get("id")

    checked_at = (
        datetime.now().astimezone().isoformat()
    )

    return {
        "job_id": (
            f"greenhouse-{board_token}-{job_id}"
            if job_id
            else f"greenhouse-{board_token}-unknown"
        ),
        "title": (
            job.get("title")
            or "Unknown"
        ),
        "company": company,
        "location": location,
        "salary": salary,
        "employment_type": employment_type,
        "industry": industry,
        "work_mode": work_mode,
        "requirements": requirements,
        "description": content,
        "posted_date": posted_date,
        "updated_date": updated_date,
        "source": build_source(
            job,
            board_token,
        ),
        "verification": {
            "status": "source_verified",
            "checked_at": checked_at,
        },
    }
