"""Build native H1 zones using the local GFL pack and H1-PC compiler output."""
import argparse
import ctypes
import hashlib
import io
import re
import struct
import zlib
from pathlib import Path

FOLLOW = 0xFDFDFDFFFFFFFFFF
BLOCK = 65536
HEADER = struct.Struct("<8sI4BIIIQQ")


def script_archive(compiled, tokens):
    names = {name: str(int(number, 16)) for number, name in
             re.findall(r'\{\s*0x([\da-fA-F]+), "([^"]+)"\s*\}', tokens.read_text(encoding="utf-8"))}
    if "maps/_load" not in names:
        raise ValueError("Missing H1 path token table")
    assets = sorted(compiled.rglob("*.gscbin"))
    if not assets:
        raise ValueError("No compiled H1 scripts")
    archive = io.BytesIO()
    archive.write(struct.pack("<4sI", b"GFL1", len(assets)))
    seen = set()
    for file in assets:
        path = file.relative_to(compiled).with_suffix("").as_posix()
        name = names.get(path, path).encode("ascii")
        if name in seen:
            raise ValueError(f"Duplicate script key: {name!r}")
        seen.add(name)
        data = file.read_bytes()
        packed, stack, code = struct.unpack_from("<3I", data, 4)
        if data[:4] != b"GSC\0" or len(data) != 16 + packed + code:
            raise ValueError(f"Invalid compiled script {file}")
        if len(zlib.decompress(data[16:16 + packed])) != stack:
            raise ValueError(f"Invalid stack {file}")
        archive.write(struct.pack("<II", len(name), len(data)))
        archive.write(name)
        archive.write(data)

    return archive.getvalue()


def inflate_models(file):
    header = HEADER.unpack(file.read(HEADER.size))
    if header[:9] != (b"S1ffu100", 66, 1, 1, 8, 4, 0, 0, 0):
        raise ValueError("Expected H1 zlib model zone with no external image packs")
    decoder = zlib.decompressobj()
    while chunk := file.read(BLOCK):
        yield decoder.decompress(chunk)
    if not decoder.eof or decoder.unused_data:
        raise ValueError("Incomplete or unexpected model stream")


def write_zone(output, chunks, lz4):
    bound = lz4.LZ4_compressBound(BLOCK)
    encoded = ctypes.create_string_buffer(bound)
    decoded = ctypes.create_string_buffer(BLOCK)
    tmp = output.with_suffix(".tmp")
    total = 0
    digest = hashlib.sha256()
    pending = bytearray()
    with tmp.open("wb") as file:
        file.write(bytes(HEADER.size + 12))
        def block(raw):
            nonlocal total
            count = lz4.LZ4_compress_default(raw, encoded, len(raw), bound)
            if count <= 0 or lz4.LZ4_decompress_safe(encoded, decoded, count, len(raw)) != len(raw) or decoded.raw[:len(raw)] != raw:
                raise ValueError("LZ4 round-trip failed")
            file.write(struct.pack("<II", count, len(raw)))
            file.write(encoded.raw[:count])
            file.write(bytes(-count % 4))
            digest.update(raw)
            total += len(raw)
        for chunk in chunks:
            pending.extend(chunk)
            used = len(pending) // BLOCK * BLOCK
            for start in range(0, used, BLOCK):
                block(bytes(pending[start:start+BLOCK]))
            del pending[:used]
        if pending:
            block(bytes(pending))
        size = file.tell()
        file.seek(0)
        file.write(HEADER.pack(b"S1ffu100", 66, 1, 4, 8, 4, 0, 0, 0, size, size))
        file.write(struct.pack("<QI", total, 0x04010000))
    tmp.replace(output)
    print(f"{output.name}: {total} decoded bytes, sha256={digest.hexdigest()}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("models", "compiled", "tokens", "lz4", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    codec = ctypes.CDLL(str(args.lz4.resolve()))
    (args.output / "gflvr_scripts.bin").write_bytes(script_archive(args.compiled, args.tokens))
    with args.models.open("rb") as original:
        write_zone(args.output / "gflvr_models.ff", inflate_models(original), codec)
