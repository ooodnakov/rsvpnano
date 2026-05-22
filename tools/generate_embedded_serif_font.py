#!/usr/bin/env python3
"""
Font generator for RSVP Nano with UTF-8 support.
Generates embedded font headers with ASCII, Latin-1, Cyrillic, and Greek support.

Usage:
    python generate_embedded_serif_font.py --font-name NotoSans --point-size 52
    python generate_embedded_serif_font.py --include-cyrillic --include-greek
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

# Escape prefix for multi-byte sequences (0xF0 followed by 2-byte UTF-8)
ESCAPE_PREFIX = 0xF0

# Default settings
DEFAULT_FONT_NAME = "NotoSans"
DEFAULT_FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/noto-cjk",  # For CJK in future
]
DEFAULT_POINT_SIZE = 52
CANVAS_WIDTH = 112
CANVAS_HEIGHT = 128
ORIGIN_X = 10
BASELINE_Y = 76
ALPHA_THRESHOLD = 16
FONT_TOP_PADDING = 4
FONT_BOTTOM_PADDING = 2
DEFAULT_FIRST_CHAR = 1  # Include custom slots for Latin Extended
DEFAULT_LAST_CHAR = 255  # Full range including custom slots
SPACE_ADVANCE = 6
DEFAULT_OUTPUT_PATH = pathlib.Path("src/display/EmbeddedSerifFont.h")
DEFAULT_SYMBOL_PREFIX = "EmbeddedSerif"

# Custom glyph slot map (maps Unicode codepoint to storage byte)
# These occupy single-byte space 0x01-0xBF for Latin Extended characters
CUSTOM_GLYPH_CODEPOINTS = {
    0x01: 0x010E,  # Dcaron
    0x02: 0x010F,  # dcaron
    0x03: 0x011A,  # Ecaron
    0x04: 0x011B,  # ecaron
    0x05: 0x0147,  # Ncaron
    0x06: 0x0148,  # ncaron
    0x07: 0x0158,  # Rcaron
    0x08: 0x0159,  # rcaron
    0x0E: 0x0164,  # Tcaron
    0x0F: 0x0165,  # tcaron
    0x10: 0x016E,  # Uring
    0x11: 0x016F,  # uring
    0x12: 0x0150,  # Odblac
    0x13: 0x0151,  # odblac
    0x14: 0x0170,  # Udblac
    0x15: 0x0171,  # udblac
    0x80: 0x0152,  # OE
    0x81: 0x0153,  # oe
    0x82: 0x0141,  # Lslash
    0x83: 0x0142,  # lslash
    0x84: 0x010C,  # Ccaron
    0x85: 0x010D,  # ccaron
    0x86: 0x0160,  # Scaron
    0x87: 0x0161,  # scaron
    0x88: 0x017D,  # Zcaron
    0x89: 0x017E,  # zcaron
    0x8A: 0x0102,  # Abreve
    0x8B: 0x0103,  # abreve
    0x8C: 0x0218,  # Scommaaccent
    0x8D: 0x0219,  # scommaaccent
    0x8E: 0x021A,  # Tcommaaccent
    0x8F: 0x021B,  # tcommaaccent
    0x90: 0x011E,  # Gbreve
    0x91: 0x011F,  # gbreve
    0x92: 0x015E,  # Scedilla
    0x93: 0x015F,  # scedilla
    0x94: 0x0130,  # Idotaccent
    0x95: 0x0131,  # dotlessi
    0x96: 0x0104,  # Aogonek
    0x97: 0x0105,  # aogonek
    0x98: 0x0118,  # Eogonek
    0x99: 0x0119,  # eogonek
    0x9A: 0x0106,  # Cacute
    0x9B: 0x0107,  # cacute
    0x9C: 0x0143,  # Nacute
    0x9D: 0x0144,  # nacute
    0x9E: 0x015A,  # Sacute
    0x9F: 0x015B,  # sacute
    0xB2: 0x0179,  # Zacute
    0xB3: 0x017A,  # zacute
    0xB4: 0x017B,  # Zdotaccent
    0xB5: 0x017C,  # zdotaccent
    0xA1: 0x0100,  # Amacron
    0xA2: 0x0101,  # amacron
    0xA3: 0x0112,  # Emacron
    0xA4: 0x0113,  # emacron
    0xA5: 0x0122,  # Gcommaaccent
    0xA6: 0x0123,  # gcommaaccent
    0xA7: 0x012A,  # Imacron
    0xA8: 0x012B,  # imacron
    0xA9: 0x0136,  # Kcommaaccent
    0xAA: 0x0137,  # kcommaaccent
    0xAB: 0x013B,  # Lcommaaccent
    0xAC: 0x013C,  # lcommaaccent
    0xAE: 0x0145,  # Ncommaaccent
    0xAF: 0x0146,  # ncommaaccent
    0xB0: 0x0116,  # Edotaccent
    0xB1: 0x0117,  # edotaccent
    0xB6: 0x012E,  # Iogonek
    0xB7: 0x012F,  # iogonek
    0xB8: 0x0172,  # Uogonek
    0xB9: 0x0173,  # uogonek
    0xBA: 0x016A,  # Umacron
    0xBB: 0x016B,  # umacron
    0xBC: 0x0110,  # Dcroat
    0xBD: 0x0111,  # dcroat
    0xBE: 0x014A,  # Eng
    0xBF: 0x014B,  # eng
    0xD7: 0x0166,  # Tbar
    0xF7: 0x0167,  # tbar
}

CUSTOM_GLYPH_NAMES = {
    0x010E: "Dcaron",
    0x010F: "dcaron",
    0x011A: "Ecaron",
    0x011B: "ecaron",
    0x0147: "Ncaron",
    0x0148: "ncaron",
    0x0158: "Rcaron",
    0x0159: "rcaron",
    0x0164: "Tcaron",
    0x0165: "tcaron",
    0x016E: "Uring",
    0x016F: "uring",
    0x0150: "Odblac",
    0x0151: "odblac",
    0x0170: "Udblac",
    0x0171: "udblac",
    0x0152: "OE",
    0x0153: "oe",
    0x0141: "Lslash",
    0x0142: "lslash",
    0x010C: "Ccaron",
    0x010D: "ccaron",
    0x0160: "Scaron",
    0x0161: "scaron",
    0x017D: "Zcaron",
    0x017E: "zcaron",
    0x0102: "Abreve",
    0x0103: "abreve",
    0x0218: "Scommaaccent",
    0x0219: "scommaaccent",
    0x021A: "Tcommaaccent",
    0x021B: "tcommaaccent",
    0x011E: "Gbreve",
    0x011F: "gbreve",
    0x015E: "Scedilla",
    0x015F: "scedilla",
    0x0130: "Idotaccent",
    0x0131: "dotlessi",
    0x0104: "Aogonek",
    0x0105: "aogonek",
    0x0118: "Eogonek",
    0x0119: "eogonek",
    0x0106: "Cacute",
    0x0107: "cacute",
    0x0143: "Nacute",
    0x0144: "nacute",
    0x015A: "Sacute",
    0x015B: "sacute",
    0x0179: "Zacute",
    0x017A: "zacute",
    0x017B: "Zdotaccent",
    0x017C: "zdotaccent",
    0x0100: "Amacron",
    0x0101: "amacron",
    0x0112: "Emacron",
    0x0113: "emacron",
    0x0122: "Gcommaaccent",
    0x0123: "gcommaaccent",
    0x012A: "Imacron",
    0x012B: "imacron",
    0x0136: "Kcommaaccent",
    0x0137: "kcommaaccent",
    0x013B: "Lcommaaccent",
    0x013C: "lcommaaccent",
    0x0145: "Ncommaaccent",
    0x0146: "ncommaaccent",
    0x0116: "Edotaccent",
    0x0117: "edotaccent",
    0x012E: "Iogonek",
    0x012F: "iogonek",
    0x0172: "Uogonek",
    0x0173: "uogonek",
    0x016A: "Umacron",
    0x016B: "umacron",
    0x0110: "Dcroat",
    0x0111: "dcroat",
    0x014A: "Eng",
    0x014B: "eng",
    0x0166: "Tbar",
    0x0167: "tbar",
}

# Cyrillic glyph names
CYRILLIC_GLYPH_NAMES = {
    0x0410: "A_Cyr", 0x0430: "a_Cyr",
    0x0411: "Be_Cyr", 0x0431: "be_Cyr",
    0x0412: "Ve_Cyr", 0x0432: "ve_Cyr",
    0x0413: "Ge_Cyr", 0x0433: "ge_Cyr",
    0x0414: "De_Cyr", 0x0434: "de_Cyr",
    0x0415: "Ie_Cyr", 0x0435: "ie_Cyr",
    0x0401: "Io_Cyr", 0x0451: "io_Cyr",
    0x0416: "Zhe_Cyr", 0x0436: "zhe_Cyr",
    0x0417: "Ze_Cyr", 0x0437: "ze_Cyr",
    0x0418: "Ze_Cyr2", 0x0438: "ze_Cyr2",
    0x0419: "I_Cyr", 0x0439: "i_Cyr",
    0x041A: "Ka_Cyr", 0x043A: "ka_Cyr",
    0x041B: "El_Cyr", 0x043B: "el_Cyr",
    0x041C: "Em_Cyr", 0x043C: "em_Cyr",
    0x041D: "En_Cyr", 0x043D: "en_Cyr",
    0x041E: "O_Cyr", 0x043E: "o_Cyr",
    0x041F: "Pe_Cyr", 0x043F: "pe_Cyr",
    0x0420: "Er_Cyr", 0x0440: "er_Cyr",
    0x0421: "Es_Cyr", 0x0441: "es_Cyr",
    0x0422: "Te_Cyr", 0x0442: "te_Cyr",
    0x0423: "U_Cyr", 0x0443: "u_Cyr",
    0x0424: "Ef_Cyr", 0x0444: "ef_Cyr",
    0x0425: "Ha_Cyr", 0x0445: "ha_Cyr",
    0x0426: "Tse_Cyr", 0x0446: "tse_Cyr",
    0x0427: "Che_Cyr", 0x0447: "che_Cyr",
    0x0428: "Sha_Cyr", 0x0448: "sha_Cyr",
    0x0429: "Shcha_Cyr", 0x0449: "shcha_Cyr",
    0x042A: "Hard_Cyr", 0x044A: "hard_Cyr",
    0x042B: "Yeri_Cyr", 0x044B: "yeri_Cyr",
    0x042C: "Soft_Cyr", 0x044C: "soft_Cyr",
    0x042D: "E_Cyr", 0x044D: "e_Cyr",
    0x042E: "Iu_Cyr", 0x044E: "iu_Cyr",
    0x042F: "Ia_Cyr", 0x044F: "ia_Cyr",
    0x040E: "Ubreve_Cyr", 0x045E: "ubreve_Cyr",
    0x0406: "Yi_Cyr", 0x0456: "yi_Cyr",
    0x0404: "UkrainianIe_Cyr", 0x0454: "ukrainianIe_Cyr",
    0x0402: "Dje_Cyr", 0x0452: "dje_Cyr",
    0x0403: "Gje_Cyr", 0x0453: "gje_Cyr",
    0x0405: "Dze_Cyr", 0x0455: "dze_Cyr",
    0x0408: "Je_Cyr", 0x0458: "je_Cyr",
    0x0409: "Lje_Cyr", 0x0459: "lje_Cyr",
    0x040A: "Nje_Cyr", 0x045A: "nje_Cyr",
    0x040B: "Tshe_Cyr", 0x045B: "tshe_Cyr",
    0x040C: "Kje_Cyr", 0x045C: "kje_Cyr",
    0x040D: "Igrave_Cyr", 0x045D: "igrave_Cyr",
    0x040F: "Dzhe_Cyr", 0x045F: "dzhe_Cyr",
}

# Greek glyph names
GREEK_GLYPH_NAMES = {
    0x0370: "Greek_Pollian", 0x0371: "Greek_Archaic",
    0x0372: "Greek_Psammetichus", 0x0373: "Greek_Sampi",
    0x0374: "Greek_NumeralSign", 0x0375: "Greek_LowerNumeralSign",
    0x0376: "Greek_PanCyrillic", 0x0377: "Greek_SampiArchaic",
    0x0378: "Greek_Unavailable", 0x0379: "Greek_Unavailable2",
    0x037A: "Greek_Ypogegrammeni", 0x037B: "Greek_RhoWithStroke",
    0x037C: "Greek_Semicolon", 0x037D: "Greek_Colon",
    0x037E: "Greek_QuestionMark", 0x037F: "Greek_Exponential",
    0x0380: "Greek_Unavailable3", 0x0381: "Greek_Unavailable4",
    0x0382: "Greek_Unavailable5", 0x0383: "Greek_Unavailable6",
    0x0384: "Greek_Tonos", 0x0385: "Greek_DialytikaTonos",
    0x0386: "Greek_AlphaWithTonos", 0x0387: "Greek_AnoTelia",
    0x0388: "Greek_EpsilonWithTonos", 0x0389: "Greek_EtaWithTonos",
    0x038A: "Greek_IotaWithTonos", 0x038B: "Greek_Unavailable7",
    0x038C: "Greek_OmicronWithTonos", 0x038D: "Greek_Unavailable8",
    0x038E: "Greek_UpsilonWithTonos", 0x038F: "Greek_OmegaWithTonos",
    0x0390: "Greek_iotaWithDialytikaAndTonos",
    0x0391: "Greek_Alpha", 0x03B1: "Greek_alpha",
    0x0392: "Greek_Beta", 0x03B2: "Greek_beta",
    0x0393: "Greek_Gamma", 0x03B3: "Greek_gamma",
    0x0394: "Greek_Delta", 0x03B4: "Greek_delta",
    0x0395: "Greek_Epsilon", 0x03B5: "Greek_epsilon",
    0x0396: "Greek_Zeta", 0x03B6: "Greek_zeta",
    0x0397: "Greek_Eta", 0x03B7: "Greek_eta",
    0x0398: "Greek_Theta", 0x03B8: "Greek_theta",
    0x0399: "Greek_Iota", 0x03B9: "Greek_iota",
    0x039A: "Greek_Kappa", 0x03BA: "Greek_kappa",
    0x039B: "Greek_Lambda", 0x03BB: "Greek_lambda",
    0x039C: "Greek_Mu", 0x03BC: "Greek_mu",
    0x039D: "Greek_Nu", 0x03BD: "Greek_nu",
    0x039E: "Greek_Xi", 0x03BE: "Greek_xi",
    0x039F: "Greek_Omicron", 0x03BF: "Greek_omicron",
    0x03A0: "Greek_Pi", 0x03C0: "Greek_pi",
    0x03A1: "Greek_Rho", 0x03C1: "Greek_rho",
    0x03A2: "Greek_FinalSigma", 0x03C2: "Greek_finalsigma",
    0x03A3: "Greek_Sigma", 0x03C3: "Greek_sigma",
    0x03A4: "Greek_Tau", 0x03C4: "Greek_tau",
    0x03A5: "Greek_Upsilon", 0x03C5: "Greek_upsilon",
    0x03A6: "Greek_Phi", 0x03C6: "Greek_phi",
    0x03A7: "Greek_Chi", 0x03C7: "Greek_chi",
    0x03A8: "Greek_Psi", 0x03C8: "Greek_psi",
    0x03A9: "Greek_Omega", 0x03C9: "Greek_omega",
    0x03AA: "Greek_IotaWithDialytika", 0x03AB: "Greek_UpsilonWithDialytika",
    0x03AC: "Greek_AlphaWithTonos", 0x03AD: "Greek_EpsilonWithTonos",
    0x03AE: "Greek_EtaWithTonos", 0x03AF: "Greek_IotaWithTonos",
    0x03B0: "Greek_UpsilonWithDialytikaAndTonos",
    0x03D0: "Greek_BetaSymbol", 0x03D1: "Greek_ThetaSymbol",
    0x03D2: "Greek_Upsilon1", 0x03D3: "Greek_Upsilon2",
    0x03D4: "Greek_Upsilon3", 0x03D5: "Greek_PhiSymbol",
    0x03D6: "Greek_PiSymbol", 0x03D7: "Greek_KaiSymbol",
    0x03D8: "Greek_ArchaicKoppa", 0x03D9: "Greek_SmallKoppa",
    0x03DA: "Greek_Stigma", 0x03DB: "Greek_SmallStigma",
    0x03DC: "Greek_Digamma", 0x03DD: "Greek_SmallDigamma",
    0x03DE: "Greek_Koppa", 0x03DF: "Greek_SmallKoppa",
    0x03E0: "Greek_Sampi", 0x03E1: "Greek_SmallSampi",
    0x03E2: "Coptic_Ala", 0x03E3: "coptic_ala",
    0x03E4: "Coptic_Alfa", 0x03E5: "coptic_alfa",
    0x03E6: "Coptic_Vida", 0x03E7: "coptic_vida",
    0x03E8: "Coptic_Gamma", 0x03E9: "coptic_gamma",
    0x03EA: "Coptic_Dalda", 0x03EB: "coptic_dalda",
    0x03EC: "Coptic_Eida", 0x03ED: "coptic_eida",
    0x03EE: "Coptic_Soou", 0x03EF: "coptic_soou",
    0x03F0: "Coptic_Fei", 0x03F1: "coptic_fei",
    0x03F2: "Coptic_Ky", 0x03F3: "coptic_kai",
    0x03F4: "Greek_CapitalThetaSymbol", 0x03F5: "Greek_LunateEpsilon",
    0x03F6: "Greek_ReversedLunateEpsilon", 0x03F7: "Greek_CapitalSampi",
    0x03F8: "Greek_SmallSampi", 0x03F9: "Greek_CapitalKappa",
    0x03FA: "Greek_CapitalLambdaWithStroke", 0x03FB: "Greek_SmallLamdaWithStroke",
    0x03FC: "Greek_RhoWithStroke", 0x03FD: "Greek_CapitalOmega",
    0x03FE: "Greek_IotaWithDiaeresis", 0x03FF: "Greek_UpsilonWithDiaeresis",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an embedded font header with UTF-8 support."
    )
    parser.add_argument(
        "--point-size",
        type=int,
        default=DEFAULT_POINT_SIZE,
        help=f"Source font point size. Default: {DEFAULT_POINT_SIZE}",
    )
    parser.add_argument(
        "--font-name",
        default=DEFAULT_FONT_NAME,
        help=f"PostScript font name. Default: {DEFAULT_FONT_NAME}",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output header path. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--symbol-prefix",
        default=DEFAULT_SYMBOL_PREFIX,
        help=f"Prefix for generated struct/constants. Default: {DEFAULT_SYMBOL_PREFIX}",
    )
    parser.add_argument(
        "--font-search-path",
        action="append",
        default=[],
        help="Additional directory to search for the source font. May be passed multiple times.",
    )
    parser.add_argument(
        "--first-char",
        type=int,
        default=DEFAULT_FIRST_CHAR,
        help=f"First character code to embed (ASCII). Default: {DEFAULT_FIRST_CHAR}",
    )
    parser.add_argument(
        "--last-char",
        type=int,
        default=DEFAULT_LAST_CHAR,
        help=f"Last character code to embed (ASCII). Default: {DEFAULT_LAST_CHAR}",
    )
    parser.add_argument(
        "--include-cyrillic",
        action="store_true",
        help="Include Cyrillic Unicode range (U+0400–U+04FF)",
    )
    parser.add_argument(
        "--include-greek",
        action="store_true",
        help="Include Greek Unicode range (U+0370–U+03FF)",
    )
    return parser.parse_args()


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
    """Use font's native Unicode encoding for extended characters."""
    return (
        f"/CodexUnicodeFont /{font_name} findfont {point_size} scalefont setfont "
    )


def glyph_name_for_codepoint(codepoint: int) -> str:
    if codepoint in CUSTOM_GLYPH_NAMES:
        return CUSTOM_GLYPH_NAMES[codepoint]
    if codepoint in CYRILLIC_GLYPH_NAMES:
        return CYRILLIC_GLYPH_NAMES[codepoint]
    if codepoint in GREEK_GLYPH_NAMES:
        return GREEK_GLYPH_NAMES[codepoint]
    return f"uni{codepoint:04X}"


def glyph_script_for_codepoint(codepoint: int) -> str:
    if codepoint <= 0xFF:
        escaped = escape_postscript_char(chr(codepoint))
        return f"({escaped}) show"
    # For extended Unicode, use UTF-16BE hex encoding
    if codepoint <= 0xFFFF:
        high = (codepoint >> 8) & 0xFF
        low = codepoint & 0xFF
        return f"<{high:02X}{low:02X}> cvn glyphshow"
    return f"<{codepoint:08X}> cvn glyphshow"


def font_setup_for_codepoint(codepoint: int, font_name: str, point_size: int) -> str:
    """Return appropriate font setup based on codepoint range."""
    if codepoint <= 0xFF:
        return latin1_font_setup(font_name, point_size)
    return unicode_font_setup(font_name, point_size)


def display_codepoint_for_slot(slot: int) -> int:
    return CUSTOM_GLYPH_CODEPOINTS.get(slot, slot)


def glyph_comment_for_slot(slot: int) -> str:
    mapped_codepoint = CUSTOM_GLYPH_CODEPOINTS.get(slot)
    if mapped_codepoint is None:
        return ascii(chr(slot))
    return f"slot 0x{slot:02X} -> U+{mapped_codepoint:04X}"


def is_cyrillic_codepoint(codepoint: int) -> bool:
    return FIRST_CYRILLIC <= codepoint <= LAST_CYRILLIC


def is_greek_codepoint(codepoint: int) -> bool:
    return FIRST_GREEK <= codepoint <= LAST_GREEK


def render_glyph(
    tmp_dir: pathlib.Path, codepoint: int, font_name: str, point_size: int, font_search_paths: list[str]
) -> pathlib.Path:
    output = tmp_dir / f"{codepoint:04X}.pgm"
    font_setup = font_setup_for_codepoint(codepoint, font_name, point_size)
    program = (
        "1 setgray clippath fill "
        "0 setgray "
        f"{font_setup}"
        f"{ORIGIN_X} {BASELINE_Y} moveto "
        f"{glyph_script_for_codepoint(codepoint)} showpage"
    )
    command = [
        "gs",
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-dTextAlphaBits=4",
        "-dGraphicsAlphaBits=4",
        "-sDEVICE=pgmraw",
        "-r72",
        f"-g{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        f"-sOutputFile={output}",
    ]

    existing_paths = [font_path for font_path in font_search_paths if pathlib.Path(font_path).is_dir()]
    if existing_paths:
        command.append(f"-sFONTPATH={os.pathsep.join(existing_paths)}")

    command += ["-c", program]

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return output


def advance_width_for_glyph(codepoint: int, font_name: str, point_size: int, font_search_paths: list[str]) -> int:
    font_setup = font_setup_for_codepoint(codepoint, font_name, point_size)
    command = [
        "gs",
        "-q",
        "-dNODISPLAY",
    ]

    existing_paths = [font_path for font_path in font_search_paths if pathlib.Path(font_path).is_dir()]
    if existing_paths:
        command.append(f"-sFONTPATH={os.pathsep.join(existing_paths)}")

    command += [
        "-c",
        (
            f"{font_setup}"
            "0 0 moveto "
            f"{glyph_script_for_codepoint(codepoint)} "
            "currentpoint pop == quit"
        ),
    ]

    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"Failed to determine advance width for U+{codepoint:04X}")

    return max(1, int(math.floor(float(lines[-1]) + 0.5)))


def parse_pgm(path: pathlib.Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"P5\n"):
        raise ValueError(f"Unexpected PGM header in {path}")

    parts = data.split(b"\n")
    index = 1
    while parts[index].startswith(b"#"):
        index += 1

    width, height = map(int, parts[index].split())
    max_value = int(parts[index + 1])
    if max_value != 255:
        raise ValueError(f"Unexpected max value {max_value} in {path}")

    raster = b"\n".join(parts[index + 2 :])
    expected_length = width * height
    if len(raster) != expected_length:
        raise ValueError(f"Unexpected raster length in {path}: {len(raster)} != {expected_length}")

    return width, height, raster


def alpha_at(raster: bytes, width: int, x: int, y: int) -> int:
    return 255 - raster[y * width + x]


def main() -> None:
    args = parse_args()
    if not (0 <= args.first_char <= args.last_char <= 255):
        raise ValueError("Character range must satisfy 0 <= first-char <= last-char <= 255")
    
    font_search_paths = list(DEFAULT_FONT_SEARCH_PATHS)
    font_search_paths.extend(args.font_search_path)
    
    # Build list of codepoints to render
    codepoints: list[int] = list(range(args.first_char, args.last_char + 1))
    
    if args.include_cyrillic:
        codepoints.extend(range(FIRST_CYRILLIC, LAST_CYRILLIC + 1))
    if args.include_greek:
        codepoints.extend(range(FIRST_GREEK, LAST_GREEK + 1))
    
    glyph_images: dict[int, tuple[int, int, bytes]] = {}
    global_top = CANVAS_HEIGHT
    global_bottom = -1

    with tempfile.TemporaryDirectory(prefix="serif_font_") as tmp:
        tmp_dir = pathlib.Path(tmp)

        for codepoint in codepoints:
            pgm_path = render_glyph(
                tmp_dir, codepoint, args.font_name, args.point_size, font_search_paths
            )
            width, height, raster = parse_pgm(pgm_path)
            glyph_images[codepoint] = (width, height, raster)

            for y in range(height):
                found = False
                for x in range(width):
                    if alpha_at(raster, width, x, y) > ALPHA_THRESHOLD:
                        global_top = min(global_top, y)
                        global_bottom = max(global_bottom, y)
                        found = True
                if found:
                    continue

    if global_bottom < global_top:
        raise RuntimeError("Failed to detect any font pixels")

    crop_top = max(0, global_top - FONT_TOP_PADDING)
    crop_bottom = min(CANVAS_HEIGHT - 1, global_bottom + FONT_BOTTOM_PADDING)
    font_height = crop_bottom - crop_top + 1
    bitmap_bytes: list[int] = []
    glyph_entries: list[str] = []

    for codepoint in codepoints:
        width, height, raster = glyph_images[codepoint]

        min_x = width
        max_x = -1
        for y in range(crop_top, crop_bottom + 1):
            for x in range(width):
                if alpha_at(raster, width, x, y) > ALPHA_THRESHOLD:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)

        bitmap_offset = len(bitmap_bytes)

        if max_x >= min_x:
            glyph_width = max_x - min_x + 1
            for y in range(crop_top, crop_bottom + 1):
                for x in range(min_x, max_x + 1):
                    alpha = alpha_at(raster, width, x, y)
                    if alpha <= ALPHA_THRESHOLD:
                        alpha = 0
                    bitmap_bytes.append(alpha)
            x_offset = min_x - ORIGIN_X
            x_advance = advance_width_for_glyph(codepoint, args.font_name, args.point_size, font_search_paths)
        else:
            x_offset = 0
            glyph_width = 0
            x_advance = advance_width_for_glyph(codepoint, args.font_name, args.point_size, font_search_paths)

        # Create comment
        if codepoint <= 0xFF:
            comment = glyph_comment_for_slot(codepoint)
        elif is_cyrillic_codepoint(codepoint):
            comment = f"U+{codepoint:04X} Cyrillic"
        elif is_greek_codepoint(codepoint):
            comment = f"U+{codepoint:04X} Greek"
        else:
            comment = f"U+{codepoint:04X}"

        glyph_entries.append(
            "    "
            + "{"
            + f"{bitmap_offset}, {x_offset}, {glyph_width}, {x_advance}"
            + "}, "
            + f"// {comment}"
        )

    # Calculate ranges for header
    lines: list[str] = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "",
        "// Generated from a real serif font at build time and embedded as glyph data.",
        f"// Source font: {args.font_name} at {args.point_size} pt",
        "",
        "// Character ranges:",
        f"//   ASCII: U+{args.first_char:02X}–U+{args.last_char:02X} (basic Latin)",
    ]
    
    if args.include_cyrillic:
        lines.append(f"//   Cyrillic: U+{FIRST_CYRILLIC:04X}–U+{LAST_CYRILLIC:04X}")
    if args.include_greek:
        lines.append(f"//   Greek: U+{FIRST_GREEK:04X}–U+{LAST_GREEK:04X}")
    
    lines.extend([
        "",
        "// Encoding:",
        "//   ASCII/Latin-1: direct single-byte",
        "//   Cyrillic/Greek: UTF-8 sequences (2 bytes)",
        "",
        f"struct {args.symbol_prefix}Glyph " + "{",
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
    
    # Add ranges if Cyrillic/Greek included
    if args.include_cyrillic:
        lines.append(f"constexpr uint32_t k{args.symbol_prefix}FirstCyrillic = 0x{FIRST_CYRILLIC:04X};")
        lines.append(f"constexpr uint32_t k{args.symbol_prefix}LastCyrillic = 0x{LAST_CYRILLIC:04X};")
    if args.include_greek:
        lines.append(f"constexpr uint32_t k{args.symbol_prefix}FirstGreek = 0x{FIRST_GREEK:04X};")
        lines.append(f"constexpr uint32_t k{args.symbol_prefix}LastGreek = 0x{LAST_GREEK:04X};")
    
    lines.extend([
        "",
        f"static const uint8_t k{args.symbol_prefix}Bitmaps[] PROGMEM = " + "{",
    ])

    for offset in range(0, len(bitmap_bytes), 16):
        chunk = bitmap_bytes[offset : offset + 16]
        lines.append("    " + ", ".join(f"{value:3d}" for value in chunk) + ",")

    lines += [
        "};",
        "",
        f"static const {args.symbol_prefix}Glyph k{args.symbol_prefix}Glyphs[] PROGMEM = " + "{",
        *glyph_entries,
        "};",
        "",
    ]

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()