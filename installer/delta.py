"""Apply a BSDIFF40 patch after the caller has verified both input hashes."""
import bz2


def number(data):
    value = int.from_bytes(data, "little")
    return -(value & ((1 << 63) - 1)) if value >> 63 else value


def apply(original, patch, target):
    data = patch.read_bytes()
    if data[:8] != b"BSDIFF40":
        raise ValueError("Unsupported client patch")
    control_size, diff_size, size = (number(data[n:n+8]) for n in (8, 16, 24))
    start = 32 + control_size
    control = bz2.decompress(data[32:start])
    differences = bz2.decompress(data[start:start+diff_size])
    extra = bz2.decompress(data[start+diff_size:])
    source = original.read_bytes()
    result = bytearray()
    old = diff = literal = 0
    for off in range(0, len(control), 24):
        add, copy, seek = (number(control[n:n+8]) for n in (off, off+8, off+16))
        if min(add, copy) < 0 or len(result) + add + copy > size:
            raise ValueError("Invalid client patch lengths")
        block = bytearray(differences[diff:diff+add])
        lo, hi = max(0, -old), min(add, len(source)-old)
        if hi > lo:
            block[lo:hi] = bytes((a + b) & 255 for a, b in zip(block[lo:hi], source[old+lo:old+hi]))
        result.extend(block)
        result.extend(extra[literal:literal+copy])
        old += add + seek
        diff += add
        literal += copy
    if len(result) != size or diff != len(differences) or literal != len(extra):
        raise ValueError("Incomplete client patch")
    target.write_bytes(result)
