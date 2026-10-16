# Game-music publication permissions

Checked 2026-10-15 for the studied repertoire. This records the evidence for distributing our song packages, separately from musical acceptance. The [asset registry](../../config/local-assets.json) owns source URLs, hashes and exact archive identities; the [publication policy](../workflows/publication-boundary.md) owns the packaging rules.

## Result

Martin Galway's Rambo loader has a positive licensing basis: his published source repository includes GPLv3 and explicitly identifies him as the current owner of its music and programming code. This supports a separately GPL-licensed reconstruction of that loader, with editable source and notices. It does not clear the complete 24-subtune Rambo archive. The [Rambo package](../../samples/rambo-loader/README.md) records the selected work and reproduction contract.

Arkanoid also has published Galway source under that licence, but our existing Arkanoid outputs are original-reference renders and a diagnostic modification, not a completed independent song. They remain local under the project's reference-file rule. No new Arkanoid reconstruction is required by this publication check.

The other reviewed game songs have no sufficient package permission established by this pass. That is a research result, not a claim that permission is impossible or that no licence exists. Separately licensed music can accompany MIT tools; it does not have to become MIT or public domain.

## Source evidence and its limits

| Source | What it establishes | Publication consequence |
| --- | --- | --- |
| Martin Galway, [README](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md), [GPLv3 licence](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/LICENSE) and [loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm) | Composer-owned release; he states that he acquired the rights from Infogrames, permits modification and new music, and requests credit. The loader header credits his composition, arrangement and programming. | Preserve GPLv3 for the covered music/source and its reconstruction, supply corresponding source and changes/attribution. Restrict the conclusion to the identified released works. |
| HVSC, [copyright notice](https://hvsc.de/info) | The archive distinguishes tolerated noncommercial remixing from an actual right and says it cannot grant licences. It also warns that credits are not necessarily current ownership. | An HVSC URL or composer credit alone cannot approve our package. Archive permission does not become a general adaptation or redistribution grant. |
| Chris Abbott, C64Audio, [How to be a remixer](https://c64audio.com/blogs/blog/how-to-be-a-remixer), 2017-10-10 | Distinguishes royalty-based cover releases from sampling a SID and discusses the established Remix.Kwed.Org community. | A venue-specific practice or a route to licensing is not a grant for GitHub song/source distribution. |
| Kevin Edwards, [Follin development archive](https://github.com/KevEdwards/TimGeoffFollinMusicDevDiskArchive); Dean Belfield, [earlier archive](https://github.com/breakintoprogram/archive-follin) | Explicit permission to archive/share development material; the newer archive describes reference use and excludes financial gain or benefit. Composer music and Stephen Ruddy's drivers have separate credits. | Do not treat archival permission as a general licence for our reconstructed SID/WAV and editable score. Clarify adaptation and redistribution scope before packaging. |
| Ben Daglish, [first-person interview](https://remix64.com/interviews/interview-ben-daglish.html), 2001-04-26 | Welcomes remixes, including a Deflektor remix. | Encouragement is useful context but supplies no defined licence for this package. |
| Chris Hülsbeck, [official site](https://www.huelsbeck.com/) | Advertises a separate royalty-free music project. | That offer does not establish that Giana Sisters or Shades belongs to the licensed selection. |

## Per-song disposition

“Unresolved” means no grant covering our proposed files was established. Composer-focused searches covered the six master studies; the remaining rows use existing provenance and the archive notice, not an exhaustive rights-holder search. Attribution below identifies the studied source, not a definitive current owner.

| Studied music | Evidence / scope | Disposition |
| --- | --- | --- |
| [Rambo loader](composition/rambo-preparation.md), Martin Galway | Selected subtune 1; published original loader and composer-owned GPLv3 release. Other film-score subtunes excluded. | Separately GPL-licensed SID/WAV package with complete editable source. |
| [Arkanoid](composition/galway-contrast.md), Martin Galway | Published `arkanoid.asm` and `arkadrum.asm` in the same GPL repository. Exact source/rip correspondence still matters. | Licensed-source candidate; existing original/diagnostic audio remains local. |
| [Ghouls 'n Ghosts](composition/ghouls-preparation.md), Tim Follin | Archival permission found, broader reconstruction grant not established. Other subtunes include separately credited arcade material. | Unresolved; no song downloads promoted. |
| [Gauntlet III](composition/follin-contrast.md), Tim and Geoff Follin | No title-specific package grant established; Follin archive permission cannot be extrapolated to every title. | Unresolved. |
| [Cybernoid II](composition/cybernoid-ii-preparation.md), Jeroen Tel | No grant found in the bounded composer-source search; some official-domain access failed. | Unresolved, not an exhaustive negative finding. |
| [Turbo Outrun](composition/tel-contrast.md), Jeroen Tel | Registry identifies separate Hiroshi Kawaguchi composition for the studied introduction. | Unresolved; do not clear underlying music through arranger credit. |
| [Monty on the Run](composition/monty-preparation.md), Rob Hubbard | No title-specific public grant found. | Unresolved. |
| [Commando](composition/hubbard-contrast.md), Rob Hubbard | No title-specific public grant found. | Unresolved. |
| Auf Wiedersehen Monty, Rob Hubbard and Ben Daglish | Reference registered; no title-specific grant established. | Unresolved; joint credits are not a licence. |
| [Deflektor](composition/deflektor-preparation.md), Ben Daglish | Composer welcomes remixes, but no package licence found. | Unresolved. |
| [Trap](composition/daglish-contrast.md), Ben Daglish | Registry also identifies a Jeff Wayne source passage. | Unresolved; underlying source needs its own basis. |
| [Giana Sisters](composition/huelsbeck-contrast.md), Chris Hülsbeck | No grant found for this title; separate royalty-free catalogue is insufficient. | Unresolved. |
| [Shades](composition/shades-preparation.md), Chris Hülsbeck | Adjacent non-game master study; no title-specific package grant found. | Unresolved; not excluded merely for being non-game music. |
| [Airwolf](composition/airwolf-preparation.md), Mark Cooksey | Archive/source attribution only in this pass. | Unresolved. |
| [Ghostbusters](composition/ghostbusters-preparation.md), Russell Lieblich | Archive/source attribution only; speech and underlying song also need a distribution basis. | Unresolved. |
| [Gyruss comparison](composition/bach-toccata.md), unidentified C64 arranger | Bach composition is public domain; this does not establish rights in the game arrangement/player. | Original reference remains local; our independently arranged Bach package has its own source basis. |

## Recheck and promotion

Recheck an unresolved row when a concrete licence, author statement or permission becomes available. Record the exact work/subtune and source revision, who grants permission and what it covers, permitted distribution/adaptation, required credit and accompanying licence/source. Then verify the proposed package against that scope. A separately licensed package must be identified in [third-party notices](../../THIRD_PARTY_NOTICES.md) and its own manifest; project MIT wording must not override it.

For Rambo, preserve the original loader attribution, identify our independent graph/player reconstruction as a modification, and distribute the editable graph plus build/player source with the SID/WAV. A raw payload is not a standalone PRG; this backend supplies no SWM. Keep reference SIDs and their audio local even where a released source grants additional rights: the user has expressly chosen that repository boundary.

HVSC identifies Chris Abbott/C64Audio as a useful first contact for rights enquiries, but that does not establish authority for every listed song. No one was contacted and no permission was requested on the user's behalf during this research.
