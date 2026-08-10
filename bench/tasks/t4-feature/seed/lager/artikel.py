"""Datentypen des Lagers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Artikel:
    """Ein Artikel im Lager.

    nummer  eindeutige Artikelnummer
    name    Bezeichnung
    menge   tatsaechlich vorhandene Stueckzahl
    """

    nummer: str
    name: str
    menge: int = 0

    def __post_init__(self) -> None:
        if not self.nummer:
            raise ValueError("nummer darf nicht leer sein")
        if self.menge < 0:
            raise ValueError("menge darf nicht negativ sein")


class LagerFehler(Exception):
    """Basisklasse fuer Fehler des Lagers."""


class UnbekannterArtikel(LagerFehler):
    """Die Artikelnummer ist nicht bekannt."""


class ZuWenigBestand(LagerFehler):
    """Es ist nicht genug vorhanden."""
