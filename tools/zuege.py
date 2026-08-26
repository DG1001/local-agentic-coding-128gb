#!/usr/bin/env python3
"""Turn economy of a Java-harness run, from its own transcript.

    python3 tools/zuege.py <runs-dir> [<runs-dir> ...]

Scores are not the interesting number when a change is meant to save
orientation turns: at 85/86 there is almost no headroom, and scores scatter
far more than turns do. These are the numbers that move when the loop gets
better at the same model:

  turns             how many round trips the task took
  tool calls        how many actions in those turns
  turns to write    the first turn that edits or writes a file — everything
                    before it is orientation
  read/bash/edit    what those calls were
  input tokens      the sum over all turns; a turn saved early is paid for
                    again in every later turn's prompt

The harness prints one line per turn and one summary line at the end, so all
of this is read out of the log rather than instrumented into the run.
"""
import pathlib
import re
import sys

ZUG = re.compile(r'^\[harness\] Zug (\d+):')
WERKZEUG = re.compile(r'^\[harness\]   ([a-z_]+) ->')
ENDE = re.compile(r'^\[harness\] (?:FERTIG|ZUGLIMIT) nach (\d+) Zuegen, '
                  r'(\d+) Werkzeugaufrufen, (\d+) s')
TOKEN = re.compile(r'^\[harness\] Token: (\d+) Eingabe, (\d+) Ausgabe')
SCHREIBT = {'edit', 'write'}


def eine(log: pathlib.Path):
    zug = 0
    erste_schreibung = None
    arten: dict[str, int] = {}
    zuege = aufrufe = sekunden = eingabe = 0
    for zeile in log.read_text(errors='replace').splitlines():
        m = ZUG.match(zeile)
        if m:
            zug = int(m.group(1))
            continue
        m = WERKZEUG.match(zeile)
        if m:
            art = m.group(1)
            arten[art] = arten.get(art, 0) + 1
            if art in SCHREIBT and erste_schreibung is None:
                erste_schreibung = zug
            continue
        m = ENDE.match(zeile)
        if m:
            zuege, aufrufe, sekunden = (int(x) for x in m.groups())
            continue
        m = TOKEN.match(zeile)
        if m:
            eingabe = int(m.group(1))
    return {'zuege': zuege or zug, 'aufrufe': aufrufe, 'sekunden': sekunden,
            'bis_schreibung': erste_schreibung, 'eingabe': eingabe, 'arten': arten}


def main():
    for wurzel in sys.argv[1:]:
        d = pathlib.Path(wurzel)
        print(f'\n{d.name}')
        print(f"  {'Aufgabe':<13}{'Zuege':>6}{'Aufrufe':>9}{'bis Schreib.':>14}"
              f"{'Sek.':>7}{'Eingabe-Token':>15}")
        summe = {'zuege': 0, 'aufrufe': 0, 'sekunden': 0, 'eingabe': 0}
        for log in sorted(d.glob('t*.log')):
            w = eine(log)
            for k in summe:
                summe[k] += w[k]
            bis = w['bis_schreibung'] if w['bis_schreibung'] is not None else '—'
            print(f"  {log.stem:<13}{w['zuege']:>6}{w['aufrufe']:>9}{bis:>14}"
                  f"{w['sekunden']:>7}{w['eingabe']:>15,}")
        print(f"  {'zusammen':<13}{summe['zuege']:>6}{summe['aufrufe']:>9}"
              f"{'':>14}{summe['sekunden']:>7}{summe['eingabe']:>15,}")


if __name__ == '__main__':
    main()
