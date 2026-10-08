from flask import Flask, request, jsonify

import json

import os

from greenhouse import get_greenhouse_jobs

from normalizer import normalize_greenhouse_job

app = Flask(__name__)

def load_jobs():

    try:

        with open(

            "jobs.json",

            "r",

            encoding="utf-8"

        ) as file:

            data = json.load(file)

            return data.get(

                "jobs",

                []

            )

    except Exception:

        return []

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

    # PUERTO RICO

    puerto_rico_queries = {

        "puerto rico",

        "puerto-rico",

        "pr"

    }

    if query in puerto_rico_queries:

        return (

            country == "pr"

            or "puerto rico" in location_text

            or region == "puerto rico"

        )

    # UNITED STATES

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

    # GENERAL LOCATION

    return query in location_text

def filter_jobs(

    jobs,

    location="",

    industry="",

    employment_type="",

    min_salary=None,

    max_salary=None

):

    """

    Apply all supported job filters.

    """

    results = jobs

    # LOCATION

    if location:

        results = [

            job

            for job in results

            if location_matches(

                job,

                location

            )

        ]

    # INDUSTRY

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

    # EMPLOYMENT TYPE

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

    # MINIMUM SALARY

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

    # MAXIMUM SALARY

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

@app.route("/")

def home():

    return jsonify({

        "agent":

            "PR Intelligence Agent",

        "status":

            "online",

        "version":

            "1.4.0",

        "description":

            "Employment intelligence service "

            "covering Puerto Rico and the "

            "United States",

        "coverage": [

            "Puerto Rico",

            "United States"

        ]

    })

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

            "1.4.0",

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

@app.route("/jobs")

def jobs():

    all_jobs = load_jobs()

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

        # LOCATION FILTER

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
