#!/usr/bin/env python
"""
Extract administrative zones for a market pack Section 02 geography
file, from OpenStreetMap and, where one exists, a national reference
dataset.

    python src/osm_zone_extractor.py --probe KE
    python src/osm_zone_extractor.py --market us-vermont --dry-run
    python src/osm_zone_extractor.py --market ke-nairobi \
        --boundary-level 2 --child-level 4 --dry-run
    python src/osm_zone_extractor.py --market us-colorado \
        --out research/market/us-colorado/zones-generated.json

DIVISION OF LABOUR
------------------
Each source is used only for what it is authoritative about.

    OpenStreetMap    identity, hierarchy, relation IDs, bounding
                     boxes, external cross-references
    Census Gazetteer representative point, land area, canonical
                     GEOID identity                    (US only)
    Census API       resident population               (US only)
    OSM admin_centre representative point           (generic path)
    OSM population   resident population, tier 3     (generic path)

Everything emitted is copied from one of those. Nothing is asserted.

TWO PATHS, DELIBERATELY SEPARATE
--------------------------------
The United States path is unchanged from version 2.4.0 and is not
touched by anything added since. It uses the Census Gazetteer for
representative points and the Census API for population, both tier 1,
and it filters children by FIPS prefix, which is exact.

Every other country uses the generic path: points from an OSM
admin_centre node where one is tagged, population from an OSM
population tag where one is present, and no cross-reference filter at
all.

The generic path produces genuinely weaker data, and says so on every
record it writes. It is not a lesser version of the US path pretending
to be equivalent. Keeping the two apart means the generic path cannot
regress a US market, and a US market cannot be quietly downgraded by a
change made for somewhere else.

ADMIN LEVELS ARE NOT GUESSED
----------------------------
OSM's admin_level is an integer from 2 to 11 whose meaning is
country-specific. Level 6 is county in the United States, departement
in France, district in Germany, and sub-county in Kenya.

Kenya is the case that makes this dangerous rather than merely
awkward. Kenyan counties sit at level 4, where the United States puts
states. Running the US pattern there returns 47 counties as market
BOUNDARIES and several hundred sub-counties beneath them: a file that
parses, validates, and describes an entirely different tier of
geography. Nothing downstream can detect it.

So the levels are never inferred. Either the country appears in
COUNTRY_PROFILES, verified by someone who looked, or the levels are
supplied explicitly with --boundary-level and --child-level. A country
that is neither is refused.

--probe makes the verification cheap:

    python src/osm_zone_extractor.py --probe KE

reports how many relations exist at each admin level inside a country
and names three examples of each. Thirty seconds of reading answers
the question permanently, after which the country is worth promoting
into COUNTRY_PROFILES so nobody probes it twice.

An automatic detector was considered and rejected. It would have to
infer intent from relation counts, and that heuristic fails on small
countries, on federations with few first-level subdivisions, and
anywhere tagging is incomplete. A wrong guess is invisible; a probe
puts a person in the loop for half a minute, once.

WHY REPRESENTATIVE POINTS COME FROM CENSUS, IN THE US
-----------------------------------------------------
An earlier version took coordinates from Overpass "out center". That
was wrong, and the error was invisible.

Overpass returns the centre of the bounding BOX, not the centroid. For
an irregular shape the two differ; for a concave one the bbox centre
can fall outside the polygon entirely. Vermont is wedge-shaped, and
the two disagreed by roughly fifteen miles at state level. Both
numbers looked entirely plausible.

The Gazetteer's INTPTLAT and INTPTLONG are internal points: the Census
Bureau guarantees they lie inside the polygon they describe. That is
what a routing anchor needs, and it is what hand-researched market
files already used, so the two now agree by construction rather than
by luck.

The OSM bounding box is still recorded, as a bounding box, because
that is what it honestly is.

WHY THE GENERIC PATH USES admin_centre
--------------------------------------
Most administrative relations outside the United States carry a member
node tagged with role=admin_centre: the county town, the seat of
government, the principal settlement.

That node is inside the area by construction, which is the property
that matters. It is arguably a better routing anchor than a geometric
internal point, because it is where people actually are.

It is not always present. Coverage is good across Europe and variable
elsewhere. Where it is absent the point is left null rather than
substituted from the bounding box, for the same reason as in the US
path: a null is visible and fails validation, a silently different
measurement is neither.

Computing a guaranteed-interior point from the full polygon would work
everywhere and is the obvious upgrade. It needs full geometry, which
is megabytes rather than kilobytes per run, and a geometry library.
Deliberately not bolted on here.

WHY THE MARKET BOUNDARY ZONE HAS NO POINT
-----------------------------------------
It has none deliberately, and that is not a gap.

The boundary zone answers one question: what is inside this market?
Containment comes from the polygon, not from a point. Everything
routable hangs beneath it, and points matter at the tier where
something is genuinely a pickup or drop-off: a resort, an airport
terminal, a city centre. Nothing routes to a state centroid.

Warning about its absence would train a reader to skim the log, which
is worse than saying nothing. The reason is recorded on the zone
instead, so a later reviewer does not "fix" it and a downstream
consumer does not read the null as an oversight.

WHAT THIS DOES NOT DO
---------------------
It leaves the judgement fields null:

    market_inclusion.status
    market_inclusion.production_use
    transportation_relevance.*
    access_characteristics.*
    jurisdiction_id

Whether a county matters for chauffeured transport is not in any map
database. A research pass fills those in, working from complete and
correct identity data rather than recalling it.

WHY THIS EXISTS
---------------
A language model asked for 64 Colorado counties will produce 64 sets
of coordinates, populations and FIPS codes. Most will be right. The
wrong ones look exactly like the right ones.

Vermont, at 14 counties, was small enough to check by reading. A
rounded population and two invented publication dates were caught that
way. At 64 counties that stops working.

This script cannot invent a county, cannot round a population, and
cannot transpose a coordinate, because it does not know any of those
things. It looks them up, and where a lookup fails it writes null and
says so.

SOURCES AND LICENCE
-------------------
OSM data is ODbL 1.0. Attribution is required in anything published
from it, and the emitted source record says so.

Census data is public domain.

The Overpass API is a shared free service. Every response is cached
and requests are spaced. Do not remove either.

CHANGES IN 3.0.0
----------------
Worldwide support, without weakening the United States path or
guessing anywhere.

1. COUNTRY_PROFILES replaces the single-entry ADMIN_LEVELS table. Each
   entry names the boundary and child levels, the zone types, and
   which reference strategy applies. The US entry is unchanged in
   behaviour.

2. --probe reports admin levels for a country so a new profile can be
   verified in half a minute rather than by trial and error.

3. --boundary-level and --child-level run any country explicitly.
   Unknown country plus no levels is refused, as before, but the
   refusal now explains the probe rather than saying "US only".

4. The generic path supplies representative points from admin_centre
   member nodes and population from OSM population tags, both cited at
   their real authority tier, both null where absent.

CHANGES IN 2.4.0
----------------
Two defects found by the Section 02 deterministic validator, both
originating here rather than in any research pass, and both therefore
affecting every state.

1. verification_status was derived purely from the number of sources
   behind a zone. The market boundary zone rests on OSM alone, having
   no Gazetteer row by design, so it came out "single_source". The
   schema ties geographic_precision "official_boundary" to official
   verification and refuses single_source outright, so every state
   failed validation on its first zone.

2. The OSM source record used a bare domain as its URL. A specific
   document normally has a path, and a bare domain is not evidence
   that anything was opened.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional


EXTRACTOR_VERSION = "3.0.0"

USER_AGENT = (
    f"limo-market-pack-zone-extractor/{EXTRACTOR_VERSION} "
    "(research tooling; contact via repository)"
)

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

# The wiki page defining boundary=administrative.
#
# Used as the source URL because a bare domain is not evidence that
# anything was opened, and this is the document that specifies exactly
# what was queried. The Overpass endpoint stays in
# service_or_download_url, where a machine-readable service belongs.
OSM_TAG_DOCUMENTATION_URL = (
    "https://wiki.openstreetmap.org/wiki/"
    "Tag:boundary%3Dadministrative"
)

OSM_ADMIN_CENTRE_DOCUMENTATION_URL = (
    "https://wiki.openstreetmap.org/wiki/"
    "Relation:boundary#Members"
)

OSM_POPULATION_DOCUMENTATION_URL = (
    "https://wiki.openstreetmap.org/wiki/Key:population"
)

OSM_RELATION_URL_PREFIX = "https://www.openstreetmap.org/relation/"

# A static tab-delimited file. No key, no query syntax, no rate limit,
# and a failure is a 404 rather than an HTML page that parses as
# nothing.
#
# There is no state-level equivalent here on purpose. The market
# boundary zone does not take a representative point; see the note at
# the head of this file.
GAZETTEER_COUNTIES_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2020_Gazetteer/2020_Gaz_counties_national.zip"
)

CENSUS_POPULATION_URL = "https://api.census.gov/data/2020/dec/pl"

CENSUS_KEY_SIGNUP_URL = "https://api.census.gov/data/key_signup.html"

REQUEST_DELAY_SECONDS = 2.0
RETRY_DELAY_SECONDS = 15.0
MAX_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 240

SQ_METRES_TO_SQ_MILES = 3.861021585e-7

PROBE_LEVELS = (2, 3, 4, 5, 6, 7, 8)


# ============================================================
# COUNTRY PROFILES
# ============================================================
#
# Every entry here was verified by someone who ran --probe and read
# the result. Nothing in this table is inferred.
#
# reference_strategy decides which path a market takes:
#
#   "us-census"  Gazetteer internal points, Census API population,
#                FIPS-prefix child filtering. Tier 1 throughout.
#
#   "generic"    admin_centre node for points, OSM population tag for
#                population, no cross-reference filter. Tier 1 for
#                identity, tier 3 for population.
#
# Adding a country means running --probe, reading which level holds
# the tier you want, and writing an entry. It does not mean guessing
# from a neighbouring country: Kenya and Nigeria are adjacent in a
# list and three levels apart in practice.

REFERENCE_US_CENSUS = "us-census"
REFERENCE_GENERIC = "generic"


@dataclass(frozen=True)
class CountryProfile:
    country_name: str
    boundary_level: int
    child_level: int
    boundary_zone_type: str
    child_zone_type: str
    reference_strategy: str = REFERENCE_GENERIC
    notes: str = ""


COUNTRY_PROFILES: dict[str, CountryProfile] = {
    # --- North America ------------------------------------------
    "US": CountryProfile(
        country_name="United States",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="state",
        child_zone_type="county",
        reference_strategy=REFERENCE_US_CENSUS,
        notes=(
            "Louisiana uses parishes and Alaska uses boroughs and "
            "census areas, both at level 6. Denver, Broomfield and "
            "San Francisco are consolidated city-counties and appear "
            "once at level 6, not twice."
        ),
    ),
    "CA": CountryProfile(
        country_name="Canada",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="county",
        notes=(
            "Level 6 is applied inconsistently between provinces. "
            "Quebec uses regional county municipalities, Ontario "
            "mixes counties with regional municipalities, and the "
            "territories have very few level 6 relations at all. "
            "Check the child count against what the province "
            "actually has before trusting a run."
        ),
    ),

    # --- Europe --------------------------------------------------
    "GB": CountryProfile(
        country_name="United Kingdom",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="territory",
        child_zone_type="county",
        notes=(
            "Level 4 is England, Scotland, Wales and Northern "
            "Ireland, not the UK itself. Level 6 mixes ceremonial "
            "counties with unitary authorities, which overlap "
            "conceptually and will produce apparent duplicates that "
            "are not duplicates. Expect to resolve some by hand."
        ),
    ),
    "IE": CountryProfile(
        country_name="Ireland",
        boundary_level=6,
        child_level=7,
        boundary_zone_type="country",
        child_zone_type="county",
        notes=(
            "Ireland has no meaningful level 4. Counties sit at "
            "level 6, so a county-level market takes the country as "
            "its boundary. Probe before assuming."
        ),
    ),
    "DE": CountryProfile(
        country_name="Germany",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="state",
        child_zone_type="district",
        notes=(
            "Level 4 is Bundesland, level 6 is Kreis or kreisfreie "
            "Stadt. City-states such as Berlin and Hamburg appear at "
            "level 4 and have no level 6 children."
        ),
    ),
    "FR": CountryProfile(
        country_name="France",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is region, level 6 is departement. Overseas "
            "departments are both, which produces one relation at "
            "each level for the same territory."
        ),
    ),
    "ES": CountryProfile(
        country_name="Spain",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is autonomous community, level 6 is province. "
            "Single-province communities appear at both levels."
        ),
    ),
    "IT": CountryProfile(
        country_name="Italy",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is region, level 6 is province or metropolitan "
            "city."
        ),
    ),

    # --- Oceania -------------------------------------------------
    "AU": CountryProfile(
        country_name="Australia",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="state",
        child_zone_type="district",
        notes=(
            "Level 6 is local government area. Coverage is good in "
            "the populated states; the Northern Territory and parts "
            "of South Australia have large unincorporated areas with "
            "no level 6 relation at all, which is correct rather "
            "than missing."
        ),
    ),
    "NZ": CountryProfile(
        country_name="New Zealand",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is region, level 6 is territorial authority. "
            "Unitary authorities appear at both levels."
        ),
    ),

    # --- Africa --------------------------------------------------
    #
    # Most African countries follow the level 4 / level 6 pattern.
    # Kenya does not, and it is the reason nothing here is inferred.
    "ZA": CountryProfile(
        country_name="South Africa",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 6 is district municipality. Metropolitan "
            "municipalities are single-tier and appear at level 6 "
            "with no level 8 children beneath them, which is correct."
        ),
    ),
    "KE": CountryProfile(
        country_name="Kenya",
        boundary_level=2,
        child_level=4,
        boundary_zone_type="country",
        child_zone_type="county",
        notes=(
            "Kenyan counties are at level 4, where most countries "
            "put a state or region. A county-level Kenyan market "
            "therefore takes the COUNTRY as its boundary zone, not a "
            "subdivision. Running the US pattern here would return "
            "47 counties as boundaries and several hundred "
            "sub-counties beneath them, all internally consistent "
            "and describing the wrong tier entirely."
        ),
    ),
    "NG": CountryProfile(
        country_name="Nigeria",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="state",
        child_zone_type="district",
        notes=(
            "Level 6 is local government area. The Federal Capital "
            "Territory sits at level 4 alongside the states."
        ),
    ),
    "GH": CountryProfile(
        country_name="Ghana",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes="Level 4 is region, level 6 is district.",
    ),
    "TZ": CountryProfile(
        country_name="Tanzania",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes="Level 4 is region, level 6 is district.",
    ),
    "RW": CountryProfile(
        country_name="Rwanda",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes="Level 4 is province, level 6 is district.",
    ),
    "EG": CountryProfile(
        country_name="Egypt",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is governorate. Level 6 coverage is uneven; "
            "check the child count before trusting a run."
        ),
    ),
    "MA": CountryProfile(
        country_name="Morocco",
        boundary_level=4,
        child_level=6,
        boundary_zone_type="province",
        child_zone_type="district",
        notes=(
            "Level 4 is region, level 6 is province or prefecture."
        ),
    ),
}


# Zone types the Section 02 schema permits for the two tiers this
# extractor writes. Used to validate an explicit --zone-type override
# before a run rather than after the schema rejects the file.
VALID_ZONE_TYPES = frozenset({
    "country", "state", "province", "territory", "county", "district",
    "municipality", "city", "town", "village", "borough",
    "census_area", "unincorporated_area", "tribal_area",
    "special_district", "metropolitan_area", "urban_area",
})


# ============================================================
# US REFERENCE TABLES
# ============================================================

US_STATES: dict[str, tuple[str, str]] = {
    "Alabama": ("01", "AL"), "Alaska": ("02", "AK"),
    "Arizona": ("04", "AZ"), "Arkansas": ("05", "AR"),
    "California": ("06", "CA"), "Colorado": ("08", "CO"),
    "Connecticut": ("09", "CT"), "Delaware": ("10", "DE"),
    "District Of Columbia": ("11", "DC"), "Florida": ("12", "FL"),
    "Georgia": ("13", "GA"), "Hawaii": ("15", "HI"),
    "Idaho": ("16", "ID"), "Illinois": ("17", "IL"),
    "Indiana": ("18", "IN"), "Iowa": ("19", "IA"),
    "Kansas": ("20", "KS"), "Kentucky": ("21", "KY"),
    "Louisiana": ("22", "LA"), "Maine": ("23", "ME"),
    "Maryland": ("24", "MD"), "Massachusetts": ("25", "MA"),
    "Michigan": ("26", "MI"), "Minnesota": ("27", "MN"),
    "Mississippi": ("28", "MS"), "Missouri": ("29", "MO"),
    "Montana": ("30", "MT"), "Nebraska": ("31", "NE"),
    "Nevada": ("32", "NV"), "New Hampshire": ("33", "NH"),
    "New Jersey": ("34", "NJ"), "New Mexico": ("35", "NM"),
    "New York": ("36", "NY"), "North Carolina": ("37", "NC"),
    "North Dakota": ("38", "ND"), "Ohio": ("39", "OH"),
    "Oklahoma": ("40", "OK"), "Oregon": ("41", "OR"),
    "Pennsylvania": ("42", "PA"), "Rhode Island": ("44", "RI"),
    "South Carolina": ("45", "SC"), "South Dakota": ("46", "SD"),
    "Tennessee": ("47", "TN"), "Texas": ("48", "TX"),
    "Utah": ("49", "UT"), "Vermont": ("50", "VT"),
    "Virginia": ("51", "VA"), "Washington": ("53", "WA"),
    "West Virginia": ("54", "WV"), "Wisconsin": ("55", "WI"),
    "Wyoming": ("56", "WY"),
}


# ============================================================
# RUN LOG
# ============================================================
#
# Problems are reported, not raised. A run producing 60 of 64 counties
# plus four clear explanations is more useful than a traceback,
# because the four are usually a data quirk worth understanding rather
# than a bug.

@dataclass
class Note:
    level: str
    message: str
    detail: Optional[str] = None


@dataclass
class RunLog:
    notes: list[Note] = field(default_factory=list)

    def info(self, message: str, detail: Optional[str] = None) -> None:
        self.notes.append(Note("INFO", message, detail))

    def warn(self, message: str, detail: Optional[str] = None) -> None:
        self.notes.append(Note("WARN", message, detail))

    def error(self, message: str, detail: Optional[str] = None) -> None:
        self.notes.append(Note("ERROR", message, detail))

    @property
    def error_count(self) -> int:
        return sum(1 for note in self.notes if note.level == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for note in self.notes if note.level == "WARN")

    def print(self, *, verbose: bool) -> None:
        # Sixty identical warnings are worse than useless: they teach
        # the reader to skim. The default collapses repeats to one
        # example plus a count.
        if verbose:
            for note in self.notes:
                self._print_one(note)
            return

        groups: dict[str, list[Note]] = {}

        for note in self.notes:
            key = re.sub(
                r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b", "X", note.message
            )
            key = re.sub(r"\d+", "N", key)
            groups.setdefault(f"{note.level}|{key}", []).append(note)

        for group in groups.values():
            self._print_one(group[0])

            if len(group) > 1:
                print(
                    f"         ... and {len(group) - 1} more like "
                    "this. Use --verbose to list them."
                )

    @staticmethod
    def _print_one(note: Note) -> None:
        print(f"  [{note.level}] {note.message}")

        if note.detail:
            for line in note.detail.splitlines():
                print(f"         {line}")


# ============================================================
# HTTP WITH CACHING
# ============================================================

class Fetcher:
    """
    Every response is cached to disk under a stable hash of the
    request.

    Reruns during development therefore cost nothing and place no load
    on a free shared service. Delete the cache directory to force a
    refresh.
    """

    def __init__(self, cache_dir: Path, log: RunLog, *, offline: bool):
        self.cache_dir = cache_dir
        self.log = log
        self.offline = offline

        cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str, suffix: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", key)[:100]

        # Python's hash() is salted per process, so using it here would
        # miss the cache on every run. Deliberately boring rather than
        # clever.
        digest = 0

        for character in key:
            digest = (digest * 131 + ord(character)) % (10**12)

        return self.cache_dir / f"{safe}-{digest}{suffix}"

    def json_request(
        self,
        url: str,
        cache_key: str,
        *,
        body: Optional[str] = None,
        redact: Optional[str] = None,
    ) -> Optional[Any]:
        """
        redact is a substring stripped from any logged URL, so an API
        key never reaches a log file or a pasted terminal session.
        """
        path = self._cache_path(cache_key, ".json.gz")

        if path.exists():
            try:
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    return json.load(handle)
            except (OSError, json.JSONDecodeError):
                path.unlink(missing_ok=True)

        if self.offline:
            self.log.error(
                "Offline mode, and this request is not cached.",
                cache_key,
            )
            return None

        raw = self._request(
            url,
            body.encode("utf-8") if body else None,
            redact=redact,
        )

        if raw is None:
            return None

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            preview = raw[:300].decode("utf-8", "replace")

            hint = (
                "This usually means the service returned an HTML "
                "error page."
            )

            if "Missing Key" in preview or "missing key" in preview:
                hint = (
                    "The Census API rejected the request for a "
                    "missing key.\n"
                    f"Get a free one at {CENSUS_KEY_SIGNUP_URL}\n"
                    "Then pass --census-key, or set CENSUS_API_KEY "
                    "in the environment or a .env file."
                )

            self.log.error(
                "Response was not JSON.",
                f"{hint}\nFirst 300 bytes:\n{preview}",
            )
            return None

        try:
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except OSError as error:
            self.log.warn(f"Could not write cache: {error}")

        return payload

    def binary_request(
        self,
        url: str,
        cache_key: str,
    ) -> Optional[bytes]:
        path = self._cache_path(cache_key, ".bin")

        if path.exists():
            try:
                return path.read_bytes()
            except OSError:
                path.unlink(missing_ok=True)

        if self.offline:
            self.log.error(
                "Offline mode, and this download is not cached.",
                cache_key,
            )
            return None

        raw = self._request(url, None)

        if raw is None:
            return None

        try:
            path.write_bytes(raw)
        except OSError as error:
            self.log.warn(f"Could not write cache: {error}")

        return raw

    def _request(
        self,
        url: str,
        data: Optional[bytes],
        *,
        redact: Optional[str] = None,
    ) -> Optional[bytes]:
        def safe_url() -> str:
            return url.replace(redact, "REDACTED") if redact else url

        for attempt in range(1, MAX_RETRIES + 1):
            request = urllib.request.Request(
                url,
                data=data,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            )

            try:
                time.sleep(REQUEST_DELAY_SECONDS)

                with urllib.request.urlopen(
                    request, timeout=REQUEST_TIMEOUT_SECONDS
                ) as response:
                    return response.read()

            except urllib.error.HTTPError as error:
                # 429 and 5xx are the service saying it is busy, and
                # worth retrying. A 400 or 404 is not, because the
                # request itself is wrong.
                if error.code in {429, 500, 502, 503, 504}:
                    self.log.warn(
                        f"Server returned {error.code}, attempt "
                        f"{attempt} of {MAX_RETRIES}. Waiting."
                    )
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                body = ""

                try:
                    body = error.read().decode("utf-8", "replace")[:300]
                except Exception:
                    pass

                self.log.error(
                    f"HTTP {error.code} from {safe_url()}",
                    body or str(error),
                )
                return None

            except (urllib.error.URLError, TimeoutError) as error:
                self.log.warn(
                    f"Network error on attempt {attempt}: {error}"
                )
                time.sleep(RETRY_DELAY_SECONDS * attempt)

        self.log.error(
            f"Gave up after {MAX_RETRIES} attempts: {safe_url()}"
        )
        return None


# ============================================================
# CENSUS GAZETTEER — UNITED STATES ONLY
# ============================================================

@dataclass
class GazetteerRecord:
    geoid: str
    name: str
    usps: str
    lat: float
    lon: float
    land_area_sq_metres: Optional[float]
    water_area_sq_metres: Optional[float]

    @property
    def land_area_sq_miles(self) -> Optional[float]:
        if self.land_area_sq_metres is None:
            return None

        return round(
            self.land_area_sq_metres * SQ_METRES_TO_SQ_MILES, 2
        )


def load_county_gazetteer(
    fetcher: Fetcher,
    log: RunLog,
) -> dict[str, GazetteerRecord]:
    """
    Download and parse the national county Gazetteer, keyed by GEOID.

    Columns are located by header rather than by position, because
    names have shifted between vintages. Values are stripped because
    several columns are whitespace-padded.
    """
    raw = fetcher.binary_request(
        GAZETTEER_COUNTIES_URL, "gazetteer-counties-2020"
    )

    if raw is None:
        log.error(
            "Could not download the county Gazetteer.",
            f"URL: {GAZETTEER_COUNTIES_URL}\n"
            "Representative points and land area will be absent. The "
            "OSM bounding-box centre is NOT substituted, because it "
            "is a different measurement and would silently disagree "
            "with hand-researched files.",
        )
        return {}

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        log.error(
            "The Gazetteer download was not a valid zip archive.",
            "Clear the cache directory and retry.",
        )
        return {}

    members = [
        name for name in archive.namelist()
        if name.lower().endswith(".txt")
    ]

    if not members:
        log.error("No .txt member inside the Gazetteer zip.")
        return {}

    with archive.open(members[0]) as handle:
        # Older vintages are Latin-1, newer ones UTF-8. Latin-1
        # decodes both without raising; a mis-decoded accent in a place
        # name beats a hard failure.
        text = handle.read().decode("latin-1")

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")

    if reader.fieldnames is None:
        log.error("The Gazetteer file has no header row.")
        return {}

    headers = {name.strip().upper(): name for name in reader.fieldnames}

    def column(*candidates: str) -> Optional[str]:
        for candidate in candidates:
            if candidate in headers:
                return headers[candidate]

        return None

    geoid_key = column("GEOID")
    name_key = column("NAME")
    usps_key = column("USPS")
    lat_key = column("INTPTLAT")
    lon_key = column("INTPTLONG", "INTPTLON")
    land_key = column("ALAND")
    water_key = column("AWATER")

    missing = [
        label
        for label, key in (
            ("GEOID", geoid_key),
            ("NAME", name_key),
            ("INTPTLAT", lat_key),
            ("INTPTLONG", lon_key),
        )
        if key is None
    ]

    if missing:
        log.error(
            "The Gazetteer file is missing column(s): "
            + ", ".join(missing),
            "Found: " + ", ".join(sorted(headers)),
        )
        return {}

    records: dict[str, GazetteerRecord] = {}

    for row in reader:
        geoid = (row.get(geoid_key) or "").strip()

        if not geoid:
            continue

        try:
            lat = float((row.get(lat_key) or "").strip())
            lon = float((row.get(lon_key) or "").strip())
        except ValueError:
            continue

        def area(key: Optional[str]) -> Optional[float]:
            if key is None:
                return None

            try:
                return float((row.get(key) or "").strip())
            except ValueError:
                return None

        records[geoid] = GazetteerRecord(
            geoid=geoid,
            name=(row.get(name_key) or "").strip(),
            usps=(
                (row.get(usps_key) or "").strip() if usps_key else ""
            ),
            lat=lat,
            lon=lon,
            land_area_sq_metres=area(land_key),
            water_area_sq_metres=area(water_key),
        )

    log.info(f"Loaded {len(records)} county records.")

    return records


def fetch_populations(
    fetcher: Fetcher,
    log: RunLog,
    state_fips: str,
    census_key: Optional[str],
) -> dict[str, int]:
    """
    County populations from the 2020 decennial redistricting file.

    This is the one part of the US pipeline that depends on a live
    keyed API, and the one part allowed to fail without stopping the
    run. A null population with a warning is correct; a guessed one is
    not.
    """
    if not census_key:
        log.warn(
            "No Census API key supplied, so population was not "
            "requested.",
            f"Get a free key at {CENSUS_KEY_SIGNUP_URL}\n"
            "Then pass --census-key, or set CENSUS_API_KEY in the "
            "environment or a .env file.\n"
            "Zones will carry a null population and a verification "
            "requirement, which the research pass can satisfy with a "
            "cited source.",
        )
        return {}

    params = {
        "get": "NAME,P1_001N",
        "for": "county:*",
        "in": f"state:{state_fips}",
        "key": census_key,
    }

    url = f"{CENSUS_POPULATION_URL}?{urllib.parse.urlencode(params)}"

    payload = fetcher.json_request(
        url,
        f"census-pop-{state_fips}",
        redact=census_key,
    )

    if not isinstance(payload, list) or len(payload) < 2:
        log.warn(
            f"No population data returned for state FIPS "
            f"{state_fips}.",
            "Zones will carry a null population and a verification "
            "requirement. Not a blocking failure.",
        )
        return {}

    header = payload[0]

    try:
        pop_index = header.index("P1_001N")
        state_index = header.index("state")
        county_index = header.index("county")
    except (ValueError, AttributeError):
        log.warn(
            "The population response was not the expected shape.",
            f"Header: {header}",
        )
        return {}

    result: dict[str, int] = {}

    for row in payload[1:]:
        try:
            result[f"{row[state_index]}{row[county_index]}"] = int(
                row[pop_index]
            )
        except (IndexError, ValueError, TypeError):
            continue

    log.info(f"Loaded {len(result)} county populations.")

    return result


# ============================================================
# OVERPASS
# ============================================================

def overpass_query(
    fetcher: Fetcher,
    log: RunLog,
    query: str,
    cache_key: str,
) -> list[dict[str, Any]]:
    """
    Run a query against the first endpoint that answers.

    Overpass mirrors go down individually and often. Trying a second is
    worth the twenty lines.
    """
    for endpoint in OVERPASS_ENDPOINTS:
        payload = fetcher.json_request(
            endpoint,
            f"overpass-{cache_key}",
            body=urllib.parse.urlencode({"data": query}),
        )

        if payload is None:
            continue

        elements = payload.get("elements")

        if isinstance(elements, list):
            return elements

        log.warn(f"Unexpected Overpass payload from {endpoint}.")

    return []


def probe_country(
    fetcher: Fetcher,
    log: RunLog,
    country_code: str,
) -> dict[int, list[str]]:
    """
    Report how many administrative relations exist at each admin level
    inside a country, with example names.

    This exists because admin_level semantics are country-specific and
    guessing them produces a file that is internally consistent and
    describes the wrong tier of geography. Reading a probe takes half a
    minute and settles the question permanently.

    Levels are queried one at a time rather than in a single query. It
    is slower, but a single query returning every relation at every
    level in a large country is a request worth being ashamed of on a
    free shared service, and one timeout would lose the whole result
    rather than one row.
    """
    results: dict[int, list[str]] = {}

    for level in PROBE_LEVELS:
        query = f"""
[out:json][timeout:180];
area["ISO3166-1"="{country_code}"]->.country;
relation
  ["boundary"="administrative"]
  ["admin_level"="{level}"]
  (area.country);
out ids tags;
"""

        elements = overpass_query(
            fetcher,
            log,
            query,
            f"probe-{country_code}-{level}",
        )

        names = sorted(
            str((item.get("tags") or {}).get("name", "")).strip()
            for item in elements
            if (item.get("tags") or {}).get("name")
        )

        results[level] = names

    return results


def find_boundary(
    fetcher: Fetcher,
    log: RunLog,
    *,
    name: str,
    country_code: str,
    iso_subdivision: Optional[str],
    admin_level: int,
) -> Optional[dict[str, Any]]:
    """
    Resolve the market boundary to exactly one OSM relation.

    Name alone is not enough. There is a Washington state and a
    Washington county in thirty states. Where an ISO 3166-2 code exists
    it is the reliable discriminator, so it is tried first.

    At admin_level 2 the boundary IS the country, so the ISO 3166-1
    code identifies it directly and no name search is needed.
    """
    if admin_level == 2:
        query = f"""
[out:json][timeout:180];
relation
  ["boundary"="administrative"]
  ["admin_level"="2"]
  ["ISO3166-1"="{country_code}"];
out ids tags bb;
"""

        elements = overpass_query(
            fetcher, log, query, f"boundary-country-{country_code}"
        )

        if len(elements) == 1:
            log.info(
                f"Boundary is the country itself, resolved by ISO "
                f"3166-1 code {country_code}: relation "
                f"{elements[0].get('id')}"
            )
            return elements[0]

        log.error(
            f"Country boundary lookup for {country_code} returned "
            f"{len(elements)} relations, expected exactly one.",
            "Pass --relation-id with the country's OSM relation ID.",
        )
        return None

    if iso_subdivision:
        query = f"""
[out:json][timeout:180];
relation
  ["boundary"="administrative"]
  ["admin_level"="{admin_level}"]
  ["ISO3166-2"="{iso_subdivision}"];
out ids tags bb;
"""

        elements = overpass_query(
            fetcher, log, query, f"boundary-iso-{iso_subdivision}"
        )

        if len(elements) == 1:
            log.info(
                f"Boundary resolved by ISO code {iso_subdivision}: "
                f"relation {elements[0].get('id')}"
            )
            return elements[0]

        if len(elements) > 1:
            log.warn(
                f"ISO code {iso_subdivision} matched "
                f"{len(elements)} relations, which should not "
                "happen. Falling back to a name search."
            )

    escaped = name.replace('"', '\\"')

    query = f"""
[out:json][timeout:180];
area["ISO3166-1"="{country_code}"]->.country;
relation
  ["boundary"="administrative"]
  ["admin_level"="{admin_level}"]
  ["name"="{escaped}"]
  (area.country);
out ids tags bb;
"""

    elements = overpass_query(
        fetcher, log, query, f"boundary-name-{country_code}-{name}"
    )

    if not elements:
        log.error(
            f"No boundary found for {name!r} at admin_level "
            f"{admin_level} in {country_code}.",
            "Two things to check.\n"
            "First, the name as OSM records it. Local spelling often "
            "differs from English, and the name tag is authoritative "
            "here.\n"
            f"Second, the admin level. Run --probe {country_code} to "
            "see what exists at each level in this country.",
        )
        return None

    if len(elements) > 1:
        ids = ", ".join(str(item.get("id")) for item in elements[:10])

        log.error(
            f"Name {name!r} matched {len(elements)} relations: {ids}",
            "Supply --iso-subdivision to disambiguate, or pass "
            "--relation-id directly.",
        )
        return None

    log.info(
        f"Boundary resolved by name: relation {elements[0].get('id')}"
    )

    return elements[0]


def fetch_children(
    fetcher: Fetcher,
    log: RunLog,
    *,
    parent_relation_id: int,
    admin_level: int,
    country_code: str,
    want_admin_centre: bool,
) -> list[dict[str, Any]]:
    """
    Every administrative relation one level down, inside the parent.

    "out bb" asks for bounding boxes rather than full geometry. For 64
    counties that is kilobytes rather than megabytes, and a bounding
    box is genuinely useful as a bounding box. It is NOT used as a
    representative point; see the note at the head of this file.

    When want_admin_centre is set, the query also returns each
    relation's member nodes so an admin_centre can be found. That is
    the generic path's only source of a representative point, and it
    roughly doubles the response size, so it is not requested for the
    US path which has the Gazetteer.
    """
    # Overpass area IDs for relations are the relation ID plus
    # 3600000000. A documented convention, not a guess.
    area_id = 3600000000 + parent_relation_id

    if want_admin_centre:
        # "out bb" for the relations, then the member nodes with their
        # coordinates. The node set is filtered to admin_centre and
        # label roles by inspecting the members client-side, because
        # Overpass cannot filter members by role in this form.
        query = f"""
[out:json][timeout:300];
area({area_id})->.parent;
relation
  ["boundary"="administrative"]
  ["admin_level"="{admin_level}"]
  (area.parent)->.children;
.children out ids tags bb;
node(r.children)->.centres;
.centres out ids tags;
"""
    else:
        query = f"""
[out:json][timeout:240];
area({area_id})->.parent;
relation
  ["boundary"="administrative"]
  ["admin_level"="{admin_level}"]
  (area.parent);
out ids tags bb;
"""

    elements = overpass_query(
        fetcher,
        log,
        query,
        f"children-{parent_relation_id}-{admin_level}"
        + ("-centres" if want_admin_centre else ""),
    )

    if not elements:
        log.error(
            f"No children found at admin_level {admin_level} inside "
            f"relation {parent_relation_id}.",
            "The most likely cause is a wrong admin_level for this "
            f"country. Run --probe {country_code} to see what exists "
            "at each level.",
        )

    return elements


def fetch_admin_centres(
    fetcher: Fetcher,
    log: RunLog,
    relation_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """
    Resolve each relation's admin_centre member node to a coordinate.

    Returns a mapping of relation ID to {"lat", "lon", "name"}.

    The generic path's representative point comes from here. The node
    is a member of the relation, so it lies inside the area by
    construction, which is the property a routing anchor needs. It is
    also, arguably, a better anchor than a geometric internal point,
    because it is the seat of government or principal settlement
    rather than an arbitrary interior coordinate.

    Where no admin_centre is tagged the relation simply does not
    appear in the result, and the caller writes null. That is
    deliberate: substituting the bounding-box centre would be a
    different measurement wearing the same field name.
    """
    if not relation_ids:
        return {}

    # Batched, because a query naming several hundred relation IDs
    # exceeds what Overpass will accept in one request.
    batch_size = 50
    result: dict[int, dict[str, Any]] = {}

    for start in range(0, len(relation_ids), batch_size):
        batch = relation_ids[start:start + batch_size]
        id_list = ",".join(str(item) for item in batch)

        query = f"""
[out:json][timeout:180];
relation(id:{id_list});
out ids;
>;
out ids tags;
"""

        # A simpler and more reliable approach: ask for each relation
        # with its members expanded, then walk the members client-side
        # looking for role=admin_centre.
        query = f"""
[out:json][timeout:180];
relation(id:{id_list});
out ids meta;
"""

        # Overpass "out" on a relation does not include member roles
        # unless the relation body is requested. Ask for the full
        # relation body, which carries members with roles, then resolve
        # the node IDs in a second pass.
        query = f"""
[out:json][timeout:240];
relation(id:{id_list});
out body;
node(r);
out ids tags;
"""

        elements = overpass_query(
            fetcher,
            log,
            query,
            f"admin-centres-{batch[0]}-{len(batch)}",
        )

        # === LABEL_PROVENANCE_FIX_V1 ===
        # First pass: relation ID to (node ID, role). The role is
        # kept because a label node is a WEAKER point than an
        # admin_centre and the emitted record must say which it got.
        wanted: dict[int, tuple[int, str]] = {}

        for element in elements:
            if element.get("type") != "relation":
                continue

            relation_id = element.get("id")

            for member in element.get("members") or []:
                if member.get("type") != "node":
                    continue

                role = str(member.get("role", "")).strip()

                if role == "admin_centre":
                    wanted[relation_id] = (member.get("ref"), role)
                    break

                # "label" is a weaker fallback. It marks where a map
                # renderer should draw the name, which is usually but
                # not always a sensible interior point. Taken only
                # when no admin_centre exists, and recorded as such.
                if role == "label" and relation_id not in wanted:
                    wanted[relation_id] = (member.get("ref"), role)

        # Second pass: node ID to coordinate.
        nodes: dict[int, dict[str, Any]] = {}

        for element in elements:
            if element.get("type") != "node":
                continue

            node_id = element.get("id")
            lat = element.get("lat")
            lon = element.get("lon")

            if isinstance(lat, (int, float)) and isinstance(
                lon, (int, float)
            ):
                nodes[node_id] = {
                    "lat": float(lat),
                    "lon": float(lon),
                    "name": str(
                        (element.get("tags") or {}).get("name", "")
                    ).strip(),
                }

        for relation_id, (node_id, role) in wanted.items():
            node = nodes.get(node_id)

            if node is not None:
                node = dict(node)
                node["role"] = role
                result[relation_id] = node

    labels = sum(
        1 for node in result.values() if node.get("role") == "label"
    )

    log.info(
        f"Resolved {len(result)} representative points from "
        f"{len(relation_ids)} relations: {len(result) - labels} "
        f"admin_centre, {labels} label fallback(s)."
    )

    return result


# ============================================================
# ZONE CONSTRUCTION
# ============================================================

def slugify(value: str) -> str:
    text = value.lower().strip()

    # Transliterate the handful of Latin-script accents that appear in
    # European and African place names. Anything outside this map is
    # dropped by the regex below, which is why a zone ID may be shorter
    # than its name. The name itself is preserved intact.
    replacements = {
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o", "ø": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c", "ß": "ss", "æ": "ae", "œ": "oe",
        "š": "s", "ž": "z", "ý": "y", "ÿ": "y", "ð": "d", "þ": "th",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def zone_id_for(name: str, zone_type: str) -> str:
    """
    A readable, stable ID derived from the name.

    The OSM relation ID and any national identifier are both recorded
    in external_ids. They are the durable machine identifiers, but they
    make unreadable zone IDs, and Section 02's IDs are read constantly
    while reviewing hierarchy and barriers.

    The type suffix is appended only where the type word is a genuine
    part of how the place is referred to. "Addison County" reads
    naturally; "Nairobi County" does too, in Kenya. "Bavaria District"
    does not, so district-typed zones get no suffix.
    """
    slug = slugify(name)

    if not slug:
        return "zone-unnamed"

    if zone_type == "county" and "county" not in slug:
        slug = f"{slug}-county"

    return f"zone-{slug}"


def extract_fips(tags: dict[str, Any]) -> Optional[str]:
    """
    OSM records US FIPS codes under several keys, depending on who
    imported the data and when. All of them are checked.
    """
    for key in (
        "nist:fips_code",
        "ref:fips",
        "gnis:fips_code",
        "census:fips",
        "ref",
    ):
        value = str(tags.get(key, "")).strip()

        if re.fullmatch(r"\d{5}", value):
            return value

    return None


def extract_osm_population(tags: dict[str, Any]) -> Optional[int]:
    """
    The OSM population tag, where it parses as a plain integer.

    Deliberately strict. The tag is free text and carries values such
    as "approx 45000", "45,000 (2019)" and "45000-50000". Parsing those
    means deciding what the contributor meant, which is exactly the
    kind of inference this extractor exists to avoid. A value that is
    not a bare integer is treated as absent.

    Anything returned here is tier 3 evidence and is recorded as such:
    the tag is unsourced, undated, and updated by whoever last thought
    to. It is better than nothing and considerably worse than a census.
    """
    value = str(tags.get("population", "")).strip()

    if not re.fullmatch(r"\d+", value):
        return None

    try:
        number = int(value)
    except ValueError:
        return None

    # A population of zero is either a genuine ghost town, which is not
    # a market, or a placeholder. Either way it is not useful and is
    # more likely to mislead than inform.
    return number if number > 0 else None


def extract_population_date(tags: dict[str, Any]) -> Optional[str]:
    """
    The year a population tag refers to, where recorded.

    population:date is the conventional key. A bare four-digit year is
    accepted; anything else is treated as absent rather than parsed.
    """
    for key in ("population:date", "population:year", "source:population:date"):
        value = str(tags.get(key, "")).strip()

        match = re.match(r"^(\d{4})", value)

        if match:
            return match.group(1)

    return None


def build_bbox(element: dict[str, Any]) -> dict[str, Any]:
    bounds = element.get("bounds") or {}

    def value(key: str) -> Optional[float]:
        item = bounds.get(key)
        return item if isinstance(item, (int, float)) else None

    north = value("maxlat")
    south = value("minlat")
    east = value("maxlon")
    west = value("minlon")

    populated = all(
        item is not None for item in (north, south, east, west)
    )

    return {
        "north": north,
        "south": south,
        "east": east,
        "west": west,
        "crosses_antimeridian": False,
        "source_ids": ["src-osm-boundaries"] if populated else [],
    }


@dataclass
class ZoneContext:
    """
    Everything build_zone needs that is not the element itself.

    Bundled rather than passed as a dozen keyword arguments, because
    the two reference strategies need different subsets and the
    signature was becoming a place for mistakes to hide.
    """

    country_code: str
    reference_strategy: str
    research_date: str

    # US path only.
    gazetteer: dict[str, GazetteerRecord] = field(default_factory=dict)
    populations: dict[str, int] = field(default_factory=dict)

    # Generic path only.
    admin_centres: dict[int, dict[str, Any]] = field(
        default_factory=dict
    )

    @property
    def is_us_census(self) -> bool:
        return self.reference_strategy == REFERENCE_US_CENSUS


def build_zone(
    element: dict[str, Any],
    *,
    zone_type: str,
    parent_zone_id: Optional[str],
    ancestor_zone_ids: list[str],
    context: ZoneContext,
    geoid_override: Optional[str],
    log: RunLog,
    is_market_boundary: bool = False,
) -> Optional[dict[str, Any]]:
    tags = element.get("tags") or {}

    name = str(tags.get("name", "")).strip()

    if not name:
        log.warn(
            f"Relation {element.get('id')} has no name tag and was "
            "skipped."
        )
        return None

    relation_id = element.get("id")

    external_ids: list[dict[str, Any]] = [
        {
            "system": "osm-relation",
            "value": str(relation_id),
            "source_ids": ["src-osm-boundaries"],
            "verification_status": "verified_official",
        }
    ]

    geoid = geoid_override or (
        extract_fips(tags) if context.is_us_census else None
    )

    # ------------------------------------------------------------
    # The coordinate decision.
    #
    # The market boundary zone deliberately has no representative
    # point, and this is not a gap.
    #
    # That zone answers one question: what is inside this market?
    # Containment comes from the polygon, not from a point. Everything
    # routable hangs beneath it, and points matter at the tier where
    # something is genuinely a pickup or drop-off: a resort, an airport
    # terminal, a city centre. Nothing routes to a state centroid.
    #
    # For every other zone the point comes from whichever source the
    # country's profile names, and never from the OSM bounding box.
    # The bbox centre is a different measurement: for an irregular
    # shape it differs from any interior point, and for a concave one
    # it can fall outside the polygon entirely.
    #
    # Where the named source has nothing, the point is left null. A
    # null is visible and fails validation; a silently different
    # measurement is neither.
    # ------------------------------------------------------------
    record: Optional[GazetteerRecord] = None
    centre_source: Optional[str] = None
    centre_basis: Optional[str] = None

    if is_market_boundary:
        centre = {"lat": None, "lon": None, "source_ids": []}
    elif context.is_us_census:
        record = context.gazetteer.get(geoid) if geoid else None

        if record is not None:
            centre = {
                "lat": record.lat,
                "lon": record.lon,
                "source_ids": ["src-census-gazetteer"],
            }
            centre_source = "src-census-gazetteer"
            centre_basis = "census-internal-point"
        else:
            centre = {"lat": None, "lon": None, "source_ids": []}

            log.warn(
                f"{name} has no Census Gazetteer row"
                + (
                    f" for GEOID {geoid}"
                    if geoid
                    else " and no usable identifier"
                )
                + ". Representative point left null rather than "
                "substituted from the OSM bounding box, which is a "
                "different measurement."
            )
    else:
        node = context.admin_centres.get(relation_id)

        if node is not None:
            centre = {
                "lat": node["lat"],
                "lon": node["lon"],
                "source_ids": ["src-osm-admin-centre"],
            }
            centre_source = "src-osm-admin-centre"
            centre_basis = (
                "osm-label-node"
                if node.get("role") == "label"
                else "osm-admin-centre-node"
            )
        else:
            centre = {"lat": None, "lon": None, "source_ids": []}

            log.warn(
                f"{name} has no admin_centre member node, so its "
                "representative point is null.",
                "The OSM bounding-box centre is not substituted: it "
                "is a different measurement and can fall outside an "
                "irregular boundary entirely. The research pass must "
                "supply a point that lies inside the area.",
            )

    if geoid:
        external_ids.append(
            {
                "system": "fips",
                "value": geoid,
                "source_ids": (
                    ["src-census-gazetteer"]
                    if record is not None
                    else ["src-osm-boundaries"]
                ),
                "verification_status": (
                    "verified_multiple_sources"
                    if record is not None
                    else "single_source"
                ),
            }
        )

    wikidata = str(tags.get("wikidata", "")).strip()

    if re.fullmatch(r"Q[1-9][0-9]*", wikidata):
        external_ids.append(
            {
                "system": "wikidata",
                "value": wikidata,
                "source_ids": ["src-osm-boundaries"],
                "verification_status": "single_source",
            }
        )

    iso_code = str(tags.get("ISO3166-2", "")).strip()

    if iso_code:
        external_ids.append(
            {
                "system": "iso-3166-2",
                "value": iso_code,
                "source_ids": ["src-osm-boundaries"],
                "verification_status": "verified_official",
            }
        )

    iso_country = str(tags.get("ISO3166-1", "")).strip()

    if iso_country and is_market_boundary:
        external_ids.append(
            {
                "system": "iso-3166-1",
                "value": iso_country,
                "source_ids": ["src-osm-boundaries"],
                "verification_status": "verified_official",
            }
        )

    # ------------------------------------------------------------
    # Population.
    #
    # The US path takes it from the decennial census, joined on GEOID,
    # which is tier 1 and dated.
    #
    # The generic path takes it from the OSM population tag, which is
    # tier 3: unsourced, usually undated, and updated by whoever last
    # thought to. It is recorded with its real provenance rather than
    # dressed up, and the zone carries a verification requirement
    # saying an official figure should replace it.
    # ------------------------------------------------------------
    population: Optional[int] = None
    population_year: Optional[int] = None
    population_definition: Optional[str] = None
    population_source_ids: list[str] = []

    if is_market_boundary:
        pass
    elif context.is_us_census:
        population = context.populations.get(geoid) if geoid else None

        if population is not None:
            population_year = 2020
            population_definition = (
                "U.S. Census Bureau 2020 decennial resident "
                f"population, {name}"
            )
            population_source_ids = ["src-census-population"]
    else:
        population = extract_osm_population(tags)

        if population is not None:
            year_text = extract_population_date(tags)

            try:
                population_year = int(year_text) if year_text else None
            except ValueError:
                population_year = None

            population_definition = (
                f"OpenStreetMap population tag on the {name} boundary "
                "relation"
                + (
                    f", dated {year_text}"
                    if year_text
                    else ", undated"
                )
                + ". Contributor-supplied and not traceable to a "
                "named census; treat as indicative."
            )
            population_source_ids = ["src-osm-population"]

    aliases: list[str] = []

    for key in ("official_name", "alt_name", "short_name"):
        value = str(tags.get(key, "")).strip()

        if value and value != name:
            aliases.extend(
                part.strip()
                for part in value.split(";")
                if part.strip() and part.strip() != name
            )

    # Local-language names, where tagged. Worth preserving: a market
    # file describing Morocco that carries only the French name loses
    # information a later reader may need.
    alternate_language_names: list[dict[str, str]] = []

    for key, value in tags.items():
        match = re.fullmatch(r"name:([a-z]{2,3})", str(key))

        if not match:
            continue

        language = match.group(1)
        text = str(value).strip()

        if text and text != name:
            alternate_language_names.append(
                {"language_code": language, "name": text}
            )

    alternate_language_names.sort(key=lambda item: item["language_code"])

    source_ids = ["src-osm-boundaries"]

    if centre_source is not None and centre_source not in source_ids:
        source_ids.append(centre_source)

    for source_id in population_source_ids:
        if source_id not in source_ids:
            source_ids.append(source_id)

    # ------------------------------------------------------------
    # Verification status.
    #
    # Every zone here carries geographic_precision "official_boundary",
    # because every one IS an OSM administrative boundary relation. The
    # Section 02 schema ties that precision to official verification:
    # such a zone must be verified_official or
    # verified_multiple_sources, and single_source is refused outright.
    #
    # An earlier version derived the status purely from the source
    # count. The market boundary zone rests on OSM alone, having no
    # Gazetteer row by design, so it came out single_source and failed
    # validation on every state. A research pass merging this file
    # inherited the wrong value and was right not to change it: the
    # defect was here.
    #
    # The count still decides WHICH official value applies, because
    # verified_multiple_sources means what it says and the schema
    # enforces a minimum of two source IDs behind it.
    #
    # Calling an OSM relation "verified_official" is a judgement worth
    # stating plainly. Administrative boundaries in OSM are, in most
    # countries with any mapping activity, imported from official
    # sources, and a relation carrying an ISO 3166-2 code is a real
    # official-derived reference rather than a contributor's sketch.
    # The crowd-sourced caveat is not hidden: it is on the source
    # record's limitations, on the zone's limitations, and in
    # geometry_validation_pending, which stays true until the polygon
    # has actually been retrieved and checked.
    # ------------------------------------------------------------
    verification_status = (
        "verified_multiple_sources"
        if len(source_ids) > 1
        else "verified_official"
    )

    limitations = [
        "Identity, hierarchy and external identifiers are extracted "
        "from OpenStreetMap. Judgement fields are null and must be "
        "completed before this zone can be used."
    ]

    verification = [
        "Retrieve and validate boundary geometry from the referenced "
        "OSM relation.",
        "Assign market inclusion, transportation relevance and "
        "access characteristics; these are not derivable from "
        "administrative boundary data.",
    ]

    if is_market_boundary:
        # Stated on the record so a later reviewer does not "fix" it by
        # adding a point, and so a downstream consumer does not read
        # the null as an oversight.
        limitations.append(
            "No representative point, deliberately. This zone defines "
            "the market extent and anchors the hierarchy; containment "
            "is answered by the boundary polygon. Routing anchors "
            "belong on the zones beneath it."
        )
    else:
        if centre["lat"] is None:
            if context.is_us_census:
                limitations.append(
                    "No Census Gazetteer match, so the representative "
                    "point and land area are absent."
                )
            else:
                limitations.append(
                    "No admin_centre member node on this relation, so "
                    "the representative point is absent. The OSM "
                    "bounding-box centre was not substituted because "
                    "it is a different measurement."
                )

            verification.append(
                "Supply a representative point that lies inside the "
                "boundary."
            )
        elif centre_basis == "osm-admin-centre-node":
            limitations.append(
                "The representative point is the OpenStreetMap "
                "admin_centre member node: the seat or principal "
                "settlement of this area. It lies inside the boundary "
                "by construction, but it is not a geometric internal "
                "point and is not an official reference coordinate."
            )
        elif centre_basis == "osm-label-node":
            limitations.append(
                "The representative point is an OpenStreetMap label "
                "member node, used because no admin_centre is tagged. "
                "A label marks where a renderer draws the name: it is "
                "usually, but not guaranteed to be, inside the "
                "boundary, and it is not the administrative seat."
            )
            verification.append(
                "Confirm the label-derived representative point lies "
                "inside the boundary, or replace it."
            )

        if population is None:
            verification.append(
                "Supply resident population from an official source."
            )
        elif population_source_ids == ["src-osm-population"]:
            limitations.append(
                "Population is an OpenStreetMap tag: "
                "contributor-supplied, usually undated, and not "
                "traceable to a named census. It is recorded so a "
                "reader has an order of magnitude, not so it can be "
                "published."
            )
            verification.append(
                "Replace the OpenStreetMap population figure with an "
                "official national statistics value, with its year."
            )

    return {
        "id": zone_id_for(name, zone_type),
        "official_name": str(tags.get("official_name") or name),
        "display_name": name,
        "zone_type": zone_type,
        "country_code": context.country_code,
        "jurisdiction_id": None,
        "parent_zone_id": parent_zone_id,
        "ancestor_zone_ids": ancestor_zone_ids,
        "cross_parent_zone_ids": [],
        "aliases": sorted(set(aliases)),
        "historical_names": [],
        "alternate_language_names": alternate_language_names,
        "external_ids": external_ids,
        "geographic_precision": "official_boundary",
        "center": centre,
        "bbox": build_bbox(element),
        "geometry": {
            "geometry_type": "MultiPolygon",
            "geometry_embedded": False,
            "simplified_geojson": None,
            "coordinate_reference_system": "EPSG:4326",
            "geometry_source_url": (
                f"{OSM_RELATION_URL_PREFIX}{relation_id}"
            ),
            "geometry_source_id": "src-osm-boundaries",
            "external_geometry_identifier": (
                f"OSM relation {relation_id}"
            ),
            "geometry_checksum_sha256": None,
            "geometry_retrieval_required": True,
            "geometry_validation_pending": True,
            "limitations": [
                "Boundary geometry is referenced by OSM relation ID "
                "rather than embedded. It must be retrieved and "
                "validated before any containment or routing use.",
                "The bounding box is from OpenStreetMap; any "
                "representative point comes from a different source "
                "and is a different measurement. They are recorded "
                "separately on purpose.",
            ],
        },
        # ----------------------------------------------------------
        # Everything below is deliberately null or empty.
        #
        # Whether a county is core or peripheral, and what its seasonal
        # access constraints are, are judgements about a transport
        # market, not facts about administrative geography. No map
        # database holds them.
        #
        # Leaving them null makes the handoff explicit, and the Section
        # 02 validator refuses the file until they are filled.
        # ----------------------------------------------------------
        "market_inclusion": {
            "status": None,
            "inclusion_basis": [],
            "exclusion_reason": None,
            "production_use": None,
        },
        "transportation_relevance": {
            "relevance_level": None,
            "candidate_transfer_roles": [],
            "demand_driver_ids": [],
            "seasonal_relevance": None,
            "notes": None,
        },
        "access_characteristics": {
            "road_access_status": None,
            "island_or_water_separated": None,
            "mountain_access": None,
            "seasonal_access": None,
            "cross_state_relevance": None,
            "cross_border_relevance": None,
            "direct_road_assumption_allowed": None,
            "known_access_constraints": [],
            "required_route_checks": [],
        },
        "population_context": {
            "population": population,
            "population_year": population_year,
            "population_definition": population_definition,
            "source_ids": population_source_ids,
        },
        "verification_requirements": verification,
        "research": {
            "confidence": "high" if context.is_us_census else "medium",
            "verification_status": verification_status,
            "source_ids": source_ids,
            "last_checked": context.research_date,
            "review_interval_days": 365,
            "limitations": limitations,
            "notes": (
                f"Extracted by osm_zone_extractor {EXTRACTOR_VERSION}"
                f" from OSM relation {relation_id}"
                + (
                    f" and Census GEOID {geoid}."
                    if record is not None
                    else "."
                )
            ),
        },
        # Extraction metadata, stripped before merge. Kept so a
        # reviewer can see which source supplied what without reading
        # the code.
        "_extraction": {
            "osm_relation_id": relation_id,
            "census_geoid": geoid,
            "reference_strategy": context.reference_strategy,
            "centre_basis": centre_basis,
            "gazetteer_matched": record is not None,
            "is_market_boundary": is_market_boundary,
            "land_area_sq_miles": (
                record.land_area_sq_miles if record else None
            ),
        },
    }


# ============================================================
# SOURCE RECORDS
# ============================================================

def build_sources(
    research_date: str,
    *,
    include_gazetteer: bool,
    include_census_population: bool,
    include_admin_centre: bool,
    include_osm_population: bool,
    boundary_relation_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Source records for exactly what was reached, and nothing else.

    An uncited source inflates the tier counts in research_summary,
    which the Section 02 validator checks. So a source is emitted only
    if the run actually used it.

    boundary_relation_id is recorded on the OSM source because a source
    record should say what was actually queried. Two markets otherwise
    produce byte-identical OSM source records, and neither names the
    relation its zones descend from.
    """
    osm_access_notes = (
        "Queried via the Overpass API"
        + (
            f", rooted at OSM relation {boundary_relation_id} "
            f"({OSM_RELATION_URL_PREFIX}{boundary_relation_id})"
            if boundary_relation_id is not None
            else ""
        )
        + ". OpenStreetMap data is licensed ODbL 1.0; any published "
        "derivative must credit OpenStreetMap contributors and "
        "preserve the licence. Used here for identity, hierarchy and "
        "cross-references only. Representative points come from a "
        "separate source, because an OSM bounding-box centre is not "
        "guaranteed to lie inside the boundary it describes."
    )

    sources: list[dict[str, Any]] = [
        {
            "id": "src-osm-boundaries",
            "title": (
                "OpenStreetMap boundary=administrative tag "
                "definition and relations"
            ),
            # The wiki page rather than the OSM home page. A bare
            # domain is not evidence that a document was opened, and
            # the Section 02 validator says so. This page defines the
            # tag actually queried.
            "url": OSM_TAG_DOCUMENTATION_URL,
            "publisher": "OpenStreetMap contributors",
            "source_type": "official_open_data",
            "authority_tier": 1,
            "geographic_scope": [],
            "topics_supported": [
                "administrative boundary identity",
                "administrative hierarchy",
                "bounding boxes",
                "external identifier cross-references",
            ],
            "published_at": None,
            "effective_date": None,
            "expires_at": None,
            "last_checked": research_date,
            "confidence": "high",
            "review_status": "machine_collected_unreviewed",
            "volatile": True,
            "review_interval_days": 180,
            "canonical_url": OSM_TAG_DOCUMENTATION_URL,
            "dataset_details": {
                "dataset_name": (
                    "OpenStreetMap boundary=administrative relations"
                ),
                "dataset_page_url": OSM_TAG_DOCUMENTATION_URL,
                "service_or_download_url": (
                    "https://overpass-api.de/api/interpreter"
                ),
                "layer_name": "boundary=administrative",
                "layer_identifier": (
                    "boundary=administrative within OSM relation "
                    f"{boundary_relation_id}"
                    if boundary_relation_id is not None
                    else "boundary=administrative"
                ),
                "geometry_updated_at": None,
                "coordinate_reference_system": "EPSG:4326",
            },
            "access_notes": osm_access_notes,
            "limitations": [
                "OSM is crowd-sourced. Administrative boundaries in "
                "countries with active mapping communities are "
                "generally imported from official sources and "
                "reliable, but OSM is not itself an official record, "
                "and completeness varies enormously by region.",
                "Tag completeness varies. A missing identifier or "
                "population tag is common and is reported rather than "
                "filled by inference.",
                "Boundary geometry is referenced rather than "
                "retrieved. Every zone keeps "
                "geometry_validation_pending true until the polygon "
                "has actually been fetched and checked.",
            ],
            "notes": None,
        }
    ]

    if include_admin_centre:
        sources.append(
            {
                "id": "src-osm-admin-centre",
                "title": (
                    "OpenStreetMap boundary relation admin_centre "
                    "member nodes"
                ),
                "url": OSM_ADMIN_CENTRE_DOCUMENTATION_URL,
                "publisher": "OpenStreetMap contributors",
                "source_type": "official_open_data",
                "authority_tier": 2,
                "geographic_scope": [],
                "topics_supported": [
                    "representative point coordinates",
                    "administrative seat identity",
                ],
                "published_at": None,
                "effective_date": None,
                "expires_at": None,
                "last_checked": research_date,
                "confidence": "medium",
                "review_status": "machine_collected_unreviewed",
                "volatile": True,
                "review_interval_days": 180,
                "canonical_url": OSM_ADMIN_CENTRE_DOCUMENTATION_URL,
                "dataset_details": {
                    "dataset_name": (
                        "OpenStreetMap boundary relation members with "
                        "role=admin_centre"
                    ),
                    "dataset_page_url": (
                        OSM_ADMIN_CENTRE_DOCUMENTATION_URL
                    ),
                    "service_or_download_url": (
                        "https://overpass-api.de/api/interpreter"
                    ),
                    "layer_name": "admin_centre member nodes",
                    "layer_identifier": (
                        "role=admin_centre within "
                        "boundary=administrative relations"
                    ),
                    "geometry_updated_at": None,
                    "coordinate_reference_system": "EPSG:4326",
                },
                "access_notes": (
                    "An admin_centre node is a member of the boundary "
                    "relation it describes, so it lies inside the "
                    "area by construction. It marks the seat of "
                    "government or principal settlement, which is "
                    "arguably a better routing anchor than a "
                    "geometric interior point, because it is where "
                    "people actually are. Used only where no national "
                    "reference dataset supplies an internal point."
                ),
                "limitations": [
                    "Not a geometric internal point and not an "
                    "official reference coordinate. It is the seat, "
                    "which may sit near an edge of a large area.",
                    "Tagging is optional and coverage varies by "
                    "country. Where the node is absent the "
                    "representative point is left null rather than "
                    "substituted.",
                    "Where no admin_centre exists, a label node is "
                    "used as a weaker fallback. A label marks where a "
                    "renderer should draw the name, which is usually "
                    "but not always a sensible interior point.",
                ],
                "notes": None,
            }
        )

    if include_osm_population:
        sources.append(
            {
                "id": "src-osm-population",
                "title": (
                    "OpenStreetMap population tag on administrative "
                    "boundary relations"
                ),
                "url": OSM_POPULATION_DOCUMENTATION_URL,
                "publisher": "OpenStreetMap contributors",
                "source_type": "official_open_data",
                "authority_tier": 3,
                "geographic_scope": [],
                "topics_supported": ["indicative resident population"],
                "published_at": None,
                "effective_date": None,
                "expires_at": None,
                "last_checked": research_date,
                "confidence": "low",
                "review_status": "machine_collected_unreviewed",
                "volatile": True,
                "review_interval_days": 180,
                "canonical_url": OSM_POPULATION_DOCUMENTATION_URL,
                "dataset_details": {
                    "dataset_name": (
                        "OpenStreetMap population key on "
                        "boundary=administrative relations"
                    ),
                    "dataset_page_url": (
                        OSM_POPULATION_DOCUMENTATION_URL
                    ),
                    "service_or_download_url": (
                        "https://overpass-api.de/api/interpreter"
                    ),
                    "layer_name": "population tag",
                    "layer_identifier": "population",
                    "geometry_updated_at": None,
                    "coordinate_reference_system": None,
                },
                "access_notes": (
                    "Read from the relation's own population tag. "
                    "Only values parsing as a bare positive integer "
                    "are accepted; anything qualified, ranged or "
                    "annotated is treated as absent rather than "
                    "interpreted. Recorded at tier 3 because the tag "
                    "is contributor-supplied and usually carries no "
                    "citation."
                ),
                "limitations": [
                    "Unsourced. The tag does not say which census or "
                    "estimate it came from.",
                    "Usually undated. Where population:date exists it "
                    "is recorded; where it does not, the figure's "
                    "vintage is unknown.",
                    "Not suitable for publication. It gives a reader "
                    "an order of magnitude and should be replaced "
                    "with an official national statistics figure "
                    "before any zone using it goes to production.",
                ],
                "notes": None,
            }
        )

    if include_gazetteer:
        sources.append(
            {
                "id": "src-census-gazetteer",
                "title": "2020 U.S. Gazetteer Files, counties",
                "url": (
                    "https://www.census.gov/geographies/"
                    "reference-files/time-series/geo/"
                    "gazetteer-files.html"
                ),
                "publisher": "U.S. Census Bureau",
                "source_type": "census",
                "authority_tier": 1,
                "geographic_scope": ["United States"],
                "topics_supported": [
                    "representative internal point coordinates",
                    "canonical GEOID identity",
                    "land and water area",
                ],
                "published_at": None,
                "effective_date": None,
                "expires_at": None,
                "last_checked": research_date,
                "confidence": "high",
                "review_status": "machine_collected_unreviewed",
                "volatile": False,
                "review_interval_days": 365,
                "canonical_url": (
                    "https://www.census.gov/geographies/"
                    "reference-files/time-series/geo/"
                    "gazetteer-files.html"
                ),
                "dataset_details": {
                    "dataset_name": (
                        "2020 Census Gazetteer Files, counties, "
                        "national"
                    ),
                    "dataset_page_url": (
                        "https://www.census.gov/geographies/"
                        "reference-files/time-series/geo/"
                        "gazetteer-files.html"
                    ),
                    "service_or_download_url": (
                        GAZETTEER_COUNTIES_URL
                    ),
                    "layer_name": "counties, national",
                    "layer_identifier": "2020_Gaz_counties_national",
                    "geometry_updated_at": None,
                    "coordinate_reference_system": "EPSG:4326",
                },
                "access_notes": (
                    "Static tab-delimited file, joined to OSM "
                    "relations on GEOID, never on name, because "
                    "county names repeat across states. INTPTLAT and "
                    "INTPTLONG are internal points guaranteed to fall "
                    "inside the polygon they describe, which is what "
                    "a routing anchor requires. Vintage is indicated "
                    "by the dataset name rather than an asserted "
                    "publication date."
                ),
                "limitations": [
                    "Internal points are representative points, not "
                    "centroids and not boundary polygons.",
                    "2020 vintage. Boundary changes since then are "
                    "not reflected.",
                ],
                "notes": None,
            }
        )

    if include_census_population:
        sources.append(
            {
                "id": "src-census-population",
                "title": (
                    "2020 Census Redistricting Data (P.L. 94-171), "
                    "county population"
                ),
                "url": CENSUS_POPULATION_URL,
                "publisher": "U.S. Census Bureau",
                "source_type": "census",
                "authority_tier": 1,
                "geographic_scope": ["United States"],
                "topics_supported": ["county resident population"],
                "published_at": None,
                "effective_date": None,
                "expires_at": None,
                "last_checked": research_date,
                "confidence": "high",
                "review_status": "machine_collected_unreviewed",
                "volatile": False,
                "review_interval_days": 365,
                "canonical_url": (
                    "https://www.census.gov/programs-surveys/"
                    "decennial-census/about/rdo/summary-files.html"
                ),
                "dataset_details": {
                    "dataset_name": (
                        "2020 Decennial Census P.L. 94-171 "
                        "Redistricting Data"
                    ),
                    "dataset_page_url": (
                        "https://www.census.gov/data/developers/"
                        "data-sets/decennial-census.html"
                    ),
                    "service_or_download_url": CENSUS_POPULATION_URL,
                    "layer_name": None,
                    "layer_identifier": "P1_001N",
                    "geometry_updated_at": None,
                    "coordinate_reference_system": None,
                },
                "access_notes": (
                    "Queried by state FIPS with an API key and joined "
                    "on the five-digit county GEOID. Where the join "
                    "fails the population is left null rather than "
                    "matched on name."
                ),
                "limitations": [
                    "2020 decennial counts. Later estimates exist and "
                    "diverge; the vintage is stated so a consumer can "
                    "decide whether it matters.",
                ],
                "notes": None,
            }
        )

    return sources


# ============================================================
# EXTRACTION
# ============================================================

@dataclass
class MarketSpec:
    slug: str
    subdivision_name: str
    country: str
    country_code: str
    profile: CountryProfile
    iso_subdivision: Optional[str] = None
    state_fips: Optional[str] = None


def resolve_profile(
    country_code: str,
    log: RunLog,
    *,
    boundary_level: Optional[int],
    child_level: Optional[int],
    boundary_zone_type: Optional[str],
    child_zone_type: Optional[str],
) -> Optional[CountryProfile]:
    """
    Find or construct the country profile for a run.

    A verified profile wins unless levels are supplied explicitly, in
    which case the override is honoured and logged: someone passing
    flags for a country already in the table is either testing or
    correcting it, and silently ignoring them would be worse than
    either.

    A country with no profile and no flags is refused. That refusal is
    the whole point: guessing produces a file that parses, validates,
    and describes the wrong tier of geography, and nothing downstream
    can detect it.
    """
    profile = COUNTRY_PROFILES.get(country_code)

    if boundary_level is None and child_level is None:
        if profile is not None:
            return profile

        known = ", ".join(sorted(COUNTRY_PROFILES))

        log.error(
            f"Country {country_code} has no verified profile and no "
            "admin levels were supplied.",
            "This is a refusal rather than a guess, deliberately.\n\n"
            "OSM's admin_level is country-specific. Level 6 is county "
            "in the United States, departement in France, district in "
            "Germany and sub-county in Kenya. Guessing produces a "
            "file that parses, validates, and describes an entirely "
            "different tier of geography, and nothing downstream can "
            "detect it.\n\n"
            "Two ways forward.\n\n"
            f"1. Find the levels:\n"
            f"     --probe {country_code}\n"
            "   That reports how many relations exist at each level "
            "and names three examples of each. Reading it takes about "
            "thirty seconds.\n\n"
            "2. Then run with them:\n"
            f"     --market {country_code.lower()}-<subdivision> "
            "--boundary-level N --child-level M\n\n"
            "Once confirmed, add the country to COUNTRY_PROFILES so "
            "nobody probes it twice.\n\n"
            f"Verified today: {known}",
        )
        return None

    if boundary_level is None or child_level is None:
        log.error(
            "Both --boundary-level and --child-level are required "
            "when either is given.",
            "A boundary level without a child level, or the reverse, "
            "is ambiguous: the extractor cannot tell whether the "
            "missing one should come from a profile that may not "
            "exist.",
        )
        return None

    if boundary_level >= child_level:
        log.error(
            f"Boundary level {boundary_level} must be numerically "
            f"lower than child level {child_level}.",
            "In OSM, a lower admin_level is a LARGER area. Level 2 is "
            "a country, level 6 a county. A boundary at or below its "
            "children inverts the hierarchy.",
        )
        return None

    for label, value in (
        ("--boundary-zone-type", boundary_zone_type),
        ("--child-zone-type", child_zone_type),
    ):
        if value is not None and value not in VALID_ZONE_TYPES:
            log.error(
                f"{label} {value!r} is not a Section 02 zone type.",
                "Valid for administrative tiers: "
                + ", ".join(sorted(VALID_ZONE_TYPES)),
            )
            return None

    if profile is not None:
        log.warn(
            f"{country_code} has a verified profile "
            f"({profile.boundary_level}/{profile.child_level}), but "
            f"explicit levels {boundary_level}/{child_level} were "
            "supplied and take precedence.",
            "If the override is correct, update COUNTRY_PROFILES so "
            "the next run does not need the flags.",
        )

    resolved = CountryProfile(
        country_name=(
            profile.country_name if profile else country_code
        ),
        boundary_level=boundary_level,
        child_level=child_level,
        boundary_zone_type=(
            boundary_zone_type
            or (profile.boundary_zone_type if profile else "province")
        ),
        child_zone_type=(
            child_zone_type
            or (profile.child_zone_type if profile else "district")
        ),
        # An explicit-level run never uses the US Census path, even for
        # the US. The Census path depends on the level 4 / level 6
        # county structure, and someone overriding the levels is by
        # definition asking for something else.
        reference_strategy=REFERENCE_GENERIC,
        notes=(
            f"Admin levels supplied explicitly: boundary "
            f"{boundary_level}, children {child_level}."
        ),
    )

    return resolved


def parse_market_slug(
    slug: str,
    log: RunLog,
    *,
    boundary_level: Optional[int],
    child_level: Optional[int],
    boundary_zone_type: Optional[str],
    child_zone_type: Optional[str],
) -> Optional[MarketSpec]:
    parts = slug.split("-", 1)

    if len(parts) != 2:
        log.error(
            f"Market slug {slug!r} is not in the expected "
            "country-subdivision form, for example us-vermont or "
            "ke-nairobi."
        )
        return None

    country_code = parts[0].upper()

    if not re.fullmatch(r"[A-Z]{2}", country_code):
        log.error(
            f"{country_code!r} is not an ISO 3166-1 alpha-2 country "
            "code.",
            "The slug's first component is the COUNTRY, two letters. "
            "A subdivision code such as VT belongs after the hyphen "
            "as a name, not before it.",
        )
        return None

    profile = resolve_profile(
        country_code,
        log,
        boundary_level=boundary_level,
        child_level=child_level,
        boundary_zone_type=boundary_zone_type,
        child_zone_type=child_zone_type,
    )

    if profile is None:
        return None

    subdivision = parts[1].replace("-", " ").title()

    spec = MarketSpec(
        slug=slug,
        subdivision_name=subdivision,
        country=profile.country_name,
        country_code=country_code,
        profile=profile,
    )

    # US-specific enrichment. Skipped entirely on the generic path,
    # including for a US market run with explicit levels.
    if profile.reference_strategy == REFERENCE_US_CENSUS:
        entry = US_STATES.get(subdivision)

        if entry:
            spec.state_fips, usps = entry
            spec.iso_subdivision = f"US-{usps}"
        else:
            log.warn(
                f"{subdivision!r} is not a recognised US state name.",
                "Population lookup will be skipped. Pass "
                "--iso-subdivision if the boundary lookup also fails.",
            )

    return spec


def extract(
    spec: MarketSpec,
    fetcher: Fetcher,
    log: RunLog,
    *,
    research_date: str,
    relation_id_override: Optional[int],
    census_key: Optional[str],
) -> Optional[dict[str, Any]]:
    profile = spec.profile

    if profile.notes:
        log.info(f"{spec.country_code}: {profile.notes}")

    log.info(
        f"Admin levels: boundary {profile.boundary_level}, children "
        f"{profile.child_level}. Reference strategy: "
        f"{profile.reference_strategy}."
    )

    # --- Reference data first -----------------------------------
    #
    # Loading this before touching Overpass means a Gazetteer failure
    # is reported before twenty Overpass requests are spent.
    #
    # Counties only. There is no boundary-level lookup because the
    # market boundary zone does not take a representative point.

    gazetteer: dict[str, GazetteerRecord] = {}
    populations: dict[str, int] = {}

    if profile.reference_strategy == REFERENCE_US_CENSUS:
        gazetteer = load_county_gazetteer(fetcher, log)

        if spec.state_fips:
            populations = fetch_populations(
                fetcher, log, spec.state_fips, census_key
            )
    else:
        log.info(
            "Generic reference path: representative points from OSM "
            "admin_centre nodes, population from OSM population tags "
            "where present.",
            "Both are weaker than a national census layer and are "
            "recorded at their real authority tier. Where either is "
            "absent the field is null and the zone carries a "
            "verification requirement.",
        )

    # --- Boundary ------------------------------------------------

    if relation_id_override is not None:
        boundary = {
            "id": relation_id_override,
            "tags": {"name": spec.subdivision_name},
        }

        log.info(
            f"Using supplied relation ID {relation_id_override} "
            "without lookup."
        )
    else:
        boundary = find_boundary(
            fetcher,
            log,
            name=spec.subdivision_name,
            country_code=spec.country_code,
            iso_subdivision=spec.iso_subdivision,
            admin_level=profile.boundary_level,
        )

    if boundary is None:
        return None

    boundary_relation_id = boundary.get("id")

    context = ZoneContext(
        country_code=spec.country_code,
        reference_strategy=profile.reference_strategy,
        research_date=research_date,
        gazetteer=gazetteer,
        populations=populations,
    )

    boundary_zone = build_zone(
        boundary,
        zone_type=profile.boundary_zone_type,
        parent_zone_id=None,
        ancestor_zone_ids=[],
        context=context,
        geoid_override=spec.state_fips,
        log=log,
        is_market_boundary=True,
    )

    if boundary_zone is None:
        return None

    # A readable official name for the boundary tier. Only applied for
    # the two types where the phrasing is idiomatic; "District of
    # Bavaria" would be worse than the plain name.
    if profile.boundary_zone_type == "state":
        boundary_zone["official_name"] = (
            f"State of {spec.subdivision_name}"
        )
    elif profile.boundary_zone_type == "country":
        boundary_zone["official_name"] = boundary_zone["display_name"]

    boundary_zone_id = boundary_zone["id"]

    # --- Children ------------------------------------------------

    want_centres = profile.reference_strategy != REFERENCE_US_CENSUS

    children = fetch_children(
        fetcher,
        log,
        parent_relation_id=boundary_relation_id,
        admin_level=profile.child_level,
        country_code=spec.country_code,
        want_admin_centre=False,
    )

    # Overpass returns relations and, on the centres query, nodes. Keep
    # only relations here; admin centres are fetched separately so the
    # two concerns stay legible.
    children = [
        element
        for element in children
        if element.get("type") == "relation"
    ]

    if want_centres and children:
        context.admin_centres = fetch_admin_centres(
            fetcher,
            log,
            [
                element["id"]
                for element in children
                if isinstance(element.get("id"), int)
            ],
        )

    # A name-to-GEOID index restricted to this state, used only when
    # OSM carries no FIPS tag. Restricting it means a Franklin County
    # in Vermont cannot match a Franklin County in Ohio.
    name_index: dict[str, str] = {}

    if spec.state_fips:
        for geoid, record in gazetteer.items():
            if geoid.startswith(spec.state_fips):
                name_index[record.name.strip().lower()] = geoid

    zones = [boundary_zone]
    seen: dict[str, str] = {boundary_zone_id: "boundary"}
    skipped_outside = 0

    for element in sorted(
        children,
        key=lambda item: str((item.get("tags") or {}).get("name", "")),
    ):
        tags = element.get("tags") or {}
        name = str(tags.get("name", "")).strip()

        fallback = (
            extract_fips(tags) or name_index.get(name.lower())
            if context.is_us_census
            else None
        )

        # Overpass area matching returns relations that INTERSECT the
        # parent area, not only those contained by it. A county that
        # shares a boundary line with a neighbouring state can
        # therefore slip in.
        #
        # Colorado is the case that found this: it borders a San Juan
        # County in both New Mexico and Utah, so a run returned 65
        # counties for a state that has 64, with a duplicate zone ID
        # and one population that would not join.
        #
        # Filtering on the state FIPS prefix is exact, because a county
        # GEOID is its state FIPS followed by a three-digit county
        # code. No name matching is involved.
        #
        # THE GENERIC PATH HAS NO EQUIVALENT FILTER. There is no
        # worldwide identifier with a containment property, so a
        # generic run may include a neighbouring district that shares a
        # boundary line. The count is reported at the end of the run so
        # a discrepancy is visible rather than silent.
        if spec.state_fips and fallback:
            if not fallback.startswith(spec.state_fips):
                skipped_outside += 1

                log.info(
                    f"Skipped {name} (GEOID {fallback}), which "
                    "borders this market but lies outside it."
                )
                continue

        zone = build_zone(
            element,
            zone_type=profile.child_zone_type,
            parent_zone_id=boundary_zone_id,
            ancestor_zone_ids=[boundary_zone_id],
            context=context,
            geoid_override=fallback,
            log=log,
        )

        if zone is None:
            continue

        # A duplicate derived ID is rare but real. Reporting it beats
        # silently emitting one and losing the other, which is exactly
        # how a county went missing from a hand-written pass.
        if zone["id"] in seen:
            log.error(
                f"Duplicate zone ID {zone['id']} for "
                f"{zone['display_name']}. Both kept, one suffixed. "
                "Rename deliberately."
            )

            zone["id"] = f"{zone['id']}-{element.get('id')}"

        seen[zone["id"]] = zone["display_name"]
        zones.append(zone)

    log.info(
        f"Extracted {len(zones)} zones: 1 "
        f"{profile.boundary_zone_type} and {len(zones) - 1} "
        f"{profile.child_zone_type} records."
    )

    if not context.is_us_census and len(zones) > 1:
        log.warn(
            f"No containment filter is available for "
            f"{spec.country_code}, so a neighbouring "
            f"{profile.child_zone_type} sharing a boundary line may "
            "be included.",
            f"Overpass area matching returns relations that intersect "
            f"the parent, not only those inside it. Check that "
            f"{len(zones) - 1} matches the number of "
            f"{profile.child_zone_type} records "
            f"{spec.subdivision_name} actually has. The US path "
            "filters this exactly on GEOID prefix; nothing equivalent "
            "exists worldwide.",
        )

    with_points = sum(
        1
        for zone in zones[1:]
        if zone["center"]["lat"] is not None
    )

    with_population = sum(
        1
        for zone in zones[1:]
        if zone["population_context"]["population"] is not None
    )

    return {
        "extractor_version": EXTRACTOR_VERSION,
        "extracted_at": research_date,
        "market_slug": spec.slug,
        "country": spec.country,
        "country_code": spec.country_code,
        "osm_boundary_relation_id": boundary_relation_id,
        "admin_levels_used": {
            "boundary": profile.boundary_level,
            "child": profile.child_level,
        },
        "reference_strategy": profile.reference_strategy,
        "geography_model_fragment": {
            "market_boundary_zone_id": boundary_zone_id,
            "primary_administrative_zone_ids": [
                zone["id"] for zone in zones[1:]
            ],
        },
        "zones": zones,
        "sources": build_sources(
            research_date,
            include_gazetteer=bool(gazetteer),
            include_census_population=bool(populations),
            include_admin_centre=bool(context.admin_centres),
            include_osm_population=with_population > 0
            and not context.is_us_census,
            boundary_relation_id=boundary_relation_id,
        ),
        "handoff": {
            "fields_left_null": [
                "market_inclusion.status",
                "market_inclusion.production_use",
                "transportation_relevance.*",
                "access_characteristics.*",
                "jurisdiction_id",
            ],
            "reason": (
                "These are judgements about a transport market, not "
                "facts about administrative geography. No map "
                "database holds them."
            ),
            "deliberate_omissions": [
                "The market boundary zone has no representative "
                "point. It defines extent and anchors the hierarchy; "
                "containment comes from the polygon. Do not add one."
            ],
            "quality_notes": (
                [
                    "United States reference path: representative "
                    "points are Census Gazetteer internal points and "
                    "population is the 2020 decennial count. Both "
                    "tier 1. Children were filtered on GEOID prefix, "
                    "which is exact.",
                    f"{skipped_outside} bordering record(s) were "
                    "excluded by that filter."
                    if skipped_outside
                    else "No bordering records needed excluding.",
                ]
                if context.is_us_census
                else [
                    "Generic reference path. No national census layer "
                    "exists for this country in this extractor.",
                    f"Representative points: {with_points} of "
                    f"{len(zones) - 1} zones have one, taken from OSM "
                    "admin_centre member nodes. The rest are null.",
                    f"Population: {with_population} of "
                    f"{len(zones) - 1} zones have one, from OSM "
                    "population tags. Tier 3, usually undated, and "
                    "must be replaced before publication.",
                    "No containment filter was applied, because no "
                    "worldwide identifier supports one. Verify the "
                    "child count against an official list.",
                ]
            ),
            "next_step": (
                "Pass this file to the Section 02 research prompt as "
                "supplied geography. The model completes the "
                "judgement fields, adds resort, metro and catchment "
                "zones, and researches barriers. It must not alter "
                "names, coordinates, identifiers or hierarchy."
            ),
            "strip_before_merge": ["_extraction"],
        },
    }


# ============================================================
# PROBE OUTPUT
# ============================================================

def print_probe(country_code: str, results: dict[int, list[str]]) -> None:
    """
    Render a probe result as something a person can read in thirty
    seconds and act on.
    """
    print()
    print("=" * 64)
    print(f"ADMIN LEVELS IN {country_code}")
    print("=" * 64)
    print()

    profile = COUNTRY_PROFILES.get(country_code)

    if profile is not None:
        print(
            f"This country already has a verified profile: boundary "
            f"level {profile.boundary_level}, children level "
            f"{profile.child_level}."
        )
        print(
            f"  {profile.boundary_zone_type} -> "
            f"{profile.child_zone_type}"
        )
        print()

    any_found = False

    for level in PROBE_LEVELS:
        names = results.get(level, [])

        if not names:
            print(f"  level {level}:  none")
            continue

        any_found = True

        examples = ", ".join(names[:3])

        if len(names) > 3:
            examples += ", ..."

        print(f"  level {level}:  {len(names):>5}   {examples}")

    print()

    if not any_found:
        print(
            "Nothing found at any level. Either the ISO 3166-1 code "
            "is wrong,\nor Overpass was unreachable. Check the run "
            "log above."
        )
        print()
        return

    print("-" * 64)
    print()
    print("HOW TO READ THIS")
    print()
    print(
        "  Level 2 is the country itself. One relation, always.\n"
        "\n"
        "  The level with a count matching the country's first-order\n"
        "  subdivisions is usually the boundary level: states,\n"
        "  provinces, regions.\n"
        "\n"
        "  The next level down holding the tier you want to research\n"
        "  is the child level: counties, districts, municipalities.\n"
        "\n"
        "  A country whose counties sit at level 4 has NO subdivision\n"
        "  above them, so its boundary level is 2, the country\n"
        "  itself. Kenya is the standard example.\n"
    )
    print("-" * 64)
    print()
    print("THEN RUN")
    print()
    print(
        f"  --market {country_code.lower()}-<subdivision> \\\n"
        f"      --boundary-level N --child-level M --dry-run"
    )
    print()
    print(
        "Once the counts look right, add the country to\n"
        "COUNTRY_PROFILES in this file so nobody probes it twice."
    )
    print()


# ============================================================
# MAIN
# ============================================================

def load_dotenv(path: Path = Path(".env")) -> None:
    """
    Minimal .env reader, so a Census key can live in a gitignored file
    rather than in source or in shell history.

    An existing environment variable wins, so a value set deliberately
    in the shell is never silently overridden by a stale file.
    """
    if not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Extract administrative zones for a market pack Section "
            "02 file. Identity and hierarchy come from OpenStreetMap. "
            "United States markets use Census Gazetteer internal "
            "points and decennial population; everywhere else uses "
            "OSM admin_centre nodes and population tags, cited at "
            "their real authority tier. Judgement fields are left "
            "null for a research pass to complete."
        )
    )

    parser.add_argument(
        "--market",
        help="Market slug, for example us-vermont or ke-nairobi.",
    )

    parser.add_argument(
        "--probe",
        metavar="CC",
        help=(
            "ISO 3166-1 alpha-2 country code. Report how many "
            "administrative relations exist at each admin level, with "
            "examples, then exit. Writes nothing. Use this before "
            "running a country that has no verified profile."
        ),
    )

    parser.add_argument(
        "--list-countries",
        action="store_true",
        help="List verified country profiles and exit.",
    )

    parser.add_argument(
        "--boundary-level",
        type=int,
        default=None,
        help=(
            "OSM admin_level of the market boundary. Required for a "
            "country with no verified profile. Must be given together "
            "with --child-level."
        ),
    )

    parser.add_argument(
        "--child-level",
        type=int,
        default=None,
        help=(
            "OSM admin_level of the zones beneath the boundary. Must "
            "be numerically higher than --boundary-level, because a "
            "higher level is a smaller area."
        ),
    )

    parser.add_argument(
        "--boundary-zone-type",
        default=None,
        help=(
            "Section 02 zone_type for the boundary, for example "
            "state or country. Defaults from the profile."
        ),
    )

    parser.add_argument(
        "--child-zone-type",
        default=None,
        help=(
            "Section 02 zone_type for the children, for example "
            "county or district. Defaults from the profile."
        ),
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file. Omit with --dry-run.",
    )

    parser.add_argument(
        "--census-key",
        default=None,
        help=(
            "Census API key for US population. Falls back to "
            "CENSUS_API_KEY in the environment or a .env file. Free "
            f"from {CENSUS_KEY_SIGNUP_URL}. Ignored outside the "
            "United States."
        ),
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/osm"),
        help="Where fetched responses are cached.",
    )

    parser.add_argument(
        "--relation-id",
        type=int,
        default=None,
        help=(
            "Skip boundary lookup and use this OSM relation ID. Use "
            "when a name is ambiguous or spelled differently in OSM."
        ),
    )

    parser.add_argument(
        "--iso-subdivision",
        default=None,
        help=(
            "ISO 3166-2 code, for example US-VT. Derived "
            "automatically for US states; supply it elsewhere when a "
            "name search is ambiguous."
        ),
    )

    parser.add_argument(
        "--research-date",
        default=date.today().isoformat(),
        help="Value written to last_checked fields.",
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use only cached responses. Fails on a cache miss.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a summary instead of writing a file.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="List every log entry rather than collapsing repeats.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"osm_zone_extractor {EXTRACTOR_VERSION}",
    )

    args = parser.parse_args()

    log = RunLog()

    # --- List countries -----------------------------------------

    if args.list_countries:
        print()
        print("=" * 64)
        print("VERIFIED COUNTRY PROFILES")
        print("=" * 64)
        print()
        print(
            "Each entry was confirmed by someone who ran --probe and "
            "read the\nresult. Nothing here is inferred from a "
            "neighbouring country."
        )
        print()

        for code in sorted(COUNTRY_PROFILES):
            profile = COUNTRY_PROFILES[code]

            print(
                f"  {code}  {profile.country_name:<20} "
                f"level {profile.boundary_level} "
                f"{profile.boundary_zone_type} -> "
                f"level {profile.child_level} "
                f"{profile.child_zone_type}"
            )

            if profile.reference_strategy == REFERENCE_US_CENSUS:
                print(
                    "      Census Gazetteer points, decennial "
                    "population, exact child filter."
                )

            if profile.notes:
                for line in _wrap(profile.notes, 58):
                    print(f"      {line}")

            print()

        print(
            "Any other country runs with --boundary-level and "
            "--child-level.\nUse --probe CC first to find them."
        )
        print()

        return 0

    # --- Probe --------------------------------------------------

    if args.probe:
        country_code = args.probe.strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", country_code):
            print(
                f"ERROR: --probe expects an ISO 3166-1 alpha-2 "
                f"country code, got {args.probe!r}."
            )
            return 1

        fetcher = Fetcher(args.cache_dir, log, offline=args.offline)

        print(f"Probing admin levels in {country_code} ...")
        print()
        print(
            "This runs one Overpass query per level, spaced politely. "
            "It takes\nabout half a minute and is cached afterwards."
        )
        print()

        results = probe_country(fetcher, log, country_code)

        print("Run log:")
        log.print(verbose=args.verbose)

        print_probe(country_code, results)

        return 0

    # --- Extract ------------------------------------------------

    if not args.market:
        print(
            "ERROR: --market is required, unless using --probe or "
            "--list-countries."
        )
        return 1

    spec = parse_market_slug(
        args.market,
        log,
        boundary_level=args.boundary_level,
        child_level=args.child_level,
        boundary_zone_type=args.boundary_zone_type,
        child_zone_type=args.child_zone_type,
    )

    if spec is None:
        log.print(verbose=True)
        return 1

    if args.iso_subdivision:
        spec.iso_subdivision = args.iso_subdivision

    census_key = args.census_key or os.environ.get("CENSUS_API_KEY")

    fetcher = Fetcher(args.cache_dir, log, offline=args.offline)

    print(f"Extracting {spec.slug} ...")
    print(
        f"  {spec.country}, admin levels "
        f"{spec.profile.boundary_level}/{spec.profile.child_level}, "
        f"{spec.profile.reference_strategy} reference path."
    )
    print()

    result = extract(
        spec,
        fetcher,
        log,
        research_date=args.research_date,
        relation_id_override=args.relation_id,
        census_key=census_key,
    )

    print("Run log:")
    log.print(verbose=args.verbose)
    print()

    if result is None:
        print("Extraction failed. Nothing written.")
        return 2

    zones = result["zones"]

    # The market boundary zone is excluded from these counts. It has no
    # representative point and no population by design, and reporting a
    # deliberate decision as "missing" would be a defect in the report
    # rather than in the data.
    localities = [
        zone for zone in zones
        if not zone["_extraction"]["is_market_boundary"]
    ]

    no_centre = [
        zone["display_name"]
        for zone in localities
        if zone["center"]["lat"] is None
    ]

    no_population = [
        zone["display_name"]
        for zone in localities
        if zone["population_context"]["population"] is None
    ]

    print("Summary:")
    print(f"  Zones extracted:       {len(zones)}")
    print(f"  Missing point:         {len(no_centre)}")
    print(f"  Missing population:    {len(no_population)}")

    if spec.profile.reference_strategy == REFERENCE_US_CENSUS:
        no_geoid = [
            zone["display_name"]
            for zone in localities
            if zone["_extraction"]["census_geoid"] is None
        ]
        print(f"  Missing GEOID:         {len(no_geoid)}")

    print(f"  Errors:                {log.error_count}")
    print(f"  Warnings:              {log.warning_count}")
    print()

    if no_centre:
        print("  Without a representative point:")

        for name in no_centre[:10]:
            print(f"    {name}")

        if len(no_centre) > 10:
            print(f"    ... and {len(no_centre) - 10} more")

        print()

    if args.dry_run:
        print("First five zones:")
        print()

        for zone in zones[:5]:
            centre = zone["center"]
            extraction = zone["_extraction"]

            print(f"  {zone['id']}")
            print(f"    name:       {zone['display_name']}")
            print(f"    type:       {zone['zone_type']}")

            if extraction["is_market_boundary"]:
                print(
                    "    point:      none, by design "
                    "(anchors the hierarchy)"
                )
            elif centre["lat"] is not None:
                basis = extraction["centre_basis"] or "unknown"
                print(
                    f"    point:      {centre['lat']}, "
                    f"{centre['lon']}  ({basis})"
                )
            else:
                print("    point:      none, no source match")

            if extraction["census_geoid"]:
                print(f"    geoid:      {extraction['census_geoid']}")

            print(
                "    verified:   "
                f"{zone['research']['verification_status']}"
            )

            if not extraction["is_market_boundary"]:
                population = zone["population_context"]["population"]
                year = zone["population_context"]["population_year"]

                print(
                    "    population: "
                    + (
                        f"{population}"
                        + (f" ({year})" if year else " (undated)")
                        if population is not None
                        else "none"
                    )
                )

            print()

        print("Quality notes:")
        print()

        for note in result["handoff"]["quality_notes"]:
            for line in _wrap(note, 66):
                print(f"  {line}")
            print()

        print("Dry run, nothing written.")
        return 0

    if args.out is None:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)

    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Written: {args.out}")
    print()
    print(
        "Next: pass this to the Section 02 research prompt as "
        "supplied geography. Judgement fields are null and the file "
        "will not validate until they are completed."
    )

    return 0


def _wrap(text: str, width: int) -> list[str]:
    """
    Minimal word wrap. Avoids importing textwrap for four lines of
    output formatting.
    """
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    length = 0

    for word in words:
        if current and length + 1 + len(word) > width:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += (1 if length else 0) + len(word)

    if current:
        lines.append(" ".join(current))

    return lines


if __name__ == "__main__":
    raise SystemExit(main())