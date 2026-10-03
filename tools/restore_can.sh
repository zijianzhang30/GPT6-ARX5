#!/usr/bin/env bash
# Recover only the known CANable link. Never initialize the robot SDK.
set -euo pipefail

adapter='/dev/serial/by-id/usb-Openlight_Labs_CANable2_b158aa7_github.com_normaldotcom_canable2.git_208833765931-if00'
worker='/home/tuojing/arx_r5_control/robot_worker.py'

if [[ $EUID != 0 ]]; then
    echo 'Administrator authorization is required; run this script with sudo or pkexec.' >&2
    exit 1
fi
if [[ ! -c "$adapter" ]]; then
    echo 'The expected CANable serial device is missing; nothing changed.' >&2
    exit 1
fi
if [[ -e /sys/class/net/can0 ]]; then
    echo 'can0 already exists; refusing to replace a potentially active connection.' >&2
    exit 1
fi

stale_pids=()
for entry in /proc/[0-9]*/cmdline; do
    args=()
    if ! mapfile -d '' -t args < "$entry" 2>/dev/null; then
        continue
    fi
    worker_arg=0
    for arg in "${args[@]}"; do
        if [[ "$arg" == "$worker" || "$arg" == 'robot_worker.py' ]]; then
            worker_arg=1
            break
        fi
    done
    # Keep the other arm online; only a worker bound to can0 blocks this recovery.
    if [[ $worker_arg == 1 && ${args[-1]:-} == can0 ]]; then
        echo 'Left-arm Robot SDK worker is still running. Disconnect it before restoring CAN.' >&2
        exit 1
    fi
    if [[ ${#args[@]} == 6 && ${args[0]##*/} == slcand &&
          ${args[1]} == -o && ${args[2]} == -f && ${args[3]} == -s8 &&
          ${args[4]} == "$adapter" && ${args[5]} == can0 ]]; then
        pid=${entry#/proc/}
        stale_pids+=("${pid%/cmdline}")
    fi
done

for pid in "${stale_pids[@]}"; do
    args=()
    if ! mapfile -d '' -t args < "/proc/$pid/cmdline" 2>/dev/null; then
        continue
    fi
    if [[ ${#args[@]} != 6 || ${args[0]##*/} != slcand ||
          ${args[1]} != -o || ${args[2]} != -f || ${args[3]} != -s8 ||
          ${args[4]} != "$adapter" || ${args[5]} != can0 ]]; then
        echo "Process $pid changed; aborting without signalling it." >&2
        exit 1
    fi
    kill -TERM "$pid"
    echo "Requested exit of stale CAN bridge PID $pid."
done

for attempt in {1..30}; do
    remaining=0
    for pid in "${stale_pids[@]}"; do
        if [[ -e /proc/$pid/cmdline ]]; then
            remaining=1
        fi
    done
    if [[ $remaining == 0 ]]; then
        break
    fi
    sleep .1
done
if [[ ${remaining:-0} != 0 ]]; then
    echo 'A stale bridge has not exited; no replacement was started.' >&2
    exit 1
fi
if /usr/bin/fuser "$adapter" >/dev/null 2>&1; then
    echo 'The adapter is still owned by another process; nothing further changed.' >&2
    exit 1
fi

/usr/bin/slcand -o -f -s8 "$adapter" can0
for attempt in {1..30}; do
    if [[ -e /sys/class/net/can0 ]]; then
        break
    fi
    sleep .1
done
if [[ ! -e /sys/class/net/can0 ]]; then
    echo 'The new bridge did not create can0. Inspect processes before retrying.' >&2
    exit 1
fi
/usr/sbin/ip link set can0 up
/usr/sbin/ip -details -statistics link show can0
echo 'CAN interface restored. Robot SDK remains disconnected; no homing was requested.'
