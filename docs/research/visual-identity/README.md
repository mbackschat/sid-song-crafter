# C64 visual identity and SID Song Crafter icon

Research date: 2026-10-17. Status: direction A and its vector redraw are accepted and installed. The user wants both SID and C64 recognition, a retro feel, and priority for C64 palette, logo colors and lettering style. The subsequent instruction is to show samples, ask for guidance and make no commit. The user subsequently authorized replacing both canonical logo assets and the README icon, then authorized committing and pushing the completed updates.

## Findings

| Element | Evidence | Design consequence |
| --- | --- | --- |
| Hardware badge | The [archived Commodore 64 badge](https://commons.wikimedia.org/wiki/File:Commodore_64.svg) identifies the Commodore Business Machines original and later vectorization: wide geometric lettering, 64 and horizontal rainbow bands. The [Harvard collection record](https://chsi.emuseum.com/objects/20698/commodore-64-computer-and-commodore-1541-disk-drive) independently describes white lettering around a raised rainbow band; its search record was accessible, but the full page returned 403. | Combine recognizable C64 lettering and a restrained rainbow stripe with a sound-chip symbol. Badge colors are distinct from screen colors. |
| Screen palette | [Pepto's VIC-II analysis](https://www.pepto.de/projects/colorvic/) explains sixteen colors generated through analog luminance/chrominance and display variation. [Colodore](https://www.colodore.com/) supplies a revised model and display controls. | Name the digital approximation; there is no single hardware-authored sRGB specification. Generated colors are not automatically exact palette colors. |
| Explicit RGB reference | The [VICE Colodore PAL palette](https://raw.githubusercontent.com/VICE-Team/svn-mirror/main/vice/data/C64/colodore.vpl), inspected on the research date, supplies RGB entries. | Screen concept: blue `#2724C4`, light blue `#6864FF`, white `#FFFFFF`, black `#000000`. Available accents include red `#96282E`, green `#41B936`, yellow `#EFF347`, cyan `#5BD6CE`. These are inspected emulator-palette values, not corporate logo specifications. |
| Screen typography | [Style's C64 font documentation](https://style64.org/c64-truetype) distinguishes proportional C64 Pro and C64 Pro Mono and documents 304 unique C64 glyphs. | A chunky character-grid treatment communicates the screen aesthetic. Generated approximation is not exact ROM typography. |
| Badge typography | The archived badge has wide, low geometric letterforms. A [community font identification](https://www.dafont.com/forum/read/292735/font-used-in-commodore-64-logo) suggests Microgramma Bold Extended; that is not a primary manufacturing specification. | Request visible extended, squared-round forms. Do not claim an exact font identification or bundle a commercial font. This style differs from the screen's pixel font. |
| SID/music | The project's [hardware reference](../sid/hardware.md) owns the synthesis facts. The current icon combines a chip and musical note without a distinctive C64 cue. | Preserve a simple chip/music relationship, introduce explicit C64 recognition, and use pulse-wave geometry. |

The hardware badge and display are separate visual sources. The samples compare those treatments. The rainbow colors are visual approximations, not verified historic ink specifications. Palette hex values guide generation; the samples are not quantized hardware-compatible C64 graphics. Exact color tokens, glyph outlines and small-size legibility will be settled after a direction is selected.

## Sample directions

| Sample | Direction | Judgment |
| --- | --- | --- |
| A — Rainbow sound chip | Dark chip badge, broad C64-style lettering, musical note/pulse form, horizontal rainbow accents. | Recommended starting point: balances C64 recognition, SID/music and icon simplicity. |
| B — Blue-screen music | Blue/light-blue frame, chunky screen-style letters, pixel note and stepped waveform. | Strong software/8-bit identity; less emphasis on the physical machine. |
| C — Breadbin badge | Warm case-color surround, dark sound chip, wide lettering and rainbow badge accent. | Strong hardware nostalgia; enclosure details may need simplification at small sizes. |

These are project-icon concepts, not a replacement Commodore corporate logo. No copied badge asset or third-party font is bundled.

## Generation and review

Use the built-in image-generation tool, not the API fallback. Retain the exact prompt in [concept-prompt.md](concept-prompt.md) and the local review sheet under `build/branding-review/`. The initial review kept the existing branding unchanged while the user selected a direction. The accepted vector redraw now owns the [branding assets](../../../assets/branding/README.md). The subsequent push instruction authorizes committing and publishing the selected assets and research.

The first generated sheet is saved locally as `build/branding-review/c64-sid-concepts.png`. Visual inspection confirms three distinct concepts with readable C64/SID labels and music symbols. A best combines the requested badge colors and typography with a compact sound-chip silhouette. B emphasizes the screen character set; its accent has four visible bands rather than the requested five. C communicates the beige computer casing but has more competing details. All are exploratory rasters with some generated shading; none has passed exact-palette or small-icon production checks. The user selected A; B and C are not being developed.

## Selected direction A

The user chose A on 2026-10-17. The [refinement prompt](refinement-prompt.md) preserves its lettering, dark tile, rainbow bands and note/pulse shape while requesting simpler flat pins and solid colors. The built-in image tool produced `build/branding-review/c64-sid-a-refined.png`; a 144-pixel WebP preview is at `build/branding-review/c64-sid-a-144.webp`. The generated result retains five pins per side despite the requested four, and subtle shading remains, so it is a visual refinement sample rather than a mechanically exact flat-color master. No production asset was replaced and nothing was committed.

The user liked the refinement and explicitly requested SVG for a small file. The [vector redraw](../../../assets/branding/sid-song-crafter.svg) uses custom outlined letters and simple geometry, with no embedded raster or font. It preserves the selected composition and five side pins, removes generated shading and joins the note head, stem and waveform into one continuous path. Solid color values are the badge-inspired web approximations recorded in the refinement prompt, not a claimed hardware palette. XML structure and absence of external dependencies were checked; previews were visually inspected at 512 and 144 pixels. The user authorized installing this redraw as `assets/branding/sid-song-crafter.svg`, regenerating the canonical WebP and using the SVG in README. The temporary duplicate SVG was removed after promotion. The assets were initially left uncommitted for review; the user subsequently authorized publication.
