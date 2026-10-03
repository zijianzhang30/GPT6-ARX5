#!/usr/bin/env bash
set -euo pipefail
adapter='/dev/serial/by-id/usb-Openlight_Labs_CANable2_b158aa7_github.com_normaldotcom_canable2.git_208833765931-if00'
if [[ ! -e "$adapter" ]]; then
    echo '未找到 CANable2（序列号 208833765931），请检查 USB 连接。' >&2
    exit 1
fi
if ! ip link show can0 >/dev/null 2>&1; then
    sudo slcand -o -f -s8 "$adapter" can0
fi
sudo ip link set can0 up
ip -brief link show can0
