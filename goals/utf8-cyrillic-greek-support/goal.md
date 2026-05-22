# UTF-8 Support: Cyrillic + Greek

## Goal

Add Cyrillic (Russian, Ukrainian, Bulgarian) and Greek alphabet support to RSVP Nano firmware via UTF-8 encoding. Keep ASCII/Latin-1 backward compatible.

## Facts

See `facts.md` for shared understanding.

## Implementation Plan

See `plan.md` for detailed execution plan.

## Done Condition

- [ ] All 6 font headers regenerated with Cyrillic + Greek glyphs
- [ ] Build succeeds under 10 MB firmware size
- [ ] Display renders "Привет" correctly on device
- [ ] Display renders "Γειά" correctly on device
- [ ] Latin-1 characters (Č, ř, ž) still work
- [ ] ASCII text unchanged