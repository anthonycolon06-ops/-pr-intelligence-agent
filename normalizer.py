def extract_location(job):
    """
    Extrae la ubicación sin asumir que todo empleo
    pertenece a Estados Unidos.

    Reconoce Puerto Rico, estados de EE. UU. y países
    internacionales. Si no puede determinar el país,
    devuelve None.
    """

    location = job.get("location")
    raw = ""
    explicit_country = ""

    if isinstance(location, dict):
        raw = (
            location.get("name")
            or location.get("raw")
            or ""
        )
        explicit_country = str(
            location.get("country") or ""
        ).strip()

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
    country_hint = explicit_country.lower()

    country = None
    region = None
    municipality = raw or None

    # --------------------------------------------------------
    # PUERTO RICO
    # --------------------------------------------------------

    puerto_rico_names = [
        "puerto rico",
        "san juan, pr",
        "bayamon, pr",
        "bayamón, pr",
    ]

    if (
        "puerto rico" in lowered
        or country_hint in {"pr", "pri", "puerto rico"}
        or re.search(r",\s*pr$", lowered)
    ):
        country = "PR"
        region = "Puerto Rico"

        match = re.search(
            r"^(.+?),\s*(?:Puerto Rico|PR)$",
            raw,
            flags=re.IGNORECASE,
        )

        if match:
            municipality = match.group(1).strip()
        else:
            municipality = "Puerto Rico"

    else:
        # ----------------------------------------------------
        # ESTADOS DE EE. UU.
        # ----------------------------------------------------

        state_names = {
            "alabama": "AL",
            "alaska": "AK",
            "arizona": "AZ",
            "arkansas": "AR",
            "california": "CA",
            "colorado": "CO",
            "connecticut": "CT",
            "delaware": "DE",
            "florida": "FL",
            "georgia": "GA",
            "hawaii": "HI",
            "idaho": "ID",
            "illinois": "IL",
            "indiana": "IN",
            "iowa": "IA",
            "kansas": "KS",
            "kentucky": "KY",
            "louisiana": "LA",
            "maine": "ME",
            "maryland": "MD",
            "massachusetts": "MA",
            "michigan": "MI",
            "minnesota": "MN",
            "mississippi": "MS",
            "missouri": "MO",
            "montana": "MT",
            "nebraska": "NE",
            "nevada": "NV",
            "new hampshire": "NH",
            "new jersey": "NJ",
            "new mexico": "NM",
            "new york": "NY",
            "north carolina": "NC",
            "north dakota": "ND",
            "ohio": "OH",
            "oklahoma": "OK",
            "oregon": "OR",
            "pennsylvania": "PA",
            "rhode island": "RI",
            "south carolina": "SC",
            "south dakota": "SD",
            "tennessee": "TN",
            "texas": "TX",
            "utah": "UT",
            "vermont": "VT",
            "virginia": "VA",
            "washington": "WA",
            "west virginia": "WV",
            "wisconsin": "WI",
            "wyoming": "WY",
            "district of columbia": "DC",
            "washington, d.c.": "DC",
        }

        state_codes = set(state_names.values())

        # Reconocer ciudades seguidas por una abreviatura estatal.
        state_match = re.search(
            r"^(.+?),\s*([A-Z]{2})"
            r"(?:,\s*(?:United States|USA|US))?$",
            raw,
        )

        # Reconocer ciudades seguidas por el nombre del estado.
        full_state_match = None

        for state_name in sorted(
            state_names,
            key=len,
            reverse=True,
        ):
            full_state_match = re.search(
                r"^(.+?),\s*"
                + re.escape(state_name)
                + r"(?:,\s*(?:United States|USA|US))?$",
                raw,
                flags=re.IGNORECASE,
            )

            if full_state_match:
                region = state_names[state_name]
                municipality = (
                    full_state_match.group(1).strip()
                )
                country = "US"
                break

        if country is None and state_match:
            state_code = state_match.group(2).upper()

            if state_code in state_codes:
                country = "US"
                region = state_code
                municipality = (
                    state_match.group(1).strip()
                )

        # ----------------------------------------------------
        # UBICACIONES REMOTAS EN EE. UU.
        # ----------------------------------------------------

        if country is None:
            if re.search(
                r"\bUnited States\b|\bUSA\b|\bU\.S\.A\.\b",
                raw,
                flags=re.IGNORECASE,
            ):
                country = "US"
                region = None

                remote_match = re.match(
                    r"^(?:United States|USA|U\.S\.A\.)"
                    r"\s*\(?(?:Remote)?\)?$",
                    raw,
                    flags=re.IGNORECASE,
                )

                if remote_match:
                    municipality = "United States (Remote)"

            elif re.fullmatch(
                r"(?:US|U\.S\.)\s*\(Remote\)",
                raw,
                flags=re.IGNORECASE,
            ):
                country = "US"
                municipality = "United States (Remote)"

        # ----------------------------------------------------
        # PAÍSES INTERNACIONALES
        # ----------------------------------------------------

        if country is None:
            international_countries = {
                "india": "IN",
                "poland": "PL",
                "canada": "CA",
                "united kingdom": "GB",
                "uk": "GB",
                "england": "GB",
                "ireland": "IE",
                "australia": "AU",
                "new zealand": "NZ",
                "germany": "DE",
                "france": "FR",
                "spain": "ES",
                "italy": "IT",
                "portugal": "PT",
                "netherlands": "NL",
                "brazil": "BR",
                "mexico": "MX",
                "philippines": "PH",
                "singapore": "SG",
                "japan": "JP",
                "china": "CN",
                "israel": "IL",
                "united arab emirates": "AE",
                "south africa": "ZA",
                "colombia": "CO",
                "argentina": "AR",
                "chile": "CL",
            }

            # Revisar nombres de países al final de la ubicación.
            for country_name in sorted(
                international_countries,
                key=len,
                reverse=True,
            ):
                if (
                    country_name in lowered
                    or country_hint == international_countries[country_name].lower()
                ):
                    country = international_countries[country_name]

                    parts = [
                        part.strip()
                        for part in raw.split(",")
                        if part.strip()
                    ]

                    if len(parts) >= 2:
                        municipality = ", ".join(parts[:-1])
                    else:
                        municipality = raw

                    break

        # ----------------------------------------------------
        # PAÍS EXPLÍCITO DEVUELTO POR LA FUENTE
        # ----------------------------------------------------

        if country is None and country_hint:
            country_codes = {
                "us": "US",
                "usa": "US",
                "united states": "US",
                "in": "IN",
                "ind": "IN",
                "pl": "PL",
                "pol": "PL",
                "ca": "CA",
                "can": "CA",
                "gb": "GB",
                "gbr": "GB",
                "au": "AU",
                "aus": "AU",
                "de": "DE",
                "deu": "DE",
                "fr": "FR",
                "fra": "FR",
                "es": "ES",
                "esp": "ES",
                "mx": "MX",
                "mex": "MX",
            }

            if country_hint in country_codes:
                country = country_codes[country_hint]

        # IMPORTANTE:
        # Nunca asignar US como valor predeterminado.
        # Si la ubicación es ambigua, el país queda desconocido.

    return {
        "country": country,
        "municipality": municipality,
        "raw": raw,
        "region": region,
    }
