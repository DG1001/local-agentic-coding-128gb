"""Umrechnung zwischen Einheiten.

Alle bekannten Einheiten liegen in einem modulweiten Verzeichnis. Jede Einheit
gehoert zu einer Basisgroesse und hat einen Faktor, der angibt, wieviele
Basiseinheiten sie ausmacht.
"""

from decimal import Decimal

_VERZEICHNIS: dict[str, tuple[str, Decimal]] = {}


class WandlerFehler(Exception):
    """Basisklasse fuer Fehler dieses Moduls."""


class UnbekannteEinheit(WandlerFehler):
    """Die Einheit ist nicht registriert."""


class UnpassendeBasis(WandlerFehler):
    """Die beiden Einheiten gehoeren zu verschiedenen Basisgroessen."""


def registriere(name: str, basis: str, faktor: Decimal | str | int) -> None:
    """Traegt eine Einheit ein.

    name    Kurzzeichen, etwa "km"
    basis   Basisgroesse, etwa "laenge"
    faktor  wieviele Basiseinheiten eine Einheit ausmacht
    """
    faktor = Decimal(str(faktor))
    if faktor <= 0:
        raise WandlerFehler("faktor muss positiv sein")
    _VERZEICHNIS[name] = (basis, faktor)


def wandle(wert: Decimal | str | int, von: str, nach: str) -> Decimal:
    """Rechnet einen Wert von einer Einheit in eine andere um."""
    for name in (von, nach):
        if name not in _VERZEICHNIS:
            raise UnbekannteEinheit(name)
    basis_von, faktor_von = _VERZEICHNIS[von]
    basis_nach, faktor_nach = _VERZEICHNIS[nach]
    if basis_von != basis_nach:
        raise UnpassendeBasis(f"{von} ist {basis_von}, {nach} ist {basis_nach}")
    return Decimal(str(wert)) * faktor_von / faktor_nach


def einheiten() -> list[str]:
    """Alle registrierten Kurzzeichen, alphabetisch."""
    return sorted(_VERZEICHNIS)


def leeren() -> None:
    """Wirft alle Eintraege weg. Nur fuer Tests gedacht."""
    _VERZEICHNIS.clear()
