#!/usr/bin/env bash
# build_binary.sh — Build standalone single-file Linux executable for SoulWave using PyInstaller
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
BUILD_DIR="${REPO_ROOT}/build/pyinstaller"

RAW_ARCH="$(uname -m 2>/dev/null || echo "x86_64")"
case "${RAW_ARCH}" in
    x86_64|amd64)
        TARGET_ARCH="x86_64"
        ;;
    aarch64|arm64|armv8*)
        TARGET_ARCH="aarch64"
        ;;
    *)
        TARGET_ARCH="${RAW_ARCH}"
        ;;
esac

TARGET_ARCH="${1:-${TARGET_ARCH}}"
OUTPUT_NAME="soulwave-linux-${TARGET_ARCH}"

echo "===================================================="
echo " Building Standalone Executable for SoulWave"
echo " Architecture: ${TARGET_ARCH}"
echo " Output File:  dist/${OUTPUT_NAME}"
echo "===================================================="

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "ERROR: 'pyinstaller' is required to build standalone executables." >&2
    echo "Install it with: pip install pyinstaller" >&2
    exit 1
fi

mkdir -p "${DIST_DIR}" "${BUILD_DIR}"

# Run PyInstaller
pyinstaller \
    --name "${OUTPUT_NAME}" \
    --onefile \
    --clean \
    --noconfirm \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}" \
    --specpath "${SCRIPT_DIR}" \
    --paths "${REPO_ROOT}" \
    --add-data "${REPO_ROOT}/soulwave/ui/styles.tcss:soulwave/ui" \
    --collect-all soulwave \
    --collect-all textual \
    --collect-all rich \
    "${SCRIPT_DIR}/entrypoint.py"

OUTPUT_PATH="${DIST_DIR}/${OUTPUT_NAME}"
if [ ! -f "${OUTPUT_PATH}" ]; then
    echo "ERROR: Expected output executable ${OUTPUT_PATH} not found!" >&2
    exit 1
fi

chmod 0755 "${OUTPUT_PATH}"

echo "==> Successfully built standalone binary: ${OUTPUT_PATH}"
ls -lh "${OUTPUT_PATH}"
if command -v sha256sum >/dev/null 2>&1; then
    echo -n "SHA-256: "
    sha256sum "${OUTPUT_PATH}"
fi
