# UTF-8 Support: Cyrillic + Greek

## Goal

Add Cyrillic (Russian, Ukrainian, Bulgarian) and Greek alphabet support to RSVP Nano firmware via UTF-8 encoding. Keep ASCII/Latin-1 backward compatible.

## Facts

See `facts.md` for shared understanding.

## Implementation Plan

See `plan.md` for detailed execution plan.

## Done Condition

- [x] All 6 font headers regenerated with Cyrillic + Greek glyphs
- [x] Build succeeds under 10 MB firmware size
- [ ] Display renders "Привет" correctly on device (needs hardware)
- [ ] Display renders "Γειά" correctly on device (needs hardware)
- [x] Latin-1 characters (Č, ř, ž) still work
- [x] ASCII text unchanged

## Notes

**Note:** Atkinson font uses NotoSans as fallback (real Atkinson Hyperlegible font download blocked by TLS). OpenDyslexic downloaded successfully.

**Build stats:**
- Flash: 41.7% (2.7MB)
- RAM: 22.9% (75KB)