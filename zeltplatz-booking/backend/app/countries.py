"""ISO 3166-1 alpha-2 countries commonly used for nationality dropdown."""

from __future__ import annotations

COUNTRIES: list[dict[str, str]] = [
    {"code": "AT", "name": "Österreich"},
    {"code": "DE", "name": "Deutschland"},
    {"code": "CH", "name": "Schweiz"},
    {"code": "IT", "name": "Italien"},
    {"code": "SI", "name": "Slowenien"},
    {"code": "HU", "name": "Ungarn"},
    {"code": "CZ", "name": "Tschechien"},
    {"code": "SK", "name": "Slowakei"},
    {"code": "PL", "name": "Polen"},
    {"code": "HR", "name": "Kroatien"},
    {"code": "LI", "name": "Liechtenstein"},
    {"code": "FR", "name": "Frankreich"},
    {"code": "BE", "name": "Belgien"},
    {"code": "NL", "name": "Niederlande"},
    {"code": "LU", "name": "Luxemburg"},
    {"code": "GB", "name": "Vereinigtes Königreich"},
    {"code": "IE", "name": "Irland"},
    {"code": "ES", "name": "Spanien"},
    {"code": "PT", "name": "Portugal"},
    {"code": "US", "name": "Vereinigte Staaten"},
    {"code": "CA", "name": "Kanada"},
    {"code": "AU", "name": "Australien"},
    {"code": "NZ", "name": "Neuseeland"},
    {"code": "SE", "name": "Schweden"},
    {"code": "NO", "name": "Norwegen"},
    {"code": "DK", "name": "Dänemark"},
    {"code": "FI", "name": "Finnland"},
    {"code": "IS", "name": "Island"},
    {"code": "RO", "name": "Rumänien"},
    {"code": "BG", "name": "Bulgarien"},
    {"code": "GR", "name": "Griechenland"},
    {"code": "TR", "name": "Türkei"},
    {"code": "UA", "name": "Ukraine"},
    {"code": "RS", "name": "Serbien"},
    {"code": "BA", "name": "Bosnien und Herzegowina"},
    {"code": "ME", "name": "Montenegro"},
    {"code": "MK", "name": "Nordmazedonien"},
    {"code": "AL", "name": "Albanien"},
    {"code": "XK", "name": "Kosovo"},
    {"code": "XX", "name": "Andere"},
]

# "OTHER" is not ISO; keep for practicality. Validate against this list.
VALID_NATIONALITY_CODES = {c["code"] for c in COUNTRIES}
