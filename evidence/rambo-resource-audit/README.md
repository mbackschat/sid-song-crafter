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

The proposed three-attack release test is deliberately narrow. Keep original attacks at calls 2355 and 2611 on A1 and move the original 2483 attack to B1 from its onset. Predicted independent lifetime clears are 2544, 2672 and 2800, before the next original attack at 2803. These are model predictions for an unbuilt variant. Independent oscillators have independent envelope histories; equal source patches do not guarantee equal attack PCM. All new overlaps need harmonic and listening review. Preserve source coupling in later passages.

Absence of noise or volume-register playback cannot rule out percussion. Eleven pulse attacks at calls 2227–2299 use a descending frequency-word step of −80, verified through the following programmed updates. The implementation supports a tonal-percussion hypothesis; the instrument's musical role is not established by those register values alone.
