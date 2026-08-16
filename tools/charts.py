#!/usr/bin/env python3
"""Regenerates the report's charts from the measurements under results/.

No third-party library, and deliberately driven *by the JSON files*: a chart
kept up to date by hand eventually drifts away from its data, and that has
already happened twice in this repo (the tokens/s column and the tool-call
counts). What comes out of here can only be wrong if the raw data is.

    python3 tools/diagramme.py        # writes docs/charts/

Colours are mid-tones that stay legible on light and dark GitHub backgrounds;
the background itself is left transparent.
"""
import json
import pathlib

WURZEL = pathlib.Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "docs" / "charts"

# Mid-tones: legible on both #ffffff and #0d1117
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
    """Two bars per row: (label, value1, value2, highlight)."""
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
    s.append(f'<text x="{links + 16}" y="{y + 10}" font-size="11" fill="{ACHSE}">generation</text>')
    s.append(f'<rect x="{links + 92}" y="{y}" width="11" height="11" rx="2" fill="{BALKEN2}" opacity="0.75"/>')
    s.append(f'<text x="{links + 108}" y="{y + 10}" font-size="11" fill="{ACHSE}">'
             f'end-to-end (~16,850 input tokens)</text>')
    s.append('</svg>')
    (ZIEL / datei).write_text("\n".join(s) + "\n")
    return ZIEL / datei


def punkte(reihen, titel, untertitel, datei, breite=760, xmin=40, xmax=90):
    """One dot strip per row — for spread across repeated runs."""
    zeilenhoehe = 46
    links = 250
    oben = 62
    hoehe = oben + len(reihen) * zeilenhoehe + 30
    skala = (breite - links - 60) / (xmax - xmin)

    s = kopf(breite, hoehe, titel)
    s.append(f'<text x="0" y="20" font-size="14" font-weight="600" fill="{TEXT}">{titel}</text>')
    s.append(f'<text x="0" y="38" font-size="11" fill="{ACHSE}">{untertitel}</text>')

    # axis
    for wert in range(xmin, xmax + 1, 10):
        x = links + (wert - xmin) * skala
        s.append(f'<line x1="{x:.1f}" y1="{oben - 8}" x2="{x:.1f}" y2="{hoehe - 26}" '
                 f'stroke="{ACHSE}" stroke-width="0.5" opacity="0.3"/>')
        s.append(f'<text x="{x:.1f}" y="{hoehe - 12}" font-size="10" text-anchor="middle" '
                 f'fill="{ACHSE}">{wert}</text>')

    for i, (name, werte, farbe) in enumerate(reihen):
        y = oben + i * zeilenhoehe
        # SVG does not wrap text: a two-line label needs two elements, or it
        # runs as one line straight into the plot area.
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
                     f'spread {max(werte) - min(werte)}</text>')
        for w in werte:
            x = links + (w - xmin) * skala
            s.append(f'<circle cx="{x:.1f}" cy="{y + 2}" r="4.5" fill="{farbe}" opacity="0.85"/>')
    s.append('</svg>')
    (ZIEL / datei).write_text("\n".join(s) + "\n")
    return ZIEL / datei


def gestapelt(daten, titel, untertitel, datei, breite=760):
    """One bar per model, split into the four tasks."""
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
            # missing points as a faint gap
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
    p = balken_doppelt(daten, "Throughput on the GX10",
                       "tokens per second · green = with speculative decoding",
                       "throughput.svg")
    print("written:", p.relative_to(WURZEL))

    # --- spread: repeated runs of one model, against the field of seven
    v = json.loads((WURZEL / "results" / "variance.json").read_text())
    m = json.loads((WURZEL / "results" / "measurements.json").read_text())
    tabelle = sorted((x["total_hidden_passed"] for x in m.values()), reverse=True)
    q = v["repeated_models"]["Qwen3.6-35B-A3B (NVFP4)"]["scores"]
    p = punkte(
        [("Nemotron-3.5-Lightning\nsame setup, %d runs" % len(v["all_nemotron_scores"]),
          v["all_nemotron_scores"], WARN),
         ("Qwen3.6-35B-A3B NVFP4\nsame setup, %d runs" % len(q), q, BETONT),
         ("the %d models in the table\nONE run each" % len(tabelle), tabelle, BALKEN)],
        "One model spreads wider than the whole field",
        "hidden tests passed, of 86 · identical tasks, identical suites",
        "variance.svg")
    print("written:", p.relative_to(WURZEL))

    # --- hidden tests passed, per task
    reihenfolge = sorted(m.items(), key=lambda kv: -kv[1]["total_hidden_passed"])
    daten = [(v2["name"].replace("NVIDIA-Nemotron-3.5-Lightning-30B-A3B", "Nemotron-3.5-Lightning"),
              [v2["tasks"][a2]["hidden_passed"] for a2 in
               ("t1-debug", "t2-refactor", "t3-neubau", "t4-feature")])
             for _, v2 in reihenfolge]
    p = gestapelt(daten, "Where the points are lost",
                  "faint = not passed · opencode, one run per model",
                  "tasks.svg")
    print("written:", p.relative_to(WURZEL))


if __name__ == "__main__":
    main()
