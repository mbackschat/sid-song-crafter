# Instrument library and characterisation spec

Status: proposed contract, settled on 2026-10-29 and now under revision after the spikes below; no validator, storage or migration exists in the repository. The [plan](../PLAN.md#deferred-work-and-unproven-outcomes) owns the agreed order: the [engine-limit audibility comparison](../../songs/studies/engine-audibility/README.md), then converter support for the full SID-Wizard instrument model, then a superset engine only if the comparison needs it.

## Spike findings that the next revision must answer

Five bounded spikes on 2026-10-29 tested the contract in practice: writing records for 19 native and 4 decoded instruments, blind selection by a LOW and a MEDIUM agent against the held-out Moon River verdicts, deriving interface fields from executed write logs, a source review of SID-Wizard Extra's expressiveness, and an automatic import of 12 upstream SID-Wizard instruments.

| Finding | Evidence | Required contract change |
| --- | --- | --- |
| The selection rule ranks context-free evidence above fit | Both blind selectors chose the rejected Moon River bass because of one "warm bass" verdict from another arrangement; MEDIUM also chose a pulse lead it called its second choice on mood | Rank by fit to the brief first; weigh a verdict only as far as its context (role, tempo, mood brief, solo or ensemble) resembles the new one |
| Verdicts are copied onto every member of an ensemble | Ensemble and pairing verdicts appeared as per-instrument evidence in up to five records each | Store each verdict once with structured scope (solo, ensemble, pairing, A/B against a named alternative) and reference it from records |
| Required character claims force placeholders | About 30% of hand-written native claims and the placeholders in all imported records were unsourced values tagged `intent` | Allow an explicit unknown; never require a value the evidence does not give |
| Interface fields are measurable, not authorable | Hand-written records left `onNewNote`/`lifetime` unknown; execution filled 39 of 48 headline interface fields for imported instruments | Generate interface fields from a standard probe phrase **through the song pipeline** (tempo matters: trial-path observations do not transfer); give interface claims a basis and evidence link |
| Vocabulary misses observed behaviour | No TEST-frame `onNewNote`, no onset latency, no pitch response (drums ignore score pitch), no written-versus-sounding transposition, no waveform field, per-component tie behaviour, `moving-pulse` covering four different behaviours | Extend from these concrete cases; define thresholds for attack, release and weight |
| Decoded master programs are not drivable through the interface alone | Every accepted transfer needed an engine-specific adapter and covered the whole trio | Keep decoded programs engine-scoped; "reusable" must name the adapter and ensemble it was proven with |
| SID-Wizard Extra combines instruments but expresses 4 of 15 decoded mechanisms exactly | Source review of `player.asm` and the exporter | Default engine pending the [audibility comparison](../../songs/studies/engine-audibility/README.md) |
| Upstream instruments can enter largely automatically | 76% of record leaves filled by parsing and execution for 12 upstream examples; converter limits block bass, chord-table and percussion instruments | Reference upstream files by path and SHA-256 (redistribution needs a separate rights check); see the [converter limits](../workflows/native-song-workflow.md#converter-limits-on-the-sid-wizard-instrument-model) |

## Purpose

Formalise the instrument notion so that an LLM can select, combine and drive SID instruments when composing. Each library record names one SID program, declares what the score must supply to play it, states the resources it consumes, and characterises its sound with a controlled vocabulary whose every claim names its basis. The record describes; listening in the target phrase still decides, as the [listening rules](../workflows/audio-comparisons.md) require.

## The instrument notion

An **instrument** is a named SID program executed by a declared engine, together with its **interface** to the score. The program develops a sound over time ([instruments as programs](../research/composition/instruments-as-programs.md)); the engine is the player whose semantics define what the program means; the interface is the contract between notes and program.

An instrument is **reusable** when a score other than the one it came from drives it through its interface and the result is accepted in listening review. Reusability is therefore evidence, not a property of the format. A decoded master program may enter the library with a declared interface and no accepted transfer yet; the index then reports it as not reusable. A program whose behaviour cannot be stated through the interface, for example because note events in another voice must perform part of it, stays in its instrument card.

The interface is where entanglement becomes visible: score-owned behaviour, state shared across voices and coupled oscillators all appear as explicit fields. Observed examples that the fields must be able to express:

| Mechanism | Interface field |
| --- | --- |
| DRAX lead/chord gate-off belongs to the score; the bass patch closes its own gate | `scoreOwned`, `afterGateOff` |
| Monty pulse width is shared by every voice selecting the record; delay and direction stay per voice | `state[].scope` |
| Rambo sound lifetime outlasts the score note | `lifetime` |
| Shades melody voice also triggers the shared filter | `resources.filter` |
| Ghouls bass spends one update on noise before its triangle body | `character.attack: staged`, `minNoteUpdates` |
| Ghostbusters release is performed by the score | `scoreOwned` |

## Record contract

One immutable JSON file per instrument version at `songs/instruments/<id>@<version>.json`. Unknown fields fail validation, as in the [catalog contract](../workflows/catalog.md#version-1-contract).

```ts
type Basis = "intent" | "measured" | "tested" | "heard";
type Claim<T> = { value: T; basis: Basis; detail?: string; record?: string };

interface InstrumentRecord {
  id: string;                    // "<role>.<descriptor>", kebab-case, e.g. "lead.pulse-moving"
  version: number;               // positive integer; a changed program is a new version
  name: string;                  // human-readable
  nativeName?: string;           // tracker label, ≤ 8 characters, e.g. "PULSEMOV"
  program: { engine: EngineId; file: string; record?: string };
  interface: Interface;
  resources: Resources;
  character: Character;
  fit: Fit;
  evidence: Evidence;
  provenance: Provenance;
  referenceContext: { phrase: string; recipe?: string };
}

type EngineId = "sidwizard-extra-1.97" | "monty" | "rambo" | "shades" | "ghouls" | string;  // each id names an owning compiler

interface Interface {
  scoreSupplies: Array<"pitch" | "onset" | "gateOff" | "tie">;
  parameters: Array<{ name: string; type: "int" | "pitch" | "enum"; range?: [number, number]; values?: string[]; default?: number | string }>;
  scoreOwned: string[];          // behaviour the score must perform, e.g. "release timing"
  onNewNote: "retrigger" | "hard-restart" | "legato" | "not-established";
  hardRestartUpdates?: number;
  onTie: "keep-envelope-and-program" | "restart-program" | "not-established";
  afterGateOff: "release-only" | "program-continues" | "not-established";
  lifetime: "until-release-ends" | "until-next-note" | { updates: number } | "not-established";
  minNoteUpdates?: { value: number; reason: string };
  state: Array<{ field: string; scope: "note" | "voice" | "instrument" | "chip" }>;
}

interface Resources {
  voices: 1 | 2 | 3;
  coupling: "none" | { kind: "sync" | "ring"; partner: "preceding-oscillator" };
  filter: "none" | "owner" | "routed";      // routed: enters a filter another part owns
  masterVolume: "none" | "writes";
  chipModels: Array<"MOS6581" | "MOS8580">;
  clocks: Array<"PAL" | "NTSC">;
  updateRate: "frame" | { hz: number; source: "cia" };
}

interface Character {
  summary: string;               // one or two sentences
  attack: Claim<"soft" | "medium" | "hard" | "staged">;
  body: Claim<"static" | "moving-pulse" | "moving-filter" | "arpeggio" | "pitch-animated" | "waveform-sequence" | "noise">;
  release: Claim<"cut" | "short" | "medium" | "long" | "keeps-moving">;
  brightness: Claim<"dark" | "warm" | "bright" | "harsh">;
  weight: Claim<"thin" | "medium" | "full">;
  motion: Array<Claim<"pwm" | "vibrato" | "delayed-vibrato" | "glide" | "pitch-bend" | "arpeggio" | "filter-sweep" | "waveform-change">>;
  heardAs: Array<{ words: string; scope: string; record: string }>;   // listener's own words only
}

interface Fit {
  roles: Array<"lead" | "countermelody" | "harmony" | "chord" | "bass" | "percussion" | "effect">;
  range?: Claim<{ low: string; high: string }>;
  worksWith: Array<{ id: string; record: string }>;
  avoid: Array<{ condition: string; record: string }>;
}

interface Evidence {
  level: "documented-reference" | "proposed-experiment" | "rendered-experiment" | "listening-reviewed" | "hardware-checked";
  verdicts: Array<{ scope: string; result: "accepted" | "qualified" | "rejected" | "no-preference"; quote?: string; record: string }>;
  transfers: Array<{ phrase: string; source: string; verdict: string }>;
}

interface Provenance {
  origin: "original" | "derived" | "decoded";
  composer?: string;
  sourceWork?: string;
  derivedFrom?: string;          // "<id>@<version>"
  card: string;
  rights: string;
}
```

### Semantics

- **Basis.** `intent` is the designer's aim. `measured` derives from a trace or render and names it in `detail` or `record`. `tested` was verified in a phrase. `heard` requires a listener verdict in `record`. A record's evidence level never upgrades the basis of an individual claim.
- **Mood words** appear only in `heardAs`, as the listener's own words with scope and link. No other field carries mood; mood matching otherwise happens in the arrangement brief, following the [score-interpretation workflow](../workflows/song-workflow.md).
- **Unknown interface behaviour** is `not-established`, never a plausible default. A record with any `not-established` interface field is not reusable until a trace settles it.
- **Evidence levels** reuse the [repertoire definitions](../research/composition/sound-design-repertoire.md#evidence-levels).
- **Engine scope.** An instrument is selectable only for a song using its engine. A translation into another engine is a new record with `origin: "derived"`, `derivedFrom` and its own evidence, because translation can change the instrument.
- **Reusable** is computed, not stored: true when `transfers` contains an accepted verdict on material other than `provenance.sourceWork`.
- **Reference context** names the phrase in which the character was assessed. The same record can be heard as a different instrument in another arrangement ([Axel F role study](../../songs/axel-f/huelsbeck-study.md#targeted-role-study-lead-support-and-the-apparent-switch)).

### Example

From the [LEAD-02 card](../research/composition/instruments/lead-02-moving-pulse.md). Characterisation the card does not establish is `intent` or empty; interface behaviour it does not establish is `not-established`.

```json
{
  "id": "lead.pulse-moving",
  "version": 1,
  "name": "Moving pulse lead with delayed vibrato",
  "program": { "engine": "sidwizard-extra-1.97", "file": "songs/studies/sidwizard-repertoire/native/instruments/pulse-moving.swi" },
  "interface": {
    "scoreSupplies": ["pitch", "onset", "gateOff", "tie"],
    "parameters": [],
    "scoreOwned": ["gate timing"],
    "onNewNote": "hard-restart",
    "onTie": "keep-envelope-and-program",
    "afterGateOff": "not-established",
    "lifetime": "not-established",
    "minNoteUpdates": { "value": 12, "reason": "vibrato delay 12; shorter notes never reach vibrato" },
    "state": [{ "field": "pulse width", "scope": "note" }]
  },
  "resources": { "voices": 1, "coupling": "none", "filter": "none", "masterVolume": "none", "chipModels": ["MOS8580"], "clocks": ["PAL"], "updateRate": "frame" },
  "character": {
    "summary": "Sustained pulse lead whose tone keeps developing through held notes; vibrato enters only on longer notes.",
    "attack": { "value": "medium", "basis": "intent" },
    "body": { "value": "moving-pulse", "basis": "measured", "detail": "width $400–$800, ±$20 per update, looping", "record": "docs/research/composition/instruments/lead-02-moving-pulse.md" },
    "release": { "value": "medium", "basis": "intent" },
    "brightness": { "value": "warm", "basis": "intent" },
    "weight": { "value": "medium", "basis": "intent" },
    "motion": [{ "value": "pwm", "basis": "measured" }, { "value": "delayed-vibrato", "basis": "measured" }],
    "heardAs": []
  },
  "fit": { "roles": ["lead"], "range": { "value": { "low": "A3", "high": "C5" }, "basis": "intent" }, "worksWith": [], "avoid": [] },
  "evidence": {
    "level": "rendered-experiment",
    "verdicts": [{ "scope": "solo A/B against static width, repertoire phrase, MOS8580", "result": "no-preference", "record": "docs/research/composition/instruments/lead-02-moving-pulse.md" }],
    "transfers": []
  },
  "provenance": { "origin": "original", "card": "docs/research/composition/instruments/lead-02-moving-pulse.md", "rights": "MIT" },
  "referenceContext": { "phrase": "songs/studies/sidwizard-repertoire/native/pulse-candidate.swm" }
}
```

## Selection procedure

1. Filter by the song's engine, free voices, coupling and filter ownership, chip model, clock and role.
2. Match `character` and `fit` against the mood brief and the phrase's note lengths (`minNoteUpdates`).
3. Read verdict scopes and prefer evidence over descriptive richness: a sparse record with an accepted transfer outranks a richly described rendered experiment.
4. Audition in the target phrase and record the verdict on the record's next version or the arrangement's study.

## Scope

**Required:** the record contract and a strict validator; a generated index of id, summary, roles, resources and evidence level linked from the [technique index](../research/technique-index.md); migration of the named SID-Wizard instruments currently embedded in `sidwizard-arrangement-v1` files, each distinct definition becoming its own version or id; new arrangements referencing `id@version`.

**Optional:** measured descriptors computed from a standard audition render (attack time, pulse-width depth, release length) with `basis: "measured"`; model-generated descriptions recorded only as experimental signals under the [model-assistance rules](../research/audio-assessment.md#use-and-reassess-model-assistance).

**Excluded:** selection without audition; mood terms outside `heardAs`; automatic cross-engine translation; rewriting existing arrangement files, which keep their embedded instruments as frozen evidence; a song-level score format, which is the separate next contract for LLM composition.

## Risks

- Most initial records will carry `intent` claims and no `heardAs`; the selection procedure must not reward description over evidence.
- Interface fields may prove insufficient for some decoded engines; extend the contract only from a concrete program that cannot otherwise be stated, and keep it in its card meanwhile.
- Embedded instrument copies in existing arrangements will not follow library versions; the index must report where each version occurs.
