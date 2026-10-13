# Two SID chips

## What changes

Two independently addressed chips provide six oscillator/envelope voices and two independent filter/master-volume groups. Their audio may be mixed or separated into stereo by the hardware. Stereo output alone does not establish six independent voices: pseudo-stereo duplication is a different configuration. FPGASID's configuration documentation makes this distinction explicit. [S15](../sources.md#s15)

Project recommendation: put melody and an associated voice group on the first chip, accompaniment and sustained support on the second. Keep each chip's filter ownership explicit. A six-voice arrangement should also have a documented three-voice reduction if standard C64 playback matters.

## Address agreement

The first SID normally lives at `$D400`. Common second-chip choices include `$D420`, `$D500`, and `$DE00`, but hardware decoding and expansion conflicts decide what is usable. Standard mirrored SID space does not create a second chip. The hardware, exported tune, and emulator must agree on the selected address. [S05](../sources.md#s05), [S15](../sources.md#s15)

PSID v3 encodes the second SID location in header byte `$7A`: `$42` means `$D420`, `$50` means `$D500`, and `$E0` means `$DE00`. Valid address codes are restricted; do not accept arbitrary bytes. v4 adds the third-chip field, which this project does not currently need. [S13](../sources.md#s13)

## Tools and execution

The implemented route uses [SID-Wizard's native two-chip Extra player](../tools/sid-wizard-trial.md): six ordered voices, two independent filters, editable `.sws` source and PSID v3 export for two 8580s at `$D400/$D420`. Follow [the shared native workflow](../../workflows/native-song-workflow.md) to reproduce its original six-voice fixture, stereo render and headless VICE checks.

GoatTracker Stereo remains an alternative tracker backend. ChiptuneSAK's GoatTracker module recognizes three- and six-voice song structures. c64bridge's inspected SIDWAVE compiler explicitly constructs only voices 1–3, so dual-SID output is not an established capability there. [S08](../sources.md#s08), [S12](../sources.md#s12), [S24](../sources.md#s24)

VICE uses `-sidextra 1` and `-sid2address 0xd420` to select the additional chip. An illustrative interactive launch is:

```sh
x64sc -pal -sidextra 1 -sid2address 0xd420 -autostart song.prg
```

The [headless verifier](../../validation/native-vice-checks.md) uses these address flags with the local VICE 3.9 build, explicit 8580 selection and monitor-controlled startup. That tested route handles SID-Wizard's address selector without changing PRG bytes; the illustrative `-autostart` command above is not the tested unattended route. [S16](../sources.md#s16)

The [ordered-store VICE tracer](../tools/sid-program-analysis.md#reproduce-the-execution-evidence) also accepts callable PAL PSID v3 with two matching 6581s or 8580s at `$D400/$D420`. It compares both sound-register banks against the CPU oracle in a controlled harness, including independent filter values. Its [executed fixture](../../../tests/sid_vice_trace_test.py) validates this mechanism; full arrangement, audio and listening checks remain separate.

## Six-voice acceptance checks

- Play one test note on each voice independently and confirm both chip addresses respond.
- Verify that chip A's filter/volume changes do not change chip B's controls.
- Check channel routing and a mono downmix for balance.
- Test the declared SID models, including a mixed-model setup if supported and intended.
- Measure player CPU cost with all six voices and effects active.

Independent fixtures establish six distinct sounding frequency words, separate filter registers and simultaneous stops. Renderer tests use different pitches and either-chip-muted variants to verify independent stereo channels without crossfeed. The native fixture passes complete note scheduling, PCM health and sampled VICE register/cadence checks. Both chips share one PAL CPU-frame budget; adding a SID does not add CPU time.

Physical hardware, mixed chip models, mono-downmix musical balance and a complete dual-SID song's listening quality remain unverified. The current converter's 105-pattern/29-instrument limit also bounds long tick-grid arrangements; successful short-fixture playback does not establish that an arbitrary six-voice score will fit.
