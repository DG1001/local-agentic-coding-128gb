#!/bin/bash
# bereit.sh — is the engine actually answering? Sourced by the run scripts.
#
# vLLM wedges. Twice on this machine, after roughly 900-950 requests, both
# times shortly after a client was killed mid-request:
#
#     /v1/models          answers
#     /metrics            answers, one request "running", none waiting
#     GPU                 96 %
#     /v1/chat/completions  times out, forever
#     docker logs         not one error line
#
# It is a known, open vLLM problem with no root cause and no fix
# (vllm-project/vllm#50880, #32262). Waiting for a release is not a plan.
# Catching it before a measurement starts is.
#
# The cost of missing it is not a failed run — it is a run that looks like a
# slow model. A throughput measurement here read "28 minutes" when the engine
# had been dead for 27 of them.
#
#     motor_bereit <base-url> <model-id>     0 = answering, 1 = give up
#
# On a timeout the vLLM container is restarted once and the probe repeated.
# ds4-server (port 8888) is not restarted: it is not a container here, and a
# wrong restart would be worse than an honest abort.

# Eine kurze Anfrage mit harter Zeitgrenze. Vier Token, damit die Probe auch
# bei einem langsamen Modell in Sekunden durch ist -- gemessen wird nicht die
# Geschwindigkeit, sondern ob ueberhaupt geantwortet wird.
_probe() {
    local url="$1" modell="$2" frist="${3:-30}"
    curl -sf -m "$frist" -o /dev/null \
        -H 'Content-Type: application/json' \
        -d "{\"model\":\"$modell\",\"max_tokens\":4,\"temperature\":0,
             \"messages\":[{\"role\":\"user\",\"content\":\"ok\"}]}" \
        "$url/chat/completions"
}

motor_bereit() {
    local url="$1" modell="$2"
    _probe "$url" "$modell" 30 && return 0

    echo "  Motor antwortet nicht -- Probe nach 30 s ohne Antwort." >&2
    case "$url" in
        *8889*)
            docker ps --format '{{.Names}}' 2>/dev/null | grep -qx vllm-model || {
                echo "  Kein Container vllm-model, kein Neustart moeglich." >&2
                return 1
            }
            echo "  Starte vllm-model neu ..." >&2
            docker restart vllm-model >/dev/null 2>&1
            for _ in $(seq 1 60); do
                sleep 10
                curl -sf -m 3 "$url/models" >/dev/null 2>&1 || continue
                _probe "$url" "$modell" 60 && { echo "  Motor wieder da." >&2; return 0; }
            done
            echo "  Motor kam nach dem Neustart nicht zurueck." >&2
            return 1 ;;
        *)
            echo "  Kein automatischer Neustart fuer $url -- von Hand nachsehen." >&2
            return 1 ;;
    esac
}
