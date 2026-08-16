"""Fachliche Vorgaenge auf dem Lagerbestand."""

from pathlib import Path

from .artikel import Artikel, UnbekannterArtikel, ZuWenigBestand
from .speicher import laden, sichern


class Lager:
    """Haelt den Bestand und schreibt ihn bei jeder Aenderung fort."""

    def __init__(self, pfad: Path) -> None:
        self.pfad = pfad
        self.artikel = laden(pfad)

    def _hole(self, nummer: str) -> Artikel:
        if nummer not in self.artikel:
            raise UnbekannterArtikel(nummer)
        return self.artikel[nummer]

    def anlegen(self, nummer: str, name: str, menge: int = 0) -> Artikel:
        """Legt einen neuen Artikel an."""
        a = Artikel(nummer=nummer, name=name, menge=menge)
        self.artikel[nummer] = a
        sichern(self.pfad, self.artikel)
        return a

    def einlagern(self, nummer: str, menge: int) -> Artikel:
        """Erhoeht den Bestand."""
        if menge <= 0:
            raise ValueError("menge muss positiv sein")
        alt = self._hole(nummer)
        neu = Artikel(alt.nummer, alt.name, alt.menge + menge)
        self.artikel[nummer] = neu
        sichern(self.pfad, self.artikel)
        return neu

    def auslagern(self, nummer: str, menge: int) -> Artikel:
        """Verringert den Bestand."""
        if menge <= 0:
            raise ValueError("menge muss positiv sein")
        alt = self._hole(nummer)
        if alt.menge < menge:
            raise ZuWenigBestand(f"{nummer}: {alt.menge} vorhanden, {menge} angefordert")
        neu = Artikel(alt.nummer, alt.name, alt.menge - menge)
        self.artikel[nummer] = neu
        sichern(self.pfad, self.artikel)
        return neu

    def bestand(self, nummer: str) -> int:
        """Tatsaechlich vorhandene Stueckzahl."""
        return self._hole(nummer).menge

    def liste(self) -> list[Artikel]:
        """Alle Artikel, nach Nummer sortiert."""
        return [self.artikel[n] for n in sorted(self.artikel)]
