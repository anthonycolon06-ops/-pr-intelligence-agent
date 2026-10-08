import re
import html
from datetime import datetime


US_STATE_ABBREVIATIONS = {
    "al": "Alabama",
    "ak": "Alaska",
    "az": "Arizona",
    "ar": "Arkansas",
    "ca": "California",
    "co": "Colorado",
    "ct": "Connecticut",
    "de": "Delaware",
    "fl": "Florida",
    "ga": "Georgia",
    "hi": "Hawaii",
    "id": "Idaho",
    "il": "Illinois",
    "in": "Indiana",
    "ia": "Iowa",
    "ks": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "me": "Maine",
    "md": "Maryland",
    "ma": "Massachusetts",
    "mi": "Michigan",
    "mn": "Minnesota",
    "ms": "Mississippi",
    "mo": "Missouri",
    "mt": "Montana",
    "ne": "Nebraska",
    "nv": "Nevada",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "ny": "New York",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "oh": "Ohio",
    "ok": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tn": "Tennessee",
    "tx": "Texas",
    "ut": "Utah",
    "vt": "Vermont",
    "va": "Virginia",
    "wa": "Washington",
    "wv": "West Virginia",
    "wi": "Wisconsin",
    "wy": "Wyoming",
    "dc": "District of Columbia",
}


US_STATE_NAMES = {
    name.lower()
    for name in US_STATE_ABBREVIATIONS.values()
}


def clean_text(value):
    if value is None:
        return ""

    text = str(value)

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def decode_greenhouse_content(value):
    """
    Greenhouse puede devolver contenido HTML
    doblemente escapado.

    Ejemplo:

    \\u0026lt;p\\u0026gt;

    Esta función convierte ese contenido
    en HTML normal.
    """

    if value is None:
        return ""

    text = str(value)

    # Decodificar escapes Unicode específicos.
    def replace_unicode(match):
        try:
            return chr(
                int(
                    match.group(1),
                    16
                )
            )
        except ValueError:
            return match.group(0)

    text = re.sub(
        r"\\u([0-9a-fA-F]{4})",
        replace_unicode,
        text,
    )

    # Decodificar entidades HTML varias veces.
    for _ in range(4):
        decoded = html.unescape(text)

        if decoded == text:
            break

        text = decoded

    return text


def html_to_text(value):
    """
    Convierte HTML de Greenhouse a texto limpio.
    """

    text = decode_greenhouse_content(value)

    if not text:
        return ""

    # Eliminar scripts.
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Eliminar estilos.
    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Saltos de línea para elementos HTML.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</(?:p|div|li|ul|ol|h1|h2|h3|h4|h5|h6|section)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Eliminar etiquetas restantes.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Decodificar entidades restantes.
    text = html.unescape(text)

    # Limpiar espacios.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s+",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def get_job_content(job):
    """
    Obtiene el contenido completo del job.

    Greenhouse normalmente utiliza 'content'.
    """

    fields = [
        "content",
        "description",
        "job_description",
        "description_html",
    ]

    for field in fields:
        value = job.get(field)

        if value:
            return value

    return ""


def detect_country(location_text):
    text = clean_text(
        location_text
    ).lower()

    if not text:
        return None

    # Puerto Rico
    if (
        "puerto rico" in text
        or text == "pr"
        or ", pr" in text
        or " pr " in f" {text} "
    ):
        return "PR"

    # Estados Unidos
    if (
        "united states" in text
        or "united states of america" in text
        or "usa" in text
        or "u.s.a" in text
        or "u.s." in text
        or " us " in f" {text} "
    ):
        return "US"

    # Estados de EE.UU.
    for state_name in US_STATE_NAMES:
        if state_name in text:
            return "US"

    words = (
        text
        .replace(",", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("-", " ")
        .split()
    )

    for word in words:
        if word in US_STATE_ABBREVIATIONS:
            return "US"

    return None


def detect_other_country(location_text):
    text = clean_text(
        location_text
    ).lower()

    countries = {
        "india": "India",
        "canada": "Canada",
        "mexico": "Mexico",
        "poland": "Poland",
        "united kingdom": "United Kingdom",
        "uk": "United Kingdom",
        "england": "United Kingdom",
        "ireland": "Ireland",
        "germany": "Germany",
        "france": "France",
        "spain": "Spain",
        "italy": "Italy",
        "brazil": "Brazil",
        "argentina": "Argentina",
        "chile": "Chile",
        "colombia": "Colombia",
        "australia": "Australia",
        "singapore": "Singapore",
        "philippines": "Philippines",
        "japan": "Japan",
        "china": "China",
    }

    for key, country_name in countries.items():
        if key in text:
            return country_name

    return None


def normalize_location(raw_location):
    raw = clean_text(
        raw_location
    )

    if not raw:
        return {
            "country": None,
            "municipality": None,
            "region": None,
            "raw": raw,
        }

    text_lower = raw.lower()

    country = detect_country(
        raw
    )

    # Puerto Rico
    if country == "PR":

        if (
            text_lower == "puerto rico"
            or text_lower == "pr"
        ):
            return {
                "country": "PR",
                "municipality": "Puerto Rico",
                "region": "Puerto Rico",
                "raw": raw,
            }

        parts = [
            clean_text(part)
            for part in raw.split(",")
            if clean_text(part)
        ]

        municipality = (
            parts[0]
            if parts
            else "Puerto Rico"
        )

        return {
            "country": "PR",
            "municipality": municipality,
            "region": "Puerto Rico",
            "raw": raw,
        }

    # Estados Unidos
    if country == "US":

        if (
            "remote" in text_lower
            and (
                "united states" in text_lower
                or "usa" in text_lower
                or "u.s." in text_lower
            )
        ):
            return {
                "country": "US",
                "municipality": "United States",
                "region": None,
                "raw": raw,
            }

        if text_lower in {
            "usa",
            "u.s.",
            "u.s.a.",
            "united states",
            "united states of america",
        }:
            return {
                "country": "US",
                "municipality": "United States",
                "region": None,
                "raw": raw,
            }

        parts = [
            clean_text(part)
            for part in raw.split(",")
            if clean_text(part)
        ]

        municipality = (
            parts[0]
            if parts
            else "United States"
        )

        region = None

        if len(parts) >= 2:

            possible_region = (
                parts[1].strip()
            )

            possible_region_lower = (
                possible_region.lower()
            )

            if (
                possible_region_lower
                in US_STATE_ABBREVIATIONS
            ):
                region = (
                    US_STATE_ABBREVIATIONS[
                        possible_region_lower
                    ]
                )

            else:
                region = possible_region

        return {
            "country": "US",
            "municipality": municipality,
            "region": region,
            "raw": raw,
        }

    # Otros países
    other_country = detect_other_country(
        raw
    )

    parts = [
        clean_text(part)
        for part in raw.split(",")
        if clean_text(part)
    ]

    municipality = (
        parts[0]
        if parts
        else raw
    )

    region = (
        parts[1]
        if len(parts) >= 2
        else None
    )

    if other_country:
        return {
            "country": other_country,
            "municipality": municipality,
            "region": region,
            "raw": raw,
        }

    return {
        "country": None,
        "municipality": municipality,
        "region": region,
        "raw": raw,
    }


def extract_location(job):
    location = job.get(
        "location"
    )

    if isinstance(location, dict):

        for key in [
            "name",
            "raw",
            "location",
            "city",
        ]:
            value = location.get(
                key
            )

            if value:
                return clean_text(
                    value
                )

    if isinstance(location, list):

        locations = []

        for item in location:

            if isinstance(item, dict):

                value = (
                    item.get("name")
                    or item.get("raw")
                    or item.get("location")
                    or item.get("city")
                )

                if value:
                    locations.append(
                        clean_text(value)
                    )

            elif item:
                locations.append(
                    clean_text(item)
                )

        if locations:
            return ", ".join(
                locations
            )

    if location:
        return clean_text(
            location
        )

    offices = job.get(
        "offices",
        []
    )

    if isinstance(offices, list):

        office_names = []

        for office in offices:

            if isinstance(
                office,
                dict
            ):
                name = office.get(
                    "name"
                )

                if name:
                    office_names.append(
                        clean_text(name)
                    )

        if office_names:
            return ", ".join(
                office_names
            )

    for key in [
        "location_name",
        "job_location",
        "office_location",
    ]:

        value = job.get(
            key
        )

        if value:
            return clean_text(
                value
            )

    return ""


def extract_posted_date(job):
    for key in [
        "first_published",
        "first_published_at",
        "published_at",
        "created_at",
        "createdAt",
        "posted_date",
    ]:

        value = job.get(
            key
        )

        if value:
            return value

    return None


def extract_updated_date(job):
    for key in [
        "updated_at",
        "updatedAt",
        "updated_date",
    ]:

        value = job.get(
            key
        )

        if value:
            return value

    return None


def extract_salary(
    job,
    content
):
    """
    Extrae salario solamente cuando
    existe una cantidad explícita.
    """

    text = clean_text(
        content
    )

    if not text:
        return {
            "min": None,
            "max": None,
            "currency": "USD",
            "period": "unknown",
            "published": False,
        }

    patterns = [

        (
            r"\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*[-–]"
            r"\s*\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*(?:per\s+hour|/hour|hourly)\b",
            "hour",
        ),

        (
            r"\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*[-–]"
            r"\s*\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*(?:per\s+year|/year|annually|annual)\b",
            "year",
        ),

        (
            r"\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*(?:per\s+hour|/hour|hourly)\b",
            "hour",
        ),

        (
            r"\$?\s*([\d,]+(?:\.\d+)?)"
            r"\s*(?:per\s+year|/year|annually|annual)\b",
            "year",
        ),
    ]

    for pattern, period in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        numbers = [
            float(
                value.replace(",", "")
            )
            for value in match.groups()
        ]

        if len(numbers) == 2:
            minimum = numbers[0]
            maximum = numbers[1]
        else:
            minimum = numbers[0]
            maximum = numbers[0]

        return {
            "min": minimum,
            "max": maximum,
            "currency": "USD",
            "period": period,
            "published": True,
        }

    return {
        "min": None,
        "max": None,
        "currency": "USD",
        "period": "unknown",
        "published": False,
    }


def extract_employment_type(
    job,
    content
):
    structured_values = [
        job.get(
            "employment_type"
        ),
        job.get(
            "employmentType"
        ),
        job.get(
            "type"
        ),
    ]

    for value in structured_values:

        if value:

            text = clean_text(
                value
            ).lower()

            if "full" in text:
                return "Full-time"

            if "part" in text:
                return "Part-time"

            if "contract" in text:
                return "Contract"

            if "temporary" in text:
                return "Temporary"

            if "intern" in text:
                return "Internship"

    text = clean_text(
        content
    ).lower()

    if re.search(
        r"\bfull[- ]time\b",
        text
    ):
        return "Full-time"

    if re.search(
        r"\bpart[- ]time\b",
        text
    ):
        return "Part-time"

    if re.search(
        r"\bcontract\b",
        text
    ):
        return "Contract"

    if re.search(
        r"\btemporary\b",
        text
    ):
        return "Temporary"

    if re.search(
        r"\bintern(ship)?\b",
        text
    ):
        return "Internship"

    return "Unknown"


def extract_industry(
    job,
    content
):
    """
    Industry inferida a partir del departamento,
    título y contenido.
    """

    department_text = ""

    departments = job.get(
        "departments",
        []
    )

    if isinstance(
        departments,
        list
    ):

        names = []

        for department in departments:

            if isinstance(
                department,
                dict
            ):

                name = department.get(
                    "name"
                )

                if name:
                    names.append(
                        str(name)
                    )

        department_text = " ".join(
            names
        )

    title = clean_text(
        job.get(
            "title",
            ""
        )
    )

    text = (
        f"{department_text} "
        f"{title} "
        f"{clean_text(content)}"
    ).lower()

    industry_keywords = {

        "Aviation": [
            "aviation",
            "aircraft",
            "airline",
            "airport",
            "a&p",
            "faa",
        ],

        "Manufacturing": [
            "manufacturing",
            "production",
            "assembly",
            "machining",
        ],

        "Logistics": [
            "logistics",
            "warehouse",
            "distribution",
            "supply chain",
        ],

        "Healthcare": [
            "healthcare",
            "medical",
            "hospital",
            "clinical",
            "nursing",
        ],

        "Hospitality": [
            "hotel",
            "hospitality",
            "resort",
            "guest services",
        ],

        "Restaurants": [
            "restaurant",
            "server",
            "waiter",
            "cook",
            "kitchen",
            "food service",
        ],

        "Retail": [
            "retail",
            "store associate",
            "merchandising",
            "sales associate",
        ],

        "Technology": [
            "software",
            "technology",
            "information technology",
            "developer",
            "programming",
            "javascript",
            "typescript",
            "python",
            "llm",
            "artificial intelligence",
            "machine learning",
        ],

        "Construction": [
            "construction",
            "carpentry",
            "concrete",
            "building",
        ],

        "Maintenance": [
            "maintenance",
            "mechanic",
            "technician",
            "repair",
            "hvac",
            "electrical",
        ],

        "Transportation": [
            "transportation",
            "driver",
            "fleet",
            "delivery",
            "trucking",
        ],

        "Customer Service": [
            "customer service",
            "customer support",
            "call center",
            "customer experience",
        ],

        "Administrative": [
            "administrative",
            "office administrator",
            "coordinator",
            "clerical",
            "receptionist",
        ],

        "Finance": [
            "finance",
            "accounting",
            "financial",
            "accountant",
            "bookkeeping",
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
            "guard",
            "protective services",
        ],

        "Sales": [
            "sales",
            "account executive",
            "business development",
        ],

        "Engineering": [
            "engineer",
            "engineering",
            "systems engineering",
        ],
    }

    scores = {}

    for industry, keywords in (
        industry_keywords.items()
    ):

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        if score:
            scores[industry] = score

    if not scores:
        return "Other"

    return max(
        scores,
        key=scores.get
    )


def extract_work_mode(
    job,
    content,
    raw_location
):
    """
    Detecta Remote, Hybrid u On-site.
    """

    title = clean_text(
        job.get(
            "title",
            ""
        )
    )

    text = (
        f"{raw_location} "
        f"{title} "
        f"{clean_text(content)}"
    ).lower()

    if (
        "#li-hybrid" in text
        or "hybrid" in text
    ):
        return "Hybrid"

    if (
        "100% remote" in text
        or "fully remote" in text
        or "work remotely" in text
        or "remote position" in text
        or "remote job" in text
        or "(remote)" in text
        or "remote" in text
    ):
        return "Remote"

    if (
        "on-site" in text
        or "onsite" in text
        or "on site" in text
        or "in-office" in text
        or "in office" in text
    ):
        return "On-site"

    return "Unknown"


def extract_requirements(
    job,
    content
):
    """
    Extrae requisitos directamente del contenido
    de la vacante.
    """

    text = clean_text(
        content
    )

    education = []
    licenses = []
    experience_values = []

    education_patterns = [

        (
            r"\bbachelor(?:'s|’s)?\b",
            "Bachelor's degree",
        ),

        (
            r"\bmaster(?:'s|’s)?\b",
            "Master's degree",
        ),

        (
            r"\bassociate(?:'s|’s)?\b",
            "Associate degree",
        ),

        (
            r"\bhigh school diploma\b",
            "High school diploma",
        ),

        (
            r"\bhigh school degree\b",
            "High school degree",
        ),

        (
            r"\bged\b",
            "GED",
        ),

        (
            r"\bdoctoral\b",
            "Doctoral degree",
        ),

        (
            r"\bph\.?d\.?\b",
            "Doctoral degree",
        ),
    ]

    for pattern, label in education_patterns:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            education.append(
                label
            )

    experience_patterns = [

        r"(\d+)\s*\+\s*years?"
        r"(?:\s+of)?"
        r"\s+(?:professional\s+)?experience",

        r"at\s+least\s+(\d+)\s+years?",

        r"minimum\s+of\s+(\d+)\s+years?",
    ]

    for pattern in experience_patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for value in matches:

            try:
                experience_values.append(
                    int(value)
                )
            except ValueError:
                pass

    experience = None

    if experience_values:

        highest = max(
            experience_values
        )

        experience = (
            f"{highest}+ years"
        )

    license_patterns = [

        (
            r"\ba&p\b",
            "A&P",
        ),

        (
            r"\bfaa\b",
            "FAA",
        ),

        (
            r"\bdriver(?:'s|’s)? license\b",
            "Driver's license",
        ),

        (
            r"\bcdl\b",
            "CDL",
        ),

        (
            r"\bpmp\b",
            "PMP",
        ),

        (
            r"\bcpa\b",
            "CPA",
        ),

        (
            r"\bcna\b",
            "CNA",
        ),

        (
            r"\bcnc\b",
            "CNC",
        ),

        (
            r"\bosha\b",
            "OSHA",
        ),

        (
            r"\bsix sigma\b",
            "Six Sigma",
        ),
    ]

    for pattern, label in license_patterns:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            licenses.append(
                label
            )

    return {
        "education": list(
            dict.fromkeys(
                education
            )
        ),

        "experience": experience,

        "licenses": list(
            dict.fromkeys(
                licenses
            )
        ),
    }


def extract_description(content):
    return html_to_text(
        content
    )


def normalize_greenhouse_job(
    job,
    company,
    board_token
):
    """
    Convierte un job de Greenhouse al
    esquema estándar de PR Intelligence Agent.
    """

    # ---------------------------------
    # CONTENIDO COMPLETO
    # ---------------------------------

    content_raw = get_job_content(
        job
    )

    content = html_to_text(
        content_raw
    )

    # ---------------------------------
    # UBICACIÓN
    # ---------------------------------

    raw_location = extract_location(
        job
    )

    location = normalize_location(
        raw_location
    )

    # ---------------------------------
    # DATOS BÁSICOS
    # ---------------------------------

    title = clean_text(
        job.get(
            "title",
            ""
        )
    )

    job_id = (
        job.get("id")
        or job.get("job_id")
        or job.get("requisition_id")
        or "unknown"
    )

    job_url = (
        job.get("absolute_url")
        or job.get("url")
        or job.get("application_url")
        or ""
    )

    # ---------------------------------
    # METADATOS
    # ---------------------------------

    posted_date = extract_posted_date(
        job
    )

    updated_date = extract_updated_date(
        job
    )

    employment_type = extract_employment_type(
        job,
        content
    )

    industry = extract_industry(
        job,
        content
    )

    salary = extract_salary(
        job,
        content
    )

    requirements = extract_requirements(
        job,
        content
    )

    work_mode = extract_work_mode(
        job,
        content,
        raw_location
    )

    description = extract_description(
        content_raw
    )

    checked_at = datetime.utcnow().isoformat()

    return {

        "company": company,

        "employment_type":
            employment_type,

        "industry":
            industry,

        "job_id":
            f"greenhouse-{board_token}-{job_id}",

        "location":
            location,

        "posted_date":
            posted_date,

        "requirements":
            requirements,

        "salary":
            salary,

        "description":
            description,

        "source": {

            "application_url":
                job_url,

            "name":
                "Greenhouse",

            "type":
                "job_board_api",

            "url":
                job_url,
        },

        "title":
            title,

        "updated_date":
            updated_date,

        "verification": {

            "checked_at":
                checked_at,

            "status":
                "source_verified",
        },

        "work_mode":
            work_mode,
    }
