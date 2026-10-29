# Instrument library and characterisation spec

Status: proposed contract, revised once from the spikes below and confirmed for MEDIUM selectors; no validator, storage or migration exists in the repository. The [plan](../PLAN.md#deferred-work-and-unproven-outcomes) owns the agreed order. SID-Wizard Extra is the composition engine ([engine-limit audibility comparison](../../songs/studies/engine-audibility/README.md#outcome)), and the converter supports its full instrument model ([converter limits](../workflows/native-song-workflow.md#converter-limits-on-the-sid-wizard-instrument-model)).

## Purpose

Formalise the instrument notion so that an LLM can select, combine and drive SID instruments when composing. Each library record names one SID program, declares what the score must supply to play it, states the resources it consumes, and characterises its sound with measured traits. Listener judgments are stored once, as verdicts with structured context, and are weighed by how closely that context resembles the new brief. The record describes; listening in the target phrase still decides, as the [listening rules](../workflows/audio-comparisons.md) require.

## The instrument notion

An **instrument** is a named SID program executed by a declared engine, together with its **interface** to the score. The program develops a sound over time ([instruments as programs](../research/composition/instruments-as-programs.md)); the engine is the player whose semantics define what the program means; the interface is the contract between notes and program.

An instrument is **reusable** when a score other than the one it came from drives it through its interface and the result is accepted in listening review. Reusability is therefore evidence, not a property of the format. A program whose behaviour cannot be stated through the interface, for example because note events in another voice must perform part of it, stays in its instrument card.

The interface is where entanglement becomes visible: score-owned behaviour, state shared across voices and coupled oscillators all appear as explicit fields. Observed examples that the fields must be able to express:

| Mechanism | Interface field |
| --- | --- |
| DRAX lead/chord gate-off belongs to the score; the bass patch closes its own gate | `scoreOwned`, `afterGateOff` |
| Monty pulse width is shared by every voice selecting the record; delay and direction stay per voice | `state[].scope` |
| Rambo sound lifetime outlasts the score note | `lifetime` |
| Shades melody voice also triggers the shared filter | `resources.filter` |
| Ghouls bass spends one update on noise before its triangle body | `character.attack: staged` |
| Ghostbusters release is performed by the score | `scoreOwned` |
| SID-Wizard tempo-1 songs replace hard restart by one TEST-bit frame | `onNewNote: test-frame` |
| A drum ignores the score pitch | `pitchResponse: percussion` |

## Record contract

One immutable JSON file per instrument version at `songs/instruments/<id>@<version>.json`, and one immutable JSON file per listener verdict at `songs/instruments/verdicts/<verdict-id>.json`. Unknown fields fail validation, as in the [catalog contract](../workflows/catalog.md#version-1-contract).

```ts
type Known<T> = { value: T; basis: "intent" | "measured" | "tested"; detail: string; record?: string };
type Claim<T> = Known<T> | { basis: "unknown" };

interface InstrumentRecord {
  id: string;                    // "<role>.<descriptor>", kebab-case, e.g. "lead.triangle-vibrato"
  version: number;               // positive integer; different program bytes are a different version
  name: string;                  // human-readable
  nativeName?: string;           // tracker label, ≤ 8 characters, e.g. "MRVOICE"
  program: { engine: EngineId; file: string; record?: string; sha256?: string };
  interface: Interface;
  resources: Resources;
  character: Character;
  fit: Fit;
  provenance: Provenance;
}

type EngineId = "sidwizard-extra-1.97" | "monty" | "rambo" | "shades" | "ghouls" | string;  // each id names an owning compiler

interface Interface {
  scoreSupplies: Array<"pitch" | "onset" | "gateOff" | "tie">;
  pitchResponse: "absolute" | "percussion";
  parameters: Array<{ name: string; type: "int" | "pitch" | "enum"; range?: [number, number]; values?: string[]; default?: number | string }>;
  scoreOwned: string[];          // behaviour the score must perform, e.g. "release timing"
  onNewNote: "retrigger" | "hard-restart" | "test-frame" | "legato" | "not-established";
  onTie: "keep-envelope-and-program" | "restart-program" | "not-established";
  afterGateOff: "release-only" | "program-continues" | "not-established";
  lifetime: "until-release-ends" | "until-next-note" | { updates: number } | "not-established";
  pitchSettlesAfterUpdates: Claim<number>;
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
  summary: string;               // one or two sentences of program behaviour, no mood words
  waveforms: Claim<Array<"triangle" | "saw" | "pulse" | "noise">>;
  envelope?: { attack: number; decay: number; sustain: number; release: number; attackMs: number; releaseMs: number };
  attack: Claim<"soft" | "medium" | "hard" | "staged">;
  body: Claim<"static" | "moving-pulse" | "moving-filter" | "arpeggio" | "pitch-animated" | "waveform-sequence" | "noise">;
  release: Claim<"cut" | "short" | "medium" | "long">;
  level: Claim<{ onsetDb: number; sustainDb: number }>;
  brightness: Claim<{ onset: number; body: number }>;
  motion: Array<Known<"pwm" | "vibrato" | "delayed-vibrato" | "glide" | "pitch-bend" | "arpeggio" | "filter-sweep" | "waveform-change"> & { startsAfterUpdates?: number }>;
}

interface Fit {
  roles: Array<"lead" | "countermelody" | "harmony" | "chord" | "bass" | "percussion" | "effect">;
  range?: Claim<{ low: string; high: string }>;
  avoid: Array<{ condition: string; verdict?: string; record?: string }>;   // at least one of verdict, record
}

interface Provenance {
  origin: "original" | "derived" | "decoded" | "upstream";
  composer?: string;
  sourceWork?: string;
  derivedFrom?: string;          // "<id>@<version>"
  card: string;
  rights: string;
}

interface Verdict {
  id: string;
  attribution: "isolated" | "group";
  members: string[];             // "<id>@<version>" of the instruments judged
  comparedWith?: Array<string | { description: string }>;   // library versions or a described alternative
  context: {
    work: string;
    roles: Record<string, string>;     // member → role in that arrangement
    tempoBpm: number | null;
    meter: string | null;
    moodBrief: string | null;
    material: "excerpt" | "phrase" | "complete";
  };
  result: "accepted" | "qualified" | "rejected" | "preferred" | "not-preferred" | "no-preference";
  quote: string | null;          // the listener's words, verbatim
  record: string;                // the owning study's listening record
}
```

### Semantics

- **Basis.** `intent` is the designer's aim. `measured` derives from this program's data, trace or probe render, named in `detail`; a value carried over from another program's trace is `intent` until a probe confirms it. `tested` was verified in a phrase named in `detail` or `record`. `unknown` states that no evidence gives a value; a record never fills a trait with a plausible default. A measured value replaces an intent claim on the same trait.
- **Listener words** live only in verdicts. A record carries no mood words and no claim based on hearing, so every listener judgment reaches selection through its verdict's context. An `avoid` condition derived from a verdict names that verdict.
- **Envelope categories.** `envelope` copies the program's ADSR nibbles and their datasheet times; the categories follow fixed thresholds on the datasheet table times before clock scaling: attack hard ≤ 8 ms, medium ≤ 24 ms, soft ≥ 38 ms, or `staged` when a measured onset passes through another waveform first; release cut ≤ 24 ms, short ≤ 114 ms, medium ≤ 300 ms, long ≥ 750 ms. Modulation continuing after gate-off is `interface.afterGateOff`, not a release category.
- **Probes.** `level` and `brightness` come from **probe-level-v1**: one note at the role pitch (bass A2, lead A4, other roles A3) gated for 100 PAL updates, the other voices silent, master volume 15, MOS8580, rendered through the song pipeline. `level` is RMS dBFS over the first 250 ms and over 1.0–1.9 s of the note; `brightness` is the spectral centroid divided by the fundamental over 0–60 ms and 50–550 ms (a pure triangle is about 1.0). Values compare directly between candidates for one role; across roles the probe pitches differ, so a level comparison is approximate. Interface fields come from a standard probe phrase through the same pipeline; trial-path observations do not transfer, because tempo changes the restart behaviour. Values from different probe versions are not compared.
- **Note lengths.** `pitchSettlesAfterUpdates` is the shortest note that sounds at its full pitch. `startsAfterUpdates` on a motion says when that motion begins; a shorter note plays without it.
- **Unknown interface behaviour** is `not-established`. A record with any `not-established` interface field is not reusable until a probe settles it.
- **Program identity.** A version is its program bytes excluding the tracker label. Byte-identical programs embedded under different labels are one version; changed bytes, including an envelope change, are a new version.
- **Verdicts.** `isolated` means the instrument was heard alone or was the only change between the compared versions; otherwise `group`. `comparedWith` is required for `preferred`, `not-preferred` and `no-preference`. A verdict names at least one library version in `members` or `comparedWith`; the validator checks that `quote` occurs verbatim in `record`.
- **Computed, never stored.** The generated index derives, per version: its verdicts (every verdict naming it), the evidence level from the [repertoire definitions](../research/composition/sound-design-repertoire.md#evidence-levels) (`listening-reviewed` only while at least one verdict names it), accepted partners (co-members of an accepted verdict), **reusable** (an accepted verdict on a work other than `provenance.sourceWork`) and every arrangement file that embeds the program. It presents each verdict from the record's side: judged member, preferred alternative or rejected alternative.
- **Engine scope.** An instrument is selectable only for a song using its engine. A translation into another engine is a new record with `origin: "derived"`, `derivedFrom` and its own verdicts, because translation can change the instrument. Decoded master programs stay engine-scoped references: every accepted transfer needed an engine-specific adapter and covered the whole trio.
- **Upstream instruments** are referenced by path and `program.sha256`; redistribution needs a separate rights check.

### Example

From the accepted [Moon River](../../songs/moon-river/README.md) lead; the verdict below is one of the three that name it.

```json
{
  "id": "lead.triangle-vibrato",
  "version": 1,
  "name": "Triangle lead with slow attack and late vibrato",
  "nativeName": "MRVOICE",
  "program": { "engine": "sidwizard-extra-1.97", "file": "songs/moon-river/restrained.json", "record": "instruments.lead" },
  "interface": {
    "scoreSupplies": ["pitch", "onset", "gateOff"],
    "pitchResponse": "absolute",
    "parameters": [],
    "scoreOwned": ["gate-off timing"],
    "onNewNote": "not-established",
    "onTie": "keep-envelope-and-program",
    "afterGateOff": "not-established",
    "lifetime": "not-established",
    "pitchSettlesAfterUpdates": { "value": 2, "basis": "measured", "detail": "stock Extra at tempo 1 sets only the frequency high byte on a new note's first frame", "record": "docs/songs/fuer-elise-native.md" },
    "state": []
  },
  "resources": { "voices": 1, "coupling": "none", "filter": "none", "masterVolume": "none", "chipModels": ["MOS8580"], "clocks": ["PAL"], "updateRate": "frame" },
  "character": {
    "summary": "Gated triangle with a 38 ms attack and vibrato entering after the note has sounded for 22 updates; no pulse or filter program.",
    "waveforms": { "value": ["triangle"], "basis": "measured", "detail": "wave table $11 after the TEST frame" },
    "envelope": { "attack": 4, "decay": 6, "sustain": 7, "release": 6, "attackMs": 38, "releaseMs": 204 },
    "attack": { "value": "soft", "basis": "measured", "detail": "attack nibble 4 = 38 ms" },
    "body": { "value": "static", "basis": "measured", "detail": "empty pulse and filter tables" },
    "release": { "value": "medium", "basis": "measured", "detail": "release nibble 6 = 204 ms" },
    "level": { "value": { "onsetDb": -27.6, "sustainDb": -28.8 }, "basis": "measured", "detail": "probe-level-v1 at A4" },
    "brightness": { "value": { "onset": 1.0, "body": 1.0 }, "basis": "measured", "detail": "probe-level-v1 at A4" },
    "motion": [{ "value": "delayed-vibrato", "basis": "measured", "detail": "vibrato $12, delay 20, plus the 2-update onset", "startsAfterUpdates": 22 }]
  },
  "fit": { "roles": ["lead"], "avoid": [] },
  "provenance": { "origin": "original", "sourceWork": "Moon River", "card": "songs/moon-river/README.md", "rights": "MIT" }
}
```

```json
{
  "id": "v-moon-restrained",
  "attribution": "group",
  "members": ["lead.triangle-vibrato@1", "bass.triangle-plain@1", "harmony.triangle-plain@2"],
  "context": {
    "work": "Moon River",
    "roles": { "lead.triangle-vibrato@1": "melody lead", "bass.triangle-plain@1": "bass", "harmony.triangle-plain@2": "accompaniment" },
    "tempoBpm": 70, "meter": "3/4", "moodBrief": "tender, intimate, wistful and quietly hopeful", "material": "complete"
  },
  "result": "accepted",
  "quote": "moon-river-sid.wav is quite nice. Can you find a SID version on the internet?",
  "record": "songs/moon-river/listening-review.json"
}
```

## Selection procedure

Follow the steps in order and name the step that decided each choice.

1. **Hard filters.** Keep candidates whose engine, voices, coupling, filter ownership, chip model, clock and roles fit the song.
2. **Fit to the brief.** Translate the brief's character into sound traits and rank candidates by how well their measured or tested traits match: attack, envelope, waveforms, body, brightness, level, release, and the phrase's note lengths against `pitchSettlesAfterUpdates` and `startsAfterUpdates`. `level` and `brightness` compare directly between candidates for one role. `unknown` counts neither way; `intent` counts less than measured.
3. **Context-weighted evidence.** Judge each verdict's context against the brief: role, tempo within about ±30%, mood brief, and attribution. A verdict from a similar context may move a candidate up or down. A verdict from an unlike context never moves a candidate up; an unlike-context rejection is a caution to check in audition. A `group` verdict is weaker evidence about one member than an `isolated` one. Fit outranks unlike-context evidence; similar-context evidence may break near-ties or overturn a weak fit.
4. **Audition.** Name one choice and one runner-up per role with the deciding trait or verdict, audition in the target phrase, and record the result as a new verdict.

## Evidence for this revision

Bounded spikes on 2026-10-29 tested the first contract: records for 19 native and 4 decoded instruments; blind selection by LOW and MEDIUM agents with the listener's verdicts for one arrangement held out; interface derivation from executed write logs; a source review of SID-Wizard Extra; and an automatic import of 12 upstream instruments. The blind selections compared each choice with frozen criteria (the held-out accepted and rejected palettes), on Moon River and on a Mozart control that tests whether a rule discards useful similar-context evidence.

| Decision | Evidence |
| --- | --- |
| Fit ranks before evidence, and evidence is weighed by context | Under "evidence over richness" both blind selectors chose the rejected Moon River bass from a "warm bass" verdict on another arrangement, and MEDIUM also chose a pulse lead where the accepted palette has a triangle. With fit first, both chose the accepted triangle lead. |
| No claim based on hearing; listener words only in verdicts | With fit first but `heard` traits still in records, the rejected bass stayed first in both tiers: "warm" from an unlike ensemble entered at the fit step. |
| Measured `level` and `brightness` from one probe | The briefs ask for restraint, but no record field could express prominence. On probe-level-v1 the rejected filtered pulse bass sustains at −21 dBFS and the accepted triangle bass at −36 dBFS. |
| `pitchSettlesAfterUpdates` and per-motion `startsAfterUpdates` replace `minNoteUpdates` | A vibrato onset of 14 updates was read as a minimum note length, and the accepted Mozart lead was excluded because its eighths are 13–14 updates. |
| Evidence level, partners and reusability are computed | A stored level of `listening-reviewed` survived on records whose verdicts had been held out and misled every selector. |
| One version per program bytes | Two records held byte-identical programs under different tracker labels and split their evidence. |
| `attribution` and an explicit comparison replace verdict kinds | Several A/B verdicts had no named alternative, and selectors could not tell an isolated swap from a palette judgment. |
| Explicit `unknown`; interface fields from probes | About 30% of hand-written claims were unsourced placeholders tagged `intent`; execution filled 39 of 48 headline interface fields for imported instruments, and 76% of all imported record fields came from parsing and execution. |
| SID-Wizard Extra as default engine; decoded programs engine-scoped | Extra expresses 4 of 15 decoded mechanisms exactly; replacing two of the others with Extra behaviour was inaudible to the listener ([outcome](../../songs/studies/engine-audibility/README.md#outcome)). |

A confirmation run repeated the same four blind selections on the revised records and procedure, with briefs and criteria unchanged:

| Held-out case | LOW selector | MEDIUM selector |
| --- | --- | --- |
| Moon River | Fails: accepted lead and accompaniment, but the louder filtered pulse bass again, read as the long legato release a tender brief needs; the accepted bass was runner-up | Passes all three roles; measured level decided the bass |
| Mozart control | Fails: a high-register A/B decided a lead whose register the brief does not state, and a chord-role instrument was taken for the inner part against the role filter; bass passes | Passes: accepted bass and inner part, another moving-pulse lead |

The contract and procedure therefore work for MEDIUM selectors. The LOW failures came from translating the brief and applying the procedure, not from missing record fields; whether LOW selectors can be supported, for example by briefs that state each role's register and level relative to the melody, is open.

## Scope

**Required:** the record and verdict contracts and a strict validator (unknown fields, basis details, threshold-consistent categories, resolvable references, verbatim quotes); probe-level-v1 and the interface probe phrase as supported tools; a generated index of id, summary, roles, resources, level, brightness and the computed evidence fields, linked from the [technique index](../research/technique-index.md); migration of the distinct SID-Wizard programs embedded in `sidwizard-arrangement-v1` files and of the existing listening verdicts that name them; new arrangements referencing `id@version`.

**Optional:** records for upstream SID-Wizard example instruments, referenced by path and SHA-256 with probe-measured fields; model-generated descriptions recorded only as experimental signals under the [model-assistance rules](../research/audio-assessment.md#use-and-reassess-model-assistance).

**Excluded:** selection without audition; mood words or hearing-based claims in records; stored evidence levels, partners or reusability; automatic cross-engine translation; rewriting existing arrangement files, which keep their embedded instruments as frozen evidence; a song-level score format, which is the separate next contract for LLM composition.

## Risks

- Probe values describe one note at one pitch. Filtered and pitch-dependent programs can sound different elsewhere in their range, and the arrangement's balance still decides prominence.
- The category thresholds and the centroid ratio are fixed choices, not perceptual calibrations; records keep the numbers beside the categories.
- Translating a mood brief into traits remains the selector's judgment; the procedure narrows candidates for audition and does not replace it.
- Interface fields may prove insufficient for some decoded engines; extend the contract only from a concrete program that cannot otherwise be stated, and keep it in its card meanwhile.
