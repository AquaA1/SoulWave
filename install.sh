#!/usr/bin/env bash
# install.sh — Production-ready installer for Soulwave
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
# Options:
#   bash install.sh [--version <v>] [--file <path>] [--user|--system] [--wheel] [--uninstall]
set -euo pipefail

REPO="${SOULWAVE_REPO:-AquaA1/SoulWave}"
TARGET_VERSION="${SOULWAVE_VERSION:-}"
LOCAL_FILE="${SOULWAVE_FILE:-}"
INSTALL_MODE="auto" # auto, user, system
FORCE_WHEEL=0
NO_DEPS=0
DO_UNINSTALL=0
TMP_DIR=""

# Color formatting
if [ -t 1 ]; then
    BOLD="\033[1m"
    GREEN="\033[32m"
    BLUE="\033[34m"
    CYAN="\033[36m"
    YELLOW="\033[33m"
    RED="\033[31m"
    RESET="\033[0m"
else
    BOLD=""
    GREEN=""
    BLUE=""
    CYAN=""
    YELLOW=""
    RED=""
    RESET=""
fi

log_info()    { echo -e "${CYAN}==>${RESET} ${BOLD}$*${RESET}"; }
log_success() { echo -e "${GREEN}==>${RESET} ${BOLD}$*${RESET}"; }
log_warn()    { echo -e "${YELLOW}==> WARNING:${RESET} $*"; }
log_error()   { echo -e "${RED}==> ERROR:${RESET} $*" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version|-v)
            TARGET_VERSION="$2"
            shift 2
            ;;
        --file|-f)
            LOCAL_FILE="$2"
            shift 2
            ;;
        --user)
            INSTALL_MODE="user"
            shift
            ;;
        --system)
            INSTALL_MODE="system"
            shift
            ;;
        --wheel)
            FORCE_WHEEL=1
            shift
            ;;
        --no-deps)
            NO_DEPS=1
            shift
            ;;
        --uninstall)
            DO_UNINSTALL=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Soulwave Installer

USAGE:
    curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash
    ./install.sh [OPTIONS]

OPTIONS:
    --version, -v <tag>  Install specific release tag (e.g. v0.1.0)
    --file, -f <path>    Install from a local .rpm or .whl file
    --user               Install into user directory (~/.local/share/soulwave)
    --system             Install into system directory (/opt/soulwave or RPM)
    --wheel              Force wheel installation even on RPM distributions
    --uninstall          Uninstall Soulwave cleanly from the system
    --help, -h           Show this help message

ENVIRONMENT VARIABLES:
    SOULWAVE_REPO        GitHub repository (default: AquaA1/SoulWave)
    SOULWAVE_VERSION     Release tag to install
    SOULWAVE_FILE        Path to local archive to install
EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Run with --help for usage information."
            exit 1
            ;;
    esac
done

# Elevation helper
run_elevated() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        log_error "Root privileges are required for this action, but 'sudo' is not available."
        exit 1
    fi
}

# Uninstallation handler
uninstall_soulwave() {
    log_info "Uninstalling Soulwave..."
    local uninstalled=0

    # 1. Check for native RPM install
    if command -v rpm >/dev/null 2>&1 && rpm -q soulwave >/dev/null 2>&1; then
        log_info "Detected RPM installation. Removing via package manager..."
        if command -v dnf >/dev/null 2>&1; then
            run_elevated dnf remove -y soulwave
        else
            run_elevated rpm -e soulwave
        fi
        uninstalled=1
    fi

    # 2. Check for system /opt install
    if [ -d "/opt/soulwave" ] || [ -f "/usr/local/bin/soulwave" ]; then
        log_info "Removing system files in /opt/soulwave and /usr/local/bin/soulwave..."
        run_elevated rm -rf "/opt/soulwave" "/usr/local/bin/soulwave"
        uninstalled=1
    fi

    # 3. Check for user install
    local user_dir="${HOME}/.local/share/soulwave"
    local user_bin="${HOME}/.local/bin/soulwave"
    if [ -d "${user_dir}" ] || [ -f "${user_bin}" ]; then
        log_info "Removing user files in ${user_dir} and ${user_bin}..."
        rm -rf "${user_dir}" "${user_bin}"
        uninstalled=1
    fi

    if [ "${uninstalled}" -eq 1 ]; then
        log_success "Soulwave uninstalled successfully."
    else
        log_warn "No Soulwave installation found to remove."
    fi
    exit 0
}

if [ "${DO_UNINSTALL}" -eq 1 ]; then
    uninstall_soulwave
fi

# Detect platform and distribution
detect_os() {
    OS_NAME="unknown"
    OS_ID="unknown"
    OS_LIKE=""
    IS_RPM_DISTRO=0

    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_NAME="${NAME:-linux}"
        OS_ID="${ID:-unknown}"
        OS_LIKE="${ID_LIKE:-}"
    elif command -v uname >/dev/null 2>&1; then
        OS_NAME="$(uname -s)"
    fi

    case "${OS_ID}" in
        fedora|rhel|centos|rocky|almalinux)
            IS_RPM_DISTRO=1
            ;;
        *)
            if [[ "${OS_LIKE}" =~ (fedora|rhel) ]]; then
                IS_RPM_DISTRO=1
            fi
            ;;
    esac
}

# Check system prerequisites
check_prerequisites() {
    log_info "Checking system prerequisites..."
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 is required but was not found. Please install Python >= 3.10."
        exit 1
    fi

    # Check python version >= 3.10
    local py_ok
    py_ok="$(python3 -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)" 2>/dev/null || echo 0)"
    if [ "${py_ok}" != "1" ]; then
        log_error "Soulwave requires Python 3.10 or higher. Found: $(python3 --version 2>&1)"
        exit 1
    fi

    # Check optional recommended utilities
    local missing_recommended=()
    if ! command -v playerctl >/dev/null 2>&1; then
        missing_recommended+=("playerctl")
    fi
    if ! command -v cava >/dev/null 2>&1; then
        missing_recommended+=("cava")
    fi

    if [ ${#missing_recommended[@]} -gt 0 ]; then
        log_warn "Recommended audio utilities not found: ${missing_recommended[*]}"
        echo "    Soulwave works without them (using mock player / audio fallback),"
        echo "    but installing them enables full MPRIS music tracking and visualizer."
        if [ "${IS_RPM_DISTRO}" -eq 1 ]; then
            echo -e "    ${BOLD}Install command:${RESET} sudo dnf install ${missing_recommended[*]}"
        else
            echo -e "    ${BOLD}Install command:${RESET} sudo apt install ${missing_recommended[*]}  (or your package manager)"
        fi
        echo ""
    fi
}

# Secure curl wrapper ensuring HTTP errors fail immediately
curl_cmd() {
    curl --fail --show-error --location "$@"
}

# Download release assets from GitHub
fetch_release_assets() {
    local tmp_dir="$1"

    if ! command -v curl >/dev/null 2>&1; then
        log_error "'curl' is required to download release assets. Please install curl."
        exit 1
    fi

    local api_url
    if [ -n "${TARGET_VERSION}" ]; then
        api_url="https://api.github.com/repos/${REPO}/releases/tags/${TARGET_VERSION}"
    else
        api_url="https://api.github.com/repos/${REPO}/releases/latest"
    fi

    log_info "Querying GitHub release from ${api_url}..."
    local release_json="${tmp_dir}/release.json"

    if ! curl_cmd -sSL -o "${release_json}" "${api_url}" 2>/dev/null; then
        log_error "Failed to fetch release metadata from ${api_url}."
        if [ -n "${TARGET_VERSION}" ]; then
            echo "    Release tag '${TARGET_VERSION}' was not found on ${REPO}."
        else
            echo "    No published releases found yet on ${REPO}."
        fi
        echo "    If installing from a local file, use: ./install.sh --file <path>"
        exit 1
    fi

    # Parse tag and assets list using Python
    local parse_result="${tmp_dir}/parsed_assets.txt"
    python3 -c "
import sys, json
try:
    with open('${release_json}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    tag = data.get('tag_name', 'unknown')
    assets = data.get('assets', [])
    with open('${parse_result}', 'w', encoding='utf-8') as out:
        out.write(tag + '\n')
        for a in assets:
            out.write(f\"{a['name']} {a['browser_download_url']}\n\")
except Exception as e:
    sys.stderr.write(f'JSON parsing error: {e}\n')
    sys.exit(1)
" || {
        log_error "Could not parse GitHub release metadata JSON."
        exit 1
    }

    TAG_NAME="$(head -n 1 "${parse_result}")"
    log_info "Found release: ${BOLD}${TAG_NAME}${RESET}"

    # Download checksums.txt (fail-closed: MUST be present for release downloads)
    local checksums_url
    checksums_url="$(grep -E "^checksums\.txt[[:space:]]" "${parse_result}" | awk '{print $2}' || true)"
    if [ -z "${checksums_url}" ]; then
        log_error "Release ${TAG_NAME} does not contain 'checksums.txt'. Refusing to install unverified release (fail-closed)."
        exit 1
    fi

    log_info "Downloading checksums.txt..."
    if ! curl_cmd -sSL -o "${tmp_dir}/checksums.txt" "${checksums_url}"; then
        log_error "Failed to download checksums.txt from ${checksums_url}."
        exit 1
    fi

    # Determine which asset to download
    CHOSEN_ASSET=""
    local chosen_url=""
    local arch
    arch="$(uname -m 2>/dev/null || echo "x86_64")"

    if [ "${IS_RPM_DISTRO}" -eq 1 ] && [ "${FORCE_WHEEL}" -eq 0 ] && [ "${INSTALL_MODE}" != "user" ]; then
        # Check architecture-specific RPM first, then noarch, then any rpm
        CHOSEN_ASSET="$(grep -E "\.${arch}\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "\.${arch}\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $2}' || true)"
        if [ -z "${CHOSEN_ASSET}" ]; then
            CHOSEN_ASSET="$(grep -E "\.noarch\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $1}' || true)"
            chosen_url="$(grep -E "\.noarch\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $2}' || true)"
        fi
        if [ -z "${CHOSEN_ASSET}" ]; then
            CHOSEN_ASSET="$(grep -E "\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $1}' || true)"
            chosen_url="$(grep -E "\.rpm[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $2}' || true)"
        fi
    fi

    # Fallback to wheel
    if [ -z "${CHOSEN_ASSET}" ]; then
        CHOSEN_ASSET="$(grep -E "\.whl[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "\.whl[[:space:]]" "${parse_result}" | head -n 1 | awk '{print $2}' || true)"
    fi

    if [ -z "${CHOSEN_ASSET}" ] || [ -z "${chosen_url}" ]; then
        log_error "No suitable .rpm or .whl asset found in release ${TAG_NAME}."
        exit 1
    fi

    log_info "Downloading ${CHOSEN_ASSET}..."
    if ! curl_cmd -#SL -o "${tmp_dir}/${CHOSEN_ASSET}" "${chosen_url}"; then
        log_error "Failed to download asset ${CHOSEN_ASSET} from ${chosen_url}."
        exit 1
    fi
    DOWNLOADED_FILE="${tmp_dir}/${CHOSEN_ASSET}"
}

# Verify SHA-256 hash (strict fail-closed verification)
verify_checksum() {
    local target_file="$1"
    local checksums_file="$2"
    local filename
    filename="$(basename "${target_file}")"

    if [ ! -f "${checksums_file}" ]; then
        log_error "Checksums file '${checksums_file}' is missing. Cannot verify release asset (fail-closed)."
        return 1
    fi

    local expected_hash
    expected_hash="$(grep -E "[[:space:]]${filename}\$" "${checksums_file}" | awk '{print $1}' | tr -d ' \r\n' || true)"

    if [ -z "${expected_hash}" ]; then
        log_error "No checksum entry found for '${filename}' in checksums.txt! Aborting for security (fail-closed)."
        return 1
    fi

    if [[ ! "${expected_hash}" =~ ^[a-fA-F0-9]{64}$ ]]; then
        log_error "Invalid SHA-256 hash format for '${filename}' in checksums.txt: '${expected_hash}'."
        return 1
    fi

    log_info "Verifying SHA-256 checksum for ${filename}..."
    local actual_hash=""
    if command -v sha256sum >/dev/null 2>&1; then
        actual_hash="$(sha256sum "${target_file}" | awk '{print $1}' | tr -d ' \r\n')"
    elif command -v shasum >/dev/null 2>&1; then
        actual_hash="$(shasum -a 256 "${target_file}" | awk '{print $1}' | tr -d ' \r\n')"
    else
        actual_hash="$(python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "${target_file}" | tr -d ' \r\n')"
    fi

    if [ "${actual_hash}" != "${expected_hash}" ]; then
        log_error "Checksum verification failed for ${filename}!"
        echo "    Expected: ${expected_hash}" >&2
        echo "    Got:      ${actual_hash}" >&2
        return 1
    fi

    log_success "SHA-256 verified: ${actual_hash:0:16}..."
    return 0
}

# Install RPM package
install_rpm() {
    local rpm_file="$1"
    log_info "Installing native RPM package (${rpm_file})..."

    if command -v dnf >/dev/null 2>&1; then
        run_elevated dnf install -y "${rpm_file}"
    elif command -v rpm >/dev/null 2>&1; then
        run_elevated rpm -Uvh --force "${rpm_file}"
    else
        log_error "Neither dnf nor rpm found to install RPM package."
        exit 1
    fi
    LAST_INSTALLED_LAUNCHER="/usr/bin/soulwave"
}

# Install Wheel into an isolated directory
install_wheel() {
    local wheel_file="$1"
    local install_dir=""
    local bin_dir=""
    local needs_sudo=0

    if [ "${INSTALL_MODE}" = "user" ]; then
        install_dir="${HOME}/.local/share/soulwave"
        bin_dir="${HOME}/.local/bin"
    elif [ "$(id -u)" -eq 0 ]; then
        install_dir="/opt/soulwave"
        bin_dir="/usr/local/bin"
    elif command -v sudo >/dev/null 2>&1 && [ "${INSTALL_MODE}" != "user" ]; then
        install_dir="/opt/soulwave"
        bin_dir="/usr/local/bin"
        needs_sudo=1
    else
        install_dir="${HOME}/.local/share/soulwave"
        bin_dir="${HOME}/.local/bin"
    fi

    log_info "Installing Soulwave to ${install_dir}..."

    local pip_opts=("--no-warn-script-location" "--upgrade")
    if [ "${NO_DEPS}" -eq 1 ]; then
        pip_opts+=("--no-deps")
    fi

    # Setup directories and isolated virtualenv
    if [ "${needs_sudo}" -eq 1 ]; then
        run_elevated mkdir -p "${install_dir}" "${bin_dir}"
        run_elevated python3 -m venv --system-site-packages "${install_dir}"
        run_elevated "${install_dir}/bin/python3" -m pip install "${pip_opts[@]}" "${wheel_file}"

        # Write launcher
        local launcher_tmp
        launcher_tmp="$(mktemp)"
        cat <<EOF > "${launcher_tmp}"
#!/bin/sh
exec "${install_dir}/bin/python3" -m soulwave.cli "\$@"
EOF
        run_elevated cp "${launcher_tmp}" "${bin_dir}/soulwave"
        run_elevated chmod 0755 "${bin_dir}/soulwave"
        rm -f "${launcher_tmp}"
    else
        mkdir -p "${install_dir}" "${bin_dir}"
        python3 -m venv --system-site-packages "${install_dir}"
        "${install_dir}/bin/python3" -m pip install "${pip_opts[@]}" "${wheel_file}"

        cat <<EOF > "${bin_dir}/soulwave"
#!/bin/sh
exec "${install_dir}/bin/python3" -m soulwave.cli "\$@"
EOF
        chmod 0755 "${bin_dir}/soulwave"
    fi
    LAST_INSTALLED_LAUNCHER="${bin_dir}/soulwave"

    # Verify PATH
    if [[ ":${PATH}:" != *":${bin_dir}:"* ]]; then
        log_warn "${bin_dir} is not currently in your PATH."
        echo "    Add it to your current session using: export PATH=\"${bin_dir}:\$PATH\""
    fi
}

main() {
    echo -e "${CYAN}${BOLD}"
    echo "  ╔═══════════════════════════════════════════╗"
    echo "  ║          Soulwave Installer               ║"
    echo "  ╚═══════════════════════════════════════════╝"
    echo -e "${RESET}"

    detect_os
    log_info "Detected OS: ${BOLD}${OS_NAME}${RESET}"

    check_prerequisites

    TMP_DIR="$(mktemp -d -t soulwave-install-XXXXXX)"
    trap 'rm -rf "${TMP_DIR:-}"' EXIT INT TERM

    local package_file=""
    if [ -n "${LOCAL_FILE}" ]; then
        if [ ! -f "${LOCAL_FILE}" ]; then
            log_error "Specified local file not found: ${LOCAL_FILE}"
            exit 1
        fi
        log_info "Installing from local file: ${BOLD}${LOCAL_FILE}${RESET}"
        log_warn "Local-file mode trusts the specified file on disk without remote checksum verification."
        package_file="${LOCAL_FILE}"
    else
        fetch_release_assets "${TMP_DIR}"
        package_file="${DOWNLOADED_FILE}"
        if ! verify_checksum "${package_file}" "${TMP_DIR}/checksums.txt"; then
            log_error "Release asset checksum verification failed closed. Aborting installation."
            exit 1
        fi
    fi

    case "${package_file}" in
        *.rpm)
            install_rpm "${package_file}"
            ;;
        *.whl)
            install_wheel "${package_file}"
            ;;
        *)
            log_error "Unrecognized package format: ${package_file}. Expected .rpm or .whl."
            exit 1
            ;;
    esac

    # Post-installation verification health check
    if [ "${NO_DEPS}" -eq 1 ]; then
        log_warn "Installed with --no-deps. Skipping full runtime health check."
    else
        log_info "Verifying installed Soulwave runtime and resources..."
        local launcher_to_check="${LAST_INSTALLED_LAUNCHER:-}"
        if [ -z "${launcher_to_check}" ] || [ ! -x "${launcher_to_check}" ]; then
            if command -v soulwave >/dev/null 2>&1; then
                launcher_to_check="$(command -v soulwave)"
            elif [ -x "/usr/local/bin/soulwave" ]; then
                launcher_to_check="/usr/local/bin/soulwave"
            elif [ -x "/usr/bin/soulwave" ]; then
                launcher_to_check="/usr/bin/soulwave"
            elif [ -x "${HOME}/.local/bin/soulwave" ]; then
                launcher_to_check="${HOME}/.local/bin/soulwave"
            fi
        fi

        if [ -z "${launcher_to_check}" ] || [ ! -x "${launcher_to_check}" ]; then
            log_error "Installation health check failed: Soulwave launcher not found."
            exit 1
        fi

        local check_out
        if ! check_out="$("${launcher_to_check}" --check 2>&1)"; then
            log_error "Installation health check failed! The installed Soulwave package is unable to start or is missing required runtime resources:"
            echo "${check_out}" >&2
            echo "" >&2
            log_error "Please ensure all Python dependencies and required system packages are installed."
            exit 1
        fi
        log_success "Post-installation health check passed."
    fi

    echo ""
    log_success "Soulwave installed successfully!"
    echo -e "  To launch Soulwave, simply run:  ${GREEN}${BOLD}soulwave${RESET}"
    echo -e "  For help and keybindings:        ${CYAN}soulwave --help${RESET}"
    echo -e "  To uninstall anytime:            ${YELLOW}install.sh --uninstall${RESET}"
    echo ""
}

if [[ "${BASH_SOURCE[0]:-}" == "${0}" || -z "${BASH_SOURCE[0]:-}" ]]; then
    main "$@"
fi
