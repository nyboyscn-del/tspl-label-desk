# Compatibility testing

Compatibility is recorded per printer, firmware, DPI, driver/RAW path, and profile. A brand keyword may suggest a profile but never changes its verification status. See the [current compatibility matrix](compatibility-matrix.md).

1. Generate `polarity-check.png` and `polarity-check.tspl` without printing.
2. Inspect pure black/white blocks, checkerboard, one-dot diagonal, Chinese sample, ruler edges, and the native Code128 command separately.
3. Print only with explicit `--print --printer` after selecting the queue.
4. Record printer model and firmware, DPI, media dimensions, command path, output hashes, measured dimensions, photos, and operator/date in a separate private evidence record.
5. Promote a profile only after visual and physical measurement review. Without photo/measurement evidence, status remains `SOFTWARE_TESTED` or `UNVERIFIED`.

The app's 1-bit glyph masks use set pixels as foreground. It packs bits MSB-first, pads each row to a whole byte, then applies the established internal mask-to-TSPL polarity conversion (`bitmap_invert: true`). This default matches the sanitized legacy 203-DPI golden output byte-for-byte. It is an encoding conversion, not a TSC-brand or model-specific workaround. `bitmap_invert: false` remains available only as an explicit profile setting; changing it changes the raw BITMAP bytes. Golden-byte agreement does not establish how every printer firmware physically renders those bytes, so hardware compatibility remains per-profile and unverified until measured. At 203-class DPI, `dots_per_mm=8` preserves the legacy 203.2 DPI raster grid; at 300 DPI, the conversion is `dpi / 25.4`.

Native `QRCODE` uses unquoted ECC and mode parameters (for example, `H,5,A,0,"content"`) per the TSC TSPL programming manual. The sanitized legacy QR fixture retains its older quoted parameters for comparison; the current output intentionally differs because that form left the QR area blank in the 2026-10-29 TTP-244 Pro physical test. This command correction does not change bitmap golden bytes.

The corrected synthetic 203-DPI test card subsequently printed Chinese text, Code128, and a visible QR on the same TTP-244 Pro. The operator reported media measured at approximately 60 × 40 mm. Firmware version, exact printed-ruler dimensions, symbol scan decoding, and the fine single-dot pattern remain unverified; this observation does not promote the generic profile to hardware-verified compatibility.

New profiles use `config_version: 2` and default to `bitmap_invert: true`. An existing profile is migrated only when its entire contents exactly match the known prior generated default; the original JSON is copied to a content-hash-named `.bak` before the polarity and version fields are updated. Other existing profiles keep their selected polarity and settings; no saved printer configuration is replaced by the default.

Calibration values under `profile.json` are the single authoritative source. `paper.json` is retained as a compatibility mirror for the existing UI/API. If an older installation has different values in the two files, startup saves the old `paper.json` to a content-hash-named backup before synchronizing the mirror from Profile. Calibration updates write both files; profile updates preserve the existing authoritative calibration values.
