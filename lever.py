import requests


LEVER_API = "https://api.lever.co/v0/postings"


def get_lever_jobs(site):
    """
    Obtiene los puestos públicos de un board de Lever.
    """

    url = f"{LEVER_API}/{site}"

    params = {
        "mode": "json",
        "limit": 100
    }

    response = requests.get(
        url,
        params=params,
        timeout=20,
        headers={
            "Accept": "application/json",
            "User-Agent": "PR-Intelligence-Agent/1.0"
        }
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        return []

    return data
