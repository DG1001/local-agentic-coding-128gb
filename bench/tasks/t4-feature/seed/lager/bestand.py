"""Fachliche Vorgaenge auf dem Lagerbestand."""

from pathlib import Path


from .artikel import Artikel, UnbekannterArtikel, ZuWenigBestand, UnbekannteReservierung
from .speicher import laden, sichern


Reservierungsschluessel = tuple[str, str]  # (artikel_nummer, auftrag)


class Lager:
    """Haelt den Bestand und schreibt ihn bei jeder Aenderung fort."""

    def __init__(self, pfad: Path) -> None:
        self.pfad = pfad
        self.artikel, self._reservierungen = laden(pfad)

    def _hole(self, nummer: str) -> Artikel:
        if nummer not in self.artikel:
            raise UnbekannterArtikel(nummer)
        return self.artikel[nummer]

    def _speichere(self) -> None:
        sichern(self.pfad, self.artikel, self._reservierungen)

    def anlegen(self, nummer: str, name: str, menge: int = 0) -> Artikel:
        """Legt neuen Artikel an."""
        a = Artikel(nummer=nummer, name=name, menge=menge)
        self.artikel[nummer] = a
        self._speichere()
        return a

    def einlagern(self, nummer: str, menge: int) -> Artikel:
        """Erhoeht den Bestand."""
        if menge <= 0:
            raise ValueError("menge muss positiv sein")
        alt = self._hole(nummer)
        neu = Artikel(alt.nummer, alt.name, alt.menge + menge)
        self.artikel[nummer] = neu
        self._speichere()
        return neu

    def auslagern(self, nummer: str, menge: int) -> Artikel:
        """Verringert den Bestand."""
        if menge <= 0:
            raise ValueError("menge muss positiv sein")
        alt = self._hole(nummer)
        if self.verfuegbar(nummer) < menge:
            raise ZuWenigBestand(f"{nummer}: {alt.menge} vorhanden, {menge} angefordert")
        neu = Artikel(alt.nummer, alt.name, alt.menge - menge)
        self.artikel[nummer] = neu
        self._speichere()
        return neu

    def bestand(self, nummer: str) -> int:
        """Tatsaechlich vorhandene Stueckzahl."""
        return self._hole(nummer).menge

    def reservieren(self, nummer: str, menge: int, auftrag: str) -> int:
        """Hält menge Stueck fuer auftrag fest und gibt neue verfuegbare Menge zurueck."""
        if menge <= 0:
            raise ValueError("menge muss positiv sein")
        verfuegbar = self.verfuegbar(nummer)
        if menge > verfuegbar:
            raise ZuWenigBestand(
                f"{nummer}: nur {verfuegbar} verfuegbar, {menge} angefordert"
            )
        key: Reservierungsschluessel = (nummer, auftrag)
        # Bereits vorhandene Reservierung dieses Auftrags addieren sich
        alt_menge = self._reservierungen.get(key, 0)
        self._reservierungen[key] = alt_menge + menge
        self._speichere()
        return self.verfuegbar(nummer)

    def freigeben(self, nummer: str, auftrag: str) -> int:
        """Löst die Reservierung dieses Auftrags auf und gibt neue verfuegbare Menge zurueck."""
        key: Reservierungsschluessel = (nummer, auftrag)
        if key not in self._reservierungen:
            raise UnbekannteReservierung(f"Auftrag {auftrag} hat keine Reservierung für {nummer}")
        menge = self._reservierungen[key]
        del self._reservierungen[key]
        self._speichere()
        return self.verfuegbar(nummer)

    def entnehmen(self, nummer: str, auftrag: str) -> int:
        """Bucht die reservierte Menge tatsächlich aus: Bestand sinkt, Reservierung verschwindet."""
        key: Reservierungsschluessel = (nummer, auftrag)
        if key not in self._reservierungen:
            raise UnbekannteReservierung(f"Auftrag {auftrag} hat keine Reservierung für {nummer}")
        menge = self._reservierungen[key]
        # Reservierung loeschen
        del self._reservierungen[key]
        # Bestand verringern
        artikel = self._hole(nummer)
        if artikel.menge < menge:
            raise ZuWenigBestand(
                f"{nummer}: nur {artikel.menge} vorhanden, {menge} zu entnehmen"
            )
        neu = Artikel(artikel.nummer, artikel.name, artikel.menge - menge)
        self.artikel[nummer] = neu
        self._speichere()
        return neu.menge

    def reserviert(self, nummer: str) -> int:
        """Liefert die Summe aller Reservierungen des Artikels."""
        return sum(
            m for (n, _), m in self._reservierungen.items() if n == nummer
        )

    def verfuegbar(self, nummer: str) -> int:
        """Liefert bestand minus reserviert."""
        return self.bestand(nummer) - self.reserviert(nummer)

    def reservierungen(self, nummer: str) -> dict[str, int]:
        """Liefert Abbildung Auftrag -> Menge (Kopie)."""
        return {
            auftrag: menge
            for (n, auftrag), menge in self._reservierungen.items()
            if n == nummer
        }

    def liste(self) -> list[Artikel]:
        """Alle Artikel, nach Nummer sortiert."""
        return [self.artikel[n] for n in sorted(self.artikel)]
