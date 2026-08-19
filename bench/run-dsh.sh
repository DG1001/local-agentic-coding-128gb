#!/bin/bash
# run-dsh.sh <label> <model-id>
#
# Same four tasks and the same hidden grading as run.sh, but through DeepSeek
# Harness (https://github.com/deepseek-ai/deepseek-harness) instead of
# opencode. Results are written to runs/<label>/ in the same format, so the
# numbers line up with every other harness measured here.
#
# The model is chosen by rewriting $DSH_HOME/settings.yaml before each run
# rather than by a flag: the headless profile takes the model from the config,
# and the runs are strictly sequential anyway -- only one model fits in memory.
#
# The tool-call column stays empty. The headless profile prints the final
# assistant message and nothing else, so there is no transcript to count. A
# zero here means "not measured", not "no tools were used".
set -u

KENNUNG="$1"
MODELL="$2"
BASIS="$HOME/bench2"
DSH="$HOME/deepseek-harness/apps/cli/lib/bin.js"
# vLLM hoert auf 8889, ds4-server auf 8888 -- deshalb uebersteuerbar.
URL="${URL:-http://127.0.0.1:8889/v1}"
ZIEL="$BASIS/runs/$KENNUNG"
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"

[ -f "$DSH" ] || { echo "dsh nicht gebaut: $DSH"; exit 1; }

# Der Endpunkt verlangt keinen Schluessel, die Kette schon.
export LOKAL_API_KEY=${LOKAL_API_KEY:-dummy}

cat > "$HOME/.dsh/settings.yaml" <<YAML
llm-pi-ai:
  providers:
    lokal:
      apiKeyEnv: LOKAL_API_KEY
      api: openai-completions
      baseURL: $URL
      models:
        - id: $MODELL
agent-default-model:
  provider: lokal
  model: $MODELL
YAML

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
    ( cd "$W" && timeout 5400 node "$DSH" --profile headless \
        "$(cat "$BASIS/tasks/$A/aufgabe.md")" ) > "$ZIEL/$A.log" 2>&1
    RC=$?
    T1=$(date +%s)
    DAUER=$((T1-T0))

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
