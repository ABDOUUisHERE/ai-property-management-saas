"""Run checksum-pinned Gitleaks against files eligible for Git, with a detector self-test."""

from __future__ import annotations

import hashlib
import io
import platform
import secrets
import shutil
import string
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "8.30.1"
ARCHIVES = {
    ("Windows", "AMD64"): (
        "windows_x64.zip",
        "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
    ),
    ("Linux", "x86_64"): (
        "linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    ("Linux", "aarch64"): (
        "linux_arm64.tar.gz",
        "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    ),
}


def executable() -> Path:
    archive_name, expected_hash = ARCHIVES[(platform.system(), platform.machine())]
    filename = f"gitleaks_{VERSION}_{archive_name}"
    cache = ROOT / ".cache/tools"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / filename
    if not archive.exists():
        url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/{filename}"
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed official HTTPS
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            raise RuntimeError("Gitleaks archive checksum mismatch")
        archive.write_bytes(payload)
    payload = archive.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_hash:
        raise RuntimeError("Cached Gitleaks archive checksum mismatch")
    name = "gitleaks.exe" if platform.system() == "Windows" else "gitleaks"
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as source:
            binary = source.read(name)
    else:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as source:
            member = source.extractfile(name)
            if member is None:
                raise RuntimeError("Gitleaks executable missing in archive")
            binary = member.read()
    target = cache / name
    target.write_bytes(binary)
    target.chmod(0o700)
    return target


def scan(binary: Path, directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - official, checksum-verified binary, no shell
        [str(binary), "dir", str(directory), "--redact", "--no-banner"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def main() -> None:
    binary = executable()
    with tempfile.TemporaryDirectory(prefix="pms-gitleaks-probe-") as temporary:
        fixture = Path(temporary) / "fixture.txt"
        fixture.write_text("Ordinary documentation.\n", encoding="utf-8")
        if scan(binary, Path(temporary)).returncode != 0:
            raise RuntimeError("Gitleaks negative detector self-test failed")
        fake = "ghp_" + "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
        )
        fixture.write_text(f"token={fake}\n", encoding="utf-8")
        if scan(binary, Path(temporary)).returncode != 1:
            raise RuntimeError("Gitleaks did not detect its synthetic secret fixture")
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git is required to determine the repository file set")
    result = subprocess.run(  # noqa: S603
        [git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=20,
    )
    names = sorted(set(result.stdout.decode("utf-8").strip("\0").split("\0")))
    with tempfile.TemporaryDirectory(prefix="pms-gitleaks-snapshot-") as temporary:
        snapshot = Path(temporary)
        for name in names:
            source = ROOT / name
            if not source.exists():
                continue
            if source.is_symlink() or not source.resolve().is_relative_to(ROOT.resolve()):
                raise RuntimeError("Refusing a file outside the repository")
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        result = scan(binary, snapshot)
        if result.returncode:
            # The scanner was explicitly invoked with full secret redaction.
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise RuntimeError("Secret scan failed; all reported secret values are redacted")
    print(f"Gitleaks {VERSION}: detector self-test and {len(names)} repository files OK")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        print(f"Secret scan failed: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
