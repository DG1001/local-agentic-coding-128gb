"""Traegt die mitgelieferten Einheiten ein.

Wird beim Import von wandler ausgefuehrt, damit die ueblichen Einheiten ohne
Zutun bereitstehen.
"""

from .einheiten import registriere

MITGELIEFERT = {
    "laenge": {"mm": "0.001", "cm": "0.01", "m": "1", "km": "1000"},
    "masse": {"mg": "0.000001", "g": "0.001", "kg": "1", "t": "1000"},
    "zeit": {"s": "1", "min": "60", "h": "3600", "d": "86400"},
}


def eintragen() -> None:
    """Traegt alle mitgelieferten Einheiten ein."""
    for basis, einheiten in MITGELIEFERT.items():
        for name, faktor in einheiten.items():
            registriere(name, basis, faktor)
