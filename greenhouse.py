import requests


def get_greenhouse_jobs(board_token):
    """
    Obtiene las vacantes de un board de Greenhouse.

    Primero obtiene la lista de jobs y luego consulta
    cada job individualmente para recuperar el contenido
    completo de la vacante.
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
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    jobs = data.get("jobs", [])

    detailed_jobs = []

    for job in jobs:
        job_id = job.get("id")

        if not job_id:
            detailed_jobs.append(job)
            continue

        try:
            detail_url = f"{jobs_url}/{job_id}"

            detail_response = requests.get(
                detail_url,
                params={
                    "content": "true"
                },
                timeout=20
            )

            detail_response.raise_for_status()

            detailed_job = detail_response.json()

            merged_job = {
                **job,
                **detailed_job
            }

            detailed_jobs.append(merged_job)

        except requests.RequestException:
            detailed_jobs.append(job)

    return detailed_jobs
