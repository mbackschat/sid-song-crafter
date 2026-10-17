# Project icon

[Editable SVG](sid-song-crafter.svg) · [512 × 512 WebP](sid-song-crafter.webp)

The selected C64 rainbow-chip design combines outlined C64/SID lettering, a continuous musical note and pulse wave, five badge-inspired color bands and a transparent surround. The SVG uses solid vector shapes without embedded bitmaps, fonts or external resources. README displays the compact SVG at 144 pixels; the lossless WebP provides a raster alternative.

The lettering is custom geometry inspired by the C64 hardware badge. Colors are deliberate badge-inspired web approximations, not a claimed exact VIC-II palette. See the [visual-identity research](../../docs/research/visual-identity/README.md) for sources, concepts and the selection. The design was visually checked at 512 and 144 pixels.

Rebuild the lossless WebP with `rsvg-convert` and `cwebp` (Homebrew packages `librsvg` and `webp`), from the repository root:

```sh
mkdir -p build/branding
rsvg-convert assets/branding/sid-song-crafter.svg -o build/branding/sid-song-crafter.png
cwebp -lossless -exact -m 6 build/branding/sid-song-crafter.png -o assets/branding/sid-song-crafter.webp
```
