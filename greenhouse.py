import requests


def get_job_location(job):
    """
    Obtiene la ubicación básica de un job de Greenhouse.
    """

    location = job.get("location")

    if isinstance(location, dict):
        name = location.get("name")

        if name:
            return str(name)

    if isinstance(location, str):
        return location

    offices = job.get("offices", [])

    if isinstance(offices, list):
        for office in offices:
            if not isinstance(office, dict):
                continue

            name = office.get("name")

            if name:
                return str(name)

    return ""


def location_matches(job, requested_location=None):
    """
    Filtra un job por ubicación cuando se solicita una ubicación.

    Ejemplos:
    Puerto Rico
    Texas
    California
    United States
    """

    if not requested_location:
        return True

    requested = str(requested_location).strip().lower()

    if not requested:
        return True

    raw_location = get_job_location(job).lower()

    if requested in raw_location:
        return True

    # United States debe aceptar ubicaciones estatales.
    if requested in {
        "united states",
        "usa",
        "us",
        "u.s.",
    }:
        us_indicators = [
            ", al",
            ", ak",
            ", az",
            ", ar",
            ", ca",
            ", co",
            ", ct",
            ", de",
            ", fl",
            ", ga",
            ", hi",
            ", id",
            ", il",
            ", in",
            ", ia",
            ", ks",
            ", ky",
            ", la",
            ", me",
            ", md",
            ", ma",
            ", mi",
            ", mn",
            ", ms",
            ", mo",
            ", mt",
            ", ne",
            ", nv",
            ", nh",
            ", nj",
            ", nm",
            ", ny",
            ", nc",
            ", nd",
            ", oh",
            ", ok",
            ", or",
            ", pa",
            ", ri",
            ", sc",
            ", sd",
            ", tn",
            ", tx",
            ", ut",
            ", vt",
            ", va",
            ", wa",
            ", wv",
            ", wi",
            ", wy",
            ", dc",
            "united states",
            "usa",
            "u.s.",
        ]

        return any(
            indicator in raw_location
            for indicator in us_indicators
        )

    return False


def get_greenhouse_jobs(board_token, location=None):
    """
    Obtiene jobs de Greenhouse.

    Flujo:

    1. Obtiene la lista de jobs.
    2. Si se solicita una ubicación, filtra primero.
    3. Consulta el detalle individual solamente de los
       jobs que interesan.
    4. Conserva el contenido completo de la vacante.
    """

    base_url = (
        f"https://boards-api.greenhouse.io/"
        f"v1/boards/{board_token}"
    )

    jobs_url = f"{base_url}/jobs"

    response = requests.get(
        jobs_url,
        params={
            "content": "true"
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    jobs = data.get("jobs", [])

    # Primero filtramos por ubicación.
    if location:
        jobs_to_process = [
            job
            for job in jobs
            if location_matches(
                job,
                location,
            )
        ]
    else:
        jobs_to_process = jobs

    detailed_jobs = []

    for job in jobs_to_process:
        job_id = job.get("id")

        if not job_id:
            detailed_jobs.append(job)
            continue

        detail_url = f"{jobs_url}/{job_id}"

        try:
            detail_response = requests.get(
                detail_url,
                params={
                    "content": "true"
                },
                timeout=30,
            )

            detail_response.raise_for_status()

            detailed_job = detail_response.json()

            # Asegurarnos de conservar TODOS los campos
            # del job original y del detalle.
            merged_job = {
                **job,
                **detailed_job,
            }

            # Si el detalle trae content, conservarlo explícitamente.
            if detailed_job.get("content"):
                merged_job["content"] = detailed_job["content"]

            detailed_jobs.append(merged_job)

        except requests.RequestException:
            # Si falla el detalle, conservamos el job básico.
            # No inventamos información.
            detailed_jobs.append(job)

    return detailed_jobs
