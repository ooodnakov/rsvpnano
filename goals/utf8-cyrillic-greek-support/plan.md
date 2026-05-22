# UTF-8 Support Plan: Cyrillic + Greek

## Status: Implementation Complete

## Summary

Added Cyrillic (Russian, Ukrainian, Bulgarian, Serbian) and Greek alphabet support to RSVP Nano firmware via UTF-8 encoding. ASCII/Latin-1 backward compatible.

## Flash Budget

| Component | Current | After UTF-8 |
|-----------|---------|-------------|
| Firmware | 2.7 MB | 2.7 MB |
| Fonts (3 typefaces × 2 sizes) | 7.4 MB | 7.4 MB |
| **Total** | 10.1 MB | 10.1 MB |
| Available | 16 MB | 16 MB |

## Components Completed

### 1. Font Generation (`tools/generate_embedded_serif_font.py`) ✓

- Added `--include-cyrillic` and `--include-greek` flags
- Added Unicode range constants for Cyrillic (U+0400–U+04FF) and Greek (U+0370–U+03FF)
- Default character range expanded to slots 1-255 (full Latin Extended)

### 2. Text Encoding (`src/text/LatinText.h`) ✓

- `LatinTextUtf8` namespace with UTF-8 encoding functions
- `codepointToUtf8()` — convert codepoint to UTF-8 bytes
- `utf8ToCodepoint()` — parse UTF-8 string to codepoints
- `stringToStorage()` — convert UTF-8 string to storage bytes
- ASCII/Latin-1 still uses single-byte legacy encoding

### 3. Display Rendering (`src/display/DisplayManager.cpp`) ✓

- `utf8NextCodepoint()` — UTF-8 decoder helper function
- `glyphForCodepoint()` — get glyph for Unicode codepoint (routes to correct typeface)
- `serifWordLayout()` — UTF-8 aware word layout
- `serifWordLayoutScaledPercent()` — UTF-8 aware scaled layout

### 4. Font Regeneration ✓

All 6 font headers regenerated with:
- Latin Extended (slots 1-255) — for Č, ř, ž, Ł, etc.
- Cyrillic (U+0400–U+04FF) — 256 characters
- Greek (U+0370–U+03FF) — supported glyphs

**Files regenerated:**
- `EmbeddedSerifFont.h` (1.5MB)
- `EmbeddedSerifFont70.h` (799KB)
- `EmbeddedAtkinsonFont.h` (1.5MB, using NotoSans as fallback)
- `EmbeddedAtkinsonFont70.h` (799KB)
- `EmbeddedOpenDyslexicFont.h` (1.5MB)
- `EmbeddedOpenDyslexicFont70.h` (799KB)

## Encoding Scheme

```
ASCII 0x00-0x7F          → 1 byte (single-byte storage)
Latin-1 direct 0x80-0xBF → 1 byte (single-byte storage)
Custom slots 0xC0-0xFF   → 1 byte (single-byte storage)
Cyrillic (U+0400+)       → UTF-8 multi-byte (2 bytes, e.g., Д = 0xD0 0x94)
Greek (U+0370+)          → UTF-8 multi-byte (2-3 bytes)
```

## Remaining Testing

Device testing requires physical hardware:
- [ ] Test Cyrillic text "Привет" on device
- [ ] Test Greek text "Γειά σου" on device
- [ ] Test Cyrillic EPUB conversion (browser)
- [ ] Test Greek EPUB conversion (browser)

## Build Status

```
Flash: 41.7% (2.7MB / 6.5MB available)
RAM: 22.9% (75KB / 320KB available)
```

## Commits

- `e3ed10c` feat: UTF-8 support for Cyrillic and Greek
- `0f430a6` feat: regenerate all fonts with Cyrillic and Greek glyphs
- `0cfcde8` fix: glyphForCodepoint() routes to correct font by typeface