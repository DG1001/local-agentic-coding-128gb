#!/bin/bash
# lauf-omp.sh <label> <cc-local-modellname>
#
# Identisch zu run.sh, nur mit Oh My Pi (omp) statt opencode als Harness.
# Gleiche Seeds, gleiche Aufgabentexte, gleiche verdeckte Testsuiten --
# damit misst der Unterschied den Harness und nicht die Aufgabe.
#
# omp spricht die Server ueber openai-completions an -- derselbe Pfad wie
# opencode, damit der Vergleich nur den Harness misst.
set -u

LABEL="$1"
MODELL="$2"       # ds4 | laguna | kat | agentworld | qwen27b
BASIS="$HOME/bench2"
ZIEL="$BASIS/runs/$LABEL"
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"

# Endpunkt wie in ~/.omp/agent/models.yml
case "$MODELL" in
    ds4)        PORT=8888; MNAME=gx10ds4/deepseek-v4-flash   ;;
    laguna)     PORT=8889; MNAME=gx10/laguna-s-2.1           ;;
    kat)        PORT=8889; MNAME=gx10/kat-coder-v2.5         ;;
    agentworld) PORT=8889; MNAME=gx10/qwen-agentworld-35b    ;;
    qwen27b)    PORT=8889; MNAME=gx10/qwen3.6-27b            ;;
    *) echo "Unbekanntes Modell: $MODELL"; exit 2 ;;
esac

curl -sf --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 || {
    echo "FEHLER: auf :$PORT antwortet nichts -- erst model-switch $MODELL"; exit 1; }

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

    echo "### $A gestartet $(date +%H:%M:%S)" >> "$ZIEL/verlauf.log"
    T0=$(date +%s)
    timeout 5400 omp --model "$MNAME" --cwd "$W" --auto-approve --no-session \
        -p "$(cat "$BASIS/tasks/$A/aufgabe.md")" > "$ZIEL/$A.log" 2>&1
    RC=$?
    T1=$(date +%s)
    DAUER=$((T1-T0))

    EIGEN=$(cd "$W" && ./.venv/bin/python -m pytest -q 2>&1 | tail -1)

    cp "$BASIS/tasks/$A/test_bench.py" "/tmp/bench_${LABEL}_${A}.py"
    BEWERTUNG=$(cd "$W" && ./.venv/bin/python -m pytest \
        "/tmp/bench_${LABEL}_${A}.py" -q 2>&1 | tail -1)

    BESTANDEN=$(echo "$BEWERTUNG" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
    [ -z "$BESTANDEN" ] && BESTANDEN=0
    case "$A" in
        t1-debug)    GESAMT=15 ;;
        t2-refactor) GESAMT=17 ;;
        t3-neubau)   GESAMT=33 ;;
        t4-feature)  GESAMT=21 ;;
    esac

    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$A" "$DAUER" "$RC" "$BESTANDEN" "$GESAMT" "$EIGEN" >> "$ZIEL/ergebnis.tsv"
    echo "### $A fertig: ${DAUER}s rc=$RC verdeckt=${BESTANDEN}/${GESAMT}" \
        >> "$ZIEL/verlauf.log"
done

echo "FERTIG $(date +%H:%M:%S)" > "$ZIEL/.done"
