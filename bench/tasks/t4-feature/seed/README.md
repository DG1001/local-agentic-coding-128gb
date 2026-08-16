# lager

Kleine Lagerverwaltung. Der Bestand liegt als JSON-Datei.

## Datentypen

- **bestand**   tatsaechlich im Lager liegende Stueckzahl
- **reserviert**   davon fuer Auftraege festgehalten
- **verfuegbar**   bestand minus reserviert, also frei zusagbar

## Neue Methoden in `lager/bestand.py`

### `reservieren(nummer, menge, auftrag)`
- Hoelt menge Stueck fuer auftrag fest und gibt die neue verfuegbare Menge zurueck
- Reicht verfuegbar nicht aus -> `ZuWenigBestand`
- menge muss positiv sein, sonst `ValueError`
- Reserviert derselbe Auftrag mehrfach denselben Artikel, addieren sich die Mengen

### `freigeben(nummer, auftrag)`
- Loest die Reservierung dieses Auftrags wieder auf, ohne Ware zu bewegen
- Gibt es fuer den Auftrag keine Reservierung -> `UnbekannteReservierung`
- Gibt die neue verfuegbare Menge zurueck

### `entnehmen(nummer, auftrag)`
- Bucht die reservierte Menge tatsaechlich aus: Bestand sinkt um reservierte Menge
- Reservierung verschwindet
- Rueckgabe ist der neue Bestand
- Keine Reservierung -> `UnbekannteReservierung`

### `reserviert(nummer)`
- Liefert die Summe aller Reservierungen des Artikels

### `verfuegbar(nummer)`
- Liefert bestand minus reserviert

### `reservierungen(nummer)`
- Liefert Abbildung Auftrag -> Menge (Kopie). Aenderungen daran wirken sich nicht aufs Lager aus

## Aenderung in `lager/artikel.py`

### `UnbekannteReservierung(LagerFehler)`
- Neue Fehlerklasse fuer unbekannte Reservierungen

## Ablage in `lager/speicher.py`

- `FORMAT_VERSION` steigt auf 2
- Reservierungen werden mitgesichert und beim Laden wiederhergestellt
- Bestehende Dateien im Format 1 muessen weiterhin ladbar sein (schlicht keine Reservierungen)
- Beim naechsten Sichern werden alte Dateien ins neue Format geschrieben

## Kommandozeile in `lager/cli.py`

Neue Befehle:

    python -m lager.cli reservieren A1 5 auftrag-42
    python -m lager.cli freigeben A1 auftrag-42
    python -m lager.cli entnehmen A1 auftrag-42

Die Ausgabe von `liste` bekommt zwei weitere Spalten (mit Tabulator getrennt):

    nummer  name  bestand  reserviert  verfuegbar

## Tests

Alle bestehenden Tests bleiben gruen. Es wurden zusatzliche Tests fuer die
neuen Funktionen hinzugefuegt, auch fuer das Laden alter Dateien im Format 1.

Ausfuehrung: `python3 -m pytest`
