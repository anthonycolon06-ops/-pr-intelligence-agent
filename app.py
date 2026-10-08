from flask import Flask, request, jsonify
import json
import os

from greenhouse import get_greenhouse_jobs
from normalizer import normalize_greenhouse_job

app = Flask(__name__)

VERSION = "1.5.0"


# ============================================================
# JOB STORAGE
# ============================================================

def load_jobs():
    """
    Carga empleos guardados en jobs.json como respaldo.
    """

    try:
        with open(
            "jobs.json",
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, dict):
                return data.get("jobs", [])

            if isinstance(data, list):
                return data

    except Exception:
        return []

    return []


# ============================================================
# GREENHOUSE SOURCE
# ============================================================

def load_greenhouse_jobs(board_token="livecareer"):
    """
    Obtiene empleos directamente desde Greenhouse y los normaliza.

    Greenhouse es una fuente dinámica.
    """

    raw_jobs = get_greenhouse_jobs(board_token)

    normalized_jobs = []

    for job in raw_jobs:

        try:

            normalized_job = normalize_greenhouse_job(
                job,
                "BOLD",
                board_token
            )

            normalized_jobs.append(
                normalized_job
            )

        except Exception:
            # Un empleo defectuoso no debe tumbar
            # toda la respuesta de la API.
            continue

    return normalized_jobs


def load_all_jobs():
    """
    Construye el inventario disponible.

    Actualmente:
    1. Greenhouse dinámico
    2. jobs.json como respaldo

    Esto permite añadir nuevas fuentes posteriormente.
    """

    jobs = []

    # --------------------------------------------------------
    # GREENHOUSE
    # --------------------------------------------------------

    try:

        greenhouse_jobs = load_greenhouse_jobs(
            "livecareer"
        )

        jobs.extend(
            greenhouse_jobs
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # JOBS.JSON BACKUP
    # --------------------------------------------------------

    stored_jobs = load_jobs()

    existing_ids = {
        str(job.get("job_id"))
        for job in jobs
        if job.get("job_id")
    }

    for job in stored_jobs:

        job_id = str(
            job.get("job_id", "")
        )

        if job_id and job_id in existing_ids:
            continue

        jobs.append(job)

    return jobs


# ============================================================
# LOCATION
# ============================================================

def get_location_text(job):

    location = job.get(
        "location",
        {}
    )

    if isinstance(location, dict):

        municipality = str(
            location.get(
                "municipality",
                ""
            )
        )

        region = str(
            location.get(
                "region",
                ""
            )
        )

        country = str(
            location.get(
                "country",
                ""
            )
        )

        raw = str(
            location.get(
                "raw",
                ""
            )
        )

        return " ".join([
            municipality,
            region,
            country,
            raw
        ]).lower()

    return str(location).lower()


def location_matches(
    job,
    requested_location
):
    """
    Match a job against a requested location.

    Supports:
    - Puerto Rico
    - United States
    - States
    - Cities
    - General location text
    """

    query = str(
        requested_location
    ).strip().lower()

    if not query:
        return True

    location = job.get(
        "location",
        {}
    )

    if not isinstance(location, dict):

        return (
            query
            in str(location).lower()
        )

    municipality = str(
        location.get(
            "municipality",
            ""
        )
    ).lower()

    region = str(
        location.get(
            "region",
            ""
        )
    ).lower()

    country = str(
        location.get(
            "country",
            ""
        )
    ).lower()

    raw = str(
        location.get(
            "raw",
            ""
        )
    ).lower()

    location_text = " ".join([
        municipality,
        region,
        country,
        raw
    ])

    # ========================================================
    # PUERTO RICO
    # ========================================================

    puerto_rico_queries = {
        "puerto rico",
        "puerto-rico",
        "pr"
    }

    if query in puerto_rico_queries:

        return (
            country == "pr"
            or region == "puerto rico"
            or "puerto rico" in location_text
        )

    # ========================================================
    # UNITED STATES
    # ========================================================

    united_states_queries = {
        "united states",
        "united states of america",
        "usa",
        "us",
        "u.s.",
        "u.s.a."
    }

    if query in united_states_queries:

        return (
            country == "us"
            or country == "usa"
            or country == "united states"
            or "united states" in location_text
            or "usa" in location_text
        )

    # ========================================================
    # US STATES
    # ========================================================

    state_codes = {
        "al", "ak", "az", "ar", "ca",
        "co", "ct", "de", "fl", "ga",
        "hi", "id", "il", "in", "ia",
        "ks", "ky", "la", "me", "md",
        "ma", "mi", "mn", "ms", "mo",
        "mt", "ne", "nv", "nh", "nj",
        "nm", "ny", "nc", "nd", "oh",
        "ok", "or", "pa", "ri", "sc",
        "sd", "tn", "tx", "ut", "vt",
        "va", "wa", "wv", "wi", "wy",
        "dc"
    }

    state_names = {
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
        "district of columbia"
    }

    if (
        query in state_codes
        or query in state_names
    ):

        return (
            query in location_text
        )

    # ========================================================
    # GENERAL LOCATION
    # ========================================================

    return query in location_text


# ============================================================
# FILTERS
# ============================================================

def filter_jobs(
    jobs,
    location="",
    industry="",
    employment_type="",
    min_salary=None,
    max_salary=None
):

    results = list(jobs)

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if location:

        results = [
            job
            for job in results
            if location_matches(
                job,
                location
            )
        ]

    # --------------------------------------------------------
    # INDUSTRY
    # --------------------------------------------------------

    if industry:

        industry_lower = (
            industry.strip().lower()
        )

        results = [
            job
            for job in results
            if industry_lower
            in str(
                job.get(
                    "industry",
                    ""
                )
            ).lower()
        ]

    # --------------------------------------------------------
    # EMPLOYMENT TYPE
    # --------------------------------------------------------

    if employment_type:

        employment_lower = (
            employment_type.strip().lower()
        )

        results = [
            job
            for job in results
            if employment_lower
            in str(
                job.get(
                    "employment_type",
                    ""
                )
            ).lower()
        ]

    # --------------------------------------------------------
    # MINIMUM SALARY
    # --------------------------------------------------------

    if min_salary is not None:

        filtered = []

        for job in results:

            salary = job.get(
                "salary",
                {}
            )

            salary_max = salary.get(
                "max"
            )

            if (
                salary_max is not None
                and salary_max >= min_salary
            ):
                filtered.append(job)

        results = filtered

    # --------------------------------------------------------
    # MAXIMUM SALARY
    # --------------------------------------------------------

    if max_salary is not None:

        filtered = []

        for job in results:

            salary = job.get(
                "salary",
                {}
            )

            salary_min = salary.get(
                "min"
            )

            if (
                salary_min is not None
                and salary_min <= max_salary
            ):
                filtered.append(job)

        results = filtered

    return results


# ============================================================
# HEALTH
# ============================================================

@app.route("/")
def home():

    return jsonify({

        "agent":
            "PR Intelligence Agent",

        "status":
            "online",

        "version":
            VERSION,

        "description":
            "Employment intelligence service "
            "covering Puerto Rico and the "
            "United States",

        "coverage": [
            "Puerto Rico",
            "United States"
        ]

    })


# ============================================================
# AGENT MANIFEST
# ============================================================

@app.route("/.well-known/agent.json")
def agent_manifest():

    return jsonify({

        "name":
            "PR Intelligence Agent",

        "description":
            "Employment intelligence service "
            "for AI agents covering Puerto Rico "
            "and the United States.",

        "version":
            VERSION,

        "capabilities": [

            "job_search",
            "salary_filtering",
            "location_filtering",
            "industry_filtering",
            "employment_type_filtering",
            "job_intelligence"

        ],

        "coverage": {

            "primary_market":
                "Puerto Rico",

            "secondary_market":
                "United States",

            "countries": [
                "Puerto Rico",
                "United States"
            ],

            "industries":
                "multiple",

            "salary_ranges":
                "all"

        },

        "api": {

            "base_path":
                "/",

            "endpoints": {

                "health":
                    "/",

                "jobs":
                    "/jobs",

                "greenhouse_test":
                    "/greenhouse-test"

            }

        },

        "pricing": {

            "model":
                "per_query",

            "target_price_usd":
                0.10

        }

    })


# ============================================================
# MAIN JOB API
# ============================================================

@app.route("/jobs")
def jobs():

    # --------------------------------------------------------
    # LOAD REAL JOB DATA
    # --------------------------------------------------------

    all_jobs = load_all_jobs()

    # --------------------------------------------------------
    # QUERY PARAMETERS
    # --------------------------------------------------------

    location = request.args.get(
        "location",
        ""
    ).strip()

    industry = request.args.get(
        "industry",
        ""
    ).strip()

    employment_type = request.args.get(
        "employment_type",
        ""
    ).strip()

    min_salary = request.args.get(
        "min_salary",
        type=float
    )

    max_salary = request.args.get(
        "max_salary",
        type=float
    )

    # --------------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------------

    results = filter_jobs(

        all_jobs,

        location=location,

        industry=industry,

        employment_type=employment_type,

        min_salary=min_salary,

        max_salary=max_salary

    )

    return jsonify({

        "count":
            len(results),

        "filters": {

            "location":
                location
                if location
                else None,

            "industry":
                industry
                if industry
                else None,

            "employment_type":
                employment_type
                if employment_type
                else None,

            "min_salary":
                min_salary,

            "max_salary":
                max_salary

        },

        "coverage": [

            "Puerto Rico",
            "United States"

        ],

        "jobs":
            results

    })


# ============================================================
# GREENHOUSE TEST
# ============================================================

@app.route("/greenhouse-test")
def greenhouse_test():

    board_token = request.args.get(
        "board"
    )

    requested_location = request.args.get(
        "location",
        ""
    ).strip()

    if not board_token:

        return jsonify({

            "error":
                "Missing board parameter",

            "example":
                "/greenhouse-test?board=livecareer"

        }), 400

    try:

        raw_jobs = get_greenhouse_jobs(
            board_token
        )

        normalized_jobs = []

        for job in raw_jobs:

            try:

                normalized_job = (
                    normalize_greenhouse_job(
                        job,
                        "BOLD",
                        board_token
                    )
                )

                normalized_jobs.append(
                    normalized_job
                )

            except Exception:

                continue

        # ----------------------------------------------------
        # LOCATION FILTER
        # ----------------------------------------------------

        if requested_location:

            normalized_jobs = [

                job

                for job in normalized_jobs

                if location_matches(
                    job,
                    requested_location
                )

            ]

        return jsonify({

            "source":
                "Greenhouse",

            "company":
                "BOLD",

            "board":
                board_token,

            "count":
                len(normalized_jobs),

            "filters": {

                "location":
                    requested_location
                    if requested_location
                    else None

            },

            "coverage": [

                "Puerto Rico",
                "United States"

            ],

            "jobs":
                normalized_jobs

        })

    except Exception as error:

        return jsonify({

            "error":
                str(error)

        }), 500


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    port = int(

        os.environ.get(
            "PORT",
            8000
        )

    )

    app.run(

        host="0.0.0.0",

        port=port

    )
