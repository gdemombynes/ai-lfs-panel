"""Download helpers: streaming, checksums, manifest, selective unzip.

Python 3.9 on this Mac links LibreSSL 2.8, which cannot negotiate TLS 1.3.
Hosts that require it (DANE) make ``requests`` raise ``SSLError``; every
network helper here falls back to the system ``curl`` in that case.
"""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests

from lfspanel.config import MANIFEST, RAW

USER_AGENT = "lfspanel/0.1 (+https://github.com/gdemombynes/ai-lfs-panel)"
MANIFEST_FIELDS = [
    "path",
    "url",
    "sha256",
    "bytes",
    "retrieved_utc",
    "http_last_modified",
]


@dataclass
class FetchResult:
    path: Path
    status: str  # cached | ok | failed
    sha256: Optional[str] = None
    bytes: int = 0
    last_modified: Optional[str] = None
    error: Optional[str] = None


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _rel(path: Path, root: Path = RAW) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def read_manifest(manifest: Path = MANIFEST) -> dict:
    """Return {relative path: row dict} for the newest entry per path."""
    if not manifest.exists():
        return {}
    rows = {}
    with open(manifest, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["path"]] = row
    return rows


def append_manifest(row: dict, manifest: Path = MANIFEST) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    new = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _curl(args: List[str], timeout: int) -> subprocess.CompletedProcess:
    cmd = ["curl", "-sS", "-L", "-A", USER_AGENT, "-m", str(timeout)] + args
    return subprocess.run(cmd, capture_output=True, text=False, timeout=timeout + 30)


def fetch_text(
    url: str, session: Optional[requests.Session] = None, timeout: int = 60
) -> str:
    """GET a page as text, falling back to curl on TLS failures."""
    s = session or make_session()
    try:
        r = s.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.exceptions.SSLError:
        proc = _curl([url], timeout)
        if proc.returncode != 0:
            raise requests.RequestException(proc.stderr.decode("utf-8", "ignore"))
        return proc.stdout.decode("utf-8", "ignore")


def url_exists(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 60,
    require_zip: bool = False,
) -> bool:
    """HEAD a URL (curl fallback); True on HTTP 200.

    With ``require_zip`` the first bytes are fetched and must be a zip
    signature, for servers that answer 200 with an HTML page for missing files.
    """
    s = session or make_session()
    try:
        ok = s.head(url, allow_redirects=True, timeout=timeout).status_code == 200
        if not ok or not require_zip:
            return ok
        with s.get(url, stream=True, timeout=timeout) as r:
            return r.status_code == 200 and next(r.iter_content(4), b"")[:2] == b"PK"
    except requests.exceptions.SSLError:
        proc = _curl(["-I", "-o", "/dev/null", "-w", "%{http_code}", url], timeout)
        if proc.returncode != 0 or proc.stdout.decode().strip() != "200":
            return False
        if not require_zip:
            return True
        proc = _curl(["-r", "0-3", url], timeout)
        return proc.returncode == 0 and proc.stdout[:2] == b"PK"


def check_remote(url: str, session: Optional[requests.Session] = None) -> dict:
    """HEAD a URL; return status, size and Last-Modified without downloading."""
    s = session or make_session()
    r = s.head(url, allow_redirects=True, timeout=60)
    return {
        "status": r.status_code,
        "bytes": int(r.headers.get("Content-Length") or 0),
        "last_modified": r.headers.get("Last-Modified"),
    }


def _stream_to(
    url: str, part: Path, session: requests.Session, timeout: int
) -> Optional[str]:
    """Download to ``part``; return the Last-Modified header if known."""
    try:
        with session.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with open(part, "wb") as f:
                for block in r.iter_content(chunk_size=1 << 20):
                    if block:
                        f.write(block)
            return r.headers.get("Last-Modified")
    except requests.exceptions.SSLError:
        proc = _curl(["-f", "-o", str(part), url], max(timeout, 1800))
        if proc.returncode != 0:
            raise requests.RequestException(proc.stderr.decode("utf-8", "ignore"))
        return None


def download(
    url: str,
    dest: Path,
    force: bool = False,
    session: Optional[requests.Session] = None,
    manifest: Path = MANIFEST,
    root: Path = RAW,
    timeout: int = 120,
) -> FetchResult:
    """Stream ``url`` to ``dest`` unless a checksummed copy already exists.

    Writes to ``dest.part`` first and renames on success, then records the file
    in the manifest. An existing file that is not in the manifest is
    checksummed and registered rather than re-downloaded.
    """
    dest = Path(dest)
    rel = _rel(dest, root)
    known = read_manifest(manifest).get(rel)
    if dest.exists() and not force:
        digest = sha256_file(dest)
        if known and known["sha256"] == digest:
            return FetchResult(
                dest,
                "cached",
                digest,
                dest.stat().st_size,
                known.get("http_last_modified"),
            )
        append_manifest(
            {
                "path": rel,
                "url": url,
                "sha256": digest,
                "bytes": dest.stat().st_size,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "http_last_modified": "",
            },
            manifest,
        )
        return FetchResult(dest, "cached", digest, dest.stat().st_size)

    s = session or make_session()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        last_mod = _stream_to(url, part, s, timeout)
    except (requests.RequestException, subprocess.TimeoutExpired) as exc:
        if part.exists():
            part.unlink()
        return FetchResult(dest, "failed", error=str(exc))
    part.replace(dest)
    digest = sha256_file(dest)
    append_manifest(
        {
            "path": rel,
            "url": url,
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": last_mod or "",
        },
        manifest,
    )
    return FetchResult(dest, "ok", digest, dest.stat().st_size, last_mod)


def unzip_selected(
    zip_path: Path, patterns: Iterable[str], dest_dir: Path, force: bool = False
) -> List[Path]:
    """Extract members whose basename matches any glob in ``patterns``."""
    zip_path, dest_dir = Path(zip_path), Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out: List[Path] = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            base = Path(info.filename).name
            if info.is_dir() or not any(
                fnmatch.fnmatch(base.lower(), p.lower()) for p in patterns
            ):
                continue
            target = dest_dir / base
            if target.exists() and not force:
                out.append(target)
                continue
            with z.open(info) as src, open(target, "wb") as dst:
                for block in iter(lambda: src.read(1 << 20), b""):
                    dst.write(block)
            out.append(target)
    return out


def list_zip(zip_path: Path) -> List[str]:
    with zipfile.ZipFile(zip_path) as z:
        return [i.filename for i in z.infolist() if not i.is_dir()]
