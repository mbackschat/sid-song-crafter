# VICE startup findings and headless build

Use genuine headless VICE for reproducible agent-launched execution. The installed ARM64 GTK3 VICE 3.9 works in the user's desktop Terminal but its restricted launch reaches GTK realization and calls an unavailable OpenGL shader function through a null pointer. Disassembly identifies the `___glewCreateShader` call; accompanying monitor/display assertions do not establish why graphics initialization failed. Disabling colour or minimization does not resolve this failure, and a damaged installation or a particular macOS permission is not established.

The desktop command is:

```sh
/Applications/vice-arm64-gtk3-3.9/bin/x64sc -pal +logcolorize
```

Executable-path fallback and bundled-font warnings can be nonfatal. Desktop startup, audible output and binary-monitor readiness are separate checks; see [local setup](local-setup.md).

## Choose the headless build correctly

`--enable-headlessui` selects VICE's separate `src/arch/headless` implementation. It is a build option, not a runtime substitute for GTK. The installed GTK3 binary rejects `-headless`, and `-console` still requires GTK initialization. The pinned [VICE 3.9 macOS guide](../../.tools/vice-headless-3.9/source/doc/building/macOS-Howto.txt) states that the headless port needs neither GTK3 nor SDL2; CoreAudio can remain enabled independently.

The [Homebrew VICE formula](https://github.com/Homebrew/homebrew-core/blob/master/Formula/v/vice.rb) selects GTK3, so the project uses the [official VICE 3.9 release](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.9.tar.gz/download). Source archive SHA-256: `40202b63455e26b87ecc63eb5a52322c6fa3f57cab12acf0c227cf9f4daec370`, matching the SourceForge release listing. Preserve upstream notices and keep source and build output separate under `.tools/vice-headless-3.9/`.

## Build dependencies and pins

The release includes generated configure scripts; Autoconf/Automake regeneration is unnecessary for this build. Required local tools include Clang/macOS SDK, make, flex, yacc, dos2unix, xa and pkg-config. The focused emulator build below avoids documentation targets that may require Texinfo.

These Homebrew `arm64_golden_gate` bottles were verified for the local ARM64 macOS 27.0.1 host. Use matching packages on another platform.

| Build tool | Version | Official metadata | Bottle SHA-256 |
| --- | --- | --- | --- |
| pkgconf (`pkg-config`) | 3.0.8 | [pkgconf API](https://formulae.brew.sh/api/formula/pkgconf.json) | `5bb5d8521f63317b2fdbc7852fc6a865d3e3a2ec32c3ff2daf8c4aa0dd6123b9` |
| dos2unix | 7.5.7 | [dos2unix API](https://formulae.brew.sh/api/formula/dos2unix.json) | `7daae03638d9fcef0cd8bde6ea3b66af9611036d1349168a2152d6bda0506fdb` |
| xa | 2.4.1 | [xa API](https://formulae.brew.sh/api/formula/xa.json) | `81a8305c109fb1d5db2c7888fd8ebe73e414b272a268f99284616f833dc89923` |

Download from the project root and compare hashes with the pins before extraction:

```sh
curl -fL --connect-timeout 8 --max-time 20 https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.9.tar.gz -o /private/tmp/vice-3.9.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/pkgconf/blobs/sha256:5bb5d8521f63317b2fdbc7852fc6a865d3e3a2ec32c3ff2daf8c4aa0dd6123b9 -o /private/tmp/vice-build-pkgconf.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/dos2unix/blobs/sha256:7daae03638d9fcef0cd8bde6ea3b66af9611036d1349168a2152d6bda0506fdb -o /private/tmp/vice-build-dos2unix.tar.gz
curl -fL --connect-timeout 8 --max-time 20 -H 'Authorization: Bearer QQ==' https://ghcr.io/v2/homebrew/core/xa/blobs/sha256:81a8305c109fb1d5db2c7888fd8ebe73e414b272a268f99284616f833dc89923 -o /private/tmp/vice-build-xa.tar.gz
shasum -a 256 /private/tmp/vice-3.9.tar.gz /private/tmp/vice-build-pkgconf.tar.gz /private/tmp/vice-build-dos2unix.tar.gz /private/tmp/vice-build-xa.tar.gz
mkdir -p .tools/vice-headless-3.9/source .tools/vice-headless-3.9/build .local/vice-build-tools
tar -xzf /private/tmp/vice-3.9.tar.gz --strip-components 1 -C .tools/vice-headless-3.9/source
tar -xzf /private/tmp/vice-build-pkgconf.tar.gz -C .local/vice-build-tools
tar -xzf /private/tmp/vice-build-dos2unix.tar.gz -C .local/vice-build-tools
tar -xzf /private/tmp/vice-build-xa.tar.gz -C .local/vice-build-tools
install_name_tool -change '@@HOMEBREW_CELLAR@@/pkgconf/3.0.8/lib/libpkgconf.8.dylib' '@executable_path/../lib/libpkgconf.8.dylib' .local/vice-build-tools/pkgconf/3.0.8/bin/pkgconf
codesign --force --sign - .local/vice-build-tools/pkgconf/3.0.8/bin/pkgconf
```

`QQ==` is the public GHCR anonymous-access header. pkgconf's project-local executable needs the library-ID relocation shown above because the bottle contains an unrelocated Homebrew cellar path. dos2unix and xa require no relocation.

## Build workarounds

The macOS archive wrapper uses Bash process substitution to filter warnings and can fail when `/dev/fd` access is restricted. Select the actual archive tools with `AR=/usr/bin/ar RANLIB=/usr/bin/ranlib`; this needs no VICE source patch.

The focused `x64sc-program` target links `src/lib/linenoise-ng/liblinenoiseng.a` without declaring it as a prerequisite. Build that library explicitly before the emulator target. From the project root:

```sh
VICE_PROJECT_ROOT="$PWD"
VICE_BUILD_TOOLS="$VICE_PROJECT_ROOT/.local/vice-build-tools"
export PATH="$VICE_BUILD_TOOLS/pkgconf/3.0.8/bin:$VICE_BUILD_TOOLS/dos2unix/7.5.7/bin:$VICE_BUILD_TOOLS/xa/2.4.1/bin:$PATH"
cd "$VICE_PROJECT_ROOT/.tools/vice-headless-3.9/build"
../source/configure --prefix="$VICE_PROJECT_ROOT/.local/vice-headless-3.9" --enable-headlessui --disable-html-docs --disable-pdf-docs --disable-openmp --disable-hidmgr --without-libcurl --without-png
make -C src/lib/linenoise-ng -j4 AR=/usr/bin/ar RANLIB=/usr/bin/ranlib
make -C src -j4 AR=/usr/bin/ar RANLIB=/usr/bin/ranlib x64sc-program
```

Configure should report `GUI: Headless`, CoreAudio and AudioUnit support. The executable is `.tools/vice-headless-3.9/build/src/x64sc`. This local build uses the existing gettext library at `/opt/homebrew/opt/gettext/lib/libintl.8.dylib`, so it is not a standalone distributable. It avoids GTK/GDK/OpenGL/GLEW while retaining macOS frameworks through VICE's shared platform configuration. Bound builds with a subprocess deadline.

## Runtime checks and limitations

Use normal startup rather than `-version` as the readiness test:

```sh
mkdir -p .local/vice-headless-3.9/state/vice .local/vice-headless-3.9/config
env -u DISPLAY -u WAYLAND_DISPLAY XDG_CONFIG_HOME="$PWD/.local/vice-headless-3.9/config" XDG_STATE_HOME="$PWD/.local/vice-headless-3.9/state" .tools/vice-headless-3.9/build/src/x64sc -config /dev/null -directory /Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice -pal -sounddev dummy +logcolorize -limitcycles 1000000
```

A headless runtime banner, ROM initialization and deliberate `cycle limit reached` establish operational startup. VICE 3.9 uses exit status 1 for that limit; a dummy-audio cycle test does not establish music or audible output. The installed resource directory supplies generated assets omitted by a raw source-data directory.

The `-version` shortcut calls `archdep_program_name()` in `src/main.c` before `archdep_init()` initializes the fallback `argv[0]`. If macOS `proc_pidpath()` fails, the shortcut lacks that fallback and can fail with `argv[0] is NULL`. Ordinary startup initializes it in time. This affects both GTK and headless binaries; use their runtime banner for version/readiness when the shortcut fails.

Localhost monitor binding is independently denied in the restricted runner (`bind() failed: Operation not permitted`). A genuine headless executable therefore supports offline file-based verification here but does not establish a live c64bridge monitor connection. Use [the PRG/audio workflow](../workflows/audio-workflow.md#full-prg-execution-in-headless-vice) and [native checkpoints](../validation/native-vice-checks.md); a live monitor requires a runner that permits localhost sockets.

## External monitor attachment

The pinned bridge's `ViceBackend.ensureProcessInternal()` probes the configured monitor with `info()` and `exitMonitor()` before launching. A successful probe attaches without resetting or taking ownership of an externally started process; bridge shutdown terminates only supervised processes. A failed probe falls through to managed launch, so this is not an unconditional attach-only mode.

The [binary-monitor manual](https://vice-emu.sourceforge.io/vice_13.html) documents `-binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502`. The [resource manual](https://vice-emu.sourceforge.io/vice_6.html) defines `BinaryMonitorServer` and `BinaryMonitorServerAddress`; [text-monitor `resourceset`](https://vice-emu.sourceforge.io/vice_12.html) can enable them on an existing desktop instance, followed by `x` to resume. Require a successful binary VICE Info response for readiness. This attachment workflow is source-supported but remains unverified locally.
