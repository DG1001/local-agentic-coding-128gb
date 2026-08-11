#!/bin/bash
# lauf-java.sh <kennung> <modellname>
# Wie lauf.sh, nur mit dem selbstgebauten Java-Harness statt opencode.
# Ergebnisse landen in runs/<kennung>/.
set -u

KENNUNG="$1"
MODELL="$2"
BASIS="$BASIS"
ZIEL="$BASIS/runs/$KENNUNG"
HARNESS="$HOME/java-harness"
JAVA=/usr/lib/jvm/java-21-openjdk-arm64/bin/java
AUFGABEN="t1-debug t2-refactor t3-neubau t4-feature"

rm -rf "$ZIEL"; mkdir -p "$ZIEL"
: > "$ZIEL/ergebnis.tsv"

for A in $AUFGABEN; do
    W="$ZIEL/$A"
    mkdir -p "$W"

    if [ -d "$BASIS/tasks/$A/seed" ]; then
        tar -C "$BASIS/tasks/$A/seed" --exclude=.venv --exclude=__pycache__ \
            --exclude=.git -cf - . | tar -C "$W" -xf -
    fi

    # Die .venv muss vor dem Lauf stehen: das Modell soll seine Zuege nicht
    # damit verbrauchen, sich eine Testumgebung zu bauen. (Genau daran ist der
    # erste t3-Versuch gescheitert.)
    python3 -m venv "$W/.venv" >/dev/null 2>&1
    "$W/.venv/bin/pip" install -q pytest

    ( cd "$W" && git init -q && git add -A 2>/dev/null
      git -c user.email=b@b -c user.name=bench commit -qm seed --allow-empty )

    echo "### $A gestartet $(date +%H:%M:%S)" >> "$ZIEL/verlauf.log"
    T0=$(date +%s)
    timeout 5400 "$JAVA" -cp "$HARNESS/out" de.dg1001.harness.Main \
        --model "$MODELL" \
        --cwd "$W" \
        --prompt-file "$BASIS/tasks/$A/aufgabe.md" \
        --max-turns 80 \
        > "$ZIEL/$A.log" 2>&1
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

    # Der Harness meldet die Zahl selbst in der Schlusszeile -- kein Raten
    # anhand von Protokollzeilen wie bei den fremden Werkzeugen.
    WERKZEUGE=$(grep -oE '[0-9]+ Werkzeugaufrufen' "$ZIEL/$A.log" | tail -1 \
                | grep -oE '^[0-9]+')
    [ -z "$WERKZEUGE" ] && WERKZEUGE=0

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$A" "$DAUER" "$RC" "$BESTANDEN" "$GESAMT" "$WERKZEUGE" "$EIGEN" \
        >> "$ZIEL/ergebnis.tsv"
    echo "### $A fertig: ${DAUER}s rc=$RC verdeckt=${BESTANDEN}/${GESAMT}" \
        >> "$ZIEL/verlauf.log"
done

echo "FERTIG $(date +%H:%M:%S)" > "$ZIEL/.done"
