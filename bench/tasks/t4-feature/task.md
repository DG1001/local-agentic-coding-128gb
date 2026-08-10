Das Lager soll Reservierungen bekommen. Der Vertrieb will Ware fuer einen
Auftrag festhalten koennen, bevor sie tatsaechlich das Haus verlaesst.

Reservierte Ware liegt weiterhin im Lager, darf aber von niemand anderem mehr
zugesagt werden. Die Erweiterung zieht sich durch alle Schichten: Datentyp,
Ablage, Fachlogik und Kommandozeile.

Die Namen und Signaturen unten sind verbindlich, es gibt eine externe Testsuite.

BEGRIFFE

    bestand     tatsaechlich im Lager liegende Stueckzahl
    reserviert  davon fuer Auftraege festgehalten
    verfuegbar  bestand minus reserviert, also frei zusagbar

NEUE METHODEN in lager/bestand.py

    def reservieren(self, nummer: str, menge: int, auftrag: str) -> int
    def freigeben(self, nummer: str, auftrag: str) -> int
    def entnehmen(self, nummer: str, auftrag: str) -> int
    def reserviert(self, nummer: str) -> int
    def verfuegbar(self, nummer: str) -> int
    def reservierungen(self, nummer: str) -> dict[str, int]

- reservieren haelt menge Stueck fuer auftrag fest und gibt die neue
  verfuegbare Menge zurueck. Reicht verfuegbar nicht aus -> ZuWenigBestand.
  menge muss positiv sein, sonst ValueError.
  Reserviert derselbe Auftrag mehrfach denselben Artikel, addieren sich die
  Mengen.
- freigeben loest die Reservierung dieses Auftrags wieder auf, ohne Ware zu
  bewegen, und gibt die neue verfuegbare Menge zurueck. Gibt es fuer den
  Auftrag keine Reservierung -> UnbekannteReservierung.
- entnehmen bucht die reservierte Menge tatsaechlich aus: der Bestand sinkt um
  die reservierte Menge, die Reservierung verschwindet. Rueckgabe ist der neue
  Bestand. Keine Reservierung -> UnbekannteReservierung.
- reserviert liefert die Summe aller Reservierungen des Artikels.
- verfuegbar liefert bestand minus reserviert.
- reservierungen liefert eine Abbildung Auftrag -> Menge. Die zurueckgegebene
  Abbildung ist eine Kopie, Aenderungen daran wirken sich nicht aufs Lager aus.
- auslagern darf reservierte Ware nicht angreifen: es prueft kuenftig gegen
  verfuegbar, nicht gegen bestand.

NEUE FEHLERKLASSE in lager/artikel.py

    class UnbekannteReservierung(LagerFehler)

ABLAGE in lager/speicher.py

- Reservierungen werden mitgesichert und beim Laden wieder hergestellt.
- FORMAT_VERSION steigt auf 2.
- WICHTIG: Bestehende Dateien im Format 1 muessen weiterhin ladbar sein. Sie
  haben schlicht keine Reservierungen. Beim naechsten Sichern werden sie ins
  neue Format geschrieben.

KOMMANDOZEILE in lager/cli.py

    python -m lager.cli reservieren A1 5 auftrag-42
    python -m lager.cli freigeben A1 auftrag-42
    python -m lager.cli entnehmen A1 auftrag-42

Die Ausgabe von "liste" bekommt zwei weitere Spalten, weiterhin mit Tabulator
getrennt, in dieser Reihenfolge:

    nummer  name  bestand  reserviert  verfuegbar

AUSSERDEM

- Die bestehenden Tests muessen gruen bleiben.
- Passe die README an.
- Schreibe eigene Tests fuer die neuen Funktionen, auch fuer das Laden einer
  alten Datei im Format 1.
- Pruefe zum Schluss selbst, dass "python -m pytest" durchlaeuft.
  Nutze dafuer den vorhandenen Interpreter .venv/bin/python.
