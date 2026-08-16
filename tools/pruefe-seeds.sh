#!/bin/bash
# Vergleicht die veroeffentlichten Seeds mit dem Stand, aus dem gemessen wurde.
#
# Anlass: die Seeds von t2-refactor und t4-feature enthielten zeitweise die
# Loesung der jeweiligen Aufgabe. Ein Modell hatte waehrend eines
# unbeaufsichtigten Laufs in dieser Arbeitskopie gearbeitet statt in seinem
# eigenen Verzeichnis -- 15 Dateien, 804 eingefuegte Zeilen -- und ein
# unachtsames `git add -A` hat es mitgenommen.
#
# Das ist der stillste Schaden, den dieses Repo nehmen kann: die Messwerte
# bleiben richtig, aber wer den Pruefstand nachbaut, bekommt eine Aufgabe, die
# schon geloest ist, und merkt es nicht. Deshalb vor jedem Commit:
#
#     ./tools/pruefe-seeds.sh          # 0 = sauber, 1 = Abweichung
#
# MESSSTAND zeigt auf die Arbeitskopie, mit der die Laeufe gefahren werden.
set -u
MESSSTAND="${MESSSTAND:-$HOME/bench2/tasks}"
HIER="$(cd "$(dirname "$0")/.." && pwd)/bench/tasks"
AUS=(--exclude=__pycache__ --exclude=.venv --exclude=.pytest_cache --exclude=.git)

[ -d "$MESSSTAND" ] || { echo "Messstand $MESSSTAND fehlt — nichts zu vergleichen."; exit 0; }

fehler=0
for pfad in "$HIER"/*/; do
    aufgabe=$(basename "$pfad")
    [ -d "$pfad/seed" ] || continue
    if [ ! -d "$MESSSTAND/$aufgabe/seed" ]; then
        echo "  $aufgabe: kein Gegenstueck im Messstand"; continue
    fi
    if diff -rq "${AUS[@]}" "$pfad/seed" "$MESSSTAND/$aufgabe/seed" >/dev/null 2>&1; then
        echo "  $aufgabe: sauber"
    else
        echo "  $aufgabe: WEICHT AB"
        diff -rq "${AUS[@]}" "$pfad/seed" "$MESSSTAND/$aufgabe/seed" 2>&1 | sed 's/^/      /'
        fehler=1
    fi
done

if [ "$fehler" = 0 ]; then
    echo "Alle Seeds entsprechen dem Messstand."
else
    echo
    echo "Ein Seed weicht ab. Wenn das keine Absicht war:"
    echo "    git checkout \$(git log --format=%h -1 --diff-filter=A -- bench/tasks) -- bench/tasks/"
    echo "und die Dateien loeschen, die im Ursprungs-Commit nicht vorkommen."
fi
exit "$fehler"
