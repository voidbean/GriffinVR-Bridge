"""Install and undo the VR overlay on Windows. Run Select.ps1 for the player UI."""
import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from payload import HERE, GAME, digest, prepare, verify

STATE = ".mwr-gfl-vr"
PROFILE = "players2/config.cfg"
ALLOWED = frozenset((HERE / "data/managed-files.txt").read_text(encoding="utf-8").splitlines())


def local(root, relative):
    path = root / relative
    if path.is_absolute() and not path.is_relative_to(root):
        raise ValueError("Path outside game: " + str(path))
    if ".." in Path(relative).parts or ":" in relative or Path(relative).anchor:
        raise ValueError("Invalid relative path: " + relative)
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink() or node.is_junction():
            raise ValueError("Linked installation path: " + str(node))
    return path


@contextlib.contextmanager
def exclusive(game):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    api.CreateMutexW.restype = ctypes.c_void_p
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    name = hashlib.sha256(str(game).casefold().encode()).hexdigest()
    ctypes.set_last_error(0)
    handle = api.CreateMutexW(None, False, "Local\\MWR-GFL-VR-" + name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if ctypes.get_last_error() == 183:
            raise RuntimeError("Another installer is using this game directory.")
        yield
    finally:
        api.CloseHandle(handle)


def write_manifest(state, record):
    with (state / "manifest.tmp").open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(state / "manifest.tmp", state / "manifest.json")


def uninstall(game):
    state = local(game, STATE)
    if not state.exists():
        print("No managed installation.")
        return
    record = json.loads(local(game, STATE + "/manifest.json").read_text(encoding="utf-8"))
    files = record["files"]
    if record["version"] != 1 or set(files) not in (ALLOWED, ALLOWED | {PROFILE}):
        raise ValueError("Invalid installation record.")
    dirs = {Path(n).parent for n in files}
    allowed_dirs = {str(p.as_posix()) for d in dirs for p in (d, *d.parents) if str(p) != "."}
    if not set(record["directories"]) <= allowed_dirs:
        raise ValueError("Invalid directory record.")
    # Check the entire backup set before restoring anything.
    for n, item in files.items():
        dst = local(game, n)
        backup = local(game, STATE + "/original/" + n)
        if item["old"]:
            verify(backup, item["old"])
    recovered = "MWR-GFL-recovered-" + uuid.uuid4().hex
    for n, item in files.items():
        dst = local(game, n)
        current = digest(dst) if dst.exists() else None
        if current == item["old"]:
            continue
        if n == PROFILE and not item["old"] and current and current != item["new"]:
            print("Kept the active player profile:", dst)
            continue
        if current and current != item["new"]:
            saved = local(game, recovered + "/" + n)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, saved)
            print("Saved a modified file:", saved)
        if item["old"]:
            src = local(game, STATE + "/original/" + n)
            dst.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dst.parent, delete=False) as f:
                tmp = Path(f.name)
            try:
                shutil.copy2(src, tmp)
                os.replace(tmp, dst)
            finally:
                tmp.unlink(missing_ok=True)
        else:
            dst.unlink(missing_ok=True)
    for n in sorted(record["directories"], key=lambda s: s.count("/"), reverse=True):
        folder = local(game, n)
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    # Retire the journal in one rename, after every restoration completed.
    retired = local(game, STATE + "-retired-" + uuid.uuid4().hex)
    state.rename(retired)
    shutil.rmtree(retired)
    print("Uninstalled. Original files restored.")


@contextlib.contextmanager
def inherited_temp(parent):
    # Windows keeps the staging ACL when files are renamed into the game or release.
    directory = parent / (".gfl-setup-" + uuid.uuid4().hex)
    directory.mkdir(mode=0o755)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def install(game, archive, cache):
    state = local(game, STATE)
    if state.exists():
        raise RuntimeError("Installation record exists. Run Uninstall before reinstalling.")
    verify(game / "h1_sp64_ship.exe", GAME)
    # Stage and snapshot before creating the recovery journal or replacing any file.
    with inherited_temp(game) as scratch:
        work = Path(scratch)
        payload = work / "payload"
        prepare(work, payload, archive, cache)
        names = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
        if names != ALLOWED:
            raise ValueError("Unexpected staged files: " + str(names ^ ALLOWED))
        profile = local(game, PROFILE)
        if not profile.exists() or profile.stat().st_size == 0:
            staged_profile = payload / PROFILE
            staged_profile.parent.mkdir(exist_ok=True)
            shutil.copyfile(HERE / "data/first-run.cfg", staged_profile)
            names.add(PROFILE)
        journal = work / "journal"
        journal.mkdir()
        files, directories = {}, set()
        for n in sorted(names):
            dst = local(game, n)
            old = None
            if dst.exists():
                old = digest(dst)
                backup = journal / "original" / n
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, backup)
                verify(backup, old)
            files[n] = {"old": old, "new": digest(payload / n)}
            for folder in dst.parents:
                if folder == game:
                    break
                if not folder.exists():
                    directories.add(folder.relative_to(game).as_posix())
        write_manifest(journal, {"version": 1, "files": files, "directories": sorted(directories)})
        journal.rename(state)
        try:
            for n, item in files.items():
                dst = local(game, n)
                if item["old"] == item["new"]:
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.replace(payload / n, dst)
                verify(dst, item["new"])
        except BaseException:
            uninstall(game)
            raise
    print("Installed. Start Play-GFL-VR.exe in the game directory.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--gfl", type=Path)
    parser.add_argument("--cache", type=Path, default=HERE / "cache")
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    if not (game / "h1_sp64_ship.exe").is_file():
        parser.error("Select the game directory containing h1_sp64_ship.exe.")
    with exclusive(game):
        # Compare executable directories so a separate test installation can coexist.
        probe = subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
            "$p=Get-Process -Name overlord,overlord-gfl,h1-mod,h1_sp64_ship,h1_mp64_ship "
            "-ErrorAction SilentlyContinue | Where-Object { $_.Path -and "
            "[IO.Path]::GetDirectoryName($_.Path) -eq $env:MWR_SETUP_TARGET }; if ($p) {exit 1}; exit 0"
        ], env={**os.environ, "MWR_SETUP_TARGET": str(game)})
        if probe.returncode:
            raise RuntimeError("Close the game and launcher in the selected directory first.")
        if args.action == "uninstall":
            uninstall(game)
        else:
            if args.gfl is None:
                parser.error("--gfl is required for installation.")
            install(game, args.gfl.resolve(strict=True), args.cache.resolve())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERROR:", error, file=sys.stderr)
        sys.exit(1)
