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

    "dc": "District of Columbia"

}

US_STATE_NAMES = {

    name.lower()

    for name in US_STATE_ABBREVIATIONS.values()

}

def clean_text(value):

    if value is None:

        return ""

    return " ".join(

        str(value).strip().split()

    )

def detect_country(location_text):

    """

    Detect the country from a location string.

    Returns:

        PR = Puerto Rico

        US = United States

        Other country name = detected other country

        None = unknown

    """

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

    # United States

    if (

        "united states" in text

        or "united states of america" in text

        or "usa" in text

        or "u.s.a" in text

        or "u.s." in text

        or " us " in f" {text} "

    ):

        return "US"

    # US state names

    for state_name in US_STATE_NAMES:

        if state_name in text:

            return "US"

    # US state abbreviations

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

    """

    Detect common non-US countries when they are explicitly

    present in a location string.

    """

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

        "china": "China"

    }

    for key, country_name in countries.items():

        if key in text:

            return country_name

    return None

def normalize_location(raw_location):

    """

    Convert a raw Greenhouse location into a consistent structure.

    Examples:

    Puerto Rico

        -> PR

    San Juan, Puerto Rico

        -> PR

    United States (Remote)

        -> US

    Austin, TX

        -> US / Texas

    Austin, Texas

        -> US / Texas

    Noida, Uttar Pradesh, India

        -> India

    Unknown

        -> None

    """

    raw = clean_text(

        raw_location

    )

    if not raw:

        return {

            "country": None,

            "municipality": None,

            "region": None,

            "raw": raw

        }

    text_lower = raw.lower()

    country = detect_country(

        raw

    )

    # ---------------------------------

    # PUERTO RICO

    # ---------------------------------

    if country == "PR":

        if (

            text_lower == "puerto rico"

            or text_lower == "pr"

        ):

            return {

                "country": "PR",

                "municipality": "Puerto Rico",

                "region": "Puerto Rico",

                "raw": raw

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

            "raw": raw

        }

    # ---------------------------------

    # UNITED STATES

    # ---------------------------------

    if country == "US":

        # United States Remote

        if (

            "united states" in text_lower

            and "remote" in text_lower

        ):

            return {

                "country": "US",

                "municipality": "United States",

                "region": None,

                "raw": raw

            }

        # USA Remote

        if (

            ("usa" in text_lower or "u.s." in text_lower)

            and "remote" in text_lower

        ):

            return {

                "country": "US",

                "municipality": "United States",

                "region": None,

                "raw": raw

            }

        # Generic United States

        if text_lower in {

            "usa",

            "u.s.",

            "u.s.a.",

            "united states",

            "united states of america"

        }:

            return {

                "country": "US",

                "municipality": "United States",

                "region": None,

                "raw": raw

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

            possible_region = parts[1].strip()

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

            elif (

                possible_region_lower

                in US_STATE_NAMES

            ):

                region = possible_region

            else:

                region = possible_region

        return {

            "country": "US",

            "municipality": municipality,

            "region": region,

            "raw": raw

        }

    # ---------------------------------

    # OTHER COUNTRIES

    # ---------------------------------

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

            "raw": raw

        }

    return {

        "country": None,

        "municipality": municipality,

        "region": region,

        "raw": raw

    }

def extract_location(job):

    """

    Extract the best available location from a Greenhouse job.

    """

    location = job.get(

        "location"

    )

    if isinstance(location, dict):

        for key in [

            "name",

            "raw",

            "location",

            "city"

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

    for key in [

        "location_name",

        "job_location",

        "office_location"

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

    """

    Extract the original posting date.

    """

    for key in [

        "first_published",

        "published_at",

        "created_at",

        "createdAt",

        "posted_date"

    ]:

        value = job.get(

            key

        )

        if value:

            return value

    return None

def extract_updated_date(job):

    """

    Extract the latest update timestamp.

    """

    for key in [

        "updated_at",

        "updatedAt",

        "updated_date"

    ]:

        value = job.get(

            key

        )

        if value:

            return value

    return None

def extract_salary(job):

    """

    Normalize salary information when available.

    """

    salary = job.get(

        "salary"

    )

    if isinstance(salary, dict):

        return {

            "min": salary.get(

                "min"

            ),

            "max": salary.get(

                "max"

            ),

            "currency": salary.get(

                "currency",

                "USD"

            ),

            "period": salary.get(

                "period",

                "unknown"

            ),

            "published": bool(

                salary.get(

                    "published",

                    False

                )

            )

        }

    return {

        "min": None,

        "max": None,

        "currency": "USD",

        "period": "unknown",

        "published": False

    }

def extract_employment_type(job):

    """

    Normalize employment type.

    """

    value = (

        job.get(

            "employment_type"

        )

        or job.get(

            "employmentType"

        )

        or job.get(

            "type"

        )

    )

    if not value:

        return "Unknown"

    return clean_text(

        value

    )

def extract_industry(job):

    """

    Normalize industry.

    """

    value = (

        job.get(

            "industry"

        )

        or job.get(

            "department"

        )

        or job.get(

            "category"

        )

    )

    if not value:

        return "Other"

    return clean_text(

        value

    )

def extract_work_mode(

    job,

    raw_location

):

    """

    Detect remote, hybrid, or on-site.

    """

    text_parts = [

        raw_location,

        str(

            job.get(

                "title",

                ""

            )

        ),

        str(

            job.get(

                "description",

                ""

            )

        )

    ]

    text = " ".join(

        text_parts

    ).lower()

    if "hybrid" in text:

        return "Hybrid"

    if (

        "remote" in text

        or "work from home" in text

        or "work-from-home" in text

    ):

        return "Remote"

    if (

        "on-site" in text

        or "onsite" in text

        or "on site" in text

    ):

        return "On-site"

    return "Unknown"

def extract_requirements(job):

    """

    Normalize basic job requirements.

    """

    requirements = job.get(

        "requirements"

    )

    if isinstance(

        requirements,

        dict

    ):

        return {

            "education": requirements.get(

                "education",

                []

            ),

            "experience": requirements.get(

                "experience"

            ),

            "licenses": requirements.get(

                "licenses",

                []

            )

        }

    return {

        "education": [],

        "experience": None,

        "licenses": []

    }

def normalize_greenhouse_job(

    job,

    company,

    board_token

):

    """

    Convert a raw Greenhouse job into

    the PR Intelligence Agent schema.

    """

    raw_location = extract_location(

        job

    )

    location = normalize_location(

        raw_location

    )

    title = clean_text(

        job.get(

            "title",

            ""

        )

    )

    job_id = (

        job.get(

            "id"

        )

        or job.get(

            "job_id"

        )

        or job.get(

            "requisition_id"

        )

    )

    if job_id is None:

        job_id = "unknown"

    job_url = (

        job.get(

            "absolute_url"

        )

        or job.get(

            "url"

        )

        or job.get(

            "application_url"

        )

    )

    posted_date = extract_posted_date(

        job

    )

    updated_date = extract_updated_date(

        job

    )

    employment_type = extract_employment_type(

        job

    )

    industry = extract_industry(

        job

    )

    salary = extract_salary(

        job

    )

    requirements = extract_requirements(

        job

    )

    work_mode = extract_work_mode(

        job,

        raw_location

    )

    checked_at = datetime.utcnow().isoformat()

    return {

        "company": company,

        "employment_type": employment_type,

        "industry": industry,

        "job_id": (

            f"greenhouse-"

            f"{board_token}-"

            f"{job_id}"

        ),

        "location": location,

        "posted_date": posted_date,

        "requirements": requirements,

        "salary": salary,

        "source": {

            "application_url": job_url,

            "name": "Greenhouse",

            "type": "job_board_api",

            "url": job_url

        },

        "title": title,

        "updated_date": updated_date,

        "verification": {

            "checked_at": checked_at,

            "status": "source_verified"

        },

        "work_mode": work_mode

    }
