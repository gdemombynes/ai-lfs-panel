import zipfile

from lfspanel.fetch.base import (
    append_manifest,
    download,
    list_zip,
    read_manifest,
    sha256_file,
    unzip_selected,
)


def test_sha256_and_manifest_roundtrip(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")
    digest = sha256_file(f)
    assert digest.startswith("2cf24dba")
    manifest = tmp_path / "manifest.csv"
    append_manifest(
        {"path": "a.bin", "url": "u", "sha256": digest, "bytes": 5}, manifest
    )
    append_manifest(
        {"path": "a.bin", "url": "u", "sha256": "new", "bytes": 5}, manifest
    )
    rows = read_manifest(manifest)
    assert rows["a.bin"]["sha256"] == "new"  # newest entry wins


def test_download_registers_existing_file_without_network(tmp_path):
    dest = tmp_path / "raw" / "x.zip"
    dest.parent.mkdir()
    dest.write_bytes(b"data")
    manifest = tmp_path / "manifest.csv"
    r = download(
        "http://invalid.example/x.zip", dest, manifest=manifest, root=tmp_path / "raw"
    )
    assert r.status == "cached"
    assert read_manifest(manifest)["x.zip"]["sha256"] == sha256_file(dest)


def test_download_failure_leaves_no_partial(tmp_path):
    dest = tmp_path / "raw" / "y.zip"
    r = download(
        "http://127.0.0.1:9/y.zip",
        dest,
        manifest=tmp_path / "m.csv",
        root=tmp_path / "raw",
        timeout=2,
    )
    assert r.status == "failed"
    assert not dest.exists()
    assert not dest.with_name("y.zip.part").exists()


def test_unzip_selected_matches_patterns(tmp_path):
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("folder/DATA.txt", "1")
        zf.writestr("folder/readme.pdf", "2")
    out = unzip_selected(z, ["*.txt"], tmp_path / "out")
    assert [p.name for p in out] == ["DATA.txt"]
    assert set(list_zip(z)) == {"folder/DATA.txt", "folder/readme.pdf"}
