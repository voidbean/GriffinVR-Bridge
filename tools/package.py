"""Package the Windows player ZIP using the official embedded Python archive."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
import contextlib
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON_HASH = "7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9"


@contextlib.contextmanager
def inherited_temp(parent):
    # Windows keeps the staging ACL when files are renamed into the game or release.
    directory = parent / (".gfl-setup-" + uuid.uuid4().hex)
    directory.mkdir(mode=0o755)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--python-embed", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    with args.python_embed.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != PYTHON_HASH:
            cli.error("Expected the official Python 3.13.5 amd64 embedded ZIP")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with inherited_temp(args.output.parent) as tmp:
        staging = Path(tmp)
        for name in ("Install.cmd", "Uninstall.cmd", "LICENSE", "README.md", "BUILD.md",
                     "ARCHITECTURE.md", "THIRD_PARTY.md"):
            shutil.copyfile(ROOT / name, staging / name)
        shutil.copytree(ROOT / "licenses", staging / "licenses")
        installer = staging / "installer"
        installer.mkdir()
        for name in ("Select.ps1", "manage.py", "payload.py", "build_gfl_zones.py", "delta.py"):
            shutil.copyfile(ROOT / "installer" / name, installer / name)
        # Windows PowerShell 5.1 requires a BOM to read Chinese UI strings.
        selector = installer / "Select.ps1"
        selector.write_text(selector.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        shutil.copytree(ROOT / "installer/data", installer / "data")
        csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        subprocess.run([csc, "/nologo", "/platform:x64", "/target:winexe",
                        "/reference:System.Windows.Forms.dll", "/out:" + str(installer / "data/Play-GFL-VR.exe"),
                        ROOT / "installer/Play-GFL-VR.cs"], check=True)
        runtime = installer / "runtime"
        with zipfile.ZipFile(args.python_embed) as z:
            z.extractall(runtime)
        with (runtime / "python313._pth").open("a", encoding="ascii") as f:
            f.write("\n..\n")
        archive = staging / "release.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(staging.rglob("*")):
                if path.is_file() and path != archive:
                    z.write(path, path.relative_to(staging))
        os.replace(archive, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
