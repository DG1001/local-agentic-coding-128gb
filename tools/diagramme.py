#!/usr/bin/env python3
"""Erzeugt die Diagramme des Berichts aus den Messdaten unter results/.

Bewusst ohne Fremdbibliothek und bewusst *aus den JSON-Dateien*: ein Diagramm,
das von Hand gepflegt wird, laeuft irgendwann den Zahlen davon, und genau das
ist in diesem Repo schon zweimal passiert (die tokens/s-Spalte und die
Werkzeugaufrufe). Was hier herauskommt, kann nur falsch sein, wenn die Rohdaten
falsch sind.

    python3 tools/diagramme.py        # schreibt nach docs/bilder/

Die Farben sind Mitteltoene, die auf hellem wie dunklem GitHub-Hintergrund
lesbar bleiben; der Hintergrund selbst bleibt durchsichtig.
"""
import json
import pathlib

WURZEL = pathlib.Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "docs" / "bilder"

# Mitteltoene: auf #ffffff und auf #0d1117 gleichermassen lesbar
TEXT = "#7d8590"
ACHSE = "#6e7781"
BALKEN = "#2f81f7"
BALKEN2 = "#8250df"
BETONT = "#1a7f37"
WARN = "#bc4c00"


def kopf(breite, hoehe, titel):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{breite}" height="{hoehe}" '
        f'viewBox="0 0 {breite} {hoehe}" font-family="-apple-system,BlinkMacSystemFont,'
        f'Segoe UI,Helvetica,Arial,sans-serif">',
        f'<title>{titel}</title>',
    ]


def balken_doppelt(daten, titel, einheit, datei, breite=760):
    """Zwei Balken je Zeile: (Beschriftung, wert1, wert2, hervorheben)."""
    zeilenhoehe = 38
    links = 250
    oben = 54
    hoehe = oben + len(daten) * zeilenhoehe + 44
    hoechst = max(max(a, b) for _, a, b, _ in daten)
    skala = (breite - links - 90) / hoechst

    s = kopf(breite, hoehe, titel)
    s.append(f'<text x="0" y="20" font-size="14" font-weight="600" fill="{TEXT}">{titel}</text>')
    s.append(f'<text x="0" y="38" font-size="11" fill="{ACHSE}">{einheit}</text>')

    for i, (name, a, b, hervor) in enumerate(daten):
        y = oben + i * zeilenhoehe
        farbe = BETONT if hervor else BALKEN
        s.append(f'<text x="{links - 8}" y="{y + 12}" font-size="12" text-anchor="end" '
                 f'fill="{TEXT}">{name}</text>')
        s.append(f'<rect x="{links}" y="{y + 2}" width="{a * skala:.1f}" height="13" '
                 f'rx="2" fill="{farbe}"/>')
        s.append(f'<text x="{links + a * skala + 6:.1f}" y="{y + 13}" font-size="11" '
                 f'fill="{TEXT}">{a:g}</text>')
        s.append(f'<rect x="{links}" y="{y + 17}" width="{b * skala:.1f}" height="13" '
                 f'rx="2" fill="{BALKEN2}" opacity="0.75"/>')
        s.append(f'<text x="{links + b * skala + 6:.1f}" y="{y + 28}" font-size="11" '
                 f'fill="{ACHSE}">{b:g}</text>')

    y = oben + len(daten) * zeilenhoehe + 14
    s.append(f'<rect x="{links}" y="{y}" width="11" height="11" rx="2" fill="{BALKEN}"/>')
    s.append(f'<text x="{links + 16}" y="{y + 10}" font-size="11" fill="{ACHSE}">Erzeugung</text>')
    s.append(f'<rect x="{links + 92}" y="{y}" width="11" height="11" rx="2" fill="{BALKEN2}" opacity="0.75"/>')
    s.append(f'<text x="{links + 108}" y="{y + 10}" font-size="11" fill="{ACHSE}">'
             f'Ende-zu-Ende (~16.850 Token Eingabe)</text>')
    s.append('</svg>')
    (ZIEL / datei).write_text("\n".join(s) + "\n")
    return ZIEL / datei


def punkte(reihen, titel, untertitel, datei, breite=760, xmin=40, xmax=90):
    """Punktwolke je Zeile — fuer Streuung ueber Wiederholungen."""
    zeilenhoehe = 46
    links = 250
    oben = 62
    hoehe = oben + len(reihen) * zeilenhoehe + 30
    skala = (breite - links - 60) / (xmax - xmin)

    s = kopf(breite, hoehe, titel)
    s.append(f'<text x="0" y="20" font-size="14" font-weight="600" fill="{TEXT}">{titel}</text>')
    s.append(f'<text x="0" y="38" font-size="11" fill="{ACHSE}">{untertitel}</text>')

    # Achse
    for wert in range(xmin, xmax + 1, 10):
        x = links + (wert - xmin) * skala
        s.append(f'<line x1="{x:.1f}" y1="{oben - 8}" x2="{x:.1f}" y2="{hoehe - 26}" '
                 f'stroke="{ACHSE}" stroke-width="0.5" opacity="0.3"/>')
        s.append(f'<text x="{x:.1f}" y="{hoehe - 12}" font-size="10" text-anchor="middle" '
                 f'fill="{ACHSE}">{wert}</text>')

    for i, (name, werte, farbe) in enumerate(reihen):
        y = oben + i * zeilenhoehe
        # SVG bricht Text nicht um: zweizeilige Beschriftungen brauchen zwei
        # Elemente, sonst steht alles in einer Zeile und laeuft ins Diagramm.
        teile = name.split("\n")
        s.append(f'<text x="{links - 8}" y="{y + 2}" font-size="12" text-anchor="end" '
                 f'fill="{TEXT}">{teile[0]}</text>')
        if len(teile) > 1:
            s.append(f'<text x="{links - 8}" y="{y + 16}" font-size="10.5" text-anchor="end" '
                     f'fill="{ACHSE}">{teile[1]}</text>')
        if len(werte) > 1:
            x1 = links + (min(werte) - xmin) * skala
            x2 = links + (max(werte) - xmin) * skala
            s.append(f'<line x1="{x1:.1f}" y1="{y + 2}" x2="{x2:.1f}" y2="{y + 2}" '
                     f'stroke="{farbe}" stroke-width="2" opacity="0.35"/>')
            s.append(f'<text x="{x2 + 10:.1f}" y="{y + 6}" font-size="10" fill="{ACHSE}">'
                     f'Spanne {max(werte) - min(werte)}</text>')
        for w in werte:
            x = links + (w - xmin) * skala
            s.append(f'<circle cx="{x:.1f}" cy="{y + 2}" r="4.5" fill="{farbe}" opacity="0.85"/>')
    s.append('</svg>')
    (ZIEL / datei).write_text("\n".join(s) + "\n")
    return ZIEL / datei


def gestapelt(daten, titel, untertitel, datei, breite=760):
    """Ein Balken je Modell, in vier Abschnitte geteilt (die vier Aufgaben)."""
    zeilenhoehe = 30
    links = 250
    oben = 62
    hoehe = oben + len(daten) * zeilenhoehe + 46
    skala = (breite - links - 70) / 86
    farben = ["#2f81f7", "#8250df", "#1a7f37", "#bf8700"]
    namen = ["t1-debug 15", "t2-refactor 17", "t3-neubau 33", "t4-feature 21"]
    voll = [15, 17, 33, 21]

    s = kopf(breite, hoehe, titel)
    s.append(f'<text x="0" y="20" font-size="14" font-weight="600" fill="{TEXT}">{titel}</text>')
    s.append(f'<text x="0" y="38" font-size="11" fill="{ACHSE}">{untertitel}</text>')
    for i, (name, werte) in enumerate(daten):
        y = oben + i * zeilenhoehe
        s.append(f'<text x="{links - 8}" y="{y + 12}" font-size="12" text-anchor="end" '
                 f'fill="{TEXT}">{name}</text>')
        x = links
        for j, w in enumerate(werte):
            if w:
                s.append(f'<rect x="{x:.1f}" y="{y + 1}" width="{w * skala:.1f}" height="15" '
                         f'fill="{farben[j]}"/>')
            # fehlende Punkte als blasse Luecke
            if w < voll[j]:
                s.append(f'<rect x="{x + w * skala:.1f}" y="{y + 1}" '
                         f'width="{(voll[j] - w) * skala:.1f}" height="15" '
                         f'fill="{farben[j]}" opacity="0.15"/>')
            x += voll[j] * skala
        s.append(f'<text x="{x + 8:.1f}" y="{y + 13}" font-size="11" fill="{TEXT}">'
                 f'{sum(werte)}</text>')
    y = oben + len(daten) * zeilenhoehe + 16
    for j, n in enumerate(namen):
        s.append(f'<rect x="{links + j * 130}" y="{y}" width="11" height="11" rx="2" fill="{farben[j]}"/>')
        s.append(f'<text x="{links + j * 130 + 16}" y="{y + 10}" font-size="11" fill="{ACHSE}">{n}</text>')
    s.append('</svg>')
    (ZIEL / datei).write_text("\n".join(s) + "\n")
    return ZIEL / datei


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    d = json.loads((WURZEL / "results" / "throughput.json").read_text())["models"]

    reihe = sorted(d.values(), key=lambda v: -v["generation_tok_s"])
    daten = [(v["name"].replace("NVIDIA-Nemotron-3.5-Lightning-30B-A3B", "Nemotron-3.5-Lightning"),
              v["generation_tok_s"], v["end_to_end_tok_s"],
              v["speculative_decoding"]) for v in reihe]
    p = balken_doppelt(daten, "Durchsatz auf dem GX10",
                       "Token je Sekunde · gruen = mit spekulativem Dekodieren",
                       "durchsatz.svg")
    print("geschrieben:", p.relative_to(WURZEL))

    # --- Streuung: ein Modell, viele Laeufe, gegen sieben Modelle, je ein Lauf
    v = json.loads((WURZEL / "results" / "variance.json").read_text())
    m = json.loads((WURZEL / "results" / "measurements.json").read_text())
    tabelle = sorted((x["total_hidden_passed"] for x in m.values()), reverse=True)
    p = punkte(
        [("Nemotron-3.5-Lightning\nderselbe Aufbau, %d Laeufe" % len(v["all_nemotron_scores"]),
          v["all_nemotron_scores"], WARN),
         ("die %d Modelle der Tabelle\nje EIN Lauf" % len(tabelle), tabelle, BALKEN)],
        "Ein Modell streut breiter als das ganze Feld",
        "bestandene verdeckte Tests von 86 · identische Aufgaben, identische Suiten",
        "streuung.svg")
    print("geschrieben:", p.relative_to(WURZEL))

    # --- Pruefstand je Aufgabe
    reihenfolge = sorted(m.items(), key=lambda kv: -kv[1]["total_hidden_passed"])
    daten = [(v2["name"].replace("NVIDIA-Nemotron-3.5-Lightning-30B-A3B", "Nemotron-3.5-Lightning"),
              [v2["tasks"][a2]["hidden_passed"] for a2 in
               ("t1-debug", "t2-refactor", "t3-neubau", "t4-feature")])
             for _, v2 in reihenfolge]
    p = gestapelt(daten, "Wo die Punkte verloren gehen",
                  "blass = nicht bestanden · opencode, ein Lauf je Modell",
                  "aufgaben.svg")
    print("geschrieben:", p.relative_to(WURZEL))


if __name__ == "__main__":
    main()
