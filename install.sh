#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "${ROOT_DIR}"

if [ "$(uname -s)" != "Linux" ]; then
  echo "ERROR: This installer supports Linux hosts only (Debian/Ubuntu with systemd)."
  echo "Current OS: $(uname -s)"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "ERROR: systemctl not found. This project requires systemd."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: apt-get not found. This installer currently supports Debian/Ubuntu-based distributions only."
  exit 1
fi

if [ ! -f "${ROOT_DIR}/setup.sh" ]; then
  echo "ERROR: setup.sh not found in ${ROOT_DIR}"
  exit 1
fi

if [ ! -f "${ROOT_DIR}/requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in ${ROOT_DIR}"
  exit 1
fi

if [ "${EUID}" -eq 0 ]; then
  exec bash "${ROOT_DIR}/setup.sh"
fi

if command -v sudo >/dev/null 2>&1; then
  exec sudo bash "${ROOT_DIR}/setup.sh"
fi

echo "ERROR: This installer requires root privileges (sudo not found and not running as root)."
exit 1
