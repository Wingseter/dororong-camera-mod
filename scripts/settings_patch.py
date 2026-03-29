#!/usr/bin/env python3
"""GP1235 Settings Block Patcher

Modifies ISP default parameters in the settings block (0xC2000) of GP1235 firmware.
Handles all three checksum systems:
  1. Profile CRC32 (standard, over bytes 0x00~0xA3)
  2. GPNV XOR checksum (32-bit word XOR at offset 0x08)
  3. SD upgrade byte-sum checksum (for filename generation)

Usage:
  python settings_patch.py <base_firmware> [--patch OFFSET=VALUE ...] [--output FILE] [--sd-copy DIR]
  python settings_patch.py analysis/GP1235_phase2_q95.bin --patch 0x0F=0x01 --patch 0x17=0x00
  python settings_patch.py analysis/GP1235_phase2_q95.bin --preset phase3
"""

import argparse
import binascii
import io
import shutil
import struct
import sys
from pathlib import Path

CONFIG_BASE = 0xC2000
PROFILE_SIZE = 512
NUM_PROFILES = 14
ACTIVE_PROFILES = range(6, 14)  # profiles 6-13
CRC_OFFSET = 0xA4
CRC_RANGE = 0xA4  # CRC32 over bytes 0x00..0xA3
GPNV_CHECKSUM_OFFSET = 0x08
BUILD_STR = "2026004291200"

FIELD_NAMES = {
    0x0F: "Photo Quality (1=High, 2=Standard, 3=Economy)",
    0x10: "White Balance (1=Auto, 2=Daylight, 3=Cloudy, 4=Tungsten, 5=Fluorescent)",
    0x11: "Exposure (1=Auto, 2=Motion, 3=Night View)",
    0x12: "Brightness (1=Auto, 2=100, 3=200)",
    0x13: "Colour (1=Standard, 2=B&W, 3=Colorful, 4=Maduro)",
    0x16: "EV Compensation",
    0x17: "Sharpness",
    0x18: "Saturation",
}

PRESETS = {
    "step0": {
        # Minimal safe test: change profile 7 flag only (done separately)
    },
    "phase3": {
        0x0F: 0x01,  # Photo Quality: High
        # 0x17 and 0x18 TBD after field mapping
    },
}


def read_firmware(path):
    with open(path, "rb") as f:
        return bytearray(f.read())


def get_profile(data, index):
    offset = CONFIG_BASE + index * PROFILE_SIZE
    return data[offset : offset + PROFILE_SIZE]


def calc_profile_crc32(block):
    return binascii.crc32(bytes(block[:CRC_RANGE])) & 0xFFFFFFFF


def calc_gpnv_xor(data):
    """Calculate GPNV 32-bit word XOR checksum over the firmware.
    The checksum at offset 0x08 is XOR of all 32-bit words (excluding itself)."""
    # Read sector count from GPNV header
    # Based on bootloader analysis: XOR all words, checksum field zeroed
    result = 0
    for i in range(0, len(data), 4):
        if i == GPNV_CHECKSUM_OFFSET:
            continue  # skip the checksum field itself
        word = struct.unpack_from("<I", data, i)[0]
        result ^= word
    return result


def update_gpnv_xor_differential(data, changes):
    """Update GPNV XOR checksum using differential method.
    changes: list of (offset, old_word, new_word)"""
    old_checksum = struct.unpack_from("<I", data, GPNV_CHECKSUM_OFFSET)[0]
    diff = 0
    for _offset, old_word, new_word in changes:
        diff ^= old_word ^ new_word
    return old_checksum ^ diff


def calc_sd_checksum(data):
    return sum(data) & 0xFFFFFFFF


def sd_upgrade_filename(data):
    checksum = calc_sd_checksum(data)
    return f"JH_5307_{BUILD_STR}{checksum:08X}.bin"


WELCOME_OFFSET = 0x0AA000
WELCOME_MAX_SIZE = 2285
VERSION_OFFSET = 0x079E6C
VERSION_MAX_LEN = 20  # USB string descriptor (length byte + type byte + UTF-16LE)

# GPNV XOR range: welcome screen (0x0AA000) and version string (0x079E6C)
# are OUTSIDE the XOR range. Confirmed: GP1235_welcome_mod.bin has identical
# GPNV checksum to original despite modifying 0x0AA000.
# Only settings block changes should be included in GPNV differential update.
GPNV_XOR_EXCLUDED_REGIONS = [
    (0x079E6C, 0x079E6C + 20),      # version string
    (0x0AA000, 0x0AA000 + 2285),     # welcome screen
]


def is_in_gpnv_xor_range(offset):
    """Check if an offset is within the GPNV XOR checksum range."""
    for start, end in GPNV_XOR_EXCLUDED_REGIONS:
        if start <= offset < end:
            return False
    return True


def apply_branding(data, version="v3.0"):
    """Apply DORORONG boot screen and version string.
    Returns empty list — these areas are outside GPNV XOR range."""
    # No word_changes returned: branding areas are excluded from GPNV XOR

    # 1. Generate welcome screen JPEG
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  WARNING: Pillow not installed, skipping welcome screen")
        return word_changes

    img = Image.new("RGB", (160, 80), (20, 20, 20))
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bbox1 = draw.textbbox((0, 0), "DORORONG", font=font_large)
    draw.text(((160 - bbox1[2] + bbox1[0]) // 2, 15), "DORORONG",
              fill=(255, 255, 255), font=font_large)
    ver_text = f"custom fw {version}"
    bbox2 = draw.textbbox((0, 0), ver_text, font=font_small)
    draw.text(((160 - bbox2[2] + bbox2[0]) // 2, 48), ver_text,
              fill=(180, 180, 180), font=font_small)

    # Find quality that fits
    for quality in range(95, 10, -5):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= WELCOME_MAX_SIZE:
            break
    jpeg_data = buf.getvalue()

    # Patch welcome screen (pad with 0xFF)
    padded = jpeg_data + b"\xFF" * (WELCOME_MAX_SIZE - len(jpeg_data))
    for i in range(0, WELCOME_MAX_SIZE, 4):
        abs_off = WELCOME_OFFSET + i
        if abs_off + 4 > len(data):
            break
        new_bytes = padded[i:i + 4]
        if len(new_bytes) < 4:
            new_bytes = new_bytes + data[abs_off + len(new_bytes):abs_off + 4]
        new_word = struct.unpack_from("<I", new_bytes, 0)[0]
        struct.pack_into("<I", data, abs_off, new_word)
    print(f"  Welcome screen: DORORONG ({len(jpeg_data)} bytes JPEG)")

    # 2. Version string (USB string descriptor: len, 0x03, UTF-16LE)
    ver_usb = version.encode("utf-16-le")
    desc_len = 2 + len(ver_usb)
    if desc_len > VERSION_MAX_LEN:
        ver_usb = ver_usb[:VERSION_MAX_LEN - 2]
        desc_len = VERSION_MAX_LEN
    ver_desc = bytes([desc_len, 0x03]) + ver_usb
    ver_desc = ver_desc.ljust(VERSION_MAX_LEN, b"\x00")

    for i in range(0, VERSION_MAX_LEN, 4):
        abs_off = VERSION_OFFSET + i
        chunk = ver_desc[i:i + 4]
        new_word = struct.unpack_from("<I", chunk, 0)[0]
        struct.pack_into("<I", data, abs_off, new_word)
    print(f"  Version string: \"{version}\" (USB descriptor)")

    return []  # no GPNV word changes — these areas are outside XOR range


def show_profile_fields(data, profile_idx):
    block = get_profile(data, profile_idx)
    print(f"  Profile {profile_idx} fields:")
    for offset, name in sorted(FIELD_NAMES.items()):
        val = block[offset]
        print(f"    +0x{offset:02X} = 0x{val:02X} ({val:3d})  {name}")


def apply_patches(data, patches, verbose=True):
    """Apply patches to all active profiles. Returns list of word-level changes for GPNV update."""
    word_changes = []

    for pidx in ACTIVE_PROFILES:
        base = CONFIG_BASE + pidx * PROFILE_SIZE
        block = data[base : base + PROFILE_SIZE]

        for field_offset, new_value in patches.items():
            abs_offset = base + field_offset
            old_value = block[field_offset]
            if old_value == new_value:
                continue

            # Record word-level change for GPNV XOR
            word_aligned = abs_offset & ~3
            old_word = struct.unpack_from("<I", data, word_aligned)[0]

            # Apply the byte change
            data[abs_offset] = new_value

            new_word = struct.unpack_from("<I", data, word_aligned)[0]
            word_changes.append((word_aligned, old_word, new_word))

            if verbose:
                name = FIELD_NAMES.get(field_offset, "Unknown")
                print(f"  Profile {pidx}: +0x{field_offset:02X} 0x{old_value:02X} -> 0x{new_value:02X}  ({name})")

        # Recalculate CRC32
        block = data[base : base + PROFILE_SIZE]
        old_crc = struct.unpack_from("<I", block, CRC_OFFSET)[0]
        new_crc = calc_profile_crc32(block)

        if old_crc != new_crc:
            crc_abs = base + CRC_OFFSET
            crc_word_aligned = crc_abs & ~3
            old_crc_word = struct.unpack_from("<I", data, crc_word_aligned)[0]

            struct.pack_into("<I", data, crc_abs, new_crc)

            new_crc_word = struct.unpack_from("<I", data, crc_word_aligned)[0]
            word_changes.append((crc_word_aligned, old_crc_word, new_crc_word))

            if verbose:
                print(f"  Profile {pidx}: CRC32 0x{old_crc:08X} -> 0x{new_crc:08X}")

    return word_changes


def update_gpnv(data, word_changes, verbose=True):
    old_checksum = struct.unpack_from("<I", data, GPNV_CHECKSUM_OFFSET)[0]
    new_checksum = update_gpnv_xor_differential(data, word_changes)
    struct.pack_into("<I", data, GPNV_CHECKSUM_OFFSET, new_checksum)
    if verbose:
        print(f"  GPNV XOR: 0x{old_checksum:08X} -> 0x{new_checksum:08X}")


def verify_all_checksums(data):
    print("\n=== Checksum Verification ===")
    all_ok = True

    # Profile CRC32
    for pidx in ACTIVE_PROFILES:
        block = get_profile(data, pidx)
        calc = calc_profile_crc32(block)
        stored = struct.unpack_from("<I", block, CRC_OFFSET)[0]
        status = "OK" if calc == stored else "FAIL"
        if calc != stored:
            all_ok = False
        print(f"  Profile {pidx}: CRC32 {status} (calc=0x{calc:08X} stored=0x{stored:08X})")

    # GPNV XOR (differential update only — exact range unknown,
    # bootloader auto-recovers on mismatch)
    stored_gpnv = struct.unpack_from("<I", data, GPNV_CHECKSUM_OFFSET)[0]
    print(f"  GPNV XOR: 0x{stored_gpnv:08X} (differential update applied)")

    # SD filename
    filename = sd_upgrade_filename(data)
    print(f"  SD Upgrade filename: {filename}")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="GP1235 Settings Block Patcher")
    parser.add_argument("firmware", help="Base firmware binary")
    parser.add_argument("--patch", action="append", default=[],
                        help="Patch in OFFSET=VALUE format (hex), e.g. 0x0F=0x01")
    parser.add_argument("--preset", choices=list(PRESETS.keys()),
                        help="Apply a named preset")
    parser.add_argument("--output", "-o", help="Output firmware path")
    parser.add_argument("--sd-copy", help="Copy output to SD card directory")
    parser.add_argument("--raw-patch", action="append", default=[],
                        help="Raw firmware byte patch at absolute offset, e.g. 0x1FDD4=0x03A04C05 (32-bit LE)")
    parser.add_argument("--brand", nargs="?", const="v3.0", metavar="VERSION",
                        help="Add DORORONG boot screen + version (default: v3.0)")
    parser.add_argument("--show", action="store_true", help="Show current profile fields")
    parser.add_argument("--verify", action="store_true", help="Verify checksums only")
    args = parser.parse_args()

    data = read_firmware(args.firmware)
    print(f"Loaded: {args.firmware} ({len(data)} bytes)")

    if args.show:
        show_profile_fields(data, 6)
        return

    if args.verify:
        verify_all_checksums(data)
        return

    # Collect patches
    patches = {}
    if args.preset:
        patches.update(PRESETS[args.preset])
        print(f"Preset '{args.preset}': {patches}")

    for p in args.patch:
        offset_str, value_str = p.split("=")
        offset = int(offset_str, 0)
        value = int(value_str, 0)
        patches[offset] = value

    # Apply raw firmware patches
    raw_patches = {}
    for rp in args.raw_patch:
        offset_str, value_str = rp.split("=")
        offset = int(offset_str, 0)
        value = int(value_str, 0)
        raw_patches[offset] = value

    has_work = bool(patches) or bool(raw_patches) or args.brand

    if not has_work:
        print("No patches specified. Use --patch, --preset, or --brand.")
        print("\nCurrent profile fields:")
        show_profile_fields(data, 6)
        return

    all_word_changes = []

    # Apply raw firmware patches (code area — within GPNV XOR range)
    if raw_patches:
        print(f"\nApplying {len(raw_patches)} raw patch(es):")
        for offset, value in raw_patches.items():
            # Determine patch size from value
            if value > 0xFFFF:
                # 32-bit patch
                old_word = struct.unpack_from("<I", data, offset)[0]
                struct.pack_into("<I", data, offset, value)
                new_word = value
                print(f"  0x{offset:05X}: 0x{old_word:08X} -> 0x{new_word:08X} (32-bit)")
                if is_in_gpnv_xor_range(offset):
                    all_word_changes.append((offset, old_word, new_word))
            elif value > 0xFF:
                # 16-bit patch
                word_aligned = offset & ~3
                old_word = struct.unpack_from("<I", data, word_aligned)[0]
                struct.pack_into("<H", data, offset, value)
                new_word = struct.unpack_from("<I", data, word_aligned)[0]
                print(f"  0x{offset:05X}: 0x{old_word:08X} -> 0x{new_word:08X} (16-bit)")
                if is_in_gpnv_xor_range(offset):
                    all_word_changes.append((word_aligned, old_word, new_word))
            else:
                # 8-bit patch
                word_aligned = offset & ~3
                old_word = struct.unpack_from("<I", data, word_aligned)[0]
                data[offset] = value
                new_word = struct.unpack_from("<I", data, word_aligned)[0]
                print(f"  0x{offset:05X}: 0x{old_word:08X} -> 0x{new_word:08X} (8-bit)")
                if is_in_gpnv_xor_range(offset):
                    all_word_changes.append((word_aligned, old_word, new_word))

    # Apply settings patches
    if patches:
        print(f"\nApplying {len(patches)} patch(es) to {len(list(ACTIVE_PROFILES))} active profiles:")
        all_word_changes.extend(apply_patches(data, patches))

    # Apply branding
    if args.brand:
        print(f"\nApplying branding ({args.brand}):")
        all_word_changes.extend(apply_branding(data, args.brand))

    print("\nUpdating GPNV XOR checksum:")
    update_gpnv(data, all_word_changes)

    # Verify
    ok = verify_all_checksums(data)

    if not ok:
        print("\nERROR: Checksum verification failed!")
        sys.exit(1)

    # Output
    output_path = args.output
    if not output_path:
        base = Path(args.firmware)
        output_path = str(base.parent / f"{base.stem}_patched{base.suffix}")

    with open(output_path, "wb") as f:
        f.write(data)
    print(f"\nSaved: {output_path}")

    # SD card copy
    filename = sd_upgrade_filename(data)
    if args.sd_copy:
        sd_path = Path(args.sd_copy) / filename
        shutil.copy2(output_path, sd_path)
        print(f"SD card: {sd_path}")
    else:
        print(f"SD filename: {filename}")
        print(f"To copy to SD: cp \"{output_path}\" /g/{filename}")


if __name__ == "__main__":
    main()
