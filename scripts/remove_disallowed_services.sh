#!/usr/bin/env bash
set -euo pipefail

disallowed_containers=(earnapp)

if command -v docker >/dev/null 2>&1; then
  for name in "${disallowed_containers[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -Fxq "$name"; then
      docker rm -f "$name" >/dev/null
      echo "Removed container: $name"
    fi
  done
else
  echo "Docker not found; skipping container cleanup."
fi

if command -v systemctl >/dev/null 2>&1; then
  mapfile -t units < <(systemctl list-unit-files --no-pager --no-legend 2>/dev/null | awk '{print $1}' | grep -E '^earnapp(\.service)?$' || true)
  for unit in "${units[@]}"; do
    systemctl stop "$unit" >/dev/null 2>&1 || true
    systemctl disable "$unit" >/dev/null 2>&1 || true
    echo "Stopped/disabled unit: $unit"
  done
fi

if command -v earnapp >/dev/null 2>&1; then
  bin_path="$(command -v earnapp || true)"
  if [[ -n "${bin_path}" && -f "${bin_path}" ]]; then
    rm -f "${bin_path}"
    echo "Removed earnapp binary: ${bin_path}"
  fi
fi
