#!/usr/bin/env bash
# build_rpm.sh — Build standalone Fedora RPM package for Soulwave with complete bundled dependencies
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VERSION="${1:-0.1.5}"
RELEASE="${2:-1}"
TMP_BUILD_DIR="/tmp/soulwave-rpmbuild-$$"
DIST_DIR="${PROJECT_ROOT}/dist"
SPEC_FILE="${PROJECT_ROOT}/packaging/rpm/soulwave.spec"
VENDOR_CACHE_DIR="${PROJECT_ROOT}/packaging/rpm/vendor_wheels"

# Find python interpreter capable of building wheels and downloading dependencies
PYTHON="python3"
if [ -x "${PROJECT_ROOT}/.venv/bin/python" ]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
fi

echo "==> Building Soulwave RPM v${VERSION}-${RELEASE} with ${PYTHON}..."

trap 'rm -rf "${TMP_BUILD_DIR}"' EXIT

# Clean and prepare build dirs
rm -rf "${TMP_BUILD_DIR}"
mkdir -p "${TMP_BUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p "${TMP_BUILD_DIR}/SOURCES/vendor_wheels"
mkdir -p "${DIST_DIR}"

# Build soulwave wheel into dist
echo "==> Building Soulwave wheel..."
"${PYTHON}" -m pip wheel --no-build-isolation --no-deps -w "${DIST_DIR}" "${PROJECT_ROOT}"

# Copy soulwave wheel to SOURCES
WHEEL_FILE="${DIST_DIR}/soulwave-${VERSION}-py3-none-any.whl"
if [ ! -f "${WHEEL_FILE}" ]; then
    echo "ERROR: Soulwave wheel file ${WHEEL_FILE} not found." >&2
    exit 1
fi
cp "${WHEEL_FILE}" "${TMP_BUILD_DIR}/SOURCES/soulwave-${VERSION}-py3-none-any.whl"

# Resolve vendor wheels:
# 1. Use local cache directory if available
# 2. Or download complete transitive dependencies if online
if [ ! -d "${VENDOR_CACHE_DIR}" ] || ! compgen -G "${VENDOR_CACHE_DIR}/*.whl" > /dev/null; then
    echo "==> Downloading transitive runtime dependency wheels..."
    mkdir -p "${VENDOR_CACHE_DIR}"
    if ! "${PYTHON}" -m pip download --only-binary=:all: --dest "${VENDOR_CACHE_DIR}" "${PROJECT_ROOT}"; then
        echo "ERROR: Failed to download dependency wheels and no cached wheels were found." >&2
        exit 1
    fi
fi

# Verify all mandatory runtime dependencies are present in vendor_wheels
REQUIRED_DEPS=("textual" "rich" "syncedlyrics" "requests")
for dep in "${REQUIRED_DEPS[@]}"; do
    if ! ls "${VENDOR_CACHE_DIR}"/${dep}-*.whl >/dev/null 2>&1 && ! ls "${VENDOR_CACHE_DIR}"/${dep}_*.whl >/dev/null 2>&1; then
        echo "ERROR: Required runtime dependency wheel for '${dep}' is missing in ${VENDOR_CACHE_DIR}." >&2
        exit 1
    fi
done

echo "==> Populating SOURCES/vendor_wheels with complete dependency set..."
cp "${VENDOR_CACHE_DIR}"/*.whl "${TMP_BUILD_DIR}/SOURCES/vendor_wheels/"

# Copy spec, doc and license
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

# Verify generated RPM metadata
echo "==> Verifying generated RPM package metadata..."
BUILT_RPM_FILE="$(find "${TMP_BUILD_DIR}/RPMS" -name "*.rpm" | head -n 1)"
if [ -z "${BUILT_RPM_FILE}" ]; then
    echo "ERROR: No RPM was produced by rpmbuild." >&2
    exit 1
fi
ACTUAL_RPM_VERSION="$(rpm -qp --queryformat '%{VERSION}' "${BUILT_RPM_FILE}")"
if [ "${ACTUAL_RPM_VERSION}" != "${VERSION}" ]; then
    echo "ERROR: Version mismatch in generated RPM! Expected version '${VERSION}', but RPM metadata has '${ACTUAL_RPM_VERSION}'." >&2
    exit 1
fi
echo "==> Verified RPM version matches expected: ${ACTUAL_RPM_VERSION}"

# Collect built RPMs
echo "==> Collecting built packages..."
find "${TMP_BUILD_DIR}/RPMS" -name "*.rpm" -exec cp -v {} "${DIST_DIR}/" \;

echo "==> Successfully built standalone RPM in ${DIST_DIR}:"
ls -la "${DIST_DIR}"/*.rpm
