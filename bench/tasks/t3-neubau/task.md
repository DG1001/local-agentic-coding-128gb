Baue von Grund auf ein kleines Abfragewerkzeug fuer Tabellendaten. Es gibt noch
keinen Code, nur diese Beschreibung. Verwende ausser pytest keine externen
Abhaengigkeiten.

Lege ein Paket abfrage/ an und schreibe Tests nach tests/.
Die Namen und Signaturen unten sind verbindlich, es gibt eine externe Testsuite.

DATENHALTUNG in abfrage/tabelle.py

    class Tabelle:
        def __init__(self, spalten: list[str], zeilen: list[dict[str, str]]) -> None
        spalten: list[str]                # Reihenfolge bleibt erhalten
        zeilen: list[dict[str, str]]      # Werte immer als str
        @classmethod
        def aus_csv(cls, text: str) -> "Tabelle"
        def als_csv(self) -> str

- aus_csv liest die erste Zeile als Spaltenkopf. Trennzeichen ist das Komma,
  Leerraum um die Felder wird abgeschnitten. Leere Eingabe ergibt eine Tabelle
  ohne Spalten und ohne Zeilen.
- als_csv gibt die Tabelle im selben Format zurueck, Kopfzeile zuerst, Zeilen
  mit \n getrennt, kein abschliessender Zeilenumbruch.
- Zwei Tabellen mit gleichem Inhalt sollen als gleich gelten (==).

FEHLER in abfrage/fehler.py

    class AbfrageFehler(Exception)      # Basisklasse
    class SyntaxFehler(AbfrageFehler)   # Abfrage nicht lesbar
    class SpaltenFehler(AbfrageFehler)  # Spalte gibt es nicht

ABFRAGEN in abfrage/motor.py

    def fuehre_aus(tabelle: Tabelle, abfrage: str) -> Tabelle

Eine Abfrage besteht aus Teilen, die in dieser Reihenfolge stehen duerfen und
alle wahlfrei sind:

    waehle <spalte>[, <spalte>...]     Spaltenauswahl, * bedeutet alle
    wo <spalte> <vergleich> <wert>     Zeilen filtern
    sortiere <spalte> [ab]             sortieren, ab kehrt die Richtung um
    grenze <n>                         hoechstens n Zeilen

Beispiel:

    waehle name, alter wo alter > 30 sortiere alter ab grenze 2

Regeln:

- Vergleiche: =  !=  <  >  <=  >=
- Lassen sich beide Seiten als Zahl lesen, wird numerisch verglichen, sonst
  als Zeichenkette. Das gilt auch fuers Sortieren: eine Spalte, in der alle
  Werte Zahlen sind, wird numerisch sortiert, sonst alphabetisch.
- Der Wert hinter dem Vergleich darf in doppelten Anfuehrungszeichen stehen,
  dann darf er Leerzeichen enthalten und wird immer als Zeichenkette behandelt.
- Die Reihenfolge der Verarbeitung ist: filtern, sortieren, begrenzen,
  Spalten auswaehlen.
- Sortieren ist stabil: gleiche Werte behalten ihre bisherige Reihenfolge.
- Unbekannte Spalte -> SpaltenFehler. Unlesbare Abfrage, unbekanntes
  Schluesselwort, fehlender Wert, nicht ganzzahliges grenze -> SyntaxFehler.
- Eine leere Abfrage gibt die Tabelle unveraendert zurueck.
- fuehre_aus veraendert die uebergebene Tabelle nicht.

ZAEHLEN

    zaehle

ist ein eigener Abfrageteil, der ganz am Schluss stehen darf und statt der
Zeilen eine Tabelle mit genau einer Spalte "anzahl" und einer Zeile liefert.
Er zaehlt, was nach Filtern und Begrenzen uebrig ist. Beispiel:

    wo ort = "Bad Vilbel" zaehle

KOMMANDOZEILE in abfrage/cli.py

    python -m abfrage.cli DATEI "waehle name wo alter > 30"

gibt das Ergebnis als CSV auf stdout aus. Bei AbfrageFehler eine Meldung nach
stderr und Rueckgabewert 2.

AUSSERDEM

- Schreibe eine README, die Format und Abfragesprache erklaert.
- Schreibe eigene Tests nach tests/.
- Pruefe zum Schluss selbst, dass "python -m pytest" durchlaeuft.
  Nutze dafuer den vorhandenen Interpreter .venv/bin/python.
