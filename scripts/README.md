# Tool boundaries

Choose tools by their supported contract. A song or composer name does not itself establish either generality or obsolescence. Study tools explain a pinned source; supported backends compute editable music within declared constraints. Listening-reviewed transfer to different material is evidence of reuse, not proof of a composer's universal style.

## Supported workflows and shared infrastructure

- [Listening packages](../docs/workflows/listening-package.md): recipe execution, verified stage reuse, timings, signal checks and audio links.
- [Reference intake](../docs/workflows/reference-intake.md): explicit source/subtune selection, execution admission, bounded traces/renders and source comparisons through the same recipe runner.
- [Song workflow](../docs/workflows/song-workflow.md) and [native SID-Wizard workflow](../docs/workflows/native-song-workflow.md): editable arrangement, export and verification.
- [Audio comparisons](../docs/workflows/audio-comparisons.md): PCM inspection and original-preserving A/B windows.
- [CPU auditing](../docs/validation/psid-audit.md), [CIA tracing](../docs/validation/cia-tracing.md) and [assembler](sid_assembler.py): execution and timing infrastructure.
- [Setup](../docs/setup/local-setup.md) and [evidence/cache management](../docs/workflows/build-cache.md): pinned assets, local tools, explicit archive promotion and verified restoration by path or group.

## Specialized composition backends

These remain in the shared scripts directory because supported workflows and tests use them. They are implementation families with explicit targets and conversion limits; they are not an unrestricted cross-composer music API.

| Backend | Supported entry and evidence |
| --- | --- |
| DRAX decoded trio | [compose-sid.py](compose-sid.py), [contract](../docs/workflows/decoded-song-workflow.md#editable-contract) |
| Flashdance | [compose-flashdance.py](compose-flashdance.py), [dual compiler](compose-flashdance-dual.py), [accepted transfer and stereo arrangement](../docs/research/composition/flashdance-preparation.md) |
| Shades | [compose-shades.py](compose-shades.py), `shades_*` runtime/CIA modules, [accepted familiar transfer](../docs/research/composition/instruments/shades-decoded-programs.md) |
| Cybernoid | [compose-cybernoid.py](compose-cybernoid.py), `cybernoid_*` runtime modules, [accepted familiar transfer](../docs/research/composition/instruments/cybernoid-decoded-programs.md) |
| Monty | [compose-monty.py](compose-monty.py), `monty_title_*` runtime modules, [accepted familiar transfer](../docs/research/composition/instruments/monty-decoded-programs.md) |
| Rambo | [compose-rambo.py](compose-rambo.py), [rambo_player.py](rambo_player.py), symbolic score/Morse and computed sound programs; [full compiled delivery](../docs/research/composition/rambo-preparation.md#independent-compiled-loader-and-musical-delivery), [accepted familiar transfer](../docs/research/composition/instruments/rambo-decoded-programs.md) |
| Deflektor | [deflektor_player.py](deflektor_player.py), numeric score/program modules; [preparation evidence](../docs/research/composition/deflektor-preparation.md), not yet a completed compiled/listening-reviewed backend |

## Source-specific work

Use [studies/](studies/README.md) for analysis, source extraction, causal experiments and fixed musical examples. New one-source tools belong there. Frozen evidence checkers stay alongside their [evidence](../evidence/README.md), with historical hashes intact. Promote reusable synthesis or validation APIs only when another musical input actually uses their declared contract; keep original-driver addresses and source acquisition outside that API.

The following compatibility boundaries deliberately remain at their established paths:

| Existing file | Why it remains |
| --- | --- |
| [prepare-monty-title.py](prepare-monty-title.py) | The saved numeric description embeds this extractor's path and byte hash; downstream preparations pin the entire description. Relocation needs a distinct provenance migration. It remains a study tool, not a production entry point. |
| [study-drax-references.py](study-drax-references.py) | Shared tracing and the explicitly deferred, untracked Flashdance analysis load this exact path. Preserving deferred work requires keeping that contract. |
| [reconstruct-drax-bass.py](reconstruct-drax-bass.py) | The supported DRAX compiler imports its synthesis helpers. Separate those helpers before relocating its source-specific command. |
| [describe-shades-score.py](describe-shades-score.py) | The live Shades player imports its pure score-expansion APIs. Source extraction and runtime expansion need an explicit split before moving the CLI. |
| [trace-shades-vice.py](trace-shades-vice.py) and [shades_programs.py](shades_programs.py) | Each contains supported runtime/validation APIs as well as reference-specific code. Their supported consumers retain these paths. |

These mixed responsibilities are existing architectural debt, not templates for new tools. The current separation does not silently change generated provenance or add a layer of root-level forwarding scripts. Historical recipes and evidence retain their original paths and hashes; revision `d91a2fe` is the pre-relocation source layout. Follow [historical reproduction guidance](../docs/workflows/build-cache.md) when executing a frozen recipe rather than rewriting its evidence.
