#!/bin/bash
# run-hermes.sh <label> <model-id> [base-url]
#
# Same four tasks and the same hidden grading as run.sh, through Hermes Agent
# (https://github.com/NousResearch/hermes-agent) instead of opencode.
#
# Two Hermes specifics, both of which cost a run before they were understood:
#
#   --no-restore-cwd  without it Hermes reopens the working directory of its
#                     last session, not the one you are in. The first smoke
#                     test searched a Java project three directories away and
#                     reported the file missing.
#   --in DIR          the task directory, given explicitly for the same reason.
#
# And the entry point matters more than it looks. `-z/--oneshot` accepts the
# model's first message as the answer: given a long task description, both
# Ornith and Nemotron wrote a detailed report of edits they had never made --
# 23 lines of prose, zero tool calls, not one file touched. `chat -q` runs the
# real agent loop; the same task produced 27 tool calls. --max-turns 80 keeps
# it comparable with the Java harness.
#
# And one guard that is not optional here. Hermes searches beyond the
# directory it was given: asked to change rabatt.py it announced it had found
# "many copies under /tmp" and picked the newest. Under bench2/runs there are
# dozens of older runs holding files of exactly the same name, so a stray edit
# would silently corrupt someone else's measurement. After every task this
# script therefore checks whether anything outside the task directory was
# touched, and says so loudly.
#
# The first version of that check watched runs/ only. It missed the case
# that actually happened: an agent solved t1-debug in tasks/t1-debug/seed --
# the source every future run is copied from -- while reporting zero changes
# in its own work copy. tools/pruefe-seeds.sh caught it afterwards. The check
# now watches tasks/ as well, because that is the file set where a stray edit
# is not one bad run but every run after it.
set -u

KENNUNG="$1"
MODELL="$2"
BASISURL="${3:-http://127.0.0.1:8889/v1}"
BASIS="$HOME/bench2"
ZIEL="$BASIS/runs/$KENNUNG"
HERMES="$HOME/.local/bin/hermes"
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"
# Vor jeder Aufgabe pruefen, ob der Motor ueberhaupt antwortet -- ein
# haengendes vLLM sieht sonst aus wie ein langsames Modell.
. "$(dirname "$0")/bereit.sh"

[ -x "$HERMES" ] || { echo "hermes nicht gefunden: $HERMES"; exit 1; }

rm -rf "$ZIEL"; mkdir -p "$ZIEL"
: > "$ZIEL/ergebnis.tsv"

for A in $AUFGABEN; do
    W="$ZIEL/$A"
    mkdir -p "$W"

    if [ -d "$BASIS/tasks/$A/seed" ]; then
        tar -C "$BASIS/tasks/$A/seed" --exclude=.venv --exclude=__pycache__ \
            --exclude=.git -cf - . | tar -C "$W" -xf -
    fi

    python3 -m venv "$W/.venv" >/dev/null 2>&1
    "$W/.venv/bin/pip" install -q pytest

    ( cd "$W" && git init -q && git add -A 2>/dev/null
      git -c user.email=b@b -c user.name=bench commit -qm seed --allow-empty )

    motor_bereit "$BASISURL" "$MODELL" || {
        echo "### $A uebersprungen: Motor antwortet nicht" >> "$ZIEL/verlauf.log"
        printf '%s\t0\t99\t0\t0\t0\tMotor haengt\n' "$A" >> "$ZIEL/ergebnis.tsv"
        continue
    }
    echo "### $A gestartet $(date +%H:%M:%S)" >> "$ZIEL/verlauf.log"
    MARKE=$(mktemp)                      # Zeitstempel fuer die Fremdschreib-Probe
    T0=$(date +%s)
    HERMES_INFERENCE_MODEL="$MODELL" HERMES_BASE_URL="$BASISURL" \
    timeout 5400 "$HERMES" chat --yolo --no-restore-cwd --in "$W" \
        -m "$MODELL" --max-turns 80 -q "$(cat "$BASIS/tasks/$A/aufgabe.md")" \
        > "$ZIEL/$A.log" 2>&1
    RC=$?
    T1=$(date +%s)
    DAUER=$((T1-T0))

    # Hat es ausserhalb geschrieben? Alles unter runs/, das seit dem Start
    # angefasst wurde und nicht zu dieser Aufgabe gehoert.
    FREMD=$(find "$BASIS/runs" "$BASIS/tasks" -newer "$MARKE" -type f \
            \( -name '*.py' -o -name '*.md' -o -name '*.txt' \) \
            -not -path "$W/*" -not -path '*__pycache__*' 2>/dev/null | head -5)
    rm -f "$MARKE"
    if [ -n "$FREMD" ]; then
        echo "### WARNUNG $A: ausserhalb geschrieben:" >> "$ZIEL/verlauf.log"
        echo "$FREMD" >> "$ZIEL/verlauf.log"
        echo "  WARNUNG: $A hat ausserhalb seines Verzeichnisses geschrieben"
    fi

    EIGEN=$(cd "$W" && ./.venv/bin/python -m pytest -q 2>&1 | tail -1)

    cp "$BASIS/tasks/$A/test_bench.py" "/tmp/bench_${KENNUNG}_${A}.py"
    BEWERTUNG=$(cd "$W" && ./.venv/bin/python -m pytest \
        "/tmp/bench_${KENNUNG}_${A}.py" -q 2>&1 | tail -1)

    BESTANDEN=$(echo "$BEWERTUNG" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
    [ -z "$BESTANDEN" ] && BESTANDEN=0
    case "$A" in
        t1-debug)    GESAMT=15 ;;
        t2-refactor) GESAMT=17 ;;
        t3-neubau)   GESAMT=33 ;;
        t4-feature)  GESAMT=21 ;;
    esac

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$A" "$DAUER" "$RC" "$BESTANDEN" "$GESAMT" "0" "$EIGEN" \
        >> "$ZIEL/ergebnis.tsv"
    echo "### $A fertig: ${DAUER}s rc=$RC verdeckt=${BESTANDEN}/${GESAMT}" \
        >> "$ZIEL/verlauf.log"
done

echo "FERTIG $(date +%H:%M:%S)" > "$ZIEL/.done"
