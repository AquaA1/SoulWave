#!/usr/bin/env bash
# build_rpm.sh — Build standalone Fedora RPM package for Soulwave
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VERSION="${1:-0.1.0}"
RELEASE="${2:-1}"
TMP_BUILD_DIR="/tmp/soulwave-rpmbuild-$$"
DIST_DIR="${PROJECT_ROOT}/dist"
SPEC_FILE="${PROJECT_ROOT}/packaging/rpm/soulwave.spec"

# Find python interpreter capable of building wheels
PYTHON="python3"
if [ -x "${PROJECT_ROOT}/.venv/bin/python" ]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
fi

echo "==> Building Soulwave RPM v${VERSION}-${RELEASE} with ${PYTHON}..."

trap 'rm -rf "${TMP_BUILD_DIR}"' EXIT

# Clean and prepare build dirs
rm -rf "${TMP_BUILD_DIR}"
mkdir -p "${TMP_BUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p "${DIST_DIR}"

# Build wheel into dist
echo "==> Building python wheel..."
"${PYTHON}" -m pip wheel --no-build-isolation --no-deps -w "${DIST_DIR}" "${PROJECT_ROOT}"

# Copy sources for rpmbuild
WHEEL_FILE="${DIST_DIR}/soulwave-${VERSION}-py3-none-any.whl"
if [ ! -f "${WHEEL_FILE}" ]; then
    echo "Error: Wheel file ${WHEEL_FILE} not found." >&2
    exit 1
fi

cp "${WHEEL_FILE}" "${TMP_BUILD_DIR}/SOURCES/soulwave-${VERSION}-py3-none-any.whl"
cp "${PROJECT_ROOT}/README.md" "${TMP_BUILD_DIR}/SOURCES/README.md"
cp "${PROJECT_ROOT}/LICENSE" "${TMP_BUILD_DIR}/SOURCES/LICENSE"
cp "${SPEC_FILE}" "${TMP_BUILD_DIR}/SPECS/soulwave.spec"

# Build RPM using /tmp for both _topdir and _tmppath
echo "==> Running rpmbuild..."
rpmbuild -bb \
    --define "_topdir ${TMP_BUILD_DIR}" \
    --define "_tmppath /tmp" \
    --define "version ${VERSION}" \
    --define "release ${RELEASE}" \
    "${TMP_BUILD_DIR}/SPECS/soulwave.spec"

# Collect built RPMs
echo "==> Collecting built packages..."
find "${TMP_BUILD_DIR}/RPMS" -name "*.rpm" -exec cp -v {} "${DIST_DIR}/" \;

echo "==> Successfully built RPMs in ${DIST_DIR}:"
ls -la "${DIST_DIR}"/*.rpm
