# Cyrillic and Greek Support Review Report V2

Date: 2026-05-26

## Purpose

This report updates the previous handoff review after inspecting the current working-tree diff.
It covers the uncommitted implementation changes, current risks, and verification results.

## Current Diff Summary

Tracked modified files:

- `src/app/App.cpp`
- `src/app/App.h`
- `src/display/DisplayManager.cpp`
- `src/display/DisplayManager.h`
- `src/display/EmbeddedSerifFont.h`
- `src/main.cpp`
- `src/storage/StorageManager.cpp`
- `src/storage/StorageManager.h`
- `tools/generate_embedded_serif_font.py`

Untracked files:

- `.envrc`
- `CYRILLIC_GREEK_REVIEW_REPORT.md`
- `CYRILLIC_GREEK_REVIEW_REPORT_V2.md`
- `src/display/EmbeddedSerif70Font.h`
- `src/display/EmbeddedSerif70Font.h.bak`

High-level changes in the current diff:

- Adds a main-menu item to rebuild all book indexes.
- Adds `StorageManager::rebuildAllIndexes()`.
- Adds serial `download` command handling in `main.cpp`.
- Adds codepoint-based display draw helpers and updates several draw paths to decode UTF-8.
- Regenerates `EmbeddedSerifFont.h` with different source font metadata and metrics.
- Changes font generation to use glyph names for Unicode codepoints.
- Changes storage normalization/tokenization to preserve non-ASCII UTF-8 bytes.

## Latest Five Commits Still Relevant

The latest five commits inspected earlier remain the baseline for this review:

- `4bff6cb` docs: update goal and plan documentation
- `0cfcde8` fix: glyphForCodepoint() routes to correct font by typeface
- `0f430a6` feat: regenerate all fonts with Cyrillic and Greek glyphs
- `e3ed10c` feat: UTF-8 support for Cyrillic and Greek
- `acd73c4` update gitignore

The current report focuses on uncommitted changes on top of those commits.

## Current Implementation State

### Display

`DisplayManager.cpp` now has codepoint-aware draw helpers:

- `drawCodepointGlyph(...)`
- `drawSerifGlyphScaledCodepoint(...)`
- `drawSerifGlyphScaledPercentCodepoint(...)`

Several draw paths now decode UTF-8 with `utf8NextCodepoint()` before drawing:

- `drawSerifTextAt()`
- `drawSerifTextScaledAt()`
- `drawWordAt()`
- `drawRsvpWordScaledAt()`
- `drawRsvpWordScaledPercentAt()`

This is the right direction because layout and drawing are closer to using the same decoded
codepoint model.

### Storage

`StorageManager::normalizeDisplayText()` now preserves decoded non-ASCII UTF-8 bytes by copying
the original byte span from input to normalized output.

Tokenization was adjusted so:

- ASCII/control whitespace below `0x80` remains a word boundary.
- UTF-8 continuation bytes `0x80..0xBF` are treated as readable token characters.

This makes the generic storage path more likely to preserve Cyrillic and Greek text.

### App and Index Rebuild

The current diff adds a `Rebuild index` main-menu item that calls
`StorageManager::rebuildAllIndexes()`. That method removes existing `.rdat`/`.ridx` files for
each book and rebuilds the indexed representation.

This is useful for migrating existing books after text normalization behavior changes.

### Fonts

`src/display/EmbeddedSerifFont.h` has been regenerated. Notable visible changes:

- Source font metadata changed from `NotoSans at 52 pt` to `NotoSans-Regular at 28 pt`.
- `kEmbeddedSerifHeight` changed from `62` to `41`.
- The diff is very large because bitmap data and glyph metrics changed.

This may be intentional, but it is a major visual/metric change and needs on-device validation.

## Findings

### 1. High: Glyph offset bug is still present

Location:

- `src/display/DisplayManager.cpp`, `glyphForCodepoint()`

Current code:

```cpp
constexpr size_t latinGlyphCount = 255;
size_t glyphIndex = latinGlyphCount - 1 + cyrillicIndex;
```

Problem:

The generated glyph array has 255 Latin/custom glyphs for slots `0x01..0xFF`, indexed
`0..254`. The first Cyrillic glyph starts at index `255`, not index `254`.

Using `latinGlyphCount - 1` keeps the previous off-by-one bug:

- `U+0400` still maps to slot `0xFF`.
- `U+0401` maps to `U+0400`.
- All Cyrillic glyphs are shifted by one.
- Greek inherits the same shift because it starts from `latinGlyphCount - 1 + 256`.

Required fix:

```cpp
size_t glyphIndex = latinGlyphCount + cyrillicIndex;
```

For Greek:

```cpp
size_t glyphIndex = latinGlyphCount + cyrillicGlyphCount + greekIndex;
```

The upper-bound checks should use the same base:

```cpp
glyphIndex < latinGlyphCount + cyrillicGlyphCount
glyphIndex < latinGlyphCount + cyrillicGlyphCount + greekGlyphCount
```

Better still, compute `latinGlyphCount` from each font header instead of hardcoding `255`.

### 2. High: Multi-character literals in transliteration code

Location:

- `src/storage/StorageManager.cpp`, Cyrillic and Greek approximations

Examples:

```cpp
target += 'CH';
target += 'TH';
```

Problem:

These are multi-character integer literals, not strings. Appending them to `String` will not
append the intended text. Depending on overload resolution and compiler behavior, this can
append a truncated byte or unintended numeric value.

Required fix:

Use existing `appendText()` for multi-character approximations:

```cpp
appendText(target, "CH");
appendText(target, "TH");
```

Search for all multi-character literals in `StorageManager.cpp`, not just the two examples.

### 3. High: 70-size RSVP drawing is still byte-based

Location:

- `src/display/DisplayManager.cpp`, `drawRsvp70WordAt()`

Problem:

Most main draw paths were moved toward UTF-8 decoding, but `drawRsvp70WordAt()` still loops
over `word[i]`, calls `glyph70For(word[i], typeface)`, and draws bytes directly.

Impact:

- Any reader mode that uses the 70-size path still renders Cyrillic/Greek UTF-8 as raw bytes.
- Focus highlighting remains byte-indexed in this path.
- The regenerated 70-size fonts may contain Cyrillic/Greek glyphs, but this path cannot reach
  them through codepoint lookup.

Required fix:

- Add `glyph70ForCodepoint()`.
- Add a codepoint-aware 70-size draw helper.
- Update `serif70WordLayout()` and `drawRsvp70WordAt()` to decode UTF-8 and use decoded
  character ordinals.

### 4. Medium: Decoded loops still use byte length for tracking end conditions

Locations:

- `src/display/DisplayManager.cpp`, decoded loops in layout and drawing

Problem:

The loops now increment `charIndex`, but calls like this still pass `word.length()`:

```cpp
trackedAdvance(glyph.xAdvance, charIndex, word.length());
trackedAdvanceScaled(glyph.xAdvance, divisor, charIndex, word.length());
trackedAdvanceScaledPercent(glyph.xAdvance, scalePercent, charIndex, word.length());
```

`word.length()` is a byte count. For UTF-8 text, it is larger than decoded character count.

Impact:

- Tracking can be applied after the final decoded character because `charIndex + 1` is still
  less than the byte length.
- Layout width and drawing width may include extra tracking for non-ASCII words.
- The issue is more visible for all-Cyrillic/all-Greek words, where every character is
  multi-byte.

Required fix:

- Count decoded codepoints once per string and pass decoded character count to tracking helpers.
- Or change the tracking helpers to take `hasNextCharacter` instead of index and length.

The second option is less error-prone:

```cpp
int trackedAdvanceForNext(int advance, bool hasNext)
```

### 5. Medium: Focus index is not fully fixed for Cyrillic/Greek

Location:

- `src/display/DisplayManager.cpp`, `findFocusLetterIndex()`

Problem:

The current diff changes draw loops to compare focus against decoded `charIndex`, but
`findFocusLetterIndex()` still uses raw byte iteration and `LatinText::isWordCharacter()`.

Impact:

- Cyrillic and Greek words still generally fall back to focus index `0`.
- The returned focus value is not reliably a decoded character ordinal.
- Draw paths that now compare against decoded `charIndex` can still receive a byte-derived
  index.

Required fix:

- Decode UTF-8 in `findFocusLetterIndex()`.
- Treat Cyrillic `U+0400..U+04FF` and Greek `U+0370..U+03FF` as word characters.
- Return a decoded character ordinal.

### 6. Medium: EPUB conversion still needs review

Location:

- `src/storage/EpubConverter.cpp`

Problem:

The current diff updates `StorageManager.cpp` but does not show a corresponding update to
`EpubConverter.cpp`. The previous review found that EPUB conversion drops unrecognized
non-Latin codepoints through `appendDisplayApproximation()`.

Impact:

- Generic text import may preserve Cyrillic/Greek.
- On-device EPUB conversion may still strip Cyrillic/Greek before storage.

Required fix:

- Apply the same preservation policy to EPUB normalization:
  preserve original UTF-8 byte spans for Cyrillic and Greek codepoints.
- Add tests or a small conversion fixture for Cyrillic/Greek EPUB content.

### 7. Medium: Regenerated serif font metrics changed substantially

Location:

- `src/display/EmbeddedSerifFont.h`

Problem:

The regenerated font changed source metadata and metrics:

- From `NotoSans at 52 pt`
- To `NotoSans-Regular at 28 pt`
- Height changed from `62` to `41`

Impact:

- Text size, centering, anchor position, line height, and visual balance can change across the
  reader UI.
- Flash usage dropped in the build, which is consistent with smaller glyph data, but that also
  means the display may no longer match the intended typography.

Required validation:

- Confirm whether the point-size change is intentional.
- Check on-device screenshots for main RSVP, scaled RSVP, scroll view, menus, and library list.
- If unintended, regenerate with the intended point size and source font.

### 8. Low: New backup/generated files are untracked

Location:

- `src/display/EmbeddedSerif70Font.h`
- `src/display/EmbeddedSerif70Font.h.bak`

Problem:

Both files are untracked. The `.bak` file especially looks like a local generation artifact.

Recommendation:

- Decide whether `EmbeddedSerif70Font.h` is the intended canonical header or a stray duplicate.
- Do not commit `.bak` unless there is a specific project convention for keeping generated
  backups.
- If generation produces `.bak`, add it to `.gitignore` or change the generator.

### 9. Low: Serial download command changes boot/runtime behavior

Location:

- `src/main.cpp`

Problem:

The loop now reads serial input and reboots to download mode when it receives `download`.
This is useful for development, but it is unrelated to Cyrillic/Greek support.

Recommendation:

- Keep it only if it is intentional for this branch.
- Consider guarding it behind a compile-time development flag if not meant for production.

## Recommended Fix Sequence

1. Fix glyph index bases:
   - Replace `latinGlyphCount - 1` with `latinGlyphCount`.
   - Update all corresponding upper-bound checks.
   - Prefer computed font-specific Latin/Cyrillic/Greek counts.

2. Fix transliteration multi-character literals:
   - Replace every `target += 'XX'` with `appendText(target, "XX")`.
   - Search the whole repo for multi-character literals in text paths.

3. Normalize decoded draw/layout iteration:
   - Introduce a small decoded iteration helper that provides codepoint, byte span, decoded
     ordinal, and `hasNext`.
   - Use decoded character count or `hasNext` for tracking.

4. Finish 70-size Unicode support:
   - Add `glyph70ForCodepoint()`.
   - Update 70-size layout and draw paths.

5. Fix focus selection:
   - Decode UTF-8 in `findFocusLetterIndex()`.
   - Return decoded ordinal.
   - Classify Cyrillic/Greek as word characters.

6. Update EPUB conversion:
   - Preserve Cyrillic/Greek UTF-8 byte spans in `EpubConverter`.
   - Keep punctuation and Latin approximation behavior unchanged.

7. Decide what to do with font regeneration:
   - Confirm the `52 pt` to `28 pt` change.
   - Remove or ignore generated backup files.

8. Add targeted tests:
   - Glyph index mapping for first/last Cyrillic and Greek.
   - UTF-8 RSVP layout/draw consistency.
   - Focus index for Cyrillic/Greek.
   - Storage normalization for Cyrillic/Greek.
   - EPUB conversion preservation.

## Suggested Acceptance Tests

### Display

- `Привет`
- `Москва`
- `κόσμος`
- `Αθήνα`

For each:

- Layout width equals draw advancement.
- One decoded character maps to one glyph lookup.
- The selected focus character is a decoded character, not a UTF-8 byte.
- Standard, OpenDyslexic, and AtkinsonHyperlegible use their own glyph arrays.

### Glyph Indexing

Check these mappings:

- `U+0400` maps to the first Cyrillic glyph.
- `U+0401` maps to the second Cyrillic glyph.
- `U+04FF` maps to the last Cyrillic glyph.
- `U+0370` maps to the first Greek glyph.
- `U+03FF` maps to the last Greek glyph.

### Storage

Input:

```text
Hello Привет κόσμος
```

Expected:

- Three readable tokens.
- Cyrillic and Greek UTF-8 byte sequences preserved.
- No malformed UTF-8 stats for valid input.

### EPUB Conversion

Input EPUB text fragment:

```text
Привет — κόσμος
```

Expected:

- Cyrillic and Greek text preserved.
- Dash normalization remains as intended.
- No silent dropping of supported script codepoints.

## Verification Performed

### Native tests

Command:

```sh
rtk platformio test -e native_test
```

Result:

- Passed.
- 59 test cases succeeded.

### Firmware build

Command:

```sh
rtk platformio run -e waveshare_esp32s3_usb_msc
```

Result:

- Passed.
- RAM usage: 75,108 bytes of 327,680 bytes, 22.9%.
- Flash usage: 2,811,117 bytes of 6,553,600 bytes, 42.9%.

Build passing does not clear the functional issues above. The current tests do not cover
Cyrillic/Greek glyph indexing, UTF-8 drawing, focus selection, or EPUB conversion preservation.

## Handoff Summary

The current diff makes meaningful progress over the earlier state by adding codepoint-aware
draw helpers and preserving non-ASCII UTF-8 in the generic storage path. The implementation is
still not ready to call complete.

The next engineer should fix the glyph index base first, because all Cyrillic/Greek rendering
depends on it. Then fix the multi-character literal bugs, finish 70-size rendering, and make
focus/tracking use decoded character semantics consistently. Finally, update EPUB conversion
and validate the regenerated font size change on-device.
