#!/bin/bash
# lauf-cc.sh <label> <cc-local-modellname>
#
# Identisch zu run.sh, nur mit Claude Code statt opencode als Harness.
# Gleiche Seeds, gleiche Aufgabentexte, gleiche verdeckte Testsuiten --
# damit misst der Unterschied den Harness und nicht die Aufgabe.
#
# Claude Code spricht die lokalen Server ueber die native Anthropic Messages
# API an (/v1/messages), ohne Uebersetzungsproxy.
set -u

LABEL="$1"
MODELL="$2"       # ds4 | laguna | kat | agentworld | qwen27b
BASIS="$HOME/bench2"
ZIEL="$BASIS/runs/$LABEL"
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"

# Endpunkt und Kontextfenster wie in ~/.local/bin/cc-local
case "$MODELL" in
    ds4)        PORT=8888; MNAME=deepseek-v4-flash;   CTX=65536  ;;
    laguna)     PORT=8889; MNAME=laguna-s-2.1;        CTX=65536  ;;
    kat)        PORT=8889; MNAME=kat-coder-v2.5;      CTX=131072 ;;
    agentworld) PORT=8889; MNAME=qwen-agentworld-35b; CTX=131072 ;;
    qwen27b)    PORT=8889; MNAME=qwen3.6-27b;         CTX=131072 ;;
    *) echo "Unbekanntes Modell: $MODELL"; exit 2 ;;
esac

curl -sf --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 || {
    echo "FEHLER: auf :$PORT antwortet nichts -- erst model-switch $MODELL"; exit 1; }

export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT"
export ANTHROPIC_AUTH_TOKEN=unused
export ANTHROPIC_API_KEY=unused
export ANTHROPIC_MODEL="$MNAME"
export ANTHROPIC_SMALL_FAST_MODEL="$MNAME"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$MNAME"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$MNAME"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MNAME"
# Claude Codes Auto-Kompaktierung rechnet die Ausgabereservierung NICHT
# gegen: sie laesst die Eingabe bis an das genannte Fenster wachsen und legt
# max_output obendrauf -- Ergebnis ist HTTP 500 "total exceeds context".
# Deshalb wird hier das nutzbare EINGABEBUDGET genannt, nicht die
# Fenstergroesse: CTX minus der Ausgabegrenze.
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=$(( CTX - 16384 ))
# Claude Code fordert sonst 32000 Ausgabetokens an. Bei einem 65536er Modell
# bleiben damit nur 33536 fuer die Eingabe, und sobald die Unterhaltung
# darueber hinauswaechst, scheitert JEDE Anfrage mit HTTP 500. 16384 ist
# derselbe Wert, mit dem opencode laeuft (limit.output in opencode.json).
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=16384

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
    ( cd "$W" && timeout 5400 claude -p "$(cat "$BASIS/tasks/$A/aufgabe.md")" \
        --permission-mode bypassPermissions ) > "$ZIEL/$A.log" 2>&1
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
