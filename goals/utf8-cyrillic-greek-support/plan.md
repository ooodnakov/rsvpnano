# UTF-8 Support Plan: Cyrillic + Greek

## Status: Implementation in Progress

## Flash Budget

| Component | Current | After UTF-8 |
|-----------|---------|-------------|
| Firmware | 2.4 MB | 2.4 MB |
| Fonts (3 typefaces × 2 sizes) | 5.1 MB | +400 KB ≈ 5.5 MB |
| **Total** | 7.5 MB | 7.9 MB |
| Available | 16 MB | 16 MB |

## Components Completed

### 1. Font Generation (`tools/generate_embedded_serif_font.py`) ✓

**Status: Done**
- Added `--include-cyrillic` and `--include-greek` flags
- Added Unicode range constants for Cyrillic (U+0400–U+04FF) and Greek (U+0370–U+03FF)
- Added glyph name maps for Cyrillic and Greek

### 2. Text Encoding (`src/text/LatinText.h`) ✓

**Status: Done**
- `LatinTextUtf8` namespace with UTF-8 encoding functions
- `codepointToUtf8()` — convert codepoint to UTF-8 bytes
- `utf8ToCodepoint()` — parse UTF-8 string to codepoints
- `stringToStorage()` — convert UTF-8 string to storage bytes
- `isCyrillic()` / `isGreek()` — range checks
- ASCII/Latin-1 still uses single-byte legacy encoding

### 3. Display Rendering (`src/display/DisplayManager.cpp`) ✓

**Status: Done**
- `utf8NextCodepoint()` — UTF-8 decoder helper function
- `glyphForCodepoint()` — get glyph for Unicode codepoint
- `serifWordLayout()` — UTF-8 aware word layout
- `serifWordLayoutScaledPercent()` — UTF-8 aware scaled layout
- Build passes ✓

## Remaining Work

### 4. Font Regeneration

**Files to regenerate:**
- `src/display/EmbeddedSerifFont.h` — serif large
- `src/display/EmbeddedSerifFont70.h` — serif small
- `src/display/EmbeddedAtkinsonFont.h` — Atkinson large
- `src/display/EmbeddedAtkinsonFont70.h` — Atkinson small
- `src/display/EmbeddedOpenDyslexicFont.h` — OpenDyslexic large
- `src/display/EmbeddedOpenDyslexicFont70.h` — OpenDyslexic small

**Command:**
```bash
python tools/generate_embedded_serif_font.py --include-cyrillic --include-greek
```

### 5. RSVP File Format (`.rsvp`)

**.rsvp files are UTF-8** — no format change needed.

### 6. Browser Converter (`web/library.js`)

**Update:** Ensure EPUB→RSVP conversion preserves Cyrillic/Greek characters.

### 7. Python Tool (`tools/epub_to_rsvp.py`)

**Update:** Ensure Python 3 handles UTF-8 correctly.

## Testing Plan

1. **Device tests:**
   - Display "Привет мир" (Hello world in Russian)
   - Display "Γειά σου κόσμε" (Hello world in Greek)
   - Read .rsvp file with Cyrillic text
   - Read .rsvp file with Greek text
2. **Integration tests:**
   - Convert Cyrillic EPUB to RSVP
   - Convert Greek EPUB to RSVP

## Success Criteria

- [ ] All 6 font headers regenerated with Cyrillic + Greek
- [ ] Build succeeds under 10 MB firmware size
- [ ] Display renders "Привет" correctly
- [ ] Display renders "Γειά" correctly
- [ ] Latin-1 characters (Č, ř, ž) still work
- [ ] ASCII text unchanged