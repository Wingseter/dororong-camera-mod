#!/usr/bin/env python3
"""Generate likely SD-upgrade filenames/checksums for the GP1235 camera.

This tool is intentionally simple:
- it reads a raw firmware image
- computes several plausible 32-bit checksum candidates
- prints filename candidates that fit the discovered `JH_5307*.bin` pattern

The main goal is to support staged on-device testing while the exact SD
upgrade packaging rule is still being reverse engineered.
"""

from __future__ import annotations

import argparse
import binascii
import struct
from pathlib import Path


MODEL_PREFIX = "JH_5307"


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def byte_sum(data: bytes) -> int:
    return u32(sum(data))


def byte_sum_skip(data: bytes, start: int, size: int) -> int:
    return u32(sum(data[:start]) + sum(data[start + size :]))


def xor32_le(data: bytes) -> int:
    work = data + (b"\x00" * ((4 - (len(data) % 4)) % 4))
    acc = 0
    for i in range(0, len(work), 4):
        acc ^= struct.unpack_from("<I", work, i)[0]
    return u32(acc)


def xor32_le_skip(data: bytes, start: int, size: int) -> int:
    patched = bytearray(data)
    patched[start : start + size] = b"\x00" * size
    return xor32_le(bytes(patched))


def format_hex(value: int) -> str:
    return f"{u32(value):08X}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate likely SD-upgrade filename candidates for a firmware image."
    )
    parser.add_argument("firmware", type=Path, help="Path to the firmware binary")
    args = parser.parse_args()

    data = args.firmware.read_bytes()
    if len(data) < 0x0C:
        raise SystemExit("Firmware file is too small.")

    header_u32_le = struct.unpack_from("<I", data, 0x08)[0]

    candidates = [
        ("header_0x08_le", header_u32_le),
        ("byte_sum_full", byte_sum(data)),
        ("byte_sum_skip_hdr08", byte_sum_skip(data, 0x08, 4)),
        ("xor32_full_le", xor32_le(data)),
        ("xor32_skip_hdr08_le", xor32_le_skip(data, 0x08, 4)),
        ("crc32_full", binascii.crc32(data) & 0xFFFFFFFF),
        ("crc32_skip_hdr08", binascii.crc32(data[:0x08] + data[0x0C:]) & 0xFFFFFFFF),
    ]

    print(f"file: {args.firmware}")
    print(f"size: {len(data)} bytes (0x{len(data):X})")
    print()
    print("checksum candidates:")
    for name, value in candidates:
        print(f"  {name:20s} {format_hex(value)}")

    print()
    print("recommended immediate tests:")
    for name, value in candidates[:4]:
        hex_value = format_hex(value)
        print(f"  {MODEL_PREFIX}{hex_value}.bin    # {name}")

    print()
    print("extra variants if parser includes a separator before the 8 hex chars:")
    for name, value in candidates[:4]:
        hex_value = format_hex(value)
        print(f"  {MODEL_PREFIX}_{hex_value}.bin   # {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
