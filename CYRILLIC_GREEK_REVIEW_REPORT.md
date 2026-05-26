# Cyrillic and Greek Support Review Report

Date: 2026-05-26

## Purpose

This report reviews the latest five commits and the current implementation state for Cyrillic
and Greek support in RSVP Nano. It is intended as a handoff document for the next engineer to
fix and verify the remaining implementation gaps without repeating the investigation.

## Latest Five Commits Reviewed

### `4bff6cb` docs: update goal and plan documentation

Changed files:

- `goals/utf8-cyrillic-greek-support/goal.md`
- `goals/utf8-cyrillic-greek-support/plan.md`

Summary:

- Documentation-only update to the UTF-8 Cyrillic/Greek goal and plan.

### `0cfcde8` fix: glyphForCodepoint() routes to correct font by typeface

Changed files:

- `src/display/DisplayManager.cpp`

Summary:

- Updated Unicode glyph lookup so `glyphForCodepoint()` selects glyph arrays based on the
  active reader typeface instead of always returning serif glyphs.
- This is directionally correct, but the current glyph index math is still wrong by one.

### `0f430a6` feat: regenerate all fonts with Cyrillic and Greek glyphs

Changed files:

- `src/display/EmbeddedAtkinsonFont.h`
- `src/display/EmbeddedAtkinsonFont70.h`
- `src/display/EmbeddedOpenDyslexicFont.h`
- `src/display/EmbeddedOpenDyslexicFont70.h`
- `src/display/EmbeddedSerifFont70.h`
- `tools/AtkinsonHyperlegible-Regular.ttf`
- `tools/NotoSans-Regular.ttf`
- `tools/OpenDyslexic-Regular.otf`

Summary:

- Regenerated embedded font headers and added source font files.
- Generated headers now advertise Cyrillic `U+0400..U+04FF` and Greek `U+0370..U+03FF`
  ranges for the main and 70-size typefaces.

### `e3ed10c` feat: UTF-8 support for Cyrillic and Greek

Changed files:

- `goals/utf8-cyrillic-greek-support/goal.md`
- `goals/utf8-cyrillic-greek-support/plan.md`
- `src/display/DisplayManager.cpp`
- `src/display/EmbeddedSerifFont.h`
- `src/text/LatinText.h`
- `tools/generate_embedded_serif_font.py`

Summary:

- Added UTF-8 helper functions and Cyrillic/Greek constants.
- Added codepoint-based display layout lookup.
- Updated font generator to emit Cyrillic and Greek glyph ranges.

### `acd73c4` update gitignore

Changed files:

- `.gitignore`

Summary:

- Unrelated gitignore update.

## Current Implementation State

### Font Data

Generated font headers include these ranges:

- Latin/custom byte slots: `0x01..0xFF`
- Cyrillic: `U+0400..U+04FF`
- Greek: `U+0370..U+03FF`

The generated glyph array layout is:

1. 255 Latin/custom byte glyphs for `0x01..0xFF`
2. 256 Cyrillic glyphs for `U+0400..U+04FF`
3. 144 Greek glyphs for `U+0370..U+03FF`

Evidence:

- `src/display/EmbeddedSerifFont.h` declares `kEmbeddedSerifFirstChar = 1` and
  `kEmbeddedSerifLastChar = 255`.
- The last Latin slot, `0xFF`, appears immediately before the first Cyrillic glyph.
- The first Cyrillic glyph is `U+0400`, then Greek starts after the 256 Cyrillic entries.

### UTF-8 Decoding

`src/display/DisplayManager.cpp` now has a local `utf8NextCodepoint()` helper that decodes
ASCII and 2-, 3-, and 4-byte UTF-8 sequences. Invalid or truncated sequences fall back to
one raw byte.

`src/text/LatinText.h` also defines `LatinTextUtf8` helper functions. These are not currently
the shared source of truth for `DisplayManager.cpp`, so UTF-8 decode behavior is duplicated.

### Layout

`serifWordLayout()` and `serifWordLayoutScaledPercent()` decode UTF-8 into codepoints before
looking up glyph metrics. This means width and anchor calculations are partially Unicode-aware
for the main scaled RSVP paths.

However, the implementation still passes byte length as the word length into tracking helpers.
This can make spacing decisions treat a UTF-8 word as longer than its decoded character count.

### Drawing

The main RSVP draw paths still iterate raw bytes and call byte-based glyph APIs:

- `DisplayManager::drawWordAt()`
- `DisplayManager::drawRsvpWordScaledAt()`
- `DisplayManager::drawRsvp70WordAt()`
- `DisplayManager::drawRsvpWordScaledPercentAt()`

As a result, Cyrillic and Greek text may be measured as Unicode glyphs but rendered as raw
UTF-8 bytes. That causes incorrect glyphs or fallback glyphs on screen.

### Storage and Tokenization

`src/storage/StorageManager.cpp` now preserves non-ASCII decoded UTF-8 bytes in
`normalizeDisplayText()`. Its tokenization treats bytes `0x80..0xBF` as readable token
characters and avoids treating UTF-8 continuation bytes as word boundaries.

This preserves many Cyrillic/Greek byte sequences through the generic storage path, but the
logic is byte-based and does not validate complete codepoint membership while tokenizing.

### EPUB Conversion

`src/storage/EpubConverter.cpp` still normalizes display text by mapping decoded codepoints
through `appendDisplayApproximation()`. That helper only preserves ASCII, known Latin storage
bytes, and selected punctuation. Unknown non-Latin codepoints return without appending text.

With `RSVP_ON_DEVICE_EPUB_CONVERSION=1`, Cyrillic and Greek EPUB content can be dropped during
conversion before it reaches the display path.

## Findings

### 1. High: Unicode glyph lookup is off by one

Location:

- `src/display/DisplayManager.cpp`, in `glyphForCodepoint()`

Problem:

The code uses `254` as the offset from the start of the glyph array to the Cyrillic block:

```cpp
size_t glyphIndex = 254 + cyrillicIndex;
```

But the generated Latin/custom range is `0x01..0xFF`, which is 255 glyphs. The first Cyrillic
glyph starts after slot `0xFF`, not after slot `0xFE`.

Impact:

- `U+0400` maps to the glyph for byte slot `0xFF`.
- `U+0401` maps to `U+0400`.
- Every Cyrillic glyph is shifted by one.
- Greek also starts one glyph too early because it uses `254 + 256 + greekIndex`.

Recommended fix:

- Replace hardcoded offsets with computed glyph counts:

```cpp
constexpr size_t latinGlyphCount =
    static_cast<size_t>(kEmbeddedSerifLastChar - kEmbeddedSerifFirstChar + 1);
```

- Use the corresponding count for each typeface:
  `kEmbeddedOpenDyslexicLastChar - kEmbeddedOpenDyslexicFirstChar + 1`,
  `kEmbeddedAtkinsonLastChar - kEmbeddedAtkinsonFirstChar + 1`, and serif equivalents.
- Use `latinGlyphCount + cyrillicIndex` for Cyrillic.
- Use `latinGlyphCount + cyrillicGlyphCount + greekIndex` for Greek.

Acceptance test:

- Verify that `glyphForCodepoint(0x0400, typeface)` indexes the glyph commented as
  `U+0400 Cyrillic`, not slot `0xFF`.
- Verify that `glyphForCodepoint(0x0370, typeface)` indexes the glyph commented as
  `U+0370 Greek`.

### 2. High: RSVP draw paths render UTF-8 byte-by-byte

Locations:

- `src/display/DisplayManager.cpp`, `DisplayManager::drawWordAt()`
- `src/display/DisplayManager.cpp`, `DisplayManager::drawRsvpWordScaledAt()`
- `src/display/DisplayManager.cpp`, `DisplayManager::drawRsvp70WordAt()`
- `src/display/DisplayManager.cpp`, `DisplayManager::drawRsvpWordScaledPercentAt()`

Problem:

Layout functions decode UTF-8 codepoints, but draw functions still iterate `word[i]` as bytes
and call `glyphFor(word[i], typeface)` or `glyph70For(word[i], typeface)`.

Impact:

- A Cyrillic or Greek character is rendered as two separate bytes.
- The bytes are looked up as Latin/custom slots or fallback ASCII.
- Width/anchor computation and actual rendered output disagree.
- Focus highlighting can apply to a byte instead of a decoded character.

Recommended fix:

- Add codepoint-aware drawing helpers:
  - `drawGlyphForCodepoint(...)`
  - `drawSerifGlyphScaledForCodepoint(...)`
  - `drawSerifGlyphScaledPercentForCodepoint(...)`
  - 70-size equivalents if the 70-size RSVP path must support Cyrillic/Greek.
- Refactor RSVP draw loops to use `utf8NextCodepoint()` and a decoded character ordinal.
- Use decoded character count, not byte length, for tracking decisions.
- Keep byte-based draw helpers only for legacy ASCII/custom single-byte paths.

Acceptance test:

- Render a word like `Привет` and confirm each Cyrillic codepoint results in one glyph lookup
  and one draw operation.
- Render a word like `κόσμος` and confirm Greek codepoints use the Greek glyph block.
- Confirm x-position advancement matches layout width for the same word.

### 3. Medium: Focus letter selection is byte/Latin-only

Location:

- `src/display/DisplayManager.cpp`, `findFocusLetterIndex()`

Problem:

`findFocusLetterIndex()` loops over raw bytes and calls `LatinText::isWordCharacter()`.
That classifier is designed for ASCII and legacy Latin/custom byte slots, not decoded
Cyrillic or Greek codepoints.

Impact:

- Cyrillic and Greek words usually have zero recognized word characters.
- The function falls back to index `0` for non-empty words.
- ORP/focus behavior is not meaningful for Cyrillic/Greek.
- The returned index is a byte index, while UTF-8-aware layout code compares focus against a
  decoded character ordinal.

Recommended fix:

- Introduce a decoded-codepoint focus function.
- Treat Cyrillic and Greek codepoints as word characters for focus placement.
- Return a decoded character ordinal for use by the UTF-8-aware layout and draw loops.
- Keep legacy behavior for ASCII and existing Latin custom slots.

Acceptance test:

- For a 6-character Cyrillic word, focus should not always be `0`; it should follow the same
  ORP ordinal rules as Latin words.
- For mixed punctuation plus Cyrillic/Greek, focus should skip punctuation and choose a decoded
  word character.

### 4. Medium: On-device EPUB conversion drops Cyrillic and Greek

Location:

- `src/storage/EpubConverter.cpp`, `normalizeDisplayText()`
- `src/storage/EpubConverter.cpp`, `appendDisplayApproximation()`

Problem:

`normalizeDisplayText()` decodes UTF-8 but always calls `appendDisplayApproximation()`.
That helper returns without appending for most codepoints outside ASCII, known Latin storage
bytes, and selected punctuation.

Impact:

- Cyrillic and Greek text in EPUBs converted on device can be removed before storage/display.
- This differs from `StorageManager::normalizeDisplayText()`, which preserves non-ASCII decoded
  UTF-8 bytes.

Recommended fix:

- Mirror the `StorageManager` preservation behavior for supported non-ASCII scripts.
- For decoded codepoints in Cyrillic `U+0400..U+04FF` or Greek `U+0370..U+03FF`, append the
  original UTF-8 bytes from the input.
- Continue approximating unsupported punctuation and Latin codepoints as before.

Acceptance test:

- Normalize an EPUB text fragment containing `Привет κόσμος`.
- Confirm the normalized output still contains the original Cyrillic and Greek UTF-8 bytes.
- Confirm existing punctuation normalization tests still pass.

### 5. Low: UTF-8 helpers are duplicated and partially unused

Locations:

- `src/display/DisplayManager.cpp`, local `utf8NextCodepoint()`
- `src/text/LatinText.h`, `LatinTextUtf8`

Problem:

UTF-8 decode/encode helpers exist in `LatinTextUtf8`, but `DisplayManager.cpp` uses its own
local decoder. This raises the risk of inconsistent handling for malformed sequences and future
script additions.

Recommended fix:

- Prefer one shared UTF-8 decode helper in `LatinText.h` or another common text utility.
- Have display, storage, EPUB conversion, and reader logic use the same decoder where practical.

## Recommended Implementation Sequence

1. Fix glyph array indexing first.
   This is small and removes a deterministic rendering bug.

2. Add shared decoded-codepoint iteration helpers.
   The display code needs decoded character ordinal, byte offset, consumed byte count, and
   codepoint.

3. Update RSVP layout and draw to use the same decoded iteration.
   Layout and drawing must use the same glyph lookup, tracking count, and focus ordinal.

4. Update focus selection for Cyrillic/Greek.
   Use decoded codepoints and classify Cyrillic/Greek as word characters.

5. Update on-device EPUB conversion preservation.
   Preserve supported script codepoints instead of dropping them during normalization.

6. Add focused tests.
   Native tests currently cover Latin pacing well, but do not cover the Cyrillic/Greek paths.

## Suggested Tests

### Glyph Index Tests

- Assert that the Cyrillic block starts after exactly `lastChar - firstChar + 1` Latin glyphs.
- Assert `U+0400`, `U+0401`, and `U+04FF` map to the expected Cyrillic indexes.
- Assert `U+0370`, `U+0391`, `U+03B1`, and `U+03FF` map to the expected Greek indexes.
- Run the checks for Standard, OpenDyslexic, and AtkinsonHyperlegible.

### UTF-8 Rendering Tests

- Use words:
  - `Привет`
  - `Москва`
  - `κόσμος`
  - `Αθήνα`
- Verify decoded character count is used for tracking and focus.
- Verify each decoded character produces one glyph draw operation.
- Verify rendered width and layout width match.

### Focus Tests

- Verify Latin behavior is unchanged.
- Verify Cyrillic and Greek words choose a non-byte-based focus ordinal.
- Verify leading/trailing punctuation does not become the focus for Cyrillic/Greek words.

### EPUB Conversion Tests

- Verify `EpubConverter::normalizeDisplayText()` preserves Cyrillic and Greek UTF-8.
- Verify unsupported scripts keep the existing fallback/drop behavior unless explicitly
  expanded.
- Verify punctuation normalization still maps dashes, quotes, ellipses, and non-breaking spaces
  as before.

### Storage Tests

- Verify `StorageManager::normalizeDisplayText()` preserves valid Cyrillic/Greek UTF-8.
- Verify malformed UTF-8 still increments malformed stats and does not corrupt token output.
- Verify a mixed line such as `Hello Привет κόσμος` becomes three readable tokens.

## Verification Performed

### Native tests

Command:

```sh
rtk platformio test -e native_test
```

Result:

- Passed.
- 59 test cases succeeded.

Note:

- The first run failed because the sandbox could not write to `/home/odnakov/.platformio`.
- The command was rerun with approved PlatformIO access and passed.

### Firmware build

Command:

```sh
rtk platformio run -e waveshare_esp32s3_usb_msc
```

Result:

- Passed.
- RAM usage: 75,108 bytes of 327,680 bytes, 22.9%.
- Flash usage: 3,277,325 bytes of 6,553,600 bytes, 50.0%.

## Current Worktree Note

At review time, the worktree already contained unrelated local modifications and untracked
files:

- `src/app/App.cpp`
- `src/app/App.h`
- `src/display/EmbeddedSerifFont.h`
- `src/main.cpp`
- `src/storage/StorageManager.cpp`
- `src/storage/StorageManager.h`
- `tools/generate_embedded_serif_font.py`
- `.envrc`
- `src/display/EmbeddedSerif70Font.h`

This report does not attempt to classify those changes as part of the latest five commits.
The next engineer should check current `git status` and avoid reverting unrelated local work.

## Handoff Summary

The project has most of the raw ingredients for Cyrillic and Greek support: generated glyph
data, UTF-8 decoding, and partial layout support. It is not complete yet. The two most important
fixes are:

1. Correct the Unicode glyph index offsets from `254` to computed Latin glyph counts.
2. Make the RSVP draw paths decode UTF-8 codepoints instead of rendering raw bytes.

After that, focus selection and EPUB conversion should be updated so Cyrillic/Greek input is
preserved end to end and aligned correctly on screen.
