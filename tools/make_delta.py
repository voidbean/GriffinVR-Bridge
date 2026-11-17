"""Refresh a BSDIFF40 patch for a newly built compatible client."""
import argparse
import hashlib
from pathlib import Path
import zipfile
import bsdiff4

cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("base_zip", type=Path)
cli.add_argument("built_client", type=Path)
cli.add_argument("output", type=Path)
args = cli.parse_args()
with args.base_zip.open("rb") as f:
    if hashlib.file_digest(f, "sha256").hexdigest() != "e5ec02fbd3df62425c76649f0078a124428d69789e9dcad34c24df84c6576ca3":
        cli.error("Expected the official Beta 10 runtime ZIP")
with zipfile.ZipFile(args.base_zip) as z:
    old = z.read("overlord.exe")
new = args.built_client.read_bytes()
patch = bsdiff4.diff(old, new)
if bsdiff4.patch(old, patch) != new:
    raise RuntimeError("Round-trip verification failed")
args.output.write_bytes(patch)
print("Client SHA-256:", hashlib.sha256(new).hexdigest())
print("Patch SHA-256:", hashlib.sha256(patch).hexdigest())
