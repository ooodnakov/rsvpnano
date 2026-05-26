// Native test for Cyrillic glyph lookup - no Arduino deps
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cassert>

// Stub Arduino types
#ifndef Arduino_h
#define __attribute__(x)
#define PROGMEM
typedef uint32_t uint32_t_t;  // Dummy
typedef int8_t int8_t_t;
typedef uint8_t uint8_t_t;
#endif

// Simulate PROGMEM access (just return pointer as-is for native test)
#define pgm_read_byte(x) (*(x))

// Include the font data directly
#include "../src/display/EmbeddedSerifFont.h"

struct TestGlyph {
    const uint8_t* bitmap;
    int8_t xOffset;
    uint8_t width;
    uint8_t xAdvance;
    uint8_t height;
};

// Simplified glyph lookup (Cyrillic only for this test)
TestGlyph test_glyphForCodepoint(uint32_t codepoint) {
    if (codepoint <= 0xFF) {
        const auto& g = kEmbeddedSerifGlyphs[codepoint];
        return {kEmbeddedSerifBitmaps + g.bitmapOffset, g.xOffset, g.width, g.xAdvance, kEmbeddedSerifHeight};
    }

    // Cyrillic: U+0400–U+04FF
    if (codepoint >= 0x0400 && codepoint <= 0x04FF) {
        size_t cyrillicIndex = codepoint - 0x0400;
        constexpr size_t latinGlyphCount = 255;  // Correct
        size_t glyphIndex = latinGlyphCount + cyrillicIndex;

        if (glyphIndex < (kEmbeddedSerifLastCyrillic - kEmbeddedSerifFirstCyrillic + 1) + latinGlyphCount) {
            const auto& g = kEmbeddedSerifGlyphs[glyphIndex];
            return {kEmbeddedSerifBitmaps + g.bitmapOffset, g.xOffset, g.width, g.xAdvance, kEmbeddedSerifHeight};
        }
    }

    const auto& g = kEmbeddedSerifGlyphs['?'];
    return {kEmbeddedSerifBitmaps + g.bitmapOffset, g.xOffset, g.width, g.xAdvance, kEmbeddedSerifHeight};
}

#if !defined(PIO_UNIT_TESTING)
int main() {
    printf("=== Cyrillic Glyph Lookup Test ===\n\n");
    printf("Font: kEmbeddedSerifHeight = %d\n", kEmbeddedSerifHeight);
    printf("Total glyphs: %lu\n\n", sizeof(kEmbeddedSerifGlyphs) / sizeof(kEmbeddedSerifGlyphs[0]));

    struct TestCase {
        uint32_t codepoint;
        const char* name;
    };

    TestCase tests[] = {
        {0x0410, "А"},
        {0x041F, "П"},
        {0x041C, "М"},
        {0x0422, "Т"},
        {0x0430, "а"},
        {0x043F, "п"},
    };

    printf("--- Testing Cyrillic Glyphs ---\n\n");

    for (const auto& t : tests) {
        auto glyph = test_glyphForCodepoint(t.codepoint);

        int nonZeroPixels = 0;
        for (int row = 0; row < glyph.height; row++) {
            for (int col = 0; col < glyph.width; col++) {
                uint8_t alpha = glyph.bitmap[row * glyph.width + col];
                if (alpha > 16) nonZeroPixels++;
            }
        }

        int firstActiveRow = -1, lastActiveRow = -1;
        for (int row = 0; row < glyph.height; row++) {
            bool hasPixels = false;
            for (int col = 0; col < glyph.width; col++) {
                if (glyph.bitmap[row * glyph.width + col] > 16) hasPixels = true;
            }
            if (hasPixels) {
                if (firstActiveRow < 0) firstActiveRow = row;
                lastActiveRow = row;
            }
        }

        printf("U+%04X %s: idx=%d, offset=%lu, w=%d, x_off=%d, advance=%d\n",
               t.codepoint, t.name,
               255 + (t.codepoint - 0x0400),
               (unsigned long)(glyph.bitmap - kEmbeddedSerifBitmaps),
               glyph.width, glyph.xOffset, glyph.xAdvance);
        printf("  height=%d, rows=[%d,%d], pixels=%d\n",
               glyph.height, firstActiveRow, lastActiveRow, nonZeroPixels);
        printf("  %s\n\n", firstActiveRow < 0 ? "FAIL: No data!" : "OK");
    }

    // Compare wrong vs correct
    printf("\n--- Wrong (80) vs Correct (255) ---\n\n");
    printf("For П (U+041F):\n");

    printf("  WRONG (index 111): ");
    const auto& g_wrong = kEmbeddedSerifGlyphs[111];
    int nz = 0;
    for (int i = 0; i < g_wrong.width * kEmbeddedSerifHeight; i++) {
        if (kEmbeddedSerifBitmaps[g_wrong.bitmapOffset + i] > 16) nz++;
    }
    printf("offset=%u, w=%d, pixels=%d -> %s\n",
           g_wrong.bitmapOffset, g_wrong.width, nz,
           nz > 0 ? "HAS DATA" : "EMPTY");

    printf("  CORRECT (index 286): ");
    const auto& g_correct = kEmbeddedSerifGlyphs[286];
    nz = 0;
    for (int i = 0; i < g_correct.width * kEmbeddedSerifHeight; i++) {
        if (kEmbeddedSerifBitmaps[g_correct.bitmapOffset + i] > 16) nz++;
    }
    printf("offset=%u, w=%d, pixels=%d -> %s\n",
           g_correct.bitmapOffset, g_correct.width, nz,
           nz > 0 ? "HAS DATA" : "EMPTY");

    return 0;
}
#endif
