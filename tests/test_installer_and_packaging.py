"""Comprehensive tests for installer script (install.sh), RPM packaging, and release workflow."""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"
RPM_SPEC = REPO_ROOT / "packaging" / "rpm" / "soulwave.spec"
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
    all_wheels = list(DIST_DIR.glob("*.whl"))
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
    assert "release" in jobs

    # Verify all build and test jobs depend on validate and use the validated checkout ref
    for job_name in ["test", "build-python", "build-rpm", "release"]:
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
    assert "Stylesheet file not found" in check_fail.stderr or "StylesheetError" in check_fail.stderr

