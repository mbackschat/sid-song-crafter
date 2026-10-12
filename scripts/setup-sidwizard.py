"""Build the pinned, unmodified SID-Wizard 1.97 native exporter for batch use."""

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SW_ARCHIVE = ROOT / ".local/research/composition-tools/SID-Wizard-1.97-sources-examples.tar.gz"
SW_URL = "https://csdb.dk/getinternalfile.php/281063/SID-Wizard-1.97-sources-examples.tar.gz"
SW_SHA256 = "aeb265f4a778b2acb5aad13e8e98af882888292f749f29f4d18cbf49850e57bc"
TASS_ARCHIVE = ROOT / ".local/downloads/64tass-1.60.3243-src.zip"
TASS_URL = "https://downloads.sourceforge.net/project/tass64/source/64tass-1.60.3243-src.zip"
TASS_SHA256 = "9d83be3d23a2c55e085b7c7a7856c2f96080447ea120a6a8c21a217ed76427f0"
SW_ROOT = ROOT / ".tools/sid-wizard-1.97"
TASS_ROOT = ROOT / ".tools/64tass-1.60.3243"
TOOL_ROOT = ROOT / ".tools/sid-wizard-exporter"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire(path, url, digest):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        subprocess.run(["curl", "--fail", "--location", "--connect-timeout", "5", "--max-time", "60", url, "-o", str(path)], check=True, timeout=75)
    if sha256(path) != digest:
        raise ValueError(f"Pinned archive checksum mismatch: {path}")


def setup():
    TOOL_ROOT.mkdir(parents=True, exist_ok=True)
    (TOOL_ROOT / "build.json").unlink(missing_ok=True)
    acquire(SW_ARCHIVE, SW_URL, SW_SHA256)
    acquire(TASS_ARCHIVE, TASS_URL, TASS_SHA256)
    SW_ROOT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(SW_ARCHIVE) as archive:
        members = archive.getmembers()
        for member in members:
            parts = Path(member.name).parts[1:]
            if not (member.isfile() or member.isdir() or member.issym()) or ".." in parts or Path(member.name).is_absolute():
                raise ValueError("Unsupported path in pinned SID-Wizard archive")
            member.name = str(Path(*parts)) if parts else "."
            try:
                (SW_ROOT / member.name).resolve().relative_to(SW_ROOT.resolve())
            except ValueError as error:
                raise ValueError("Existing extraction path leaves the SID-Wizard source directory") from error
            if member.issym():
                target = (SW_ROOT / member.name).parent / member.linkname
                try:
                    target.resolve().relative_to(SW_ROOT.resolve())
                except ValueError as error:
                    raise ValueError("Unsupported symlink in pinned SID-Wizard archive") from error
        archive.extractall(SW_ROOT, members=members)
    TASS_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TASS_ARCHIVE) as archive:
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in archive.namelist()):
            raise ValueError("Unsupported path in pinned 64tass archive")
        for name in archive.namelist():
            try:
                (TASS_ROOT / name).resolve().relative_to(TASS_ROOT.resolve())
            except ValueError as error:
                raise ValueError("Existing extraction path leaves the 64tass source directory") from error
        archive.extractall(TASS_ROOT)
    assembler_root = TASS_ROOT / "64tass-1.60.3243-src"
    with (TOOL_ROOT / "build.log").open("w") as log:
        subprocess.run(["make", "-j2"], cwd=assembler_root, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        assembler = assembler_root / "64tass"
        subprocess.run([
            str(assembler), "-C", "-a", "-Wno-deprecated", "-DEMULATOR=0", "-DTUI_ONLY=0",
            "-DSID_AMOUNT=1", '-DSWversion="1.9"', "--vice-labels-numeric",
            "-l", str(TOOL_ROOT / "exporter.labels"), "-o", str(TOOL_ROOT / "exporter.prg"), "exporter.asm",
        ], cwd=SW_ROOT / "native/sources", stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    labels_path = TOOL_ROOT / "exporter.labels"
    labels_path.write_text("\n".join(sorted(labels_path.read_text().splitlines())) + "\n")
    manifest = {
        "sidWizardVersion": "1.97", "sidWizardArchiveUrl": SW_URL, "sidWizardArchiveSha256": SW_SHA256,
        "assemblerVersion": "64tass 1.60.3243", "assemblerArchiveUrl": TASS_URL, "assemblerArchiveSha256": TASS_SHA256,
        "exporterSha256": sha256(TOOL_ROOT / "exporter.prg"), "labelsSha256": sha256(TOOL_ROOT / "exporter.labels"),
        "sourceModified": False,
    }
    (TOOL_ROOT / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    try:
        print(json.dumps(setup(), indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
