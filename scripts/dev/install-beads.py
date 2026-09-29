#!/usr/bin/env python3
"""Install the latest stable official Linux release, with checksum verification."""
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request


def fetch(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "quoridor-beads-setup"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out)


def main():
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or arch is None:
        raise SystemExit("This DevContainer installer supports Linux amd64/arm64.")
    target = Path.home() / ".local/bin/bd"
    with tempfile.TemporaryDirectory(prefix="quoridor-beads-install-") as directory:
        work = Path(directory)
        fetch("https://api.github.com/repos/gastownhall/beads/releases/latest", work / "release.json")
        release = json.loads((work / "release.json").read_text())
        if release["draft"] or release["prerelease"]:
            raise SystemExit("Expected a stable, published release")
        version = release["tag_name"].removeprefix("v")
        name = f"beads_{version}_linux_{arch}.tar.gz"
        assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
        for name_on_disk, asset_name in [("release.tar.gz", name), ("checksums.txt", "checksums.txt")]:
            url = assets[asset_name]
            if not url.startswith("https://github.com/gastownhall/beads/releases/download/"):
                raise SystemExit("Unexpected release asset URL")
            fetch(url, work / name_on_disk)
        expected = next(line.split()[0] for line in (work / "checksums.txt").read_text().splitlines()
                        if line.split()[-1].lstrip("*") == name)
        with (work / "release.tar.gz").open("rb") as archive:
            actual = hashlib.file_digest(archive, "sha256").hexdigest()
        if actual != expected:
            raise SystemExit("Beads release checksum mismatch; existing binary preserved")
        # Extract only the regular executable, never archive paths or links.
        with tarfile.open(work / "release.tar.gz") as archive:
            member = archive.getmember("bd")
            if not member.isfile():
                raise SystemExit("Release bd is not a regular file")
            with archive.extractfile(member) as source, (work / "bd").open("wb") as dest:
                shutil.copyfileobj(source, dest)
        (work / "bd").chmod(0o755)
        installed = subprocess.check_output([str(work / "bd"), "version"], text=True).strip()
        if not installed.startswith(f"bd version {version} "):
            raise SystemExit("Binary version differs from release metadata")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name("bd.installing")
        shutil.copyfile(work / "bd", temporary)
        temporary.chmod(0o755)
        os.replace(temporary, target)
        record = {"version": installed, "release": release["html_url"], "archive": name,
                  "sha256": actual, "installed_at": datetime.now(timezone.utc).isoformat()}
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
