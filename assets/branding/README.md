# Project icon

[Editable SVG](sid-song-crafter.svg) · [512 × 512 WebP](sid-song-crafter.webp)

The icon combines a microchip, a musical note with a pulse-wave beam, and three colored accents for the SID's three voices. It uses vector paths without external fonts or linked images. The dark tile keeps its contrast on light and dark README backgrounds; the rounded corners are transparent.

Rebuild the lossless WebP with `rsvg-convert` and `cwebp` (Homebrew packages `librsvg` and `webp`), from the repository root:

```sh
mkdir -p build/branding
rsvg-convert assets/branding/sid-song-crafter.svg -o build/branding/sid-song-crafter.png
cwebp -lossless -exact -m 6 build/branding/sid-song-crafter.png -o assets/branding/sid-song-crafter.webp
```
