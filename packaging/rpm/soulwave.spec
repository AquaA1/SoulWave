%{!?version: %global version 0.1.3}
Name:           soulwave
Version:        %{version}
Release:        %{?release}%{!?release:1}%{?dist}
Summary:        Retro-futuristic terminal music controller with grooving soul mascot

License:        MIT
URL:            https://github.com/AquaA1/SoulWave
Source0:        %{name}-%{version}-py3-none-any.whl
Source1:        README.md
Source2:        LICENSE


BuildRequires:  python3

Requires:       python3 >= 3.10
Requires:       python3-gobject
Requires:       python3-dbus

Recommends:     playerctl
Recommends:     cava

%description
Soulwave is a retro-futuristic terminal music controller that connects to
active music players (Spotify, Firefox, Chromium, Cider, etc.) via MPRIS,
renders an animated grooving pixel-art soul mascot and companions, displays
synchronized lyrics with auto-scroll, and features an audio visualizer.

%prep
# Pre-built wheel source

%build
# No compilation required for pure Python wheel

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_prefix}/lib/%{name}/vendor
mkdir -p %{buildroot}%{_bindir}

# Install runtime dependencies into isolated vendor directory
if [ ! -d %{_sourcedir}/vendor_wheels ] || ! compgen -G "%{_sourcedir}/vendor_wheels/*.whl" > /dev/null; then
    echo "ERROR: Missing required vendor_wheels. Complete runtime dependencies must be provided." >&2
    exit 1
fi
%{__python3} -m pip install --no-deps --target %{buildroot}%{_prefix}/lib/%{name}/vendor %{_sourcedir}/vendor_wheels/*.whl

# Install soulwave wheel into isolated vendor directory
%{__python3} -m pip install --no-deps --target %{buildroot}%{_prefix}/lib/%{name}/vendor %{SOURCE0}

# Install doc and license
install -D -m 0644 %{SOURCE1} %{buildroot}%{_docdir}/%{name}/README.md
install -D -m 0644 %{SOURCE2} %{buildroot}%{_licensedir}/%{name}/LICENSE

# Create launcher script in /usr/bin/soulwave
cat << 'EOF' > %{buildroot}%{_bindir}/%{name}
#!/bin/sh
export PYTHONPATH="%{_prefix}/lib/soulwave/vendor:${PYTHONPATH}"
exec /usr/bin/python3 -m soulwave.cli "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/%{name}

%check
PYTHONPATH=%{buildroot}%{_prefix}/lib/%{name}/vendor %{__python3} -m soulwave.cli --check

%files
%{_docdir}/%{name}
%{_licensedir}/%{name}
%{_bindir}/%{name}
%{_prefix}/lib/%{name}

%changelog
* Fri Oct 16 2026 Soulwave Contributors <support@soulwave.local> - 0.1.3-1
- Fix stale lyrics when switching between mascot dance and lyrics view on track change
- Enable background lyrics prefetching while companion view is active
- Protect in-flight async lyrics queries against duplicate requests

* Fri Oct 16 2026 Soulwave Contributors <support@soulwave.local> - 0.1.2-1
- Fix slow/missing lyrics by prioritizing Lrclib and cleaning YouTube metadata
- Fix mid-song position sync and backward seek handling in interpolator and D-Bus
- Prevent intro lyric lines from highlighting before first timestamp

* Fri Oct 16 2026 Soulwave Contributors <support@soulwave.local> - 0.1.1-1
- Critical fix: bundle styles.tcss package data into wheel and vendor runtime
- Add non-interactive health check verification

* Fri Oct 16 2026 Soulwave Contributors <support@soulwave.local> - 0.1.0-1
- Production release of Soulwave
