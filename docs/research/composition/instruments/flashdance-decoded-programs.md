# Flashdance decoded instrument programs

These independently computed programs reconstruct DRAX's **Flashdance (conversion)** (`1990 Vibrants`) and transfer its mechanisms to an original phrase. The [reference study](../flashdance-reference.md) owns attribution and archive identity; [the preparation study](../flashdance-preparation.md) owns executed evidence. Program names describe behavior rather than recovered composer symbols.

**Status:** rendered experiment on one PAL MOS6581 at `$D400`, updated once per 19,656 cycles. Execution and audio checks are complete for the linked examples; listening acceptance and physical-hardware equivalence are pending.

## Choose a program for the phrase

| Role and musical use | Editable program | Performance constraint |
| --- | --- | --- |
| Bass: mark an entrance, then retain a moving low tail | `record-00`: AD/SR `$02/$5F`; one absolute-pitch noise call `$C4E0/$81`, one root-pitch pulse call `$41`, then gate-clear pulse `$40`. Width starts `$100`, moves `$40` per body call and reverses on high bytes `$4/$F`. Bass-only resonant low-pass cutoff stages are 1280→832→512→384→256. | The instrument closes its own gate at restart+3; pulse motion and filter state continue in release. Retriggering replaces that oscillator's tail. Allow spacing when tail development is the purpose. |
| Lead: articulate short notes and animate held or connected notes | `record-10`: AD/SR `$03/$3C`; triangle for one body call, saw for two, then looping pulse. Width starts `$D00`; its first row moves `$70`, then the successor moves `$10`, with high-byte bounds `$A/$F`. | Restart returns to the staged attack; legato preserves waveform/PWM phase and envelope. Vibrato and accumulating pitch offset are explicit score effects. |
| Lead variant: exercise a broader pulse excursion | `record-38`: the same envelope and waveform stages, width `$100`, bounds `$1/$F`, first step `$50`, successor `$40`. | This variant is executed in the complete reconstruction. Its musical preference over `record-10` has not been judged. |
| Chord: imply four tones with one unfiltered voice | AD/SR `$03/$34`, plain pulse, width `$040`, step `$0D`, bounds `$1/$F`; each pitch lasts two body calls. Major `record-18` uses 0/4/7/12 semitones; minor `record-28` uses 0/3/7/12. The complete bank also retains 0/3/8/12, 0/5/8/12 and 0/5/7/12 variants. | These are one-voice pitch cycles, with one envelope and continuing PWM. They provide no independent chord-note tails. Choose the score root and inversion deliberately. |

Edit the [portable reconstruction](../../../../songs/flashdance-decoded.json) or [original transfer phrase](../../../../songs/flashdance-transfer.json). The [Python programs](../../../../scripts/flashdance_programs.py), [pitch effects](../../../../scripts/flashdance_pitch.py) and [6502 routines](../../../../songs/players/flashdance-programs.asm) compute motion from those parameters, without the original driver or register replay.

## Edit the demonstrated contract

PWM rows expose `lower`/`upper` high bytes 0–15, unsigned `step` 0–255, `duration` 0–63, optional `reset_width` and `hold`. Duration 8 moves on the loading call and eight following calls; the next row loads on the tenth. `hold` retains the row for rereads. Row changes preserve width and direction unless reset is requested.

PWM uses 16-bit carry/borrow and reverses only when the updated **high byte equals** its bound, retaining overshoot: the opening lead reverses at `$F30` and `$AF0`. There is no clamp. SID width uses 12 bits; software state retains 16-bit wrap.

Filter rows have byte-valued bounds, step and cutoff, the same duration/hold convention and optional reset. After 8-bit movement, ascent reverses at **greater than or equal to** the upper bound; descent reverses only **below** the lower bound. The bass contour uses zero-step reset stages. Only the owner advances the shared filter; every body writer repeats cutoff in voice order 3→2→1.

Wave rows select a relative offset or absolute note, control byte, or one jump to a sounding row. Resolved pitches must fit the 96-word table; active vibrato also needs the entry above the untransposed score note. Fine tuning adds 0/1/2 to bass/lead/chord before effects. Exact register words remain authoritative.

Vibrato shifts the adjacent-note difference plus its evolving high-byte depth. Counter decrement precedes reversal: reload 4/initial 3 gives three initial updates, then five between reversals. The transfer delays it eight calls; count two survives one following legato note. Slide takes priority, accumulates through absolute steps and adds its offset only to relative steps. Notes consume enable counts without clearing effect history.

Restart initializes envelope/TEST and skips the body writer. PWM row/optional width change immediately; direction, bounds and rate reset on following row consumption. ADSR is not rewritten every body call. Preserve the two silent startup calls and their preloaded state.

Absolute `call` events govern changes. `durationCalls` describes rows and schedules delayed envelope changes; it does not close gates automatically. Use explicit off, instrument release or the authored ending: 64 releasing/modulating calls followed by a 64-call fade, suppressing the next cycle.

## Transfer and reproduce

The transfer authors **C–F–D minor–G–C**: chord roots C4/F4/D4/G3/C4; bass roots/fifths C2/G2, F2/C3, D2/A2, G1/D2, then C2. Lead A4–A5 alternates restarted/legato notes and ends on held C5. F5 over G deliberately supplies a melodic dominant seventh.

After [local dependency setup](../../../setup/local-setup.md), use a fresh output directory:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compose-flashdance.py songs/flashdance-transfer.json --output build/flashdance-transfer-new
.local/bin/render-sid build/flashdance-transfer-new/reconstructed.sid build/flashdance-transfer-new/reconstructed.wav 16
python3 scripts/trace-sid-vice.py build/flashdance-transfer-new/reconstructed.sid --oracle build/flashdance-transfer-new/writes.json --first-call 0 --last-call 706 --output build/flashdance-transfer-new/vice
```

On 2026-10-13, the complete reconstruction matched all **27,905 initialization/music writes** through call 1537 by call, address, value and order ([comparison](../../../../build/flashdance-independent-full/reference-comparison.json)). Its independently authored ending is additional behavior. Headless VICE matched **30,203 play writes across 1,667 calls**, through the first stopped call ([receipt](../../../../build/flashdance-independent-full/vice/study.json)). Original and reconstruction instruction timing differ; neither ordered equality nor VICE proves identical PCM.

The transfer matched **12,761 play writes across 707 VICE calls**, including stopped call 706 ([receipt](../../../../build/flashdance-transfer/vice/study.json)). Its [16-second mono PCM16 render](../../../../build/flashdance-transfer/reconstructed.wav) is unclipped with zero final-half-second AC RMS ([evidence](../../../../build/flashdance-transfer/audio-evidence.json)). [Aligned duration annotations preserved the verified binary](../../../../build/flashdance-transfer/description-update.json). These checks establish executable reuse and a quiet ending; listening remains pending.

## Constraints and listening status

The demonstrated programs target PAL MOS6581 and one shared filter owned by bass; the lead and chord remain unfiltered and use no ring/sync coupling. Chip-model changes, new oscillator dependencies, different filter ownership and other update cadences require separate evidence. The transfer is a short phrase, and the reconstruction covers the selected recurring SID arrangement rather than the complete original song.

Listening is pending for both the complete reconstruction and transfer. Audition the transfer in its full mix for attack clarity, connected-note phrasing, bass-tail development and the chord cycle's harmonic clarity. Retain that verdict here before promoting these programs to listening-reviewed instruments.
