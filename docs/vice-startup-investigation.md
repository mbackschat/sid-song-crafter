# VICE startup investigation

Investigated on 2026-10-12 using the installed ARM64 GTK3 VICE 3.9 distribution at `/Applications/vice-arm64-gtk3-3.9`. See [local setup](local-setup.md) for the MCP configuration and earlier launch results.

## Confirmed failure locus

The bridge's startup crash reaches GTK window realization, then calls an unavailable OpenGL function. Two independent macOS crash reports, `~/Library/Logs/DiagnosticReports/x64sc-2026-10-12-200455.ips` and `x64sc-2026-10-12-201330.ips`, both report `EXC_BAD_ACCESS` at address zero on the main thread, followed by the same VICE frames at image offsets `0x229de0`, `0x229350`, and `0x228f3c`, and `gtk_widget_realize` / `gtk_widget_map` frames.

Disassembly of the installed executable identifies the call immediately before return address `0x229de0`: instructions at image offsets `0x229dd4` and `0x229dd8` load `___glewCreateShader`, and `0x229ddc` executes `blr x8`. The null program counter therefore identifies a call through a null OpenGL shader function pointer. This is stronger evidence than the accompanying `GDK_IS_MONITOR` assertions alone. A successful graphics context and loaded shader entry points are required before this rendering path can run; the installed build does not stop before the invalid call in this execution context.

The explanation that the restricted process cannot initialize its graphics environment is supported by the repeated monitor assertions and a later `Failed to initialize CVDisplayLink!` warning, but the exact reason that GLEW leaves the entry point unavailable was not independently instrumented. Do not claim a damaged installation or identify a specific macOS permission as proven.

The earlier direct shell `-version` failure is a different startup path. Report `x64sc-2026-10-12-190715.ips` shows `_platform_strlen` followed by VICE offsets `0x28110`, `0x283e0`, and `0x29b70`, rather than the GTK realization frames. It should not be used as evidence for the OpenGL crash.

## Desktop comparison and unsuccessful alternatives

The user reported that `/Applications/vice-arm64-gtk3-3.9/bin/x64sc -pal +logcolorize` opens a window from an ordinary desktop Terminal and prints `VICE Version 3.9`. The executable-path fallback and `PetMe1282Y.ttf` warning are nonfatal in that run. This establishes a working desktop launch by user observation; it does not establish agent-launched playback, audible output, or a binary-monitor connection.

The user subsequently chose genuine headless operation. No UI actions or AppleScript execution were performed. No user-owned VICE instance was stopped.

| Probe | Result | Evidence |
| --- | --- | --- |
| Bridge launch with `-pal -minimized` | Exit 139 during GTK realization | Earlier diagnostic logs listed in [local setup](local-setup.md) |
| Add `+logcolorize` | Same exit 139 | `.local/c64bridge/diagnostics/2026-10-12T18-13-27-353Z-91203-mcp-server.ndjson` |
| Remove `-minimized` | Same exit 139 | Earlier comparison documented in [local setup](local-setup.md) |
| Direct binary with `-console` | `SIGTRAP`: `Can't create a GtkStyleContext without a display connection` | `/private/tmp/vice-startup-console.stderr.log` |
| Direct binary with `-headless` | Exit 255: `Unknown option '-headless'` | `/private/tmp/vice-startup-headless.stderr.log` |

The direct probes used `/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/bin/x64sc`, the GTK environment values from the installed launcher, and arguments `-config /dev/null -directory /Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice -sounddev dummy -pal +logcolorize -limitcycles 1000000`, prefixed respectively with `-console` or `-headless`. The Bun subprocess probe imposed a six-second termination deadline and a seven-second kill deadline; both processes exited before either deadline. Probe source is `/private/tmp/vice-startup-probe.mjs`. No note was played by these probes.

The installed terminal launcher initializes the bundled GTK environment and invokes the internal executable; the `.app` executables are application launchers rather than alternate headless C64 emulators. An inventory of `/Applications` and `/opt/homebrew` found no second installed `x64`, `x64sc`, or `vsid` implementation. The bridge's comment that runtime `-headless` requires VICE 3.5+ does not match this GTK3 build's accepted command-line options.

## Genuine headless build

VICE's official build option is `--enable-headlessui`. This selects separate sources under `src/arch/headless`; it is not a runtime switch for the installed GTK3 binary. The VICE 3.9 [macOS build guide](../.tools/vice-headless-3.9/source/doc/building/macOS-Howto.txt) explicitly states that the headless port needs neither GTK3 nor SDL2. The 3.9 configure source selects CoreAudio independently on macOS, so a headless build can retain native sound output. The [official configure source](https://github.com/VICE-Team/svn-mirror/blob/main/vice/configure.ac) documents the same build selection, but the local investigation uses the pinned 3.9 release rather than a moving development snapshot.

The [official VICE 3.9 source release](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.9.tar.gz/download) was downloaded successfully from `https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.9.tar.gz` to `/private/tmp/vice-3.9.tar.gz`. Its SHA-256 is `40202b63455e26b87ecc63eb5a52322c6fa3f57cab12acf0c227cf9f4daec370`, matching the checksum published by SourceForge. Source was extracted into `.tools/vice-headless-3.9/source`; build output is separate under `.tools/vice-headless-3.9/build`, with a project-local install prefix planned at `.local/vice-headless-3.9`.

The first bounded configure attempt used:

```sh
cd .tools/vice-headless-3.9/build
../source/configure --prefix=/Users/mbackschat/Projects/c64-sid-skill/.local/vice-headless-3.9 --enable-headlessui --disable-html-docs --disable-pdf-docs --disable-openmp --disable-hidmgr --without-libcurl --without-png
```

Clang, the macOS SDK, `make`, `flex`, and `yacc` are available. The first configuration stopped with `configure: error: The dos2unix tool is missing, please install dos2unix`; `xa` and `pkg-config` were also absent from `PATH` and are mandatory checks later in the same configure source. The generated release configure exists, so regenerating it with Autoconf/Automake is unnecessary. It accepts Automake's `missing makeinfo` wrapper; building documentation may still need Texinfo, so verification uses the `x64sc-program` target rather than a distribution or documentation build. No executable was substituted with a no-op to pass a check.

The [Homebrew VICE formula](https://github.com/Homebrew/homebrew-core/blob/master/Formula/v/vice.rb), inspected on 2026-10-12, selects `--enable-gtk3ui`; the [formula API](https://formulae.brew.sh/api/formula/vice.json) has no headless option. Its `-console` smoke test does not turn the package into a genuine headless build. Accordingly, the installation uses VICE's official source while obtaining the missing tools from Homebrew bottles.

The following Homebrew `arm64_golden_gate` bottles match this ARM64 macOS 27.0.1 host. Each was downloaded using its URL from the official formula API, verified against the published SHA-256, and extracted under `.local/vice-build-tools`, retaining the formula/version directory. All three executable version probes succeeded.

| Build tool | Version | Official metadata | Bottle SHA-256 |
| --- | --- | --- | --- |
| pkgconf (`pkg-config`) | 3.0.8 | [pkgconf API](https://formulae.brew.sh/api/formula/pkgconf.json) | `5bb5d8521f63317b2fdbc7852fc6a865d3e3a2ec32c3ff2daf8c4aa0dd6123b9` |
| dos2unix | 7.5.7 | [dos2unix API](https://formulae.brew.sh/api/formula/dos2unix.json) | `7daae03638d9fcef0cd8bde6ea3b66af9611036d1349168a2152d6bda0506fdb` |
| xa | 2.4.1 | [xa API](https://formulae.brew.sh/api/formula/xa.json) | `81a8305c109fb1d5db2c7888fd8ebe73e414b272a268f99284616f833dc89923` |

pkgconf's bottled executable initially references the unrelocated path `@@HOMEBREW_CELLAR@@/pkgconf/3.0.8/lib/libpkgconf.8.dylib`. In the project-local copy only, `install_name_tool -change` replaced this with `@executable_path/../lib/libpkgconf.8.dylib`, followed by `codesign --force --sign -` on that executable. The dos2unix and xa bottles are marked `any_skip_relocation` and required no binary edits. No system Homebrew installation or `/Applications` file was changed.

Pinned download and staging commands, executed from the project root, are:

```sh
curl -fL --connect-timeout 8 --max-time 20 https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.9.tar.gz -o /private/tmp/vice-3.9.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/pkgconf/blobs/sha256:5bb5d8521f63317b2fdbc7852fc6a865d3e3a2ec32c3ff2daf8c4aa0dd6123b9 -o /private/tmp/vice-build-pkgconf.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/dos2unix/blobs/sha256:7daae03638d9fcef0cd8bde6ea3b66af9611036d1349168a2152d6bda0506fdb -o /private/tmp/vice-build-dos2unix.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/xa/blobs/sha256:81a8305c109fb1d5db2c7888fd8ebe73e414b272a268f99284616f833dc89923 -o /private/tmp/vice-build-xa.tar.gz
shasum -a 256 /private/tmp/vice-3.9.tar.gz /private/tmp/vice-build-pkgconf.tar.gz /private/tmp/vice-build-dos2unix.tar.gz /private/tmp/vice-build-xa.tar.gz
```

Compare those hashes with the pinned values above before extraction. `QQ==` is the public GHCR anonymous access header used for Homebrew bottles, not a personal credential.

```sh
mkdir -p .tools/vice-headless-3.9/source .tools/vice-headless-3.9/build .local/vice-build-tools
tar -xzf /private/tmp/vice-3.9.tar.gz --strip-components 1 -C .tools/vice-headless-3.9/source
tar -xzf /private/tmp/vice-build-pkgconf.tar.gz -C .local/vice-build-tools
tar -xzf /private/tmp/vice-build-dos2unix.tar.gz -C .local/vice-build-tools
tar -xzf /private/tmp/vice-build-xa.tar.gz -C .local/vice-build-tools
install_name_tool -change '@@HOMEBREW_CELLAR@@/pkgconf/3.0.8/lib/libpkgconf.8.dylib' '@executable_path/../lib/libpkgconf.8.dylib' .local/vice-build-tools/pkgconf/3.0.8/bin/pkgconf
codesign --force --sign - .local/vice-build-tools/pkgconf/3.0.8/bin/pkgconf
```

Repeating configure with these three versioned `bin` directories prepended to `PATH` succeeded. Its summary explicitly reports `GUI: Headless`, `CoreAudio sound support: yes`, and `AudioUnit sound support: yes`. The full successful output is `.tools/vice-headless-3.9/build/configure-output.log`.

The first bounded `make -C src -j4 x64sc-program` attempt failed in VICE's `src/arch/shared/macOS-wrap-ar.sh` at line 8 with `/dev/fd/62: Operation not permitted`. The wrapper uses Bash process substitution solely to filter archive warnings; three independent archives (`libhwsiddrv.a`, `libtapeport.a`, and `libc64sc.a`) reproduced the same mechanism. Output is preserved at `.tools/vice-headless-3.9/build/build-wrapper-failure.log`. The rerun selects the actual native tools through Make variables, using `AR=/usr/bin/ar RANLIB=/usr/bin/ranlib`, without editing VICE source.

The next attempt compiled the C64 core, reSID, and headless libraries, then failed at the linker because `src/lib/linenoise-ng/liblinenoiseng.a` was missing. The upstream focused `x64sc-program` target includes this archive in its link arguments but omits it from its declared prerequisites. Building that library explicitly and relinking succeeded; a full recursive build would include it through `src/lib`. This is a dependency defect in the focused upstream target, not a C64 or sound implementation failure. Combined output, including the failed link and successful rerun, is `.tools/vice-headless-3.9/build/build-output.log`.

The complete successful build sequence is:

```sh
VICE_BUILD_TOOLS=/Users/mbackschat/Projects/c64-sid-skill/.local/vice-build-tools
export PATH="$VICE_BUILD_TOOLS/pkgconf/3.0.8/bin:$VICE_BUILD_TOOLS/dos2unix/7.5.7/bin:$VICE_BUILD_TOOLS/xa/2.4.1/bin:$PATH"
cd /Users/mbackschat/Projects/c64-sid-skill/.tools/vice-headless-3.9/build
../source/configure --prefix=/Users/mbackschat/Projects/c64-sid-skill/.local/vice-headless-3.9 --enable-headlessui --disable-html-docs --disable-pdf-docs --disable-openmp --disable-hidmgr --without-libcurl --without-png
make -C src/lib/linenoise-ng -j4 AR=/usr/bin/ar RANLIB=/usr/bin/ranlib
make -C src -j4 AR=/usr/bin/ar RANLIB=/usr/bin/ranlib x64sc-program
```

Each build attempt had a cancellation deadline of at most 120 seconds. The binary is `.tools/vice-headless-3.9/build/src/x64sc`; no global install was performed. It links the existing `/opt/homebrew/opt/gettext/lib/libintl.8.dylib`, so this local binary is not a standalone distributable. `otool -L` confirms no GTK, GDK, OpenGL, or GLEW library dependencies; VICE's common macOS configure path still links native frameworks including AppKit, CoreText, CoreServices, and CoreGraphics. Its startup source is `src/arch/headless/main.c`, which calls the normal emulation entry point without a GTK application loop.

## Verified headless execution

The following direct cycle probe succeeded with both display environment variables absent:

```sh
mkdir -p .local/vice-headless-3.9/state/vice .local/vice-headless-3.9/config
env -u DISPLAY -u WAYLAND_DISPLAY XDG_CONFIG_HOME=/Users/mbackschat/Projects/c64-sid-skill/.local/vice-headless-3.9/config XDG_STATE_HOME=/Users/mbackschat/Projects/c64-sid-skill/.local/vice-headless-3.9/state .tools/vice-headless-3.9/build/src/x64sc -config /dev/null -directory /Users/mbackschat/Projects/c64-sid-skill/.tools/vice-headless-3.9/source/data -pal -sounddev dummy +logcolorize -limitcycles 1000000
```

The process printed `Initialising headless ui` and `VICE Version 3.9`, loaded C64 and drive ROMs, emulated to `cycle limit reached`, and exited with code 1 before the six-second safety deadline. Code 1 is expected for VICE 3.9's cycle-limit oracle; the shutdown was deliberate rather than a startup crash. Output is `.local/vice-headless-3.9/cycles-probe.log`. This test used the dummy sound driver and does not establish audible playback or music correctness.

The source-data probe reported missing default keymaps and the MPS803 printer charset, a `/dev/null` config version warning, dummy sound buffer overflows, and an unknown `SaveResourcesOnExit` resource during shutdown. These warnings did not prevent the cycle oracle from completing. The already installed resource directory at `/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice` contains generated assets and is a candidate for subsequent monitor tests; successful use must be verified separately.

A separate bounded headless `-version` probe still exited with code 1 and the early `failed to retrieve executable path` / `argv[0] is NULL` messages. Its output is `.local/vice-headless-3.9/version-probe.log`. Normal operational arguments reach the headless initialization and cycle oracle, so the failing early version shortcut is not evidence that the compiled emulator cannot run. Neither `VICE_HEADLESS=1` nor runtime `-headless` should be inferred necessary for a binary compiled with `--enable-headlessui`; bridge monitor startup is a separate verification step.

The pinned source explains the early version failure precisely. `src/main.c` handles `-version` in its early option loop by calling `archdep_program_name()` before calling `archdep_init()`. `src/arch/headless/archdep.c` supplies the fallback argument through `archdep_program_path_set_argv0()` inside that later initialization. On macOS, `src/arch/shared/archdep_program_path.c` first tries `proc_pidpath()`; if that call fails, it requires the initialized fallback reference. Thus the version shortcut breaks the initialization-order invariant when executable-path retrieval is unavailable, while ordinary startup initializes the fallback before using it. The same observable failure occurs in the installed GTK executable and the newly compiled headless executable. Runtime banners identify 3.9 successfully without relying on this shortcut; no source patch was applied.

The subsequent root-agent monitor test on `127.0.0.1:6512` distinguished a separate sandbox constraint: the genuine headless executable printed `vice_network_server(): bind() failed: Operation not permitted`, followed by `monitor_binary_activate(): could not initialize listening socket`. The corresponding bounded c64bridge attempt timed out before monitor readiness; diagnostics are `.local/c64bridge/diagnostics/2026-10-12T18-43-24-649Z-28232-mcp-server.ndjson`. Its child output tails were empty within the short startup window, so the direct binary output is the evidence for denied binding. The agent closed its owned processes with `SIGTERM`; it did not retry by escalating or changing bind targets. The installed resource directory allowed normal ROM startup in the direct probe.

Consequently, this restricted session supports headless offline emulation but has not established c64bridge's live binary-monitor workflow. The subsequent [file-based PRG and audio verification](audio-workflow.md#full-prg-execution-in-headless-vice) successfully ran the program through BASIC, checked its return and SID state, and captured all nine pitches with reSID MOS8580. It uses ordinary files without a listening socket; host speaker playback remains unverified.

## External monitor behavior

Source inspection establishes an optional desktop attachment workflow, but it was not exercised successfully in this investigation. In c64bridge, `ViceBackend.ensureProcessInternal()` first connects to a configured local monitor and sends `info()` and `exitMonitor()`. A successful response returns before launching, resetting, or registering a supervised process. Bridge shutdown only terminates handles in its supervisor map, so it does not take ownership of an externally started instance. A failed local probe falls through to a managed launch; this is not an unconditional attach-only mode.

The [official binary-monitor manual](https://vice-emu.sourceforge.io/vice_13.html) documents `-binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502`. The [monitor resource manual](https://vice-emu.sourceforge.io/vice_6.html) defines `BinaryMonitorServer` and `BinaryMonitorServerAddress`; the [text-monitor manual](https://vice-emu.sourceforge.io/vice_12.html) defines `resourceset`. Those resources can enable a monitor on an existing desktop instance without restarting it, followed by the text-monitor `x` command to resume emulation. No endpoint is considered ready until a binary VICE Info response succeeds; an open window alone is insufficient.
