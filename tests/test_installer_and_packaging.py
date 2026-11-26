"""Comprehensive tests for installer script (install.sh), RPM packaging, binary packaging, and release workflow."""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
import unittest

try:
    import pytest
except ImportError:
    class _PytestMock:
        @staticmethod
        def skip(reason=""):
            raise unittest.SkipTest(reason)

        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

    pytest = _PytestMock()  # type: ignore

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"
RPM_SPEC = REPO_ROOT / "packaging" / "rpm" / "soulwave.spec"
BINARY_SPEC = REPO_ROOT / "packaging" / "binary" / "soulwave.spec"
BUILD_BINARY_SH = REPO_ROOT / "packaging" / "binary" / "build_binary.sh"
ENTRYPOINT_PY = REPO_ROOT / "packaging" / "binary" / "entrypoint.py"
SOULWAVE_MAIN_PY = REPO_ROOT / "soulwave" / "__main__.py"
RELEASE_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"
DIST_DIR = REPO_ROOT / "dist"
VENDOR_WHEELS_DIR = REPO_ROOT / "packaging" / "rpm" / "vendor_wheels"

import re
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"
if tomllib is not None:
    PROJECT_VERSION = tomllib.loads(PYPROJECT_TOML.read_text(encoding="utf-8"))["project"]["version"]
else:
    _match = re.search(r'version\s*=\s*"([^"]+)"', PYPROJECT_TOML.read_text(encoding="utf-8"))
    PROJECT_VERSION = _match.group(1) if _match else "0.1.2"


def get_built_rpm(version: str = PROJECT_VERSION):
    """Find built RPM in dist directory matching version."""
    rpms = [r for r in DIST_DIR.glob("*.rpm") if version in r.name]
    if not rpms:
        rpms = sorted(DIST_DIR.glob("*.rpm"), key=lambda r: r.name, reverse=True)
    # Prefer x86_64, then noarch
    x86_64_rpms = [r for r in rpms if "x86_64" in r.name]
    if x86_64_rpms:
        return x86_64_rpms[0]
    return rpms[0] if rpms else None


def get_built_wheel(version: str = PROJECT_VERSION):
    """Find or build wheel in dist directory matching version."""
    wheels = [w for w in DIST_DIR.glob("*.whl") if version in w.name]
    if wheels:
        return wheels[0]
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps", "-w", str(DIST_DIR), str(REPO_ROOT)],
        check=False,
        capture_output=True,
    )
    wheels = [w for w in DIST_DIR.glob("*.whl") if version in w.name]
    if wheels:
        return wheels[0]
    all_wheels = sorted(DIST_DIR.glob("*.whl"), key=lambda w: w.name, reverse=True)
    return all_wheels[0] if all_wheels else None


def test_install_script_exists_and_executable():
    assert INSTALL_SH.is_file(), "install.sh must exist at repo root"
    assert os.access(INSTALL_SH, os.X_OK), "install.sh must be executable"


def test_install_script_help():
    result = subprocess.run(
        [str(INSTALL_SH), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Soulwave Installer" in result.stdout
    assert "--binary" in result.stdout
    assert "--rpm" in result.stdout
    assert "--wheel" in result.stdout
    assert "--version" in result.stdout
    assert "--file" in result.stdout
    assert "--user" in result.stdout
    assert "--system" in result.stdout
    assert "--uninstall" in result.stdout


def test_pyinstaller_spec_and_build_script():
    """Verify PyInstaller spec file, entrypoint, and build script exist, include styles.tcss, and are valid."""
    assert BINARY_SPEC.is_file(), f"Binary spec {BINARY_SPEC} must exist"
    spec_content = BINARY_SPEC.read_text(encoding="utf-8")
    assert "styles.tcss" in spec_content, "soulwave.spec must bundle styles.tcss"
    assert "soulwave.cli" in spec_content, "soulwave.spec must include soulwave.cli entry point"
    assert "textual" in spec_content, "soulwave.spec must collect textual"
    assert "entrypoint.py" in spec_content, "soulwave.spec must target entrypoint.py"

    assert ENTRYPOINT_PY.is_file(), f"Binary entrypoint {ENTRYPOINT_PY} must exist"
    assert os.access(ENTRYPOINT_PY, os.X_OK), "entrypoint.py must be executable"
    entrypoint_content = ENTRYPOINT_PY.read_text(encoding="utf-8")
    assert "from soulwave.cli import main" in entrypoint_content

    assert SOULWAVE_MAIN_PY.is_file(), f"soulwave/__main__.py must exist at {SOULWAVE_MAIN_PY}"

    assert BUILD_BINARY_SH.is_file(), f"Build binary script {BUILD_BINARY_SH} must exist"
    assert os.access(BUILD_BINARY_SH, os.X_OK), "build_binary.sh must be executable"
    build_sh_content = BUILD_BINARY_SH.read_text(encoding="utf-8")
    assert "pyinstaller" in build_sh_content
    assert "soulwave-linux-" in build_sh_content
    assert "entrypoint.py" in build_sh_content


def test_direct_script_and_entrypoint_execution():
    """Verify cli.py, entrypoint.py, and -m soulwave execute without 'attempted relative import' error."""
    # 1. python3 packaging/binary/entrypoint.py --version
    res_entry = subprocess.run(
        [sys.executable, str(ENTRYPOINT_PY), "--version"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert res_entry.returncode == 0, f"entrypoint.py failed: {res_entry.stderr}"
    assert "Soulwave v" in res_entry.stdout
    assert "ImportError: attempted relative import" not in res_entry.stderr

    # 2. python3 soulwave/cli.py --version (must not fail even when run directly without -m)
    res_cli = subprocess.run(
        [sys.executable, str(REPO_ROOT / "soulwave" / "cli.py"), "--version"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert res_cli.returncode == 0, f"soulwave/cli.py direct execution failed: {res_cli.stderr}"
    assert "Soulwave v" in res_cli.stdout
    assert "ImportError: attempted relative import" not in res_cli.stderr

    # 3. python3 -m soulwave --version
    res_mod = subprocess.run(
        [sys.executable, "-m", "soulwave", "--version"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert res_mod.returncode == 0, f"python -m soulwave failed: {res_mod.stderr}"
    assert "Soulwave v" in res_mod.stdout


def test_install_script_rejects_non_linux_os():
    """Verify install.sh detects and cleanly rejects non-Linux kernels (e.g. Darwin/macOS)."""
    mock_non_linux = """
    target="$1"
    set --
    uname() { echo "Darwin"; }
    source "${target}"
    detect_os
    """
    res = subprocess.run(
        ["bash", "-c", mock_non_linux, "_", str(INSTALL_SH)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "Soulwave standalone installer currently targets Linux" in res.stderr



def test_install_script_user_binary_and_uninstall(tmp_path):
    """Test standalone binary installation with --user into ~/.local/bin and clean --uninstall."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_bin = tmp_path / "soulwave-linux-x86_64"

    # Create a mock standalone binary that satisfies --check
    fake_bin.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--check\" ]; then\n"
        "    echo 'Post-installation health check passed.'\n"
        "    exit 0\n"
        "fi\n"
        "echo 'Soulwave standalone binary'\n"
    )
    fake_bin.chmod(0o755)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    # 1. Install using --user and --file <binary>
    res_install = subprocess.run(
        [str(INSTALL_SH), "--file", str(fake_bin), "--user"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_install.returncode == 0, f"Installer failed: {res_install.stderr}\n{res_install.stdout}"
    assert "Installing standalone Soulwave binary" in res_install.stdout
    assert "Soulwave installed successfully!" in res_install.stdout

    installed_launcher = fake_home / ".local" / "bin" / "soulwave"
    assert installed_launcher.is_file(), "Launcher executable must exist at ~/.local/bin/soulwave"
    assert os.access(installed_launcher, os.X_OK), "Installed launcher must be executable"

    # Test launcher execution
    run_res = subprocess.run([str(installed_launcher)], capture_output=True, text=True)
    assert "Soulwave standalone binary" in run_res.stdout

    # 2. Uninstall cleanly using --uninstall
    res_uninstall = subprocess.run(
        [str(INSTALL_SH), "--uninstall"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_uninstall.returncode == 0, f"Uninstaller failed: {res_uninstall.stderr}"
    assert "Soulwave uninstalled successfully." in res_uninstall.stdout
    assert not installed_launcher.exists(), "Launcher binary must be removed after uninstall"






def test_install_script_missing_local_file():
    result = subprocess.run(
        [str(INSTALL_SH), "--file", "nonexistent-package.whl"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Specified local file not found" in result.stderr or "Specified local file not found" in result.stdout


def test_checksum_verification_valid(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_content = b"fake-package-data-12345"
    test_file.write_bytes(test_content)

    correct_hash = hashlib.sha256(test_content).hexdigest()
    checksums_file = tmp_path / "checksums.txt"
    checksums_file.write_text(f"{correct_hash}  test-pkg.whl\n")

    bash_verify = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{checksums_file}"
    """
    res = subprocess.run(["bash", "-c", bash_verify], capture_output=True, text=True)
    assert res.returncode == 0
    assert "SHA-256 verified" in res.stdout or "SHA-256 verified" in res.stderr


def test_checksum_verification_tampered_fails_closed(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_file.write_bytes(b"tampered-content")

    tampered_checksums = tmp_path / "checksums.txt"
    tampered_checksums.write_text("0000000000000000000000000000000000000000000000000000000000000000  test-pkg.whl\n")

    bash_cmd = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{tampered_checksums}"
    """
    res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
    assert res.returncode != 0
    assert "Checksum verification failed" in res.stderr or "Checksum verification failed" in res.stdout


def test_checksum_verification_absent_checksums_fails_closed(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_file.write_bytes(b"package-data")
    non_existent_sums = tmp_path / "non_existent_checksums.txt"

    bash_cmd = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{non_existent_sums}"
    """
    res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
    assert res.returncode != 0
    assert "is missing" in res.stderr or "is missing" in res.stdout


def test_checksum_verification_missing_asset_entry_fails_closed(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_file.write_bytes(b"package-data")

    checksums_file = tmp_path / "checksums.txt"
    checksums_file.write_text("a" * 64 + "  other-package.whl\n")

    bash_cmd = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{checksums_file}"
    """
    res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
    assert res.returncode != 0
    assert "No checksum entry found" in res.stderr or "No checksum entry found" in res.stdout


def test_checksum_verification_invalid_format_fails_closed(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_file.write_bytes(b"package-data")

    checksums_file = tmp_path / "checksums.txt"
    checksums_file.write_text("not-a-valid-sha256-hash  test-pkg.whl\n")

    bash_cmd = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{checksums_file}"
    """
    res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
    assert res.returncode != 0
    assert "Invalid SHA-256 hash format" in res.stderr or "Invalid SHA-256 hash format" in res.stdout


def test_curl_cmd_http_error_fails_immediately():
    bash_cmd = f"""
    source "{INSTALL_SH}"
    curl_cmd -sSL -o /dev/null "http://127.0.0.1:9" 2>&1
    """
    res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
    assert res.returncode != 0, "curl_cmd must fail immediately on connection/HTTP errors"


def test_user_mode_installation_and_uninstallation(tmp_path):
    wheel_file = get_built_wheel()
    if wheel_file is None or not wheel_file.is_file():
        pytest.skip("Built wheel file not available")

    # Probe whether python3 venv works on this host
    test_v = subprocess.run(["python3", "-m", "venv", str(tmp_path / "probe_v")], capture_output=True)
    if test_v.returncode != 0:
        pytest.skip("System python3 venv creation not supported on this host")

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    # 1. Install using --user and --no-deps
    res_install = subprocess.run(
        [str(INSTALL_SH), "--file", str(wheel_file), "--user", "--no-deps"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_install.returncode == 0, f"Installer failed: {res_install.stderr}"

    launcher = fake_home / ".local" / "bin" / "soulwave"
    install_dir = fake_home / ".local" / "share" / "soulwave"

    assert launcher.is_file(), "Launcher script should be created"
    assert os.access(launcher, os.X_OK), "Launcher script should be executable"
    assert install_dir.is_dir(), "Isolated install directory should be created"
    assert (install_dir / "bin" / "python3").exists(), "Python venv interpreter should exist"

    # Verify launcher script content
    launcher_text = launcher.read_text()
    assert "-m soulwave.cli" in launcher_text
    assert str(install_dir) in launcher_text

    # 2. Uninstall using --uninstall
    res_uninstall = subprocess.run(
        [str(INSTALL_SH), "--uninstall"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_uninstall.returncode == 0, f"Uninstaller failed: {res_uninstall.stderr}"
    assert not launcher.exists(), "Launcher script should be removed after uninstall"
    assert not install_dir.exists(), "Install directory should be removed after uninstall"


def test_wheel_installation_with_real_dependencies(tmp_path):
    """Test regular isolated virtualenv installation using local wheels without --no-deps."""
    wheel_file = get_built_wheel()
    if wheel_file is None or not wheel_file.is_file():
        pytest.skip("Built wheel file not available")

    # Probe whether python3 venv works on this host
    test_v = subprocess.run(["python3", "-m", "venv", str(tmp_path / "probe_v2")], capture_output=True)
    if test_v.returncode != 0:
        pytest.skip("System python3 venv creation not supported on this host")

    if not VENDOR_WHEELS_DIR.is_dir() or not list(VENDOR_WHEELS_DIR.glob("*.whl")):
        pytest.skip("Vendor wheels directory not populated for offline test")

    test_venv = tmp_path / "test_venv"
    # Create isolated venv
    subprocess.run(["python3", "-m", "venv", str(test_venv)], check=True)

    # Install soulwave wheel using vendor_wheels as find-links
    pip_install_cmd = [
        str(test_venv / "bin" / "python3"),
        "-m", "pip", "install",
        "--no-index",
        f"--find-links={VENDOR_WHEELS_DIR}",
        f"--find-links={DIST_DIR}",
        str(wheel_file),
    ]
    res = subprocess.run(pip_install_cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"pip install with real dependencies failed: {res.stderr}"

    # Verify startup test in the venv
    run_cmd = [str(test_venv / "bin" / "python3"), "-m", "soulwave.cli", "--help"]
    run_res = subprocess.run(run_cmd, capture_output=True, text=True)
    assert run_res.returncode == 0
    assert "Soulwave" in run_res.stdout
    assert "--demo" in run_res.stdout


def test_rpm_spec_syntax_and_metadata():
    if shutil.which("rpmspec") is None:
        pytest.skip("rpmspec tool not installed on host")
    assert RPM_SPEC.is_file(), "soulwave.spec must exist"
    result = subprocess.run(
        ["rpmspec", "-q", str(RPM_SPEC)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"rpmspec failed: {result.stderr}"
    pkg_name = result.stdout.strip()
    assert f"soulwave-{PROJECT_VERSION}-1" in pkg_name

    # Verify requires
    req_res = subprocess.run(
        ["rpmspec", "-q", "--requires", str(RPM_SPEC)],
        capture_output=True,
        text=True,
        check=True,
    )
    requires = req_res.stdout.splitlines()
    assert any("python3" in r for r in requires)
    assert any("python3-gobject" in r for r in requires)
    assert any("python3-dbus" in r for r in requires)


def test_rpm_installation_and_standalone_launch(tmp_path):
    """Verify that the built RPM installs a self-contained runtime capable of launching soulwave."""
    if shutil.which("rpm2cpio") is None or shutil.which("cpio") is None:
        pytest.skip("rpm2cpio or cpio not installed on host")
    built_rpm = get_built_rpm()
    if built_rpm is None or not built_rpm.is_file():
        pytest.skip(f"Built RPM not found in {DIST_DIR} (run build_rpm.sh first)")

    clean_root = tmp_path / "clean_root"
    clean_root.mkdir()

    # Extract RPM payload using rpm2cpio and cpio quietly
    with open(os.devnull, "wb") as devnull:
        p_rpm2cpio = subprocess.Popen(["rpm2cpio", str(built_rpm)], stdout=subprocess.PIPE, stderr=devnull)
        subprocess.run(["cpio", "-idm", "--quiet"], cwd=str(clean_root), stdin=p_rpm2cpio.stdout, stdout=devnull, stderr=devnull, check=True)
        p_rpm2cpio.wait()

    # Verify directory layout
    vendor_dir = clean_root / "usr" / "lib" / "soulwave" / "vendor"
    bin_launcher = clean_root / "usr" / "bin" / "soulwave"

    assert vendor_dir.is_dir(), "Vendor runtime directory /usr/lib/soulwave/vendor must exist"
    assert bin_launcher.is_file(), "Launcher script /usr/bin/soulwave must exist"
    assert os.access(bin_launcher, os.X_OK), "Launcher script must be executable"

    # Verify core dependencies exist inside vendor
    assert (vendor_dir / "soulwave").is_dir(), "soulwave package must exist in vendor"
    assert (vendor_dir / "textual").is_dir(), "textual package must exist in vendor"
    assert (vendor_dir / "rich").is_dir(), "rich package must exist in vendor"
    assert (vendor_dir / "syncedlyrics").is_dir(), "syncedlyrics package must exist in vendor"
    assert (vendor_dir / "requests").is_dir(), "requests package must exist in vendor"

    # Launch CLI startup test non-interactively using system python with ONLY the isolated vendor runtime
    # -s: don't add current directory to sys.path
    env = os.environ.copy()
    env["PYTHONPATH"] = str(vendor_dir)
    cli_test = subprocess.run(
        ["/usr/bin/python3", "-s", "-m", "soulwave.cli", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert cli_test.returncode == 0, f"CLI startup test failed: {cli_test.stderr}"
    assert "Soulwave" in cli_test.stdout
    assert "--demo" in cli_test.stdout
    assert "--theme" in cli_test.stdout

    # Verify styles.tcss exists inside vendor soulwave package
    rpm_tcss = vendor_dir / "soulwave" / "ui" / "styles.tcss"
    assert rpm_tcss.is_file(), f"styles.tcss missing from RPM vendor runtime: {rpm_tcss}"
    assert rpm_tcss.stat().st_size > 50

    # Launch CLI health check using system python with ONLY the isolated vendor runtime
    check_rpm = subprocess.run(
        ["/usr/bin/python3", "-s", "-m", "soulwave.cli", "--check"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert check_rpm.returncode == 0, f"RPM health check failed: {check_rpm.stderr}\n{check_rpm.stdout}"
    assert "health check passed" in check_rpm.stdout


def test_rpm_spec_dynamic_version_override():
    """Verify that passing version and release macros dynamically overrides spec metadata."""
    if shutil.which("rpmspec") is None:
        pytest.skip("rpmspec tool not installed on host")
    assert RPM_SPEC.is_file(), "soulwave.spec must exist"
    
    # 1. Default version
    res_default = subprocess.run(["rpmspec", "-q", str(RPM_SPEC)], capture_output=True, text=True, check=True)
    assert f"soulwave-{PROJECT_VERSION}-1" in res_default.stdout

    # 2. Dynamic version override
    res_v2 = subprocess.run(
        ["rpmspec", "-q", "--define", "version 0.2.0", "--define", "release 3", str(RPM_SPEC)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "soulwave-0.2.0-3" in res_v2.stdout


def test_release_workflow_syntax_and_safety():
    assert RELEASE_YML.is_file(), "release.yml must exist"
    content = RELEASE_YML.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    assert "on" in data
    # Check trigger on v*
    assert "push" in data["on"]
    assert "tags" in data["on"]["push"]
    assert "v*" in data["on"]["push"]["tags"]

    # Verify workflow_dispatch requires tag input
    assert "workflow_dispatch" in data["on"]
    assert "inputs" in data["on"]["workflow_dispatch"]
    assert "tag" in data["on"]["workflow_dispatch"]["inputs"]
    assert data["on"]["workflow_dispatch"]["inputs"]["tag"]["required"] is True

    assert "jobs" in data
    jobs = data["jobs"]
    assert "validate" in jobs
    assert "test" in jobs
    assert "build-python" in jobs
    assert "build-rpm" in jobs
    assert "build-binary" in jobs
    assert "release" in jobs

    # Verify release job depends on all build and test jobs
    release_needs = jobs["release"]["needs"]
    for required_dep in ["validate", "test", "build-python", "build-rpm", "build-binary"]:
        assert required_dep in release_needs, f"Release job must depend on '{required_dep}'"

    # Verify all build and test jobs depend on validate and use the validated checkout ref
    for job_name in ["test", "build-python", "build-rpm", "build-binary", "release"]:
        job_needs = jobs[job_name]["needs"]
        if isinstance(job_needs, list):
            assert "validate" in job_needs, f"Job '{job_name}' must depend on 'validate'"
        else:
            assert job_needs == "validate", f"Job '{job_name}' must depend on 'validate'"

        # Verify checkout step uses the validated ref
        checkout_steps = [s for s in jobs[job_name]["steps"] if "actions/checkout" in s.get("uses", "")]
        assert len(checkout_steps) > 0, f"Job '{job_name}' must have a checkout step"
        ref_val = checkout_steps[0].get("with", {}).get("ref", "")
        assert "${{ needs.validate.outputs.checkout-ref }}" in ref_val, f"Job '{job_name}' must checkout the validated ref"


def test_release_tag_and_pyproject_version_consistency():
    """Verify semantic tag format validation and version matching against pyproject.toml."""
    import re
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject_text, re.M)
    assert match is not None
    current_version = match.group(1)

    # Valid matching tag
    valid_tag = f"v{current_version}"
    assert re.match(r"^v[0-9]+\.[0-9]+\.[0-9]+.*$", valid_tag)
    assert valid_tag.lstrip("v") == current_version

    # Invalid tags
    invalid_tags = ["0.1.0", "release-0.1.0", "v0", "v0.1", "latest", "main"]
    for t in invalid_tags:
        assert not re.match(r"^v[0-9]+\.[0-9]+\.[0-9]+.*$", t), f"Tag '{t}' should not pass semantic tag regex"

    # Mismatched version
    mismatched_tag = "v99.99.99"
    assert mismatched_tag.lstrip("v") != current_version


def test_release_workflow_version_extraction_snippet():
    """Verify that the exact python script in release.yml extracts project.version without error."""
    import sys
    import yaml
    import subprocess

    if sys.version_info < (3, 11):
        pytest.skip("tomllib standard library requires Python 3.11+")
    content = RELEASE_YML.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    steps = data["jobs"]["validate"]["steps"]
    resolve_step = next(s for s in steps if s.get("id") == "resolve")
    run_script = resolve_step["run"]

    # Verify tomllib is used in the script
    assert "tomllib" in run_script
    assert "PYPROJECT_VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open(\"pyproject.toml\", \"rb\"))[\"project\"][\"version\"])')" in run_script

    # Run the exact snippet directly from repo root
    res = subprocess.run(
        [
            sys.executable,
            "-c",
            'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])',
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == PROJECT_VERSION


def test_built_wheel_contains_stylesheet_package_data():
    """Regression test: Built wheel MUST contain soulwave/ui/styles.tcss."""
    import zipfile
    wheel = get_built_wheel()
    assert wheel is not None, "Wheel must exist or be built"
    with zipfile.ZipFile(wheel, "r") as z:
        names = z.namelist()
        assert "soulwave/ui/styles.tcss" in names, "Wheel archive MUST contain soulwave/ui/styles.tcss"
        content = z.read("soulwave/ui/styles.tcss").decode("utf-8")
        assert len(content.strip()) > 50, "styles.tcss in wheel must not be empty"
        assert "Screen" in content, "styles.tcss in wheel must contain valid Textual CSS"


def test_built_sdist_contains_stylesheet_package_data():
    """Regression test: Built sdist MUST contain soulwave/ui/styles.tcss."""
    import tarfile
    sdists = [s for s in DIST_DIR.glob("*.tar.gz") if PROJECT_VERSION in s.name]
    if not sdists:
        sdists = sorted(DIST_DIR.glob("*.tar.gz"), key=lambda s: s.name, reverse=True)
    if not sdists:
        pytest.skip("Source distribution not found in dist/")
    with tarfile.open(sdists[0], "r:gz") as tar:
        names = tar.getnames()
        matching = [n for n in names if n.endswith("soulwave/ui/styles.tcss")]
        assert len(matching) > 0, "Source distribution archive MUST contain soulwave/ui/styles.tcss"


def test_isolated_wheel_install_mounts_ui_without_stylesheet_error(tmp_path):
    """Regression test: Installing wheel into clean isolated environment mounts Textual UI without StylesheetError."""
    wheel_file = get_built_wheel()
    if wheel_file is None or not wheel_file.is_file():
        pytest.skip("Built wheel file not available")

    # Probe whether python3 venv works on this host
    test_v = subprocess.run(["python3", "-m", "venv", str(tmp_path / "probe_v_ui")], capture_output=True)
    if test_v.returncode != 0:
        pytest.skip("System python3 venv creation not supported on this host")

    if not VENDOR_WHEELS_DIR.is_dir() or not list(VENDOR_WHEELS_DIR.glob("*.whl")):
        pytest.skip("Vendor wheels directory not populated for offline test")

    test_venv = tmp_path / "ui_test_venv"
    subprocess.run(["python3", "-m", "venv", str(test_venv)], check=True)

    # Install soulwave wheel using vendor_wheels
    pip_install_cmd = [
        str(test_venv / "bin" / "python3"),
        "-m", "pip", "install",
        "--no-index",
        f"--find-links={VENDOR_WHEELS_DIR}",
        f"--find-links={DIST_DIR}",
        str(wheel_file),
    ]
    res = subprocess.run(pip_install_cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"pip install failed: {res.stderr}"

    # 1. Assert stylesheet file actually exists in site-packages
    site_packages_dirs = list(test_venv.glob("lib/python*/site-packages"))
    assert len(site_packages_dirs) > 0, "site-packages not found in venv"
    installed_tcss = site_packages_dirs[0] / "soulwave" / "ui" / "styles.tcss"
    assert installed_tcss.is_file(), f"styles.tcss was not installed to site-packages: {installed_tcss}"
    assert installed_tcss.stat().st_size > 50

    # 2. Run soulwave --check inside the isolated environment
    check_res = subprocess.run(
        [str(test_venv / "bin" / "python3"), "-m", "soulwave.cli", "--check"],
        capture_output=True,
        text=True,
    )
    assert check_res.returncode == 0, f"soulwave --check failed: {check_res.stderr}\n{check_res.stdout}"
    assert "health check passed" in check_res.stdout

    # 3. Mount SoulwaveApp headless to verify no StylesheetError
    headless_test = subprocess.run(
        [
            str(test_venv / "bin" / "python3"),
            "-c",
            (
                "import asyncio\n"
                "from soulwave.ui.app import SoulwaveApp\n"
                "async def test():\n"
                "    app = SoulwaveApp(force_demo=True)\n"
                "    async with app.run_test(size=(80, 24)) as pilot:\n"
                "        await pilot.pause(0.05)\n"
                "        assert app.mascot_view is not None\n"
                "        print('SUCCESS_UI_MOUNTED')\n"
                "asyncio.run(test())\n"
            ),
        ],
        capture_output=True,
        text=True,
    )
    assert headless_test.returncode == 0, f"Headless UI test failed with: {headless_test.stderr}"
    assert "SUCCESS_UI_MOUNTED" in headless_test.stdout


def test_installer_health_check_catches_missing_resource(tmp_path):
    """Verify that install.sh runs health check and fails if styles.tcss is missing."""
    wheel_file = get_built_wheel()
    if wheel_file is None or not wheel_file.is_file():
        pytest.skip("Built wheel file not available")

    test_v = subprocess.run(["python3", "-m", "venv", str(tmp_path / "probe_v_h")], capture_output=True)
    if test_v.returncode != 0:
        pytest.skip("System python3 venv creation not supported on this host")

    if not VENDOR_WHEELS_DIR.is_dir() or not list(VENDOR_WHEELS_DIR.glob("*.whl")):
        pytest.skip("Vendor wheels directory not populated for offline test")

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PIP_FIND_LINKS"] = f"{VENDOR_WHEELS_DIR} {DIST_DIR}"
    env["PIP_NO_INDEX"] = "1"

    # Normal install should succeed and output health check passed
    res_install = subprocess.run(
        [str(INSTALL_SH), "--file", str(wheel_file), "--user"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_install.returncode == 0, f"Installer failed: {res_install.stderr}\n{res_install.stdout}"
    assert "Post-installation health check passed" in res_install.stdout
    assert "Soulwave installed successfully!" in res_install.stdout

    launcher = fake_home / ".local" / "bin" / "soulwave"
    assert launcher.is_file()

    # Now simulate missing stylesheet defect in installed location
    installed_tcss_files = list(fake_home.glob(".local/share/soulwave/**/styles.tcss"))
    assert len(installed_tcss_files) > 0, "styles.tcss should be present in installed directory"
    for f in installed_tcss_files:
        f.unlink()

    # Health check directly must now FAIL with non-zero exit code
    check_fail = subprocess.run([str(launcher), "--check"], capture_output=True, text=True, env=env, cwd=str(tmp_path))
    assert check_fail.returncode != 0
    assert ("Stylesheet file" in check_fail.stderr and "not found" in check_fail.stderr) or "StylesheetError" in check_fail.stderr


def test_playerctl_availability_and_distro_hints():
    """Verify is_mpris_available and get_playerctl_install_hint behave as expected across distros."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from soulwave.player.mpris import is_mpris_available, get_playerctl_install_hint
    import shutil

    # get_playerctl_install_hint returns a valid string containing 'install playerctl'
    hint = get_playerctl_install_hint()
    assert "install" in hint
    assert "playerctl" in hint

    # When playerctl is mocked as missing and dbus is False, is_mpris_available returns False
    from soulwave.player import mpris
    orig_dbus = mpris._DBUS_AVAILABLE
    orig_which = shutil.which
    try:
        mpris._DBUS_AVAILABLE = False
        shutil.which = lambda cmd: None
        assert is_mpris_available() is False

        # In this state, hint suggests a valid command
        mock_hint = get_playerctl_install_hint()
        assert "sudo apt install playerctl" in mock_hint

        # Verify UI views render the hint if textual is available in environment
        try:
            import textual
            from soulwave.ui.widgets.now_playing import NowPlayingView
            from soulwave.ui.widgets.lyrics_panel import LyricsPanelView
            from soulwave.player.base import PlayerState, PlaybackStatus

            np = NowPlayingView(PlayerState(status=PlaybackStatus.DISCONNECTED))
            rendered_np = np.render()
            assert "playerctl" in str(rendered_np)

            lp = LyricsPanelView()
            lp.is_waiting = True
            rendered_lp = lp.render()
            assert "playerctl" in str(rendered_lp)
        except ImportError:
            pass
    finally:
        mpris._DBUS_AVAILABLE = orig_dbus
        shutil.which = orig_which


def _make_mock_binary(tmp_path: Path) -> Path:
    mock_bin = tmp_path / "soulwave-linux-x86_64"
    mock_bin.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--check\" ]; then\n"
        "    echo 'Post-installation health check passed.'\n"
        "    exit 0\n"
        "fi\n"
        "echo 'Soulwave standalone binary'\n"
    )
    mock_bin.chmod(0o755)
    return mock_bin


def _create_mock_sudo(tmp_path: Path, log_file: Path, exit_code: int = 0, create_target: Path = None) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    sudo_script = bin_dir / "sudo"
    create_stmt = f'touch "{create_target}"' if create_target else ""
    sudo_script.write_text(
        f"#!/bin/sh\n"
        f"echo \"$*\" >> \"{log_file}\"\n"
        f"{create_stmt}\n"
        f"exit {exit_code}\n"
    )
    sudo_script.chmod(0o755)
    return bin_dir


def test_installer_menu_displayed_when_playerctl_missing(tmp_path):
    """Verify that when playerctl is missing, installer shows the warning and 2-option menu."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    # Feed '2\n' so it exits cleanly after rendering the menu
    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="2\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "WARNING: Recommended audio utility not found: playerctl" in res.stdout
    assert "SoulWave needs playerctl to track live music" in res.stdout
    assert "[1] (Recommended) Install playerctl automatically using sudo" in res.stdout
    assert "[2] Exit and install playerctl manually" in res.stdout
    assert "[3] Skip playerctl and continue" in res.stdout
    assert "[4] Exit installer" in res.stdout
    assert "Select an option [1-4] (default: 1):" in res.stdout


def test_installer_option_1_invokes_correct_package_manager_command(tmp_path):
    """Verify that Option 1 invokes the exact distro-specific install command using sudo."""
    expected_commands = {
        "apt": "apt install -y playerctl",
        "dnf": "dnf install -y playerctl",
        "pacman": "pacman -S --noconfirm playerctl",
        "zypper": "zypper install -y playerctl",
    }

    mock_bin = _make_mock_binary(tmp_path)

    for pkg_mgr, expected_cmd in expected_commands.items():
        sub_tmp = tmp_path / pkg_mgr
        sub_tmp.mkdir()
        fake_home = sub_tmp / "home"
        fake_home.mkdir()
        mock_playerctl = sub_tmp / "mock_playerctl"
        sudo_log = sub_tmp / "sudo.log"
        mock_bin_dir = _create_mock_sudo(sub_tmp, sudo_log, exit_code=0, create_target=mock_playerctl)

        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
        env["SOULWAVE_TEST_PKG_MGR"] = pkg_mgr
        env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
        env["SOULWAVE_READ_STDIN"] = "1"

        res = subprocess.run(
            [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
            input="1\n",
            capture_output=True,
            text=True,
            env=env,
        )
        assert res.returncode == 0, f"Failed for {pkg_mgr}: {res.stderr}\n{res.stdout}"
        assert f"Installing playerctl using: sudo {expected_cmd}" in res.stdout
        assert "Successfully installed and verified playerctl!" in res.stdout
        assert "Soulwave installed successfully!" in res.stdout

        # Verify sudo log recorded exact invocation
        assert sudo_log.exists(), f"sudo was not called for {pkg_mgr}"
        log_content = sudo_log.read_text().strip()
        assert expected_cmd in log_content, f"Expected '{expected_cmd}' in sudo call, got: {log_content}"


def test_installer_option_1_verifies_dependency_before_continuing(tmp_path):
    """Verify that if sudo succeeds but playerctl is still not verified, installer aborts."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"  # Will NOT be created
    sudo_log = tmp_path / "sudo.log"
    mock_bin_dir = _create_mock_sudo(tmp_path, sudo_log, exit_code=0, create_target=None)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="1\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode != 0
    assert "Installation command completed, but 'playerctl' was not found in PATH" in (res.stdout + res.stderr)

    # SoulWave should NOT be installed
    installed_launcher = fake_home / ".local" / "bin" / "soulwave"
    assert not installed_launcher.exists()


def test_installer_option_2_prints_distro_specific_manual_command(tmp_path):
    """Verify that Option 2 prints the correct distro-specific manual install command."""
    expected_manual_commands = {
        "apt": "sudo apt install playerctl",
        "dnf": "sudo dnf install playerctl",
        "pacman": "sudo pacman -S playerctl",
        "zypper": "sudo zypper install playerctl",
    }

    mock_bin = _make_mock_binary(tmp_path)

    for pkg_mgr, expected_cmd in expected_manual_commands.items():
        sub_tmp = tmp_path / pkg_mgr
        sub_tmp.mkdir()
        fake_home = sub_tmp / "home"
        fake_home.mkdir()
        mock_playerctl = sub_tmp / "mock_playerctl"

        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
        env["SOULWAVE_TEST_PKG_MGR"] = pkg_mgr
        env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
        env["SOULWAVE_READ_STDIN"] = "1"

        res = subprocess.run(
            [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
            input="2\n",
            capture_output=True,
            text=True,
            env=env,
        )
        assert res.returncode == 0
        assert "Manual Installation Instructions" in res.stdout
        assert expected_cmd in res.stdout, f"Expected '{expected_cmd}' in output for {pkg_mgr}:\n{res.stdout}"


def test_installer_option_2_prints_rerun_command(tmp_path):
    """Verify that Option 2 prints the exact curl rerun command."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="2\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash" in res.stdout


def test_installer_option_2_exits_zero_without_installing(tmp_path):
    """Verify that Option 2 exits cleanly (code 0) without installing SoulWave or leaving files."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "pacman"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="2\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "Exiting installer." in res.stdout
    # Verify no files installed
    assert not (fake_home / ".local" / "bin" / "soulwave").exists()
    assert not (fake_home / ".local" / "share" / "soulwave").exists()


def test_installer_invalid_input_prompts_again(tmp_path):
    """Verify that invalid inputs display an error and reprompt until valid choice is provided."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    # Provide two invalid options ('invalid', '99'), then '2'
    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="invalid\n99\n2\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "Invalid selection: 'invalid'. Please enter 1, 2, 3, or 4." in res.stdout
    assert "Invalid selection: '99'. Please enter 1, 2, 3, or 4." in res.stdout
    assert "Manual Installation Instructions" in res.stdout


def test_installer_empty_input_selects_option_1(tmp_path):
    """Verify that pressing Enter (empty input) defaults to Option 1 and installs playerctl."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"
    sudo_log = tmp_path / "sudo.log"
    mock_bin_dir = _create_mock_sudo(tmp_path, sudo_log, exit_code=0, create_target=mock_playerctl)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="\n",  # Empty string defaults to 1
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0, f"Installer failed: {res.stderr}\n{res.stdout}"
    assert sudo_log.exists()
    assert "apt install -y playerctl" in sudo_log.read_text()
    assert "Soulwave installed successfully!" in res.stdout


def test_installer_unsupported_package_manager_handled_safely(tmp_path):
    """Verify that unknown/unsupported package managers display manual advice and exit cleanly without sudo."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"
    sudo_log = tmp_path / "sudo.log"
    mock_bin_dir = _create_mock_sudo(tmp_path, sudo_log, exit_code=0, create_target=None)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "unknown"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 1
    assert "Automatic installation is unavailable because no supported package manager was detected." in res.stdout
    assert "Please install 'playerctl' manually through your distribution's package manager" in res.stdout
    assert not sudo_log.exists(), "sudo must never be invoked for unsupported package managers"
    assert not (fake_home / ".local" / "bin" / "soulwave").exists()


def test_installer_non_interactive_execution_does_not_hang(tmp_path):
    """Verify non-interactive / headless execution exits with error and does not hang; --no-deps bypasses."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_NONINTERACTIVE"] = "1"

    # 1. Non-interactive without --no-deps should exit 1 immediately without hanging
    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    assert res.returncode == 1
    assert "Interactive terminal not available for dependency installation." in (res.stdout + res.stderr)
    assert "sudo apt install playerctl" in res.stdout
    assert "--no-deps" in res.stdout

    # 2. Non-interactive WITH --no-deps should bypass dependency check and install successfully
    res_nodeps = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user", "--no-deps"],
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    assert res_nodeps.returncode == 0
    assert "Skipping dependency installation (--no-deps specified)." in res_nodeps.stdout
    assert "Soulwave installed successfully!" in res_nodeps.stdout
    assert (fake_home / ".local" / "bin" / "soulwave").is_file()


def test_installer_failed_dependency_installation_stops(tmp_path):
    """Verify that when the package manager sudo command fails, the installer aborts with clear diagnostics."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"
    sudo_log = tmp_path / "sudo.log"
    # Sudo exits with error 1
    mock_bin_dir = _create_mock_sudo(tmp_path, sudo_log, exit_code=1, create_target=None)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="1\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 1
    assert "Failed to install playerctl" in (res.stdout + res.stderr)
    assert "Sudo authentication failed or permission was denied" in res.stdout
    assert "package manager process is currently running and holding the lock" in res.stdout
    assert "Repository mirrors or network connections are unreachable" in res.stdout
    assert "sudo apt install playerctl" in res.stdout

    # Verify SoulWave was NOT installed
    assert not (fake_home / ".local" / "bin" / "soulwave").exists()


def test_installer_diagnostics_stage_output(tmp_path):
    """Verify that Stage 1 System Diagnostics outputs required system parameters and indicators."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user", "--no-deps"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "Stage [1/5]: System Diagnostics" in res.stdout
    assert "• Linux Distribution:" in res.stdout
    assert "• CPU Architecture:" in res.stdout
    assert "• Package Manager:" in res.stdout
    assert "• D-Bus Session:" in res.stdout
    assert "• Download Utility:" in res.stdout
    assert "• Python Runtime:" in res.stdout
    assert "• playerctl (MPRIS):" in res.stdout
    assert "• cava (Visualizer):" in res.stdout
    assert "• Target Directory:" in res.stdout
    assert "• PATH Status:" in res.stdout


def test_installer_option_3_skip_selection_installs_and_continues(tmp_path):
    """Verify that selecting Option 3 skips playerctl, issues an informative notice, and completes installation."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "apt"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="3\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "Skipping playerctl. Live desktop music tracking will be inactive until playerctl is installed." in res.stdout
    assert "soulwave -d" in res.stdout
    assert "Soulwave installed successfully!" in res.stdout
    installed_launcher = fake_home / ".local" / "bin" / "soulwave"
    assert installed_launcher.is_file()


def test_installer_option_4_exit_selection(tmp_path):
    """Verify that Option 4 cancels installation and exits cleanly with 0 without leaving files."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)
    mock_playerctl = tmp_path / "mock_playerctl"

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["SOULWAVE_TEST_MOCK_PLAYERCTL_FILE"] = str(mock_playerctl)
    env["SOULWAVE_TEST_PKG_MGR"] = "dnf"
    env["SOULWAVE_FORCE_INTERACTIVE"] = "1"
    env["SOULWAVE_READ_STDIN"] = "1"

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user"],
        input="4\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "Installation cancelled by user. Exiting installer." in res.stdout
    assert not (fake_home / ".local" / "bin" / "soulwave").exists()


def test_installer_package_manager_commands_all_distros():
    """Verify package manager commands for all supported distributions (apt, dnf, pacman, zypper)."""
    bash_script = f"""
    source "{INSTALL_SH}"
    for mgr in apt dnf pacman zypper; do
        auto_pctl=$(get_playerctl_install_command "$mgr" "auto")
        man_pctl=$(get_playerctl_install_command "$mgr" "manual")
        auto_cava=$(get_cava_install_command "$mgr" "auto")
        man_cava=$(get_cava_install_command "$mgr" "manual")
        comb=$(get_combined_install_command "$mgr" "auto")
        echo "[$mgr] auto_pctl: $auto_pctl"
        echo "[$mgr] man_pctl: $man_pctl"
        echo "[$mgr] auto_cava: $auto_cava"
        echo "[$mgr] man_cava: $man_cava"
        echo "[$mgr] comb: $comb"
    done
    """
    res = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True, check=True)
    out = res.stdout

    # apt
    assert "[apt] auto_pctl: sudo apt install -y playerctl" in out
    assert "[apt] man_pctl: sudo apt install playerctl" in out
    assert "[apt] auto_cava: sudo apt install -y cava" in out
    assert "[apt] comb: sudo apt install -y playerctl cava" in out

    # dnf
    assert "[dnf] auto_pctl: sudo dnf install -y playerctl" in out
    assert "[dnf] man_pctl: sudo dnf install playerctl" in out
    assert "[dnf] auto_cava: sudo dnf install -y cava" in out
    assert "[dnf] comb: sudo dnf install -y playerctl cava" in out

    # pacman
    assert "[pacman] auto_pctl: sudo pacman -S --noconfirm playerctl" in out
    assert "[pacman] man_pctl: sudo pacman -S playerctl" in out
    assert "[pacman] auto_cava: sudo pacman -S --noconfirm cava" in out
    assert "[pacman] comb: sudo pacman -S --noconfirm playerctl cava" in out

    # zypper
    assert "[zypper] auto_pctl: sudo zypper install -y playerctl" in out
    assert "[zypper] man_pctl: sudo zypper install playerctl" in out
    assert "[zypper] auto_cava: sudo zypper install -y cava" in out
    assert "[zypper] comb: sudo zypper install -y playerctl cava" in out


def test_installer_uninstall_preserves_user_config_and_cache(tmp_path):
    """Verify that uninstallation removes binaries but strictly preserves user configuration and cache."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)

    # Pre-populate user configuration and lyrics cache
    config_dir = fake_home / ".config" / "soulwave"
    config_dir.mkdir(parents=True)
    user_config_file = config_dir / "config.toml"
    user_config_file.write_text('theme = "cyberpunk"\nfps = 20\n')

    cache_dir = fake_home / ".cache" / "soulwave" / "lyrics"
    cache_dir.mkdir(parents=True)
    cached_lrc = cache_dir / "test_song.lrc"
    cached_lrc.write_text("[00:01.00] Test lyric line\n")

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    # 1. Install
    res_install = subprocess.run(
        [str(INSTALL_SH), "--file", str(mock_bin), "--user", "--no-deps"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_install.returncode == 0
    launcher = fake_home / ".local" / "bin" / "soulwave"
    assert launcher.is_file()

    # 2. Uninstall
    res_uninstall = subprocess.run(
        [str(INSTALL_SH), "--uninstall"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_uninstall.returncode == 0
    assert not launcher.exists(), "Binary must be deleted upon uninstall"
    assert "User Data Preservation:" in res_uninstall.stdout
    assert "User configuration (~/.config/soulwave) and cache (~/.cache/soulwave) were preserved." in res_uninstall.stdout

    # Verify files still exist intact
    assert user_config_file.is_file(), "User config file must be preserved"
    assert "cyberpunk" in user_config_file.read_text()
    assert cached_lrc.is_file(), "User lyrics cache must be preserved"
    assert "Test lyric line" in cached_lrc.read_text()


def test_installer_repair_mode(tmp_path):
    """Verify that --repair runs the repair assistant and re-verifies installation."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_bin = _make_mock_binary(tmp_path)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    res_repair = subprocess.run(
        [str(INSTALL_SH), "--repair", "--file", str(mock_bin), "--user", "--no-deps"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_repair.returncode == 0
    assert "Soulwave Installation Repair Assistant" in res_repair.stdout
    assert "Stage [1/5]: System Diagnostics" in res_repair.stdout
    assert "Soulwave repaired successfully!" in res_repair.stdout
    assert (fake_home / ".local" / "bin" / "soulwave").is_file()


def test_installer_invalid_local_file_rejected(tmp_path):
    """Verify that passing an invalid local file (not .rpm, .whl, or ELF binary) is rejected cleanly."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    invalid_file = tmp_path / "invalid_package.txt"
    invalid_file.write_text("This is an ordinary text file, not a Soulwave binary or package.")
    # Ensure it's not executable
    invalid_file.chmod(0o644)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    res = subprocess.run(
        [str(INSTALL_SH), "--file", str(invalid_file), "--user"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode != 0
    assert "Unsupported file type for" in (res.stdout + res.stderr)
    assert "Expected an ELF binary, .rpm, or .whl file." in (res.stdout + res.stderr)


def test_installer_missing_version_and_file_arguments():
    """Verify that omitting required arguments for --version and --file gives friendly error messages."""
    # 1. Missing version arg
    res_v = subprocess.run([str(INSTALL_SH), "--version"], capture_output=True, text=True)
    assert res_v.returncode != 0
    assert "Option '--version' requires a version argument" in (res_v.stdout + res_v.stderr)

    # 2. Missing file arg
    res_f = subprocess.run([str(INSTALL_SH), "--file"], capture_output=True, text=True)
    assert res_f.returncode != 0
    assert "Option '--file' requires a file path argument" in (res_f.stdout + res_f.stderr)


def test_cli_doctor_command():
    """Verify that soulwave --doctor runs the complete diagnostic report and exits with 0."""
    res = subprocess.run(
        [sys.executable, "-m", "soulwave.cli", "--doctor"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0, f"Doctor failed: {res.stderr}\n{res.stdout}"
    out = res.stdout
    assert "Soulwave Doctor — Diagnostic Report" in out
    assert "[1] System Environment" in out
    assert "[2] Core Runtime & UI Resources" in out
    assert "[3] D-Bus & MPRIS Subsystem" in out
    assert "[4] Audio Visualizer & Sound Server" in out
    assert "[5] User Configuration & Data Storage" in out
    assert "textual" in out
    assert "rich" in out
    assert "requests" in out
    assert "syncedlyrics" in out
    assert "styles.tcss" in out
    assert "SYSTEM STATUS" in out


if __name__ == "__main__":
    import inspect
    import tempfile

    current_module = sys.modules[__name__]
    test_names = [
        name for name in dir(current_module)
        if name.startswith("test_") and callable(getattr(current_module, name))
    ]

    passed = 0
    skipped = 0
    failed = 0

    print(f"Running {len(test_names)} packaging and installer tests...")
    for name in sorted(test_names):
        fn = getattr(current_module, name)
        sig = inspect.signature(fn)
        try:
            if "tmp_path" in sig.parameters:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            print(f"  [PASS] {name}")
            passed += 1
        except unittest.SkipTest as e:
            print(f"  [SKIP] {name}: {e}")
            skipped += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nTest Summary: {passed} passed, {skipped} skipped, {failed} failed")
    if failed > 0:
        sys.exit(1)


