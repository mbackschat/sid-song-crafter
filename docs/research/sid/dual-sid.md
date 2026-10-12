# Two SID chips

## What changes

Two independently addressed chips provide six oscillator/envelope voices and two independent filter/master-volume groups. Their audio may be mixed or separated into stereo by the hardware. Stereo output alone does not establish six independent voices: pseudo-stereo duplication is a different configuration. FPGASID's configuration documentation makes this distinction explicit. [S15](../sources.md#s15)

Project recommendation: put melody and an associated voice group on the first chip, accompaniment and sustained support on the second. Keep each chip's filter ownership explicit. A six-voice arrangement should also have a documented three-voice reduction if standard C64 playback matters.

## Address agreement

The first SID normally lives at `$D400`. Common second-chip choices include `$D420`, `$D500`, and `$DE00`, but hardware decoding and expansion conflicts decide what is usable. Standard mirrored SID space does not create a second chip. The hardware, exported tune, and emulator must agree on the selected address. [S05](../sources.md#s05), [S15](../sources.md#s15)

PSID v3 encodes the second SID location in header byte `$7A`: `$42` means `$D420`, `$50` means `$D500`, and `$E0` means `$DE00`. Valid address codes are restricted; do not accept arbitrary bytes. v4 adds the third-chip field, which this project does not currently need. [S13](../sources.md#s13)

## Tools and execution

GoatTracker Stereo is the most direct tracker candidate in this research. ChiptuneSAK's GoatTracker module recognizes three- and six-voice song structures. c64bridge's inspected SIDWAVE compiler explicitly constructs only voices 1–3, so dual-SID output is not an established capability there. [S08](../sources.md#s08), [S12](../sources.md#s12), [S24](../sources.md#s24)

The current online VICE manual documents `-sidextra 1` and `-sid2address 0xd420`. An illustrative launch is:

```sh
x64sc -pal -sidextra 1 -sid2address 0xd420 -autostart song.prg
```

Check the installed version's help before relying on current online flags; the user's local installation is VICE 3.9. This command has not been verified locally. [S16](../sources.md#s16)

## Six-voice acceptance checks

- Play one test note on each voice independently and confirm both chip addresses respond.
- Verify that chip A's filter/volume changes do not change chip B's controls.
- Check channel routing and a mono downmix for balance.
- Test the declared SID models, including a mixed-model setup if supported and intended.
- Measure player CPU cost with all six voices and effects active.

These are proposed tests. No dual-SID hardware or six-voice render has yet been validated in this workspace.
