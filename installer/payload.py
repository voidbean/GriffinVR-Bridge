"""Materialize the supported GFL release in a private staging directory."""
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

import build_gfl_zones as zones
import delta

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
GFL = {
    "1ecbe678fea33c3a306e89ef0f958af8eacaf5dd99d6a4d4306c7b95edffd704": (
        "1.0", 316, "zone/mod.ff", "c61bc2a4e7ae450dc528dc8a546ba11ccdf7fbcd495f14bf30ccecdd5c44107b",
        "df5a907bb8d5a871afd4408cc7da360f30157279be3a529f4c7bb0a69c3ea7d8"),

}
GAME = "3d23e86930668244d43a026552d5e1298a7c8cc63b82a54a7ad857e7b41f9190"
CLIENT = "df10c17a29565550d50f044e5dfd807bcd31979a204d1540084e17284b107fe6"
DEPENDENCIES = {
    "MWR-VR-Beta-10.zip": ("lesan0622/MWR-VR", "v0.1-beta10", "e5ec02fbd3df62425c76649f0078a124428d69789e9dcad34c24df84c6576ca3"),
    "windows-x64-release.zip": ("xensik/gsc-tool", "1.6.2", "770e7794a10984465c9df62b69be28ee78c12823d359be0bd1dd363432c9478c"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise ValueError("Unsupported version or damaged file: " + str(path))


ASSET_IDS = {"MWR-VR-Beta-10.zip": (743012062, 26594983), "windows-x64-release.zip": (666224550, 7843967)}


class StopRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def download_chunks(repo, name, out):
    asset, size = ASSET_IDS[name]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/assets/{asset}?t={int(time.time())}",
        headers={"Accept": "application/octet-stream", "User-Agent": "MWR-GFL-VR-installer"})
    try:
        with urllib.request.build_opener(StopRedirect()).open(request, timeout=15):
            raise ValueError("GitHub did not return an asset redirect")
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        location = error.headers["Location"]
    if not location.startswith("https://"):
        raise ValueError("Invalid asset URL")
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with out.open("wb") as f:
        for start in range(0, size, 4 * 1024 * 1024):
            end = min(size, start + 4 * 1024 * 1024) - 1
            part = urllib.request.Request(location, headers={"Range": f"bytes={start}-{end}"})
            with direct.open(part, timeout=20) as response:
                if response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}":
                    raise ValueError("Invalid asset range")
                data = response.read(end - start + 2)
            if len(data) != end - start + 1:
                raise ValueError("Incomplete asset range")
            f.write(data)
            print(f"{name}: {(end+1)*100//size}%", flush=True)


def dependency(name, cache):
    repo, tag, checksum = DEPENDENCIES[name]
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / name
    if dest.is_file():
        verify(dest, checksum)
        return dest
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    print("Downloading", url, flush=True)
    # HTTPS with the system proxy first, then a direct connection.
    for opener in (None, urllib.request.build_opener(), urllib.request.build_opener(urllib.request.ProxyHandler({}))):
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as f:
            tmp = Path(f.name)
        try:
            if opener is None:
                download_chunks(repo, name, tmp)
            else:
                with opener.open(url, timeout=20) as src, tmp.open("wb") as out:
                    shutil.copyfileobj(src, out)
            verify(tmp, checksum)
            os.replace(tmp, dest)
            return dest
        except (OSError, ValueError) as error:
            reason = error
        finally:
            tmp.unlink(missing_ok=True)
    raise RuntimeError(f"Download failed. Put {name} in {cache} and retry. {reason}")


def prepare(work, payload, archive, cache):
    version = GFL.get(digest(archive))
    if version is None:
        raise ValueError("Select the official GFL 1.0 release ZIP (h1-mod-gfl.zip).")
    label, count, model_name, script_hash, model_hash = version
    print("GFL release", label, flush=True)
    runtime = dependency("MWR-VR-Beta-10.zip", cache)
    compiler = dependency("windows-x64-release.zip", cache)
    with zipfile.ZipFile(runtime) as z:
        z.extractall(payload)  # the complete archive hash was verified
    delta_file = DATA / "client.bsdiff"
    verify(delta_file, "48a68f8db22840bafc3d4d3f7f6ecc9e65a02ec8cafb52c5571532a353a21c93")
    delta.apply(payload / "overlord.exe", delta_file, payload / "overlord-gfl.exe")
    verify(payload / "overlord-gfl.exe", CLIENT)
    (payload / "overlord.exe").unlink()
    shutil.copyfile(DATA / "Play-GFL-VR.exe", payload / "Play-GFL-VR.exe")
    with zipfile.ZipFile(compiler) as z:
        tool = z.extract("gsc-tool.exe", work)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.startswith("mods/gfl/") and name.endswith((".gsc", "/mod.ff")):
                z.extract(name, work)
            if name in ("mods/gfl/info.json", "mods/gfl/ui_scripts/gfl_ui/main.lua",
                        "mods/gfl/ui_scripts/gfl_ui/__init__.lua"):
                z.extract(name, payload)
    sources = work / "mods/gfl"
    print("Compiling campaign scripts...", flush=True)
    result = subprocess.run([tool, "-m", "comp", "-g", "h1", "-s", "pc", str(sources)],
                            cwd=work, capture_output=True)
    compiled = work / "compiled/h1"
    files = list(compiled.rglob("*.gscbin"))
    if result.returncode or len(files) != count:
        raise RuntimeError("GSC compilation failed: " + (result.stdout + result.stderr)[-1200:].decode(errors="replace"))
    out = payload / "zone"
    out.mkdir()
    scripts = out / "gflvr_scripts.bin"
    scripts.write_bytes(zones.script_archive(compiled, DATA / "h1-paths.txt"))
    verify(scripts, script_hash)
    print("Converting campaign models...", flush=True)
    lib = DATA / "liblz4.dll"
    verify(lib, "201269203caf42be76ef92c36a1cfbb9680e744bc0b28459849c0ba74b5748c3")
    with (sources / model_name).open("rb") as src:
        model = out / "gflvr_models.ff"
        zones.write_zone(model, zones.inflate_models(src), ctypes.CDLL(str(lib)))
    verify(model, model_hash)
