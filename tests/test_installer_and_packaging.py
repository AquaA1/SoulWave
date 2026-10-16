"""Tests for installer script (install.sh), RPM spec, and release workflow."""
import hashlib
import os
import subprocess
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"
RPM_SPEC = REPO_ROOT / "packaging" / "rpm" / "soulwave.spec"
RELEASE_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"
WHEEL_FILE = REPO_ROOT / "dist" / "soulwave-0.1.0-py3-none-any.whl"


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
    assert "--version" in result.stdout
    assert "--file" in result.stdout
    assert "--user" in result.stdout
    assert "--uninstall" in result.stdout


def test_install_script_missing_local_file():
    result = subprocess.run(
        [str(INSTALL_SH), "--file", "nonexistent-package.whl"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Specified local file not found" in result.stderr or "Specified local file not found" in result.stdout


def test_checksum_verification_logic(tmp_path):
    test_file = tmp_path / "test-pkg.whl"
    test_content = b"fake-package-data-12345"
    test_file.write_bytes(test_content)

    correct_hash = hashlib.sha256(test_content).hexdigest()
    checksums_file = tmp_path / "checksums.txt"
    checksums_file.write_text(f"{correct_hash}  test-pkg.whl\n")

    # Source install.sh and run verify_checksum function
    bash_verify = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{checksums_file}"
    """
    res_ok = subprocess.run(
        ["bash", "-c", bash_verify],
        capture_output=True,
        text=True,
    )
    assert res_ok.returncode == 0
    assert "SHA-256 verified" in res_ok.stdout or "SHA-256 verified" in res_ok.stderr

    # Test tampering
    tampered_checksums = tmp_path / "tampered_checksums.txt"
    tampered_checksums.write_text("0000000000000000000000000000000000000000000000000000000000000000  test-pkg.whl\n")

    bash_tampered = f"""
    source "{INSTALL_SH}"
    verify_checksum "{test_file}" "{tampered_checksums}"
    """
    res_bad = subprocess.run(
        ["bash", "-c", bash_tampered],
        capture_output=True,
        text=True,
    )
    assert res_bad.returncode != 0
    assert "Checksum verification failed" in res_bad.stderr or "Checksum verification failed" in res_bad.stdout


def test_user_mode_installation_and_uninstallation(tmp_path):
    assert WHEEL_FILE.is_file(), f"Wheel file {WHEEL_FILE} must exist before running test"

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    # 1. Install using --user and --no-deps
    res_install = subprocess.run(
        [str(INSTALL_SH), "--file", str(WHEEL_FILE), "--user", "--no-deps"],
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


def test_rpm_spec_syntax_and_metadata():
    assert RPM_SPEC.is_file(), "soulwave.spec must exist"
    result = subprocess.run(
        ["rpmspec", "-q", str(RPM_SPEC)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"rpmspec failed: {result.stderr}"
    pkg_name = result.stdout.strip()
    assert pkg_name.startswith("soulwave-0.1.0-1")

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


def test_release_workflow_syntax():
    assert RELEASE_YML.is_file(), "release.yml must exist"
    content = RELEASE_YML.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    assert "on" in data
    # Check trigger on v*
    assert "push" in data["on"]
    assert "tags" in data["on"]["push"]
    assert "v*" in data["on"]["push"]["tags"]

    assert "jobs" in data
    jobs = data["jobs"]
    assert "test" in jobs
    assert "build-python" in jobs
    assert "build-rpm" in jobs
    assert "release" in jobs

    # Verify release job needs dependencies
    assert set(jobs["release"]["needs"]) == {"test", "build-python", "build-rpm"}
