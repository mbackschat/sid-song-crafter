# Rambo source resource audit

This 2026-10-15 audit supports the [resource-informed revision](../../songs/studies/rambo-ensemble/README.md#resource-informed-revision). It describes executed behavior and candidate experiments, not missing intended notes, proven audible defects or Galway's unexpressed wishes. Music-derived records retain the [Rambo loader's GPLv3 terms and attribution](../../samples/rambo-loader/README.md).

| Evidence | Contract |
| --- | --- |
| [Backend audit](backend-audit.json), [probe](backend-probe.py), [complete pre-note observations](backend-note-observations.json.gz) | Compare all 87,534 source writes and 2,477 note/patch entries; check 32,445 final per-voice/call SOUND states against retained evidence. Three duplicate reentrant invocation keys are collapsed, so this is not all 32,448 separate invocation states. Retain actual SID control shadows separately from saved instrument control. |
| [Design audit](design-audit.json.gz), [probe](design-probe.py) | Verify source-node/bank identity and the complete ordered-store oracle; retain note-entry state, changing roles, arpeggio pitch packing, clears, coupling and descending-pitch attacks. |

From the repository root, reproduce into fresh ignored output directories:

```sh
python3 evidence/rambo-resource-audit/backend-probe.py --root . --output build/rambo-resource-backend-recheck
python3 evidence/rambo-resource-audit/design-probe.py --root . --output build/rambo-resource-design-recheck.json
```

The design probe additionally requires the pinned local composer source at `.tools/martin-galway-c64/rambload.asm`, used by the [loader source verification](../../samples/rambo-loader/README.md). Its recorded inputs include the source hash. The backend probe uses retained canonical evidence and does not require downloading an original SID. Verify stored and original archive hashes with `python3 scripts/evidence.py verify --group rambo-resource-audit`; see [restoration](../../docs/workflows/build-cache.md).

The initially proposed three-attack release test was deliberately narrow and is now rejected by the screening below. It would have kept the original attacks at calls 2355 and 2611 on A1 and moved the original 2483 attack to B1 from its onset. Predicted independent lifetime clears are 2544, 2672 and 2800, before the next original attack at 2803. These remain model predictions for an unbuilt, rejected variant. Independent oscillators have independent envelope histories; equal source patches do not guarantee equal attack PCM. All new overlaps need harmonic and listening review. Preserve source coupling in later passages.

Absence of noise or volume-register playback cannot rule out percussion. Eleven pulse attacks at calls 2227–2299 use a descending frequency-word step of −80, verified through the following programmed updates. The implementation supports a tonal-percussion hypothesis; the instrument's musical role is not established by those register values alone.

## Release hypothesis rejected before rendering

The subsequent [harmonic screening](release-harmony-audit.json) and [reproducible probe](release-harmony-probe.py) reject the proposed 2483 relocation as the next musical test. Five of six qualifying lead triples in the bounded uncoupled region fail whole-overlap source-chord membership. The remaining nominal pitch-class match at 4019/4147/4371 contains a large executed pitch bend against the preceding held tone, so it is not a robust alternative. No release-overlap arrangement or WAV was generated.

This screening is conservative, not a claim that all non-chord tones are bad music. Its purpose is to avoid presenting an unmotivated new dissonance as restored polyphony. The reusable consequence is to inspect the complete sounding pitch trajectory against each concurrent harmonic region before extending a tail; correct source onset pitches and spare voices do not establish a musically useful overlap. The [selected chord-body revision](../../songs/studies/rambo-ensemble/README.md#resource-informed-revision) instead develops the demonstrated one-voice chord compression.
