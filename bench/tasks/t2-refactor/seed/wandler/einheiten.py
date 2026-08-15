"""Umrechnung zwischen Einheiten.

Alle bekannten Einheiten liegen in einem modulweiten Verzeichnis. Jede Einheit
gehoert zu einer Basisgroesse und hat einen Faktor, der angibt, wieviele
Basiseinheiten sie ausmacht.
"""

from decimal import Decimal


class Register:
    """Verwaltet einen eigenen Satz registrierter Einheiten."""

    def __init__(self) -> None:
        self._verzeichnis: dict[str, tuple[str, Decimal]] = {}

    def registriere(self, name: str, basis: str, faktor: Decimal | str | int) -> None:
        """Traegt eine Einheit in dieses Register ein.

        name     Kurzzeichen, etwa "km"
        basis    Basisgroesse, etwa "laenge"
        faktor   wieviele Basiseinheiten eine Einheit ausmacht
        """
        faktor = Decimal(str(faktor))
        if faktor <= 0:
            raise WandlerFehler("faktor muss positiv sein")
        self._verzeichnis[name] = (basis, faktor)

    def wandle(self, wert: Decimal | str | int, von: str, nach: str) -> Decimal:
        """Rechnet einen Wert von einer Einheit in eine andere um."""
        for name in (von, nach):
            if name not in self._verzeichnis:
                raise UnbekannteEinheit(name)
        basis_von, faktor_von = self._verzeichnis[von]
        basis_nach, faktor_nach = self._verzeichnis[nach]
        if basis_von != basis_nach:
            raise UnpassendeBasis(f"{von} ist {basis_von}, {nach} ist {basis_nach}")
        return Decimal(str(wert)) * faktor_von / faktor_nach

    def einheiten(self) -> list[str]:
        """Alle registrierten Kurzzeichen, alphabetisch."""
        return sorted(self._verzeichnis)

    def kopie(self) -> "Register":
        """Liefert ein neues Register mit demselben Inhalt, das sich spaeter unabhaengig weiterentwickelt."""
        neues = Register()
        neues._verzeichnis = self._verzeichnis.copy()
        return neues


class WandlerFehler(Exception):
    """Basisklasse fuer Fehler dieses Moduls."""


class UnbekannteEinheit(WandlerFehler):
    """Die Einheit ist nicht registriert."""


class UnpassendeBasis(WandlerFehler):
    """Die beiden Einheiten gehoeren zu verschiedenen Basisgroßen."""


# Standard-Register: wird befüllt, wenn wandler importiert wird
_STANDARD: Register = Register()


def _init_standard() -> None:
    """Traegt die mitgelieferten Einheiten in STANDARD ein."""
    from .basis import MITGELIEFERT  # lazy import, um Kreislauf zu vermeiden

    for basis, einheiten in MITGELIEFERT.items():
        for name, faktor in einheiten.items():
            _STANDARD.registriere(name, basis, faktor)


_init_standard()


def registriere(name: str, basis: str, faktor: Decimal | str | int) -> None:
    """Traegte eine Einheit in das Standard-Register ein.

    Bleibt fuer Rueckwaertskompatibilitaet erhalten.
    """
    _STANDARD.registriere(name, basis, faktor)


def wandle(wert: Decimal | str | int, von: str, nach: str) -> Decimal:
    """Rechnet einen Wert von einer Einheit in die andere um.

    Bleibt fuer Rueckwaertskompatibilitaet erhalten und arbeitet auf STANDARD."""
    return _STANDARD.wandle(wert, von, nach)


def einheiten() -> list[str]:
    """Liefert die bekannten Einheiten aus dem Standard-Register.

    Bleibt fuer Rueckwaertskompatibilitaet erhalten."""
    return _STANDARD.einheiten()


def leeren() -> None:
    """Wirft alle Eintraege weg. Nur fuer Tests gedacht."""
    _STANDARD._verzeichnis.clear()
