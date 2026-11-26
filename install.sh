#!/usr/bin/env bash
# install.sh — Universal, production-ready installer and setup assistant for Soulwave
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
# Options:
#   bash install.sh [--version <v>] [--file <path>] [--binary|--rpm|--wheel] [--user|--system] [--uninstall] [--repair]
set -euo pipefail

REPO="${SOULWAVE_REPO:-AquaA1/SoulWave}"
TARGET_VERSION="${SOULWAVE_VERSION:-}"
LOCAL_FILE="${SOULWAVE_FILE:-}"
INSTALL_SCOPE="user" # user (default, rootless) or system
INSTALL_SCOPE_EXPLICIT=0
INSTALL_FORMAT="auto" # auto (prefers binary), binary, rpm, wheel
NO_DEPS=0
DO_UNINSTALL=0
DO_REPAIR=0
TMP_DIR=""
LAST_INSTALLED_LAUNCHER=""

# Color formatting
if [ -t 1 ]; then
    BOLD="\033[1m"
    GREEN="\033[32m"
    BLUE="\033[34m"
    CYAN="\033[36m"
    YELLOW="\033[33m"
    RED="\033[31m"
    DIM="\033[2m"
    RESET="\033[0m"
else
    BOLD=""
    GREEN=""
    BLUE=""
    CYAN=""
    YELLOW=""
    RED=""
    DIM=""
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
            if [ $# -lt 2 ] || [[ "$2" == --* ]] || [[ "$2" == -* ]]; then
                log_error "Option '$1' requires a version argument (e.g. v0.2.0)."
                exit 1
            fi
            TARGET_VERSION="$2"
            shift 2
            ;;
        --file|-f)
            if [ $# -lt 2 ] || [[ "$2" == --* ]] || [[ "$2" == -* ]]; then
                log_error "Option '$1' requires a file path argument."
                exit 1
            fi
            LOCAL_FILE="$2"
            shift 2
            ;;
        --binary)
            INSTALL_FORMAT="binary"
            shift
            ;;
        --rpm)
            INSTALL_FORMAT="rpm"
            shift
            ;;
        --wheel)
            INSTALL_FORMAT="wheel"
            shift
            ;;
        --user)
            INSTALL_SCOPE="user"
            INSTALL_SCOPE_EXPLICIT=1
            shift
            ;;
        --system)
            INSTALL_SCOPE="system"
            INSTALL_SCOPE_EXPLICIT=1
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
        --repair)
            DO_REPAIR=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Soulwave Installer & Setup Assistant

USAGE:
    curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash
    ./install.sh [OPTIONS]

OPTIONS:
    --binary             Install standalone binary executable (default: universal, no Python required)
    --rpm                Install native RPM package (Fedora, RHEL, openSUSE)
    --wheel              Install via Python wheel into isolated virtual environment
    --version, -v <tag>  Install specific release tag (e.g. v0.2.0)
    --file, -f <path>    Install from a local standalone binary, .rpm, or .whl file
    --user               Install into user directory (~/.local/bin, rootless, default)
    --system             Install into system directory (/usr/local/bin or RPM)
    --no-deps            Skip dependency installation / check (for offline/custom environments)
    --repair             Re-verify and repair existing installation without affecting user config
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

# If running as root without explicit --user, default to system scope
if [ "$(id -u)" -eq 0 ] && [ "${INSTALL_SCOPE_EXPLICIT}" -eq 0 ]; then
    INSTALL_SCOPE="system"
fi

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

# Secure curl wrapper ensuring HTTP errors fail immediately
curl_cmd() {
    curl --fail --show-error --location "$@"
}

# Uninstallation handler
uninstall_soulwave() {
    log_info "Uninstalling Soulwave..."
    local uninstalled=0

    # 1. Remove user-level files (rootless)
    local user_bin="${HOME}/.local/bin/soulwave"
    local user_dir="${HOME}/.local/share/soulwave"
    if [ -f "${user_bin}" ]; then
        log_info "Removing user binary ${user_bin}..."
        rm -f "${user_bin}"
        uninstalled=1
    fi
    if [ -d "${user_dir}" ]; then
        log_info "Removing user environment directory ${user_dir}..."
        rm -rf "${user_dir}"
        uninstalled=1
    fi

    # 2. Check for system files /opt install and /usr/local/bin
    local sys_bin="/usr/local/bin/soulwave"
    local sys_dir="/opt/soulwave"
    if [ -f "${sys_bin}" ] || [ -d "${sys_dir}" ]; then
        log_info "Removing system files in /usr/local/bin/soulwave and /opt/soulwave..."
        run_elevated rm -rf "${sys_bin}" "${sys_dir}"
        uninstalled=1
    fi

    # 3. Check for native RPM install
    if command -v rpm >/dev/null 2>&1 && rpm -q soulwave >/dev/null 2>&1; then
        log_info "Detected RPM installation. Removing via package manager..."
        if command -v dnf >/dev/null 2>&1; then
            run_elevated dnf remove -y soulwave
        elif command -v zypper >/dev/null 2>&1; then
            run_elevated zypper remove -y soulwave
        else
            run_elevated rpm -e soulwave
        fi
        uninstalled=1
    fi

    # 4. Remove /usr/bin/soulwave if remaining
    if [ -f "/usr/bin/soulwave" ]; then
        run_elevated rm -f "/usr/bin/soulwave"
        uninstalled=1
    fi

    echo ""
    log_info "User Data Preservation:"
    echo "    User configuration (~/.config/soulwave) and cache (~/.cache/soulwave) were preserved."
    echo ""

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

# Detect architecture
detect_arch() {
    local raw_arch
    raw_arch="$(uname -m 2>/dev/null || echo "x86_64")"
    case "${raw_arch}" in
        x86_64|amd64)
            ARCH="x86_64"
            ;;
        aarch64|arm64|armv8*)
            ARCH="aarch64"
            ;;
        *)
            ARCH="${raw_arch}"
            ;;
    esac
}

# Detect platform and distribution
detect_os() {
    OS_NAME="unknown"
    OS_VERSION=""
    OS_ID="unknown"
    OS_LIKE=""
    IS_RPM_DISTRO=0

    local kernel_name
    kernel_name="$(uname -s 2>/dev/null || echo "unknown")"
    if [ "${kernel_name}" != "Linux" ]; then
        log_error "Soulwave standalone installer currently targets Linux (detected: ${kernel_name})."
        echo "    To install on other platforms, use pip in a Python environment: pip install soulwave"
        exit 1
    fi

    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_NAME="${NAME:-linux}"
        OS_VERSION="${VERSION_ID:-${VERSION:-}}"
        OS_ID="${ID:-unknown}"
        OS_LIKE="${ID_LIKE:-}"
    elif command -v uname >/dev/null 2>&1; then
        OS_NAME="$(uname -s)"
    fi

    case "${OS_ID}" in
        fedora|rhel|centos|rocky|almalinux|opensuse*|suse|sles)
            IS_RPM_DISTRO=1
            ;;
        *)
            if [[ "${OS_LIKE}" =~ (fedora|rhel|suse) ]]; then
                IS_RPM_DISTRO=1
            fi
            ;;
    esac
}

# Detect available Linux package manager based on distro and presence of binaries
detect_package_manager() {
    if [ -n "${SOULWAVE_TEST_PKG_MGR:-}" ]; then
        echo "${SOULWAVE_TEST_PKG_MGR}"
        return 0
    fi

    # Distro-first detection using detect_os outputs
    case "${OS_ID:-}" in
        ubuntu|debian|linuxmint|pop)
            if command -v apt-get >/dev/null 2>&1 || command -v apt >/dev/null 2>&1; then
                echo "apt"
                return 0
            fi
            ;;
        fedora|rhel|centos|rocky|almalinux)
            if command -v dnf >/dev/null 2>&1; then
                echo "dnf"
                return 0
            fi
            ;;
        arch|manjaro|endeavouros)
            if command -v pacman >/dev/null 2>&1; then
                echo "pacman"
                return 0
            fi
            ;;
        opensuse*|suse|sles)
            if command -v zypper >/dev/null 2>&1; then
                echo "zypper"
                return 0
            fi
            ;;
    esac

    # Check OS_LIKE if OS_ID was derived/custom
    if [[ "${OS_LIKE:-}" =~ (debian|ubuntu) ]] && (command -v apt-get >/dev/null 2>&1 || command -v apt >/dev/null 2>&1); then
        echo "apt"
        return 0
    elif [[ "${OS_LIKE:-}" =~ (fedora|rhel) ]] && command -v dnf >/dev/null 2>&1; then
        echo "dnf"
        return 0
    elif [[ "${OS_LIKE:-}" =~ (arch) ]] && command -v pacman >/dev/null 2>&1; then
        echo "pacman"
        return 0
    elif [[ "${OS_LIKE:-}" =~ (suse) ]] && command -v zypper >/dev/null 2>&1; then
        echo "zypper"
        return 0
    fi

    # Check IS_RPM_DISTRO flag
    if [ "${IS_RPM_DISTRO:-0}" -eq 1 ]; then
        if command -v dnf >/dev/null 2>&1; then
            echo "dnf"
            return 0
        elif command -v zypper >/dev/null 2>&1; then
            echo "zypper"
            return 0
        fi
    fi

    # Generic binary fallback
    if command -v dnf >/dev/null 2>&1; then
        echo "dnf"
        return 0
    elif command -v apt-get >/dev/null 2>&1 || command -v apt >/dev/null 2>&1; then
        echo "apt"
        return 0
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
        return 0
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
        return 0
    fi

    echo "unknown"
    return 1
}

# Return the appropriate command to install playerctl for the given package manager
get_playerctl_install_command() {
    local pkg_mgr="$1"
    local mode="${2:-auto}" # auto (default) or manual

    case "${pkg_mgr}" in
        apt)
            if [ "${mode}" = "manual" ]; then
                echo "sudo apt install playerctl"
            else
                echo "sudo apt install -y playerctl"
            fi
            ;;
        dnf)
            if [ "${mode}" = "manual" ]; then
                echo "sudo dnf install playerctl"
            else
                echo "sudo dnf install -y playerctl"
            fi
            ;;
        pacman)
            if [ "${mode}" = "manual" ]; then
                echo "sudo pacman -S playerctl"
            else
                echo "sudo pacman -S --noconfirm playerctl"
            fi
            ;;
        zypper)
            if [ "${mode}" = "manual" ]; then
                echo "sudo zypper install playerctl"
            else
                echo "sudo zypper install -y playerctl"
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

# Return the appropriate command to install cava for the given package manager
get_cava_install_command() {
    local pkg_mgr="$1"
    local mode="${2:-auto}"

    case "${pkg_mgr}" in
        apt)
            if [ "${mode}" = "manual" ]; then
                echo "sudo apt install cava"
            else
                echo "sudo apt install -y cava"
            fi
            ;;
        dnf)
            if [ "${mode}" = "manual" ]; then
                echo "sudo dnf install cava"
            else
                echo "sudo dnf install -y cava"
            fi
            ;;
        pacman)
            if [ "${mode}" = "manual" ]; then
                echo "sudo pacman -S cava"
            else
                echo "sudo pacman -S --noconfirm cava"
            fi
            ;;
        zypper)
            if [ "${mode}" = "manual" ]; then
                echo "sudo zypper install cava"
            else
                echo "sudo zypper install -y cava"
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

# Return combined command to install both playerctl and cava
get_combined_install_command() {
    local pkg_mgr="$1"
    local mode="${2:-auto}"

    case "${pkg_mgr}" in
        apt)
            if [ "${mode}" = "manual" ]; then
                echo "sudo apt install playerctl cava"
            else
                echo "sudo apt install -y playerctl cava"
            fi
            ;;
        dnf)
            if [ "${mode}" = "manual" ]; then
                echo "sudo dnf install playerctl cava"
            else
                echo "sudo dnf install -y playerctl cava"
            fi
            ;;
        pacman)
            if [ "${mode}" = "manual" ]; then
                echo "sudo pacman -S playerctl cava"
            else
                echo "sudo pacman -S --noconfirm playerctl cava"
            fi
            ;;
        zypper)
            if [ "${mode}" = "manual" ]; then
                echo "sudo zypper install playerctl cava"
            else
                echo "sudo zypper install -y playerctl cava"
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

# Verify that playerctl is installed and available in PATH
verify_playerctl() {
    if [ -n "${SOULWAVE_TEST_MOCK_PLAYERCTL_FILE:-}" ]; then
        [ -f "${SOULWAVE_TEST_MOCK_PLAYERCTL_FILE}" ]
        return $?
    fi
    command -v playerctl >/dev/null 2>&1
}

# Verify that cava is installed and available in PATH
verify_cava() {
    if [ -n "${SOULWAVE_TEST_MOCK_CAVA_FILE:-}" ]; then
        [ -f "${SOULWAVE_TEST_MOCK_CAVA_FILE}" ]
        return $?
    fi
    command -v cava >/dev/null 2>&1
}

# Check if interactive input can be read
is_interactive() {
    if [ -n "${SOULWAVE_FORCE_INTERACTIVE:-}" ]; then
        return 0
    fi
    if [ -n "${SOULWAVE_FORCE_NONINTERACTIVE:-}" ]; then
        return 1
    fi
    if [ -n "${CI:-}" ] || [ -n "${NONINTERACTIVE:-}" ] || [ "${DEBIAN_FRONTEND:-}" = "noninteractive" ]; then
        return 1
    fi
    if [ -c /dev/tty ] && (true < /dev/tty) 2>/dev/null; then
        return 0
    fi
    if [ -t 0 ]; then
        return 0
    fi
    return 1
}

# Execute installation of playerctl via detected package manager and verify success
install_playerctl() {
    local pkg_mgr="$1"
    local install_cmd
    install_cmd="$(get_playerctl_install_command "${pkg_mgr}" "auto")"

    if [ -z "${install_cmd}" ]; then
        log_error "No installation command available for package manager '${pkg_mgr}'."
        exit 1
    fi

    log_info "Installing playerctl using: ${install_cmd}"

    local exit_code=0
    if [ -c /dev/tty ] && (true < /dev/tty) 2>/dev/null && [ -z "${SOULWAVE_TEST_INPUT:-}" ] && [ -z "${SOULWAVE_READ_STDIN:-}" ]; then
        eval "${install_cmd} < /dev/tty" || exit_code=$?
    else
        eval "${install_cmd}" || exit_code=$?
    fi

    if [ "${exit_code}" -ne 0 ]; then
        echo ""
        log_error "Failed to install playerctl (command exited with code ${exit_code})."
        echo "    Possible reasons:"
        echo "      - Sudo authentication failed or permission was denied"
        echo "      - Another package manager process is currently running and holding the lock"
        echo "      - Repository mirrors or network connections are unreachable"
        echo ""
        echo "    You can install playerctl manually and rerun the installer:"
        local manual_cmd
        manual_cmd="$(get_playerctl_install_command "${pkg_mgr}" "manual")"
        echo "       ${manual_cmd:-Install playerctl via your distribution package manager.}"
        echo ""
        exit 1
    fi

    if ! verify_playerctl; then
        log_error "Installation command completed, but 'playerctl' was not found in PATH."
        exit 1
    fi

    log_success "Successfully installed and verified playerctl!"
}

# Execute installation of cava via detected package manager
install_cava() {
    local pkg_mgr="$1"
    local install_cmd
    install_cmd="$(get_cava_install_command "${pkg_mgr}" "auto")"

    if [ -z "${install_cmd}" ]; then
        log_warn "No automatic installation command for cava on '${pkg_mgr}'."
        return 1
    fi

    log_info "Installing cava using: ${install_cmd}"
    local exit_code=0
    if [ -c /dev/tty ] && (true < /dev/tty) 2>/dev/null && [ -z "${SOULWAVE_TEST_INPUT:-}" ] && [ -z "${SOULWAVE_READ_STDIN:-}" ]; then
        eval "${install_cmd} < /dev/tty" || exit_code=$?
    else
        eval "${install_cmd}" || exit_code=$?
    fi

    if [ "${exit_code}" -ne 0 ]; then
        log_warn "Failed to install cava (command exited with code ${exit_code}). Soulwave will use built-in procedural visualizer fallback."
        return 1
    fi

    if verify_cava; then
        log_success "Successfully installed and verified cava!"
        return 0
    fi
    return 1
}

# Stage 1: Run comprehensive system diagnostics
run_diagnostics() {
    local distro_str="${OS_NAME}"
    if [ -n "${OS_VERSION:-}" ]; then
        distro_str="${distro_str} ${OS_VERSION}"
    fi

    local pkg_mgr
    pkg_mgr="$(detect_package_manager || echo "unknown")"

    local dbus_str="[NOTICE]"
    local dbus_desc="Not detected (headless/non-desktop session)"
    if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || [ -S "/run/user/$(id -u)/bus" 2>/dev/null ]; then
        dbus_str="[  OK  ]"
        dbus_desc="Available"
    fi

    local dl_str="[MISSING]"
    local dl_desc="None (curl or wget required for remote install)"
    if command -v curl >/dev/null 2>&1; then
        dl_str="[  OK  ]"
        dl_desc="curl ($(command -v curl))"
    elif command -v wget >/dev/null 2>&1; then
        dl_str="[  OK  ]"
        dl_desc="wget ($(command -v wget))"
    fi

    local py_str="[INFO]"
    local py_desc="Not required for standalone binary"
    if command -v python3 >/dev/null 2>&1; then
        local py_ver
        py_ver="$(python3 --version 2>&1 | awk '{print $2}')"
        if [ "${INSTALL_FORMAT}" = "wheel" ]; then
            local py_ok
            py_ok="$(python3 -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)" 2>/dev/null || echo 0)"
            if [ "${py_ok}" = "1" ]; then
                py_str="[  OK  ]"
                py_desc="Python ${py_ver} (>= 3.10 verified)"
            else
                py_str="[MISSING]"
                py_desc="Python ${py_ver} (< 3.10; >= 3.10 required for wheel)"
            fi
        else
            py_str="[  OK  ]"
            py_desc="Python ${py_ver} (host detected)"
        fi
    elif [ "${INSTALL_FORMAT}" = "wheel" ]; then
        py_str="[MISSING]"
        py_desc="Python 3 not found (required for --wheel mode)"
    fi

    local pctl_str="[MISSING]"
    local pctl_desc="Not found (recommended for live Spotify/browser media tracking)"
    if verify_playerctl; then
        pctl_str="[  OK  ]"
        local pctl_bin
        pctl_bin="$(command -v playerctl 2>/dev/null || echo "playerctl")"
        pctl_desc="Available (${pctl_bin})"
    fi

    local cava_str="[OPTIONAL]"
    local cava_desc="Not found (Soulwave procedural wave fallback ready)"
    if verify_cava; then
        cava_str="[  OK  ]"
        local cava_bin
        cava_bin="$(command -v cava 2>/dev/null || echo "cava")"
        cava_desc="Available (${cava_bin} — spectrum visualizer enabled)"
    fi

    local target_dir=""
    if [ "${INSTALL_SCOPE}" = "system" ] || [ "$(id -u)" -eq 0 ]; then
        target_dir="/usr/local/bin"
    else
        target_dir="${HOME}/.local/bin"
    fi
    local path_str="[WARNING]"
    local path_desc="${target_dir} is NOT in current PATH"
    if [[ ":${PATH}:" == *":${target_dir}:"* ]]; then
        path_str="[  OK  ]"
        path_desc="${target_dir} is in PATH"
    fi

    echo -e "  ${BOLD}Stage [1/5]: System Diagnostics${RESET}"
    echo "  ───────────────────────────────────────────────────────────────────"
    printf "  %-22s %s\n" "• Linux Distribution:" "${distro_str}"
    printf "  %-22s %s\n" "• CPU Architecture:"   "${ARCH}"
    printf "  %-22s %s\n" "• Package Manager:"    "${pkg_mgr}"
    printf "  %-22s %-32s %s\n" "• D-Bus Session:"     "${dbus_desc}" "${dbus_str}"
    printf "  %-22s %-32s %s\n" "• Download Utility:"  "${dl_desc}"   "${dl_str}"
    printf "  %-22s %-32s %s\n" "• Python Runtime:"    "${py_desc}"   "${py_str}"
    printf "  %-22s %-32s %s\n" "• playerctl (MPRIS):" "${pctl_desc}" "${pctl_str}"
    printf "  %-22s %-32s %s\n" "• cava (Visualizer):" "${cava_desc}" "${cava_str}"
    printf "  %-22s %s\n" "• Target Directory:"    "${target_dir}/soulwave"
    printf "  %-22s %-32s %s\n" "• PATH Status:"       "${path_desc}" "${path_str}"
    echo "  ───────────────────────────────────────────────────────────────────"
    echo ""
}

# Check system prerequisites and resolve dependencies interactively
check_prerequisites() {
    log_info "Stage [2/5]: Dependency Resolution..."

    # Check download utility if not installing from local file
    if [ -z "${LOCAL_FILE}" ]; then
        if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
            log_error "'curl' or 'wget' is required to download release assets. Please install one of them."
            exit 1
        fi
    fi

    # If user explicitly forced wheel mode, check python requirements
    if [ "${INSTALL_FORMAT}" = "wheel" ]; then
        if ! command -v python3 >/dev/null 2>&1; then
            log_error "Python 3 is required for --wheel mode but was not found. Please install Python >= 3.10, or use the default standalone binary installation."
            exit 1
        fi

        local py_ok
        py_ok="$(python3 -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)" 2>/dev/null || echo 0)"
        if [ "${py_ok}" != "1" ]; then
            log_error "Soulwave --wheel mode requires Python 3.10 or higher. Found: $(python3 --version 2>&1)"
            exit 1
        fi
    fi

    # If --no-deps was specified, skip dependency checks
    if [ "${NO_DEPS}" -eq 1 ]; then
        log_info "Skipping dependency installation (--no-deps specified)."
        return 0
    fi

    local has_playerctl=0
    if verify_playerctl; then
        has_playerctl=1
    fi

    local has_cava=0
    if verify_cava; then
        has_cava=1
    fi

    if [ "${has_playerctl}" -eq 1 ] && [ "${has_cava}" -eq 1 ]; then
        log_success "All recommended and optional audio utilities found (playerctl, cava)."
        return 0
    fi

    local pkg_mgr
    pkg_mgr="$(detect_package_manager || echo "unknown")"
    local manual_cmd
    manual_cmd="$(get_playerctl_install_command "${pkg_mgr}" "manual")"
    if [ -z "${manual_cmd}" ]; then
        manual_cmd="sudo <package-manager> install playerctl"
    fi

    # Handle missing playerctl
    if [ "${has_playerctl}" -eq 0 ]; then
        log_warn "Recommended audio utility not found: playerctl"
        echo ""
        echo "    SoulWave needs playerctl to track live music across Spotify,"
        echo "    browsers, and media players."
        echo ""

        if [ "${pkg_mgr}" = "unknown" ]; then
            log_warn "Automatic installation is unavailable because no supported package manager was detected."
            echo "    Please install 'playerctl' manually through your distribution's package manager,"
            echo "    then rerun the SoulWave installer:"
            echo ""
            echo "       curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash"
            echo ""
            log_info "Exiting installer."
            exit 1
        fi

        if ! is_interactive; then
            log_error "Interactive terminal not available for dependency installation."
            echo "    Please install 'playerctl' manually:"
            echo ""
            echo "       ${manual_cmd}"
            echo ""
            echo "    Or rerun the installer with --no-deps to skip dependency installation:"
            echo ""
            echo "       curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash -s -- --no-deps"
            echo ""
            exit 1
        fi

        echo "  How would you like to proceed?"
        echo ""
        echo "    [1] (Recommended) Install playerctl automatically using sudo"
        echo "    [2] Exit and install playerctl manually"
        echo "    [3] Skip playerctl and continue (SoulWave will run in demo/fallback mode)"
        echo "    [4] Exit installer"
        echo ""

        local tty_in="/dev/tty"
        if [ -n "${SOULWAVE_TEST_INPUT:-}" ] || [ -n "${SOULWAVE_READ_STDIN:-}" ] || [ ! -c /dev/tty ] || ! (true < /dev/tty) 2>/dev/null; then
            tty_in="/dev/stdin"
        fi

        local choice=""
        while true; do
            printf "  Select an option [1-4] (default: 1): "
            if ! read -r choice < "${tty_in}"; then
                echo ""
                log_error "Installation cancelled by user."
                exit 1
            fi
            choice="$(echo "${choice}" | xargs 2>/dev/null || echo "${choice}")"
            if [ -z "${choice}" ] || [ "${choice}" = "1" ]; then
                choice="1"
                break
            elif [ "${choice}" = "2" ]; then
                choice="2"
                break
            elif [ "${choice}" = "3" ]; then
                choice="3"
                break
            elif [ "${choice}" = "4" ]; then
                choice="4"
                break
            else
                echo "Invalid selection: '${choice}'. Please enter 1, 2, 3, or 4."
            fi
        done

        if [ "${choice}" = "1" ]; then
            install_playerctl "${pkg_mgr}"
        elif [ "${choice}" = "2" ]; then
            echo ""
            log_info "Manual Installation Instructions"
            echo ""
            echo "    1. Install playerctl:"
            echo ""
            echo "       ${manual_cmd}"
            echo ""
            echo "    2. Once installed, rerun the SoulWave installer:"
            echo ""
            echo "       curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | bash"
            echo ""
            log_info "Exiting installer."
            exit 0
        elif [ "${choice}" = "3" ]; then
            echo ""
            log_warn "Skipping playerctl. Live desktop music tracking will be inactive until playerctl is installed."
            echo "    (Soulwave can still be launched with 'soulwave -d' for built-in demo music and lyrics!)"
            echo ""
        elif [ "${choice}" = "4" ]; then
            echo ""
            log_info "Installation cancelled by user. Exiting installer."
            exit 0
        fi
    fi

    # Check optional visualizer utility (cava) if still missing
    if ! verify_cava; then
        log_info "Note: Audio visualizer utility 'cava' not found."
        echo "    Soulwave will use its built-in visualizer fallback."
        echo "    (Optional) Install cava to enable real-time hardware spectrum analysis."
    fi
}

# Download helper using curl or wget
fetch_file() {
    local url="$1"
    local dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --show-error --location -sSL -o "${dest}" "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "${dest}" "${url}"
    else
        log_error "Neither curl nor wget found to download files."
        exit 1
    fi
}

# Parse GitHub release JSON portably without python or jq dependencies
parse_release_json() {
    local json_file="$1"
    local parsed_out="$2"

    if command -v jq >/dev/null 2>&1; then
        jq -r '.tag_name, (.assets[] | "\(.name) \(.browser_download_url)")' "${json_file}" > "${parsed_out}" 2>/dev/null && return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import sys, json
try:
    with open('${json_file}', 'r', encoding='utf-8') as f:
        d = json.load(f)
    print(d.get('tag_name', ''))
    for a in d.get('assets', []):
        name = a.get('name', '')
        url = a.get('browser_download_url', '')
        if name and url:
            print(f'{name} {url}')
except Exception:
    sys.exit(1)
" > "${parsed_out}" 2>/dev/null && return 0
    fi

    # POSIX awk/grep fallback (works without python3 or jq)
    local tag
    tag="$(grep -m 1 '"tag_name":' "${json_file}" | sed -E 's/.*"tag_name":[[:space:]]*"([^"]+)".*/\1/')"
    echo "${tag}" > "${parsed_out}"
    awk '
        /"name":/ {
            sub(/.*"name":[[:space:]]*"/, "")
            sub(/".*/, "")
            cur_name = $0
        }
        /"browser_download_url":/ {
            sub(/.*"browser_download_url":[[:space:]]*"/, "")
            sub(/".*/, "")
            if (cur_name != "") {
                print cur_name " " $0
                cur_name = ""
            }
        }
    ' "${json_file}" >> "${parsed_out}"
}

# Download release assets from GitHub
fetch_release_assets() {
    local tmp_dir="$1"

    local api_url
    if [ -n "${TARGET_VERSION}" ]; then
        local tag_to_query="${TARGET_VERSION}"
        if [[ "${tag_to_query}" != v* ]]; then
            tag_to_query="v${tag_to_query}"
        fi
        api_url="https://api.github.com/repos/${REPO}/releases/tags/${tag_to_query}"
    else
        api_url="https://api.github.com/repos/${REPO}/releases/latest"
    fi

    log_info "Querying GitHub release from ${api_url}..."
    local release_json="${tmp_dir}/release.json"

    if ! fetch_file "${api_url}" "${release_json}"; then
        log_error "Failed to fetch release metadata from ${api_url}."
        if [ -n "${TARGET_VERSION}" ]; then
            echo "    Release tag '${TARGET_VERSION}' was not found on ${REPO}."
        else
            echo "    No published releases found yet on ${REPO}."
        fi
        echo "    If installing from a local file, use: ./install.sh --file <path>"
        exit 1
    fi

    local parsed_result="${tmp_dir}/parsed_assets.txt"
    if ! parse_release_json "${release_json}" "${parsed_result}"; then
        log_error "Could not parse GitHub release metadata JSON."
        exit 1
    fi

    TAG_NAME="$(head -n 1 "${parsed_result}")"
    if [ -z "${TAG_NAME}" ] || [[ "${TAG_NAME}" == *"API rate limit"* ]] || [[ "${TAG_NAME}" == *"Not Found"* ]] || [[ "${TAG_NAME}" == *"message"* ]]; then
        log_error "Could not retrieve release metadata from GitHub API (response: '${TAG_NAME:-empty}')."
        echo "    GitHub may be temporarily unreachable or rate-limited."
        echo "    You can browse and download releases at: https://github.com/${REPO}/releases"
        exit 1
    fi
    log_info "Found release: ${BOLD}${TAG_NAME}${RESET}"

    # Download checksums.txt (fail-closed: MUST be present for release downloads)
    local checksums_url
    checksums_url="$(grep -E "^checksums\.txt[[:space:]]" "${parsed_result}" | awk '{print $2}' || true)"
    if [ -z "${checksums_url}" ]; then
        log_error "Release ${TAG_NAME} does not contain 'checksums.txt'. Refusing to install unverified release (fail-closed)."
        exit 1
    fi

    log_info "Downloading checksums.txt..."
    if ! fetch_file "${checksums_url}" "${tmp_dir}/checksums.txt"; then
        log_error "Failed to download checksums.txt from ${checksums_url}."
        exit 1
    fi

    # Determine which asset to download based on INSTALL_FORMAT and system
    CHOSEN_ASSET=""
    local chosen_url=""

    # 1. Native RPM option if requested
    if [ "${INSTALL_FORMAT}" = "rpm" ] || ([ "${INSTALL_FORMAT}" = "auto" ] && [ "${IS_RPM_DISTRO}" -eq 1 ] && [ "${INSTALL_SCOPE}" = "system" ]); then
        CHOSEN_ASSET="$(grep -E "\.${ARCH}\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "\.${ARCH}\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
        if [ -z "${CHOSEN_ASSET}" ]; then
            CHOSEN_ASSET="$(grep -E "\.noarch\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
            chosen_url="$(grep -E "\.noarch\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
        fi
        if [ -z "${CHOSEN_ASSET}" ]; then
            CHOSEN_ASSET="$(grep -E "\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
            chosen_url="$(grep -E "\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
        fi
    fi

    # 2. Wheel option if requested
    if [ "${INSTALL_FORMAT}" = "wheel" ] && [ -z "${CHOSEN_ASSET}" ]; then
        CHOSEN_ASSET="$(grep -E "\.whl[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "\.whl[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
    fi

    # 3. Default: Standalone binary (preferred universal format)
    if [ -z "${CHOSEN_ASSET}" ]; then
        local bin_pattern="soulwave-linux-${ARCH}[[:space:]]"
        CHOSEN_ASSET="$(grep -E "^${bin_pattern}" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "^${bin_pattern}" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
    fi

    # 4. Fallback if binary asset wasn't found
    if [ -z "${CHOSEN_ASSET}" ]; then
        if [ "${IS_RPM_DISTRO}" -eq 1 ]; then
            CHOSEN_ASSET="$(grep -E "\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
            chosen_url="$(grep -E "\.rpm[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
        fi
    fi
    if [ -z "${CHOSEN_ASSET}" ]; then
        CHOSEN_ASSET="$(grep -E "\.whl[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $1}' || true)"
        chosen_url="$(grep -E "\.whl[[:space:]]" "${parsed_result}" | head -n 1 | awk '{print $2}' || true)"
    fi

    if [ -z "${CHOSEN_ASSET}" ] || [ -z "${chosen_url}" ]; then
        log_error "No suitable release asset found for architecture '${ARCH}' in release ${TAG_NAME}."
        exit 1
    fi

    log_info "Stage [3/5]: Downloading ${CHOSEN_ASSET}..."
    if ! fetch_file "${chosen_url}" "${tmp_dir}/${CHOSEN_ASSET}"; then
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
    elif command -v openssl >/dev/null 2>&1; then
        actual_hash="$(openssl dgst -sha256 "${target_file}" | awk '{print $NF}' | tr -d ' \r\n')"
    elif command -v python3 >/dev/null 2>&1; then
        actual_hash="$(python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "${target_file}" | tr -d ' \r\n')"
    else
        log_error "No SHA-256 tool found (sha256sum, shasum, openssl, or python3)."
        return 1
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

# Install standalone executable binary
install_binary() {
    local bin_file="$1"
    local bin_dir=""
    local target_path=""

    if [ "${INSTALL_SCOPE}" = "system" ] || [ "$(id -u)" -eq 0 ]; then
        bin_dir="/usr/local/bin"
        target_path="${bin_dir}/soulwave"
        log_info "Installing standalone Soulwave binary to ${target_path} (system)..."
        run_elevated mkdir -p "${bin_dir}"
        run_elevated cp "${bin_file}" "${target_path}"
        run_elevated chmod 0755 "${target_path}"
    else
        bin_dir="${HOME}/.local/bin"
        target_path="${bin_dir}/soulwave"
        log_info "Installing standalone Soulwave binary to ${target_path} (user)..."
        mkdir -p "${bin_dir}"
        cp "${bin_file}" "${target_path}"
        chmod 0755 "${target_path}"
    fi

    LAST_INSTALLED_LAUNCHER="${target_path}"

    # PATH verification
    if [[ ":${PATH}:" != *":${bin_dir}:"* ]]; then
        log_warn "${bin_dir} is not currently in your PATH."
        echo "    To run 'soulwave' directly from any terminal, add it to your PATH:"
        echo -e "        ${BOLD}export PATH=\"${bin_dir}:\$PATH\"${RESET}"
        echo "    You can add this line to your ~/.bashrc, ~/.zshrc, or ~/.profile."
        echo ""
    fi
}

# Install RPM package
install_rpm() {
    local rpm_file="$1"
    log_info "Installing native RPM package (${rpm_file})..."

    if command -v dnf >/dev/null 2>&1; then
        run_elevated dnf install -y "${rpm_file}"
    elif command -v zypper >/dev/null 2>&1; then
        run_elevated zypper install -y "${rpm_file}"
    elif command -v rpm >/dev/null 2>&1; then
        run_elevated rpm -Uvh --force "${rpm_file}"
    else
        log_error "Neither dnf, zypper nor rpm found to install RPM package."
        exit 1
    fi
    LAST_INSTALLED_LAUNCHER="/usr/bin/soulwave"
}

# Install Wheel into an isolated directory (virtualenv)
install_wheel() {
    local wheel_file="$1"
    local install_dir=""
    local bin_dir=""
    local needs_sudo=0

    if [ "${INSTALL_SCOPE}" = "system" ] || [ "$(id -u)" -eq 0 ]; then
        install_dir="/opt/soulwave"
        bin_dir="/usr/local/bin"
        if [ "$(id -u)" -ne 0 ]; then
            needs_sudo=1
        fi
    else
        install_dir="${HOME}/.local/share/soulwave"
        bin_dir="${HOME}/.local/bin"
    fi

    log_info "Installing Soulwave via Python wheel to ${install_dir}..."

    local pip_opts=("--no-warn-script-location" "--upgrade")
    if [ "${NO_DEPS}" -eq 1 ]; then
        pip_opts+=("--no-deps")
    fi

    # Helper to create virtualenv safely with virtualenv.pyz fallback if python3-venv is missing
    create_virtualenv() {
        local target_dir="$1"
        local elevated="${2:-0}"

        if [ "${elevated}" -eq 1 ]; then
            if run_elevated python3 -m venv --system-site-packages "${target_dir}" 2>/dev/null; then
                return 0
            fi
        else
            if python3 -m venv --system-site-packages "${target_dir}" 2>/dev/null; then
                return 0
            fi
        fi

        log_warn "Standard 'python3-venv' / ensurepip is unavailable on this system."
        log_info "Bootstrapping standalone virtual environment runner (virtualenv.pyz)..."
        local venv_pyz
        venv_pyz="$(mktemp -t virtualenv-XXXXXX.pyz)"
        if fetch_file "https://bootstrap.pypa.io/virtualenv.pyz" "${venv_pyz}"; then
            if [ "${elevated}" -eq 1 ]; then
                run_elevated python3 "${venv_pyz}" --system-site-packages "${target_dir}"
            else
                python3 "${venv_pyz}" --system-site-packages "${target_dir}"
            fi
            rm -f "${venv_pyz}"
            return 0
        else
            rm -f "${venv_pyz}"
            log_error "Failed to create virtual environment using standard venv and fallback."
            return 1
        fi
    }

    # Setup directories and isolated virtualenv
    if [ "${needs_sudo}" -eq 1 ]; then
        run_elevated mkdir -p "${install_dir}" "${bin_dir}"
        create_virtualenv "${install_dir}" 1
        run_elevated "${install_dir}/bin/python3" -m pip install "${pip_opts[@]}" "${wheel_file}"

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
        create_virtualenv "${install_dir}" 0
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
    echo "  ╔═══════════════════════════════════════════════════════════════════╗"
    if [ "${DO_REPAIR}" -eq 1 ]; then
        echo "  ║              Soulwave Installation Repair Assistant               ║"
    else
        echo "  ║                  Soulwave Linux Setup Assistant                   ║"
    fi
    echo "  ╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${RESET}"

    detect_arch
    detect_os
    log_info "Detected OS: ${BOLD}${OS_NAME}${RESET} (${ARCH})"

    run_diagnostics

    check_prerequisites

    TMP_DIR="$(mktemp -d -t soulwave-install-XXXXXX)"
    trap 'rm -rf "${TMP_DIR:-}"' EXIT INT TERM

    local package_file=""
    if [ -n "${LOCAL_FILE}" ]; then
        if [ ! -f "${LOCAL_FILE}" ]; then
            log_error "Specified local file not found: ${LOCAL_FILE}"
            exit 1
        fi
        if [ ! -r "${LOCAL_FILE}" ]; then
            log_error "Specified local file is not readable: ${LOCAL_FILE}"
            exit 1
        fi

        # Validate local file type
        case "${LOCAL_FILE}" in
            *.rpm|*.whl)
                ;;
            *)
                local is_valid_bin=0
                if [ -x "${LOCAL_FILE}" ]; then
                    is_valid_bin=1
                elif command -v file >/dev/null 2>&1 && file "${LOCAL_FILE}" | grep -qiE "ELF|executable|script"; then
                    is_valid_bin=1
                else
                    local magic
                    magic="$(head -c 4 "${LOCAL_FILE}" 2>/dev/null || true)"
                    if [[ "${magic}" == *ELF* ]] || [[ "${magic}" == *'#!'* ]]; then
                        is_valid_bin=1
                    fi
                fi
                if [ "${is_valid_bin}" -eq 0 ]; then
                    log_error "Unsupported file type for '${LOCAL_FILE}'. Expected an ELF binary, .rpm, or .whl file."
                    exit 1
                fi
                ;;
        esac

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

    log_info "Stage [4/5]: Installing Soulwave package..."
    # Determine installer route by file extension/format
    case "${package_file}" in
        *.rpm)
            install_rpm "${package_file}"
            ;;
        *.whl)
            install_wheel "${package_file}"
            ;;
        *)
            # Standalone binary executable
            install_binary "${package_file}"
            ;;
    esac

    # Post-installation verification health check
    if [ "${NO_DEPS}" -eq 1 ]; then
        log_warn "Installed with --no-deps. Skipping full runtime health check."
    else
        log_info "Stage [5/5]: Verifying installed Soulwave runtime and resources..."
        local launcher_to_check="${LAST_INSTALLED_LAUNCHER:-}"
        if [ -z "${launcher_to_check}" ] || [ ! -x "${launcher_to_check}" ]; then
            if [ -x "${HOME}/.local/bin/soulwave" ] && [ "${INSTALL_SCOPE}" = "user" ]; then
                launcher_to_check="${HOME}/.local/bin/soulwave"
            elif [ -x "/usr/local/bin/soulwave" ]; then
                launcher_to_check="/usr/local/bin/soulwave"
            elif [ -x "/usr/bin/soulwave" ]; then
                launcher_to_check="/usr/bin/soulwave"
            elif command -v soulwave >/dev/null 2>&1; then
                launcher_to_check="$(command -v soulwave)"
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
            log_error "Please ensure your system meets minimum requirements."
            exit 1
        fi
        log_success "Post-installation health check passed."
    fi

    echo ""
    if [ "${DO_REPAIR}" -eq 1 ]; then
        log_success "Soulwave repaired successfully!"
    else
        log_success "Soulwave installed successfully!"
    fi
    echo -e "  To launch Soulwave, simply run:  ${GREEN}${BOLD}soulwave${RESET}"
    echo -e "  To run system diagnostics:      ${CYAN}soulwave --doctor${RESET}"
    echo -e "  For help and keybindings:        ${CYAN}soulwave --help${RESET}"
    echo -e "  To repair anytime:               ${YELLOW}install.sh --repair${RESET}"
    echo -e "  To uninstall anytime:            ${YELLOW}install.sh --uninstall${RESET}"
    echo ""

    if ! verify_playerctl; then
        local distro_cmd="sudo apt install playerctl"
        if [ "${IS_RPM_DISTRO:-0}" -eq 1 ]; then
            distro_cmd="sudo dnf install playerctl"
        elif command -v pacman >/dev/null 2>&1; then
            distro_cmd="sudo pacman -S playerctl"
        elif command -v zypper >/dev/null 2>&1; then
            distro_cmd="sudo zypper install playerctl"
        fi
        echo -e "${YELLOW}┌────────────────────────────────────────────────────────────────────────┐${RESET}"
        echo -e "${YELLOW}│${RESET} ${BOLD}Notice:${RESET} 'playerctl' is not installed on your system.                  ${YELLOW}│${RESET}"
        echo -e "${YELLOW}│${RESET} To enable live music tracking from Spotify, YouTube, or browser:        ${YELLOW}│${RESET}"
        echo -e "${YELLOW}│${RESET}   ${CYAN}${distro_cmd}${RESET}"
        echo -e "${YELLOW}│${RESET} (Or launch with ${GREEN}soulwave -d${RESET} to enjoy built-in demo tracks with lyrics!) ${YELLOW}│${RESET}"
        echo -e "${YELLOW}└────────────────────────────────────────────────────────────────────────┘${RESET}"
        echo ""
    fi
}

if [[ "${BASH_SOURCE[0]:-}" == "${0}" || -z "${BASH_SOURCE[0]:-}" ]]; then
    main "$@"
fi
