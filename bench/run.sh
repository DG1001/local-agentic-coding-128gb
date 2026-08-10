#!/bin/bash
# run.sh <label> <provider/model>
# Runs all four tasks in sequence and grades each with the hidden suite.
# Results are written to runs/<label>/.
set -u

KENNUNG="$1"
MODELL="$2"
BASIS="$HOME/bench2"
ZIEL="$BASIS/runs/$KENNUNG"
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"

rm -rf "$ZIEL"; mkdir -p "$ZIEL"
: > "$ZIEL/ergebnis.tsv"

for A in $AUFGABEN; do
    W="$ZIEL/$A"
    mkdir -p "$W"

    # Copy in the seed repo if there is one (t3 starts from an empty directory)
    if [ -d "$BASIS/tasks/$A/seed" ]; then
        tar -C "$BASIS/tasks/$A/seed" --exclude=.venv --exclude=__pycache__ \
            --exclude=.git -cf - . | tar -C "$W" -xf -
    fi

    python3 -m venv "$W/.venv" >/dev/null 2>&1
    "$W/.venv/bin/pip" install -q pytest

    ( cd "$W" && git init -q && git add -A 2>/dev/null
      git -c user.email=b@b -c user.name=bench commit -qm seed --allow-empty )

    echo "### $A gestartet $(date +%H:%M:%S)" >> "$ZIEL/verlauf.log"
    T0=$(date +%s)
    timeout 5400 opencode run -m "$MODELL" --auto --dir "$W" \
        "$(cat "$BASIS/tasks/$A/aufgabe.md")" > "$ZIEL/$A.log" 2>&1
    RC=$?
    T1=$(date +%s)
    DAUER=$((T1-T0))

    # The model's own claim: what do its own tests say?
    EIGEN=$(cd "$W" && ./.venv/bin/python -m pytest -q 2>&1 | tail -1)

    # Hidden grading
    cp "$BASIS/tasks/$A/test_bench.py" "/tmp/bench_${KENNUNG}_${A}.py"
    BEWERTUNG=$(cd "$W" && ./.venv/bin/python -m pytest \
        "/tmp/bench_${KENNUNG}_${A}.py" -q 2>&1 | tail -1)

    # Count passes. The total is hard-coded: otherwise a collection error
    # (missing class -> pytest aborts before running) would be recorded as
    # "0 of 1" instead of "0 of all".
    BESTANDEN=$(echo "$BEWERTUNG" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
    [ -z "$BESTANDEN" ] && BESTANDEN=0
    case "$A" in
        t1-debug)    GESAMT=15 ;;
        t2-refactor) GESAMT=17 ;;
        t3-neubau)   GESAMT=33 ;;
        t4-feature)  GESAMT=21 ;;
    esac

    # Rough count of tool calls from the transcript
    WERKZEUGE=$(grep -cE '^\s*(\x1b\[[0-9;]*m)*→' "$ZIEL/$A.log" 2>/dev/null || echo 0)

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$A" "$DAUER" "$RC" "$BESTANDEN" "$GESAMT" "$WERKZEUGE" "$EIGEN" \
        >> "$ZIEL/ergebnis.tsv"
    echo "### $A fertig: ${DAUER}s rc=$RC verdeckt=${BESTANDEN}/${GESAMT}" \
        >> "$ZIEL/verlauf.log"
done

echo "FERTIG $(date +%H:%M:%S)" > "$ZIEL/.done"
