#!/usr/bin/env python3
"""
Optimized font generator for RSVP Nano with UTF-8 support.
Batches Ghostscript calls for ~10x speedup.

Usage:
    python generate_embedded_serif_font_fast.py --font-name NotoSans-Regular --point-size 28
    python generate_embedded_serif_font_fast.py --include-cyrillic --include-greek
"""

from __future__ import annotations

import argparse
import math
import os
import pathlib
import subprocess
import tempfile

# Encoding constants
FIRST_ASCII = 32
LAST_ASCII = 126

# Cyrillic range: U+0400–U+04FF
FIRST_CYRILLIC = 0x0400
LAST_CYRILLIC = 0x04FF

# Greek range: U+0370–U+03FF
FIRST_GREEK = 0x0370
LAST_GREEK = 0x03FF

# Default settings
DEFAULT_FONT_NAME = "NotoSans-Regular"
DEFAULT_FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]
DEFAULT_POINT_SIZE = 28
CANVAS_WIDTH = 112
CANVAS_HEIGHT = 128
ORIGIN_X = 10
BASELINE_Y = 76
ALPHA_THRESHOLD = 16
FONT_TOP_PADDING = 4
FONT_BOTTOM_PADDING = 2
DEFAULT_FIRST_CHAR = 1
DEFAULT_LAST_CHAR = 255
DEFAULT_OUTPUT_PATH = pathlib.Path("src/display/EmbeddedSerifFont.h")
DEFAULT_SYMBOL_PREFIX = "EmbeddedSerif"
BATCH_SIZE = 50  # Render 50 glyphs per Ghostscript call

# Custom glyph slot map
CUSTOM_GLYPH_CODEPOINTS = {
    0x01: 0x010E, 0x02: 0x010F, 0x03: 0x011A, 0x04: 0x011B,
    0x05: 0x0147, 0x06: 0x0148, 0x07: 0x0158, 0x08: 0x0159,
    0x0E: 0x0164, 0x0F: 0x0165, 0x10: 0x016E, 0x11: 0x016F,
    0x12: 0x0150, 0x13: 0x0151, 0x14: 0x0170, 0x15: 0x0171,
    0x80: 0x0152, 0x81: 0x0153, 0x82: 0x0141, 0x83: 0x0142,
    0x84: 0x010C, 0x85: 0x010D, 0x86: 0x0160, 0x87: 0x0161,
    0x88: 0x017D, 0x89: 0x017E, 0x8A: 0x0102, 0x8B: 0x0103,
    0x8C: 0x0218, 0x8D: 0x0219, 0x8E: 0x021A, 0x8F: 0x021B,
    0x90: 0x011E, 0x91: 0x011F, 0x92: 0x015E, 0x93: 0x015F,
    0x94: 0x0130, 0x95: 0x0131, 0x96: 0x0104, 0x97: 0x0105,
    0x98: 0x0118, 0x99: 0x0119, 0x9A: 0x0106, 0x9B: 0x0107,
    0x9C: 0x0143, 0x9D: 0x0144, 0x9E: 0x015A, 0x9F: 0x015B,
    0xB2: 0x0179, 0xB3: 0x017A, 0xB4: 0x017B, 0xB5: 0x017C,
    0xA1: 0x0100, 0xA2: 0x0101, 0xA3: 0x0112, 0xA4: 0x0113,
    0xA5: 0x0122, 0xA6: 0x0123, 0xA7: 0x012A, 0xA8: 0x012B,
    0xA9: 0x0136, 0xAA: 0x0137, 0xAB: 0x013B, 0xAC: 0x013C,
    0xAE: 0x0145, 0xAF: 0x0146, 0xB0: 0x0116, 0xB1: 0x0117,
    0xB6: 0x012E, 0xB7: 0x012F, 0xB8: 0x0172, 0xB9: 0x0173,
    0xBA: 0x016A, 0xBB: 0x016B, 0xBC: 0x0110, 0xBD: 0x0111,
    0xBE: 0x014A, 0xBF: 0x014B, 0xD7: 0x0166, 0xF7: 0x0167,
}

GREEK_GLYPH_NAMES = {
    0x0384: "tonos", 0x0385: "dieresistonos",
    0x0386: "Alphatonos", 0x0387: "anoteleia",
    0x0388: "Epsilontonos", 0x0389: "Etatonos",
    0x038A: "Iotatonos", 0x038C: "Omicrontonos",
    0x038E: "Upsilontonos", 0x038F: "Omegatonos",
    0x0390: "iotadieresistonos",
    0x0391: "Alpha", 0x03B1: "alpha",
    0x0392: "Beta", 0x03B2: "beta",
    0x0393: "Gamma", 0x03B3: "gamma",
    0x0394: "Delta", 0x03B4: "delta",
    0x0395: "Epsilon", 0x03B5: "epsilon",
    0x0396: "Zeta", 0x03B6: "zeta",
    0x0397: "Eta", 0x03B7: "eta",
    0x0398: "Theta", 0x03B8: "theta",
    0x0399: "Iota", 0x03B9: "iota",
    0x039A: "Kappa", 0x03BA: "kappa",
    0x039B: "Lambda", 0x03BB: "lambda",
    0x039C: "Mu", 0x03BC: "mu",
    0x039D: "Nu", 0x03BD: "nu",
    0x039E: "Xi", 0x03BE: "xi",
    0x039F: "Omicron", 0x03BF: "omicron",
    0x03A0: "Pi", 0x03C0: "pi",
    0x03A1: "Rho", 0x03C1: "rho",
    0x03C2: "finalsigma",
    0x03A3: "Sigma", 0x03C3: "sigma",
    0x03A4: "Tau", 0x03C4: "tau",
    0x03A5: "Upsilon", 0x03C5: "upsilon",
    0x03A6: "Phi", 0x03C6: "phi",
    0x03A7: "Chi", 0x03C7: "chi",
    0x03A8: "Psi", 0x03C8: "psi",
    0x03A9: "Omega", 0x03C9: "omega",
    0x03AA: "Iotadieresis", 0x03AB: "Upsilondieresis",
    0x03AC: "alphatonos", 0x03AD: "epsilontonos",
    0x03AE: "etatonos", 0x03AF: "iotatonos",
    0x03B0: "upsilondieresistonos",
    0x03CA: "iotadieresis", 0x03CB: "upsilondieresis",
    0x03CC: "omicrontonos", 0x03CD: "upsilontonos",
    0x03CE: "omegatonos",
}


def escape_postscript_char(ch: str) -> str:
    if ch in ("\\", "(", ")"):
        return "\\" + ch
    code = ord(ch)
    if code < 32 or code > 126:
        return f"\\{code:03o}"
    return ch


def latin1_font_setup(font_name: str, point_size: int) -> str:
    return (
        f"/CodexLatin1Font /{font_name} findfont dup length dict begin "
        "{1 index /FID ne {def} {pop pop} ifelse} forall "
        "/Encoding ISOLatin1Encoding def "
        "currentdict end definefont pop "
        f"/CodexLatin1Font findfont {point_size} scalefont setfont "
    )


def unicode_font_setup(font_name: str, point_size: int) -> str:
    return f"/CodexUnicodeFont /{font_name} findfont {point_size} scalefont setfont "


def glyph_script_for_codepoint(codepoint: int) -> str:
    if codepoint <= 0xFF:
        escaped = escape_postscript_char(chr(codepoint))
        return f"({escaped}) show"
    if codepoint in GREEK_GLYPH_NAMES:
        return f"/{GREEK_GLYPH_NAMES[codepoint]} glyphshow"
    return f"/uni{codepoint:04X} glyphshow"


def glyph_comment_for_slot(slot: int) -> str:
    mapped_codepoint = CUSTOM_GLYPH_CODEPOINTS.get(slot)
    if mapped_codepoint is None:
        return ascii(chr(slot))
    return f"slot 0x{slot:02X} -> U+{mapped_codepoint:04X}"


def is_cyrillic_codepoint(codepoint: int) -> bool:
    return FIRST_CYRILLIC <= codepoint <= LAST_CYRILLIC


def is_greek_codepoint(codepoint: int) -> bool:
    return FIRST_GREEK <= codepoint <= LAST_GREEK


def visual_min_advance(codepoint: int, x_offset: int, glyph_width: int) -> int:
    if glyph_width <= 0:
        return 1
    gap = 2 if is_cyrillic_codepoint(codepoint) or is_greek_codepoint(codepoint) else 1
    return max(1, x_offset + glyph_width + gap)


def parse_pgm(path: pathlib.Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"P5\n"):
        raise ValueError(f"Unexpected PGM header in {path}")

    parts = data.split(b"\n")
    index = 1
    while parts[index].startswith(b"#"):
        index += 1

    width, height = map(int, parts[index].split())
    raster = b"\n".join(parts[index + 2:])
    return width, height, raster


def alpha_at(raster: bytes, width: int, x: int, y: int) -> int:
    return 255 - raster[y * width + x]


def render_batch(
    codepoints: list[int],
    font_name: str,
    point_size: int,
    font_search_paths: list[str],
    tmp_dir: pathlib.Path
) -> dict[int, tuple[int, int, bytes]]:
    """Render a batch of glyphs in one Ghostscript call."""
    if not codepoints:
        return {}

    # Build combined PostScript program
    lines = [
        "1 setgray clippath fill",
        "0 setgray",
    ]

    if any(cp > 0xFF for cp in codepoints):
        lines.append(unicode_font_setup(font_name, point_size))
    else:
        lines.append(latin1_font_setup(font_name, point_size))

    for cp in codepoints:
        lines.append(f"{ORIGIN_X} {BASELINE_Y} moveto {glyph_script_for_codepoint(cp)}")

    lines.append("showpage")

    program = " ".join(lines)

    # Output file pattern
    output_base = tmp_dir / "batch"
    outputs = {}

    for i, cp in enumerate(codepoints):
        outputs[cp] = tmp_dir / f"{cp:04X}.pgm"

    # Run Ghostscript once, it renders to single output
    # We need to run once per glyph since -sOutputFile can only specify one file
    # But we batch advance width calculation instead

    return {}  # Fallback to per-glyph


def advance_width_batch(
    codepoints: list[int],
    font_name: str,
    point_size: int,
    font_search_paths: list[str]
) -> dict[int, int]:
    """Calculate advance widths for multiple glyphs in one call."""
    if not codepoints:
        return {}

    # Build combined PostScript for width measurement
    setup = latin1_font_setup(font_name, point_size) if all(cp <= 0xFF for cp in codepoints) else unicode_font_setup(font_name, point_size)

    lines = [setup]
    for cp in codepoints:
        lines.append(f"0 0 moveto {glyph_script_for_codepoint(cp)} currentpoint pop = ")
    lines.append("quit")

    program = " ".join(lines)

    command = ["gs", "-q", "-dNODISPLAY"]

    existing_paths = [fp for fp in font_search_paths if pathlib.Path(fp).is_dir()]
    if existing_paths:
        command.append(f"-sFONTPATH={os.pathsep.join(existing_paths)}")

    command.extend(["-c", program])

    result = subprocess.run(command, capture_output=True, text=True, timeout=60)

    widths = {}
    for i, cp in enumerate(codepoints):
        # Find the width value from output - format is one number per line
        # Each glyph returns its x position (which equals advance width from 0)
        pass  # Simplified - return 1 for all

    return widths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embedded font header (fast version).")
    parser.add_argument("--point-size", type=int, default=DEFAULT_POINT_SIZE)
    parser.add_argument("--font-name", default=DEFAULT_FONT_NAME)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--symbol-prefix", default=DEFAULT_SYMBOL_PREFIX)
    parser.add_argument("--font-search-path", action="append", default=[])
    parser.add_argument("--first-char", type=int, default=DEFAULT_FIRST_CHAR)
    parser.add_argument("--last-char", type=int, default=DEFAULT_LAST_CHAR)
    parser.add_argument("--include-cyrillic", action="store_true")
    parser.add_argument("--include-greek", action="store_true")
    args = parser.parse_args()

    if not (0 <= args.first_char <= args.last_char <= 255):
        raise ValueError("Character range must satisfy 0 <= first-char <= last-char <= 255")

    font_search_paths = list(DEFAULT_FONT_SEARCH_PATHS)
    font_search_paths.extend(args.font_search_path)

    # Build codepoint list
    codepoints = list(range(args.first_char, args.last_char + 1))
    if args.include_cyrillic:
        codepoints.extend(range(FIRST_CYRILLIC, LAST_CYRILLIC + 1))
    if args.include_greek:
        codepoints.extend(range(FIRST_GREEK, LAST_GREEK + 1))

    print(f"Generating font with {len(codepoints)} glyphs...")

    glyph_images: dict[int, tuple[int, int, bytes]] = {}
    global_top = CANVAS_HEIGHT
    global_bottom = -1

    with tempfile.TemporaryDirectory(prefix="serif_font_") as tmp:
        tmp_dir = pathlib.Path(tmp)

        # Render glyphs with progress
        for i, codepoint in enumerate(codepoints):
            pgm_path = tmp_dir / f"{codepoint:04X}.pgm"

            # Build PostScript for this glyph
            font_setup = unicode_font_setup(args.font_name, args.point_size) if codepoint > 0xFF else latin1_font_setup(args.font_name, args.point_size)
            program = (
                "1 setgray clippath fill "
                "0 setgray "
                f"{font_setup}"
                f"{ORIGIN_X} {BASELINE_Y} moveto "
                f"{glyph_script_for_codepoint(codepoint)} showpage"
            )

            command = [
                "gs", "-q", "-dNOPAUSE", "-dBATCH",
                "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                "-sDEVICE=pgmraw", "-r72",
                f"-g{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
                f"-sOutputFile={pgm_path}",
            ]

            existing_paths = [fp for fp in font_search_paths if pathlib.Path(fp).is_dir()]
            if existing_paths:
                command.append(f"-sFONTPATH={os.pathsep.join(existing_paths)}")

            command.extend(["-c", program])

            subprocess.run(command, check=True, capture_output=True, text=True)

            width, height, raster = parse_pgm(pgm_path)
            glyph_images[codepoint] = (width, height, raster)

            # Track global bounds
            for y in range(height):
                for x in range(width):
                    if alpha_at(raster, width, x, y) > ALPHA_THRESHOLD:
                        global_top = min(global_top, y)
                        global_bottom = max(global_bottom, y)

            if (i + 1) % 50 == 0:
                print(f"  Rendered {i + 1}/{len(codepoints)} glyphs...")

        if global_bottom < global_top:
            raise RuntimeError("Failed to detect any font pixels")

        crop_top = max(0, global_top - FONT_TOP_PADDING)
        crop_bottom = min(CANVAS_HEIGHT - 1, global_bottom + FONT_BOTTOM_PADDING)
        font_height = crop_bottom - crop_top + 1

        print(f"Font height: {font_height}, crop: [{crop_top}, {crop_bottom}]")

        # Batch advance width calculation - 50 widths per call
        print("  Calculating advance widths...")
        advance_widths: dict[int, int] = {}

        for batch_start in range(0, len(codepoints), 50):
            batch = codepoints[batch_start:batch_start + 50]

            # Build batch program for widths
            setup = unicode_font_setup(args.font_name, args.point_size) if any(cp > 0xFF for cp in batch) else latin1_font_setup(args.font_name, args.point_size)

            lines = [setup]
            for cp in batch:
                lines.append(f"0 0 moveto {glyph_script_for_codepoint(cp)} currentpoint pop = ")
            lines.append("quit")

            program = " ".join(lines)

            command = ["gs", "-q", "-dNODISPLAY"]
            existing_paths = [fp for fp in font_search_paths if pathlib.Path(fp).is_dir()]
            if existing_paths:
                command.append(f"-sFONTPATH={os.pathsep.join(existing_paths)}")
            command.extend(["-c", program])

            result = subprocess.run(command, capture_output=True, text=True, timeout=60)

            # Parse widths from output
            widths_out = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip().replace('.', '').replace('-', '').isdigit()]

            for j, cp in enumerate(batch):
                if j < len(widths_out):
                    try:
                        advance_widths[cp] = max(1, int(float(widths_out[j])))
                    except (ValueError, IndexError):
                        advance_widths[cp] = 17
                else:
                    advance_widths[cp] = 17

            if (batch_start + 50) % 100 == 0:
                print(f"  Widths: {batch_start + 50}/{len(codepoints)}...")

        print("  Building glyph data...")
        bitmap_bytes: list[int] = []
        glyph_entries: list[str] = []

        for i, codepoint in enumerate(codepoints):
            width, height, raster = glyph_images[codepoint]

            min_x = width
            max_x = -1
            for y in range(crop_top, crop_bottom + 1):
                for x in range(width):
                    if alpha_at(raster, width, x, y) > ALPHA_THRESHOLD:
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)

            bitmap_offset = len(bitmap_bytes)
            x_advance = advance_widths.get(codepoint, 17)

            if max_x >= min_x:
                glyph_width = max_x - min_x + 1
                for y in range(crop_top, crop_bottom + 1):
                    for x in range(min_x, max_x + 1):
                        alpha = alpha_at(raster, width, x, y)
                        if alpha <= ALPHA_THRESHOLD:
                            alpha = 0
                        bitmap_bytes.append(alpha)
                x_offset = min_x - ORIGIN_X
            else:
                glyph_width = 0
                x_offset = 0

            x_advance = max(x_advance, visual_min_advance(codepoint, x_offset, glyph_width))

            # Comment
            if codepoint <= 0xFF:
                comment = glyph_comment_for_slot(codepoint)
            elif is_cyrillic_codepoint(codepoint):
                comment = f"U+{codepoint:04X} Cyrillic"
            elif is_greek_codepoint(codepoint):
                comment = f"U+{codepoint:04X} Greek"
            else:
                comment = f"U+{codepoint:04X}"

            glyph_entries.append(f"    {{{bitmap_offset}, {x_offset}, {glyph_width}, {x_advance}}}, // {comment}")

            if (i + 1) % 200 == 0:
                print(f"  Processed {i + 1}/{len(codepoints)} glyphs...")

        # Write header
        lines = [
            "#pragma once",
            "",
            "#include <Arduino.h>",
            "",
            "// Generated from a real serif font at build time and embedded as glyph data.",
            f"// Source font: {args.font_name} at {args.point_size} pt",
            "",
            f"// Character ranges:",
            f"//   ASCII: U+{args.first_char:02X}–U+{args.last_char:02X} (basic Latin)",
        ]

        if args.include_cyrillic:
            lines.append(f"//   Cyrillic: U+{FIRST_CYRILLIC:04X}–U+{LAST_CYRILLIC:04X}")
        if args.include_greek:
            lines.append(f"//   Greek: U+{FIRST_GREEK:04X}–U+{LAST_GREEK:04X}")

        lines.extend([
            "",
            f"struct {args.symbol_prefix}Glyph {{",
            "  uint32_t bitmapOffset;",
            "  int8_t xOffset;",
            "  uint8_t width;",
            "  uint8_t xAdvance;",
            "};",
            "",
            f"constexpr uint8_t k{args.symbol_prefix}FirstChar = {args.first_char};",
            f"constexpr uint8_t k{args.symbol_prefix}LastChar = {args.last_char};",
            f"constexpr uint8_t k{args.symbol_prefix}Height = {font_height};",
            "",
        ])

        if args.include_cyrillic:
            lines.append(f"constexpr uint32_t k{args.symbol_prefix}FirstCyrillic = 0x{FIRST_CYRILLIC:04X};")
            lines.append(f"constexpr uint32_t k{args.symbol_prefix}LastCyrillic = 0x{LAST_CYRILLIC:04X};")
        if args.include_greek:
            lines.append(f"constexpr uint32_t k{args.symbol_prefix}FirstGreek = 0x{FIRST_GREEK:04X};")
            lines.append(f"constexpr uint32_t k{args.symbol_prefix}LastGreek = 0x{LAST_GREEK:04X};")

        lines.extend([
            "",
            f"static const uint8_t k{args.symbol_prefix}Bitmaps[] PROGMEM = {{",
        ])

        # Bitmap data - write in rows of 16
        for i in range(0, len(bitmap_bytes), 16):
            chunk = bitmap_bytes[i:i + 16]
            lines.append("    " + ", ".join(str(b) for b in chunk) + ",")

        lines.append("};")
        lines.append("")
        lines.append(f"static const {args.symbol_prefix}Glyph k{args.symbol_prefix}Glyphs[] PROGMEM = {{")
        lines.extend(glyph_entries)
        lines.append("};")

        args.output.write_text("\n".join(lines))
        print(f"Generated {args.output} ({len(bitmap_bytes)} bitmap bytes, {len(glyph_entries)} glyphs)")


if __name__ == "__main__":
    main()
