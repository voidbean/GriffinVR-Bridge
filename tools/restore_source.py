"""Reconstruct the client source from the pinned upstream full-source release."""
import argparse
import hashlib
from pathlib import Path
import shutil
import contextlib
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "0e237708efd88aa87737e6ae8cd3b1d249d7f7e39fd5fdd7d8f5d9b2b21fb577"


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
    cli.add_argument("source_zip", type=Path)
    cli.add_argument("destination", type=Path)
    args = cli.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        cli.error("Choose a new destination directory")
    with args.source_zip.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != BASE_SHA:
            cli.error("Expected MWR-VR-Beta-10-source.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with inherited_temp(dest.parent) as tmp:
        with zipfile.ZipFile(args.source_zip) as z:
            z.extractall(tmp)
        source = Path(tmp) / "MWR-VR"
        shutil.copytree(ROOT / "overlay", source, dirs_exist_ok=True)
        source.rename(dest)
    print(dest)


if __name__ == "__main__":
    main()
