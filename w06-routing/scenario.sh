#!/usr/bin/env bash
# OSPF reconvergence lab.
#
#   bash scenario.sh up        Start the three-router topology
#   bash scenario.sh routes    Save and display all routing tables
#   bash scenario.sh cut       Measure convergence after taking r1-r2 down
#   bash scenario.sh restore  Measure convergence after restoring r1-r2
#   bash scenario.sh cost     Measure convergence after changing OSPF cost
#   bash scenario.sh down     Stop the topology
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/out"
DOCKER_BIN="${DOCKER_BIN:-docker}"
PROJECT_DIR="$SCRIPT_DIR"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
if [[ "$DOCKER_BIN" == *.exe ]] && command -v wslpath >/dev/null 2>&1; then
  PROJECT_DIR="$(wslpath -w "$SCRIPT_DIR")"
  COMPOSE_FILE="$(wslpath -w "$SCRIPT_DIR/docker-compose.yml")"
fi
COMPOSE=("$DOCKER_BIN" compose --project-directory "$PROJECT_DIR" -f "$COMPOSE_FILE")
POLL_SECONDS="${POLL_SECONDS:-0.25}"
STABLE_POLLS="${STABLE_POLLS:-3}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"
mkdir -p "$OUT"

capture_routes() {
  local router
  for router in r1 r2 r3; do
    printf '===== %s =====\n' "$router"
    "${COMPOSE[@]}" exec -T "$router" vtysh -c "show ip route ospf"
  done
}

route_signature() {
  sed -n -E \
    -e 's/, [0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?$//' \
    -e '/^O[ >*!]/p' \
    -e '/^  \*/p'
}

elapsed_seconds() {
  awk -v ms="$1" 'BEGIN { printf "%.2f", ms / 1000 }'
}

clock_ms() {
  local timestamp="${EPOCHREALTIME:-}"
  if [[ "$timestamp" == *.* ]]; then
    local seconds="${timestamp%%.*}"
    local fraction="${timestamp#*.}000"
    printf '%s%03d' "$seconds" "$((10#${fraction:0:3}))"
  else
    printf '%s000' "$(date +%s)"
  fi
}

wait_for_stable_routes() {
  local baseline="${1:-}"
  local result_file="$2"
  local start_ms="${3:-$(clock_ms)}"
  local current_ms deadline_ms stable_count=0
  local previous_signature="" signature

  deadline_ms=$((start_ms + TIMEOUT_SECONDS * 1000))
  while :; do
    capture_routes > "$result_file"
    signature="$(route_signature < "$result_file")"
    current_ms="$(clock_ms)"

    if [[ "$signature" == "$previous_signature" ]]; then
      stable_count=$((stable_count + 1))
    else
      stable_count=1
      previous_signature="$signature"
    fi

    if [[ -n "$signature" ]] && (( stable_count >= STABLE_POLLS )) &&
       routes_complete "$result_file" &&
       { [[ -z "$baseline" ]] || [[ "$signature" != "$baseline" ]]; }; then
      printf '%s' "$((current_ms - start_ms))"
      return 0
    fi

    if (( current_ms >= deadline_ms )); then
      return 1
    fi
    sleep "$POLL_SECONDS"
  done
}

read_signature() {
  route_signature < "$1"
}

routes_complete() {
  awk '
    /^===== r1 =====/ { router = "r1"; next }
    /^===== r2 =====/ { router = "r2"; next }
    /^===== r3 =====/ { router = "r3"; next }
    router == "r1" && $2 == "172.19.0.0/16" { r1 = 1 }
    router == "r2" && $2 == "172.21.0.0/16" { r2 = 1 }
    router == "r3" && $2 == "172.20.0.0/16" { r3 = 1 }
    END { exit !(r1 && r2 && r3) }
  ' "$1"
}

fail_timeout() {
  local event="$1"
  printf '%s\n' \
    "$event: no stable, changed all-router route table within ${TIMEOUT_SECONDS}s." \
    | tee "$OUT/reconverge.txt"
  return 1
}

case "${1:-}" in
  up)
    "${COMPOSE[@]}" up -d
    echo "Waiting for stable OSPF routes, including remote networks, on all three routers..."
    start_ms="$(clock_ms)"
    deadline_ms=$((start_ms + TIMEOUT_SECONDS * 1000))
    stable_count=0
    previous_signature=""
    while :; do
      capture_routes > "$OUT/route-before.txt"
      signature="$(read_signature "$OUT/route-before.txt")"
      if [[ -n "$signature" && "$signature" == "$previous_signature" ]]; then
        stable_count=$((stable_count + 1))
      else
        stable_count=1
        previous_signature="$signature"
      fi
      if (( stable_count >= STABLE_POLLS )) && routes_complete "$OUT/route-before.txt"; then
        break
      fi
      if (( $(clock_ms) >= deadline_ms )); then
        echo "OSPF routes did not converge on all routers before the timeout." >&2
        exit 1
      fi
      sleep "$POLL_SECONDS"
    done
    if routes_complete "$OUT/route-before.txt"; then
      echo "OSPF routes are stable. Initial tables saved to out/route-before.txt."
      "${COMPOSE[@]}" exec -T r1 vtysh -c "show ip ospf neighbor"
      {
        echo "OSPF timer configuration on r1:"
        "${COMPOSE[@]}" exec -T r1 vtysh -c "show ip ospf interface eth0"
        "${COMPOSE[@]}" exec -T r1 vtysh -c "show ip ospf interface eth1"
      } > "$OUT/ospf-timers.txt"
    else
      echo "OSPF routes did not stabilize before the timeout." >&2
      exit 1
    fi
    ;;

  routes)
    capture_routes | tee "$OUT/routes-latest.txt"
    ;;

  cut)
    capture_routes > "$OUT/route-before.txt"
    baseline="$(read_signature "$OUT/route-before.txt")"
    echo "Taking r1 eth1 (the r1-r2 link) down."
    start_ms="$(clock_ms)"
    "${COMPOSE[@]}" exec -T r1 ip link set eth1 down
    if elapsed_ms="$(wait_for_stable_routes "$baseline" "$OUT/route-after.txt" "$start_ms")"; then
      {
        echo "Failure: r1 eth1 down -> all three OSPF routing tables changed and stabilized."
        echo "Polling interval: ${POLL_SECONDS}s; stable samples: $STABLE_POLLS."
        echo "Measured convergence: $(elapsed_seconds "$elapsed_ms") s."
      } | tee "$OUT/reconverge.txt"
    else
      fail_timeout "Failure"
    fi
    ;;

  restore)
    [[ -s "$OUT/route-after.txt" && -s "$OUT/route-before.txt" ]] || {
      echo "No cut snapshots; run 'cut' before 'restore'." >&2
      exit 1
    }
    baseline="$(read_signature "$OUT/route-after.txt")"
    start_ms="$(clock_ms)"
    "${COMPOSE[@]}" exec -T r1 ip link set eth1 up
    if elapsed_ms="$(wait_for_stable_routes "$baseline" "$OUT/route-restored.txt" "$start_ms")"; then
      if ! grep -Fq '172.20.0.0/16 [110/10] is directly connected, eth1' "$OUT/route-restored.txt"; then
        echo "Restoration converged, but r1 eth1's directly connected route is missing." >&2
        exit 1
      fi
      {
        echo "Restoration: r1 eth1 up -> all three OSPF routing tables changed and stabilized."
        echo "Polling interval: ${POLL_SECONDS}s; stable samples: $STABLE_POLLS."
        echo "Measured restoration convergence: $(elapsed_seconds "$elapsed_ms") s."
      } | tee "$OUT/link-restore.txt"
    else
      fail_timeout "Restoration"
    fi
    ;;

  cost)
    capture_routes > "$OUT/route-cost-before.txt"
    baseline="$(read_signature "$OUT/route-cost-before.txt")"
    start_ms="$(clock_ms)"
    echo "Changing r1 eth0 OSPF cost from 10 to 100 without taking the link down."
    "${COMPOSE[@]}" exec -T r1 vtysh \
      -c "configure terminal" -c "interface eth0" -c "ip ospf cost 100"
    if elapsed_ms="$(wait_for_stable_routes "$baseline" "$OUT/route-cost-after.txt" "$start_ms")"; then
      {
        echo "Cost change: r1 eth0 OSPF cost 10 -> 100; link remained up."
        echo "Polling interval: ${POLL_SECONDS}s; stable samples: $STABLE_POLLS."
        echo "Measured all-router convergence: $(elapsed_seconds "$elapsed_ms") s."
      } | tee "$OUT/cost-change.txt"
    else
      fail_timeout "Cost change"
    fi
    ;;

  down)
    "${COMPOSE[@]}" down
    ;;

  *)
    sed -n '2,10p' "$SCRIPT_DIR/scenario.sh"
    exit 2
    ;;
esac
