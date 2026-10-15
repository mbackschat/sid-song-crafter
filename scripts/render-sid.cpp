#include <sidplayfp/SidConfig.h>
#include <sidplayfp/SidInfo.h>
#include <sidplayfp/SidTune.h>
#include <sidplayfp/SidTuneInfo.h>
#include <sidplayfp/builders/sidlite.h>
#include <sidplayfp/sidplayfp.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

static void write_u16(std::ostream &output, uint16_t value) {
    output.put(static_cast<char>(value & 255));
    output.put(static_cast<char>(value >> 8));
}

static void write_u32(std::ostream &output, uint32_t value) {
    write_u16(output, value & 65535);
    write_u16(output, value >> 16);
}

enum class DualSidProfile { None, PsidVbi, RsidNative };

static DualSidProfile dual_sid_profile(const char *path, SidConfig::c64_model_t render_clock, bool model_assumption) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Unable to open the SID input");
    std::array<unsigned char, 124> header{};
    input.read(reinterpret_cast<char *>(header.data()), header.size());
    const std::string format(reinterpret_cast<char *>(header.data()), 4);
    const bool sid_header = format == "PSID" || format == "RSID";
    const unsigned int version = header[4] << 8 | header[5];
    if (!sid_header || input.gcount() < 124 || version < 2) return DualSidProfile::None;
    if (model_assumption && (header[122] != 0 || header[123] != 0)) {
        throw std::runtime_error("SID model assumption requires one SID chip");
    }
    if (header[123] != 0) throw std::runtime_error("This renderer supports one or two SID chips");
    if (header[122] == 0) return DualSidProfile::None;
    // PSID parsers may discard invalid extra-SID addresses; validate the original declaration before loading.
    if (version != 3) {
        throw std::runtime_error("Two-SID rendering requires PSID or native RSID v3");
    }
    if (header[122] != 0x42) throw std::runtime_error("Two-SID rendering requires SID bases $D400/$D420");
    const unsigned int flags = header[118] << 8 | header[119];
    if (flags != 0xa4 && flags != 0x54 && flags != 0xa8 && flags != 0x58) {
        throw std::runtime_error("Two-SID rendering requires explicit PAL or NTSC and two same-model MOS6581 or MOS8580 chips without MUS/PlaySID/BASIC flags");
    }
    const SidConfig::c64_model_t declared_clock = (flags & 0x0c) == 4 ? SidConfig::PAL : SidConfig::NTSC;
    if (render_clock != declared_clock) throw std::runtime_error("Two-SID rendering clock must match the explicit header clock");
    if (std::any_of(header.begin() + 18, header.begin() + 22, [](unsigned char value) { return value != 0; })) {
        throw std::runtime_error("Two-SID PSID requires VBI timing; native RSID requires a zero reserved speed word");
    }
    if (format == "RSID") {
        if (header[6] != 0 || header[7] != 124 || header[8] != 0 || header[9] != 0
            || header[12] != 0 || header[13] != 0 || header[120] != 0 || header[121] != 0) {
            throw std::runtime_error("Native two-SID RSID requires a 124-byte header, zero header load/play addresses and no relocation");
        }
        return DualSidProfile::RsidNative;
    }
    return DualSidProfile::PsidVbi;
}

static std::array<bool, 3> selected_voices(const std::string &list) {
    std::array<bool, 3> selected{};
    if (list == "none") return selected;
    size_t start = 0;
    while (start < list.size()) {
        const size_t end = list.find(',', start);
        const std::string voice = list.substr(start, end == std::string::npos ? end : end - start);
        if (voice.size() != 1 || voice[0] < '1' || voice[0] > '3' || selected[voice[0] - '1']) {
            throw std::runtime_error("Voices must be distinct numbers 1,2,3 separated by commas, or none");
        }
        selected[voice[0] - '1'] = true;
        if (end == std::string::npos) return selected;
        start = end + 1;
    }
    throw std::runtime_error("Voices must not be empty or end with a comma");
}

static unsigned int selected_subtune(const std::string &value) {
    unsigned int song = 0;
    if (value.empty()) throw std::runtime_error("Subtune must be a positive one-based integer");
    for (char character : value) {
        if (character < '0' || character > '9') throw std::runtime_error("Subtune must be a positive one-based integer");
        const unsigned int digit = character - '0';
        if (song > (std::numeric_limits<unsigned int>::max() - digit) / 10) {
            throw std::runtime_error("Subtune is outside the supported integer range");
        }
        song = song * 10 + digit;
    }
    if (song == 0) throw std::runtime_error("Subtune must be a positive one-based integer");
    return song;
}

static const char *sid_model_name(SidTuneInfo::model_t model) {
    switch (model) {
        case SidTuneInfo::SIDMODEL_6581: return "MOS6581";
        case SidTuneInfo::SIDMODEL_8580: return "MOS8580";
        case SidTuneInfo::SIDMODEL_ANY: return "any";
        case SidTuneInfo::SIDMODEL_UNKNOWN: return "unknown";
    }
    throw std::runtime_error("Unsupported SID model");
}

template<size_t size>
static std::array<uint8_t, size> read_rom(const std::string &directory, const char *name) {
    const std::filesystem::path path = std::filesystem::path(directory) / name;
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) throw std::runtime_error("Unable to open C64 ROM: " + path.string());
    if (input.tellg() != static_cast<std::streamoff>(size)) {
        throw std::runtime_error("C64 ROM must contain exactly " + std::to_string(size) + " bytes: " + path.string());
    }
    std::array<uint8_t, size> rom{};
    input.seekg(0);
    if (!input.read(reinterpret_cast<char *>(rom.data()), rom.size())) {
        throw std::runtime_error("Unable to read C64 ROM: " + path.string());
    }
    return rom;
}

enum class RenderOption { Voices, Subtune, Clock, SidModelAssumption, RomDirectory };

struct RenderOptions {
    bool voice_diagnostic = false;
    bool explicit_subtune = false;
    bool explicit_clock = false;
    bool explicit_sid_model = false;
    bool explicit_rom_directory = false;
    std::string rom_directory;
    unsigned int subtune = 0;
    SidConfig::c64_model_t clock = SidConfig::PAL;
    SidConfig::sid_model_t assumed_sid_model = SidConfig::MOS8580;
    std::array<bool, 3> voices{true, true, true};
};

static RenderOptions parse_options(int argc, char **argv) {
    if (argc < 4) throw std::runtime_error("Usage: render-sid INPUT.sid OUTPUT.wav SECONDS [--voices 1,2,3|none] [--subtune N] [--clock pal|ntsc] [--assume-sid-model MOS6581|MOS8580] [--rom-dir DIRECTORY] (default PAL, 0 < seconds <= 600; subtune is one-based; voices is a one-SID control-mask diagnostic; model assumption requires an unknown-model one-SID input; RSID BASIC requires C64 ROMs)");
    RenderOptions options;
    for (int index = 4; index < argc; index += 2) {
        const std::string name = argv[index];
        RenderOption option;
        if (name == "--voices") option = RenderOption::Voices;
        else if (name == "--subtune") option = RenderOption::Subtune;
        else if (name == "--clock") option = RenderOption::Clock;
        else if (name == "--assume-sid-model") option = RenderOption::SidModelAssumption;
        else if (name == "--rom-dir") option = RenderOption::RomDirectory;
        else throw std::runtime_error("Unknown renderer option: " + name);
        if (index + 1 == argc) throw std::runtime_error("Renderer option requires a value: " + name);
        switch (option) {
            case RenderOption::Voices:
                if (options.voice_diagnostic) throw std::runtime_error("Duplicate --voices option");
                options.voices = selected_voices(argv[index + 1]);
                options.voice_diagnostic = true;
                break;
            case RenderOption::Subtune:
                if (options.explicit_subtune) throw std::runtime_error("Duplicate --subtune option");
                options.subtune = selected_subtune(argv[index + 1]);
                options.explicit_subtune = true;
                break;
            case RenderOption::Clock: {
                if (options.explicit_clock) throw std::runtime_error("Duplicate --clock option");
                const std::string clock = argv[index + 1];
                if (clock == "pal") options.clock = SidConfig::PAL;
                else if (clock == "ntsc") options.clock = SidConfig::NTSC;
                else throw std::runtime_error("Clock must be pal or ntsc");
                options.explicit_clock = true;
                break;
            }
            case RenderOption::SidModelAssumption: {
                if (options.explicit_sid_model) throw std::runtime_error("Duplicate --assume-sid-model option");
                const std::string model = argv[index + 1];
                if (model == "MOS6581") options.assumed_sid_model = SidConfig::MOS6581;
                else if (model == "MOS8580") options.assumed_sid_model = SidConfig::MOS8580;
                else throw std::runtime_error("Assumed SID model must be MOS6581 or MOS8580");
                options.explicit_sid_model = true;
                break;
            }
            case RenderOption::RomDirectory:
                if (options.explicit_rom_directory) throw std::runtime_error("Duplicate --rom-dir option");
                options.rom_directory = argv[index + 1];
                if (options.rom_directory.empty()) throw std::runtime_error("ROM directory must not be empty");
                options.explicit_rom_directory = true;
                break;
        }
    }
    return options;
}

int main(int argc, char **argv) {
    try {
        const RenderOptions options = parse_options(argc, argv);
        size_t parsed = 0;
        const double seconds = std::stod(argv[3], &parsed);
        if (parsed != std::string(argv[3]).size() || !std::isfinite(seconds) || seconds <= 0 || seconds > 600) {
            throw std::runtime_error("Seconds must be greater than zero and at most 600");
        }
        constexpr uint32_t rate = 44100;
        // libsidplayfp v3.1.1 src/player.cpp:241 dispatches scheduler events rather than CPU cycles; retain the legacy batch for stable snapshots.
        constexpr unsigned int batch_size = 19656;
        const uint32_t frame_count = std::max(1L, std::lround(seconds * rate));
        SIDLiteBuilder builder("SIDLite");
        const DualSidProfile dual_profile = dual_sid_profile(argv[1], options.clock, options.explicit_sid_model);
        SidTune tune(argv[1]);
        if (!tune.getStatus()) throw std::runtime_error(tune.statusString());
        // SidTune starts unselected; psiddrv passes currentSong()-1 to init (libsidplayfp v3.1.1 src/psiddrv.cpp).
        if (options.explicit_subtune && options.subtune > tune.getInfo()->songs()) {
            throw std::runtime_error("Subtune exceeds the SID's declared song count");
        }
        if (tune.selectSong(options.subtune) == 0) throw std::runtime_error("Unable to select the SID subtune");
        const SidTuneInfo *tune_info = tune.getInfo();
        if (tune_info->compatibility() == SidTuneInfo::COMPATIBILITY_BASIC && !options.explicit_rom_directory) {
            throw std::runtime_error("RSID BASIC requires --rom-dir with C64 KERNAL, BASIC and character ROMs");
        }
        const SidTuneInfo::clock_t selected_clock = options.clock == SidConfig::PAL ? SidTuneInfo::CLOCK_PAL : SidTuneInfo::CLOCK_NTSC;
        const unsigned int sid_count = tune_info->sidChips();
        if (options.explicit_sid_model) {
            if (sid_count != 1) throw std::runtime_error("SID model assumption requires one SID chip");
            if (tune_info->sidModel(0) != SidTuneInfo::SIDMODEL_UNKNOWN) {
                throw std::runtime_error("SID model assumption requires an unknown model declaration");
            }
        }
        unsigned int channels;
        switch (sid_count) {
            case 1:
                if (dual_profile != DualSidProfile::None) throw std::runtime_error("The declared second SID was not loaded");
                channels = 1;
                break;
            case 2: {
                const bool native = dual_profile == DualSidProfile::RsidNative;
                // libsidplayfp v3.1.1 PSID.cpp maps RSID to native/CIA metadata; its speed field remains reserved zero.
                const int speed = native ? SidTuneInfo::SPEED_CIA_1A : SidTuneInfo::SPEED_VBI;
                if (dual_profile == DualSidProfile::None || tune_info->sidChipBase(0) != 0xd400 || tune_info->sidChipBase(1) != 0xd420
                    || tune_info->clockSpeed() != selected_clock || tune_info->songSpeed() != speed
                    || (tune_info->compatibility() == SidTuneInfo::COMPATIBILITY_R64) != native
                    || (tune_info->sidModel(0) != SidTuneInfo::SIDMODEL_6581 && tune_info->sidModel(0) != SidTuneInfo::SIDMODEL_8580)
                    || tune_info->sidModel(0) != tune_info->sidModel(1)) {
                    throw std::runtime_error("Unsupported two-SID playback contract");
                }
                channels = 2;
                break;
            }
            default:
                throw std::runtime_error("This renderer supports one or two SID chips");
        }
        if (options.voice_diagnostic && sid_count != 1) throw std::runtime_error("Voice diagnostics require one SID chip");
        sidplayfp player;
        if (options.explicit_rom_directory) {
            const auto kernal = read_rom<8192>(options.rom_directory, "kernal-901227-03.bin");
            const auto basic = read_rom<8192>(options.rom_directory, "basic-901226-01.bin");
            const auto chargen = read_rom<4096>(options.rom_directory, "chargen-901225-01.bin");
            player.setRoms(kernal.data(), basic.data(), chargen.data());
            const std::array<const char *, 3> descriptions{
                player.info().kernalDesc(), player.info().basicDesc(), player.info().chargenDesc()
            };
            if (std::any_of(descriptions.begin(), descriptions.end(), [](const char *description) {
                return std::string(description) == "Unknown Rom";
            })) {
                throw std::runtime_error("Unrecognized C64 ROM contents in --rom-dir");
            }
        }
        SidConfig config = player.config();
        config.frequency = rate;
        config.defaultC64Model = options.clock;
        config.forceC64Model = true;
        config.defaultSidModel = options.assumed_sid_model;
        config.forceSidModel = false;
        // SidConfig::MAX_POWER_ON_DELAY defines larger values as randomized startup.
        config.powerOnDelay = 0;
        config.sidEmulation = &builder;
        if (!player.config(config) || !player.load(&tune)) throw std::runtime_error(player.error());
        if (player.installedSIDs() != sid_count) throw std::runtime_error("Installed SID count differs from the declared tune");
        if (options.voice_diagnostic) {
            // v3.1.1 sidemu masks GATE/waveform writes; true mutes despite the public header's enable wording: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidemu.cpp.
            for (unsigned int voice = 0; voice < options.voices.size(); ++voice) player.mute(0, voice, !options.voices[voice]);
        }
        player.initMixer(channels == 2);
        // v3.1.1 returns samples despite the header saying bytes: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591.
        const int buffer_size = player.getBufSize(batch_size);
        if (buffer_size <= 0) throw std::runtime_error("Invalid mixer buffer size");
        std::vector<short> buffer(buffer_size);
        std::ofstream output(argv[2], std::ios::binary);
        std::ofstream trace(std::string(argv[2]) + ".registers.tsv");
        if (!output || !trace) throw std::runtime_error("Unable to open output files");
        output.write("RIFF", 4);
        write_u32(output, 36 + frame_count * channels * 2);
        output.write("WAVEfmt ", 8);
        write_u32(output, 16);
        write_u16(output, 1);
        write_u16(output, channels);
        write_u32(output, rate);
        write_u32(output, rate * channels * 2);
        write_u16(output, channels * 2);
        write_u16(output, 16);
        output.write("data", 4);
        write_u32(output, frame_count * channels * 2);
        trace << "time_ms\tregisters_hex";
        if (channels == 2) trace << "\tregisters_sid2_hex";
        trace << '\n';
        uint32_t written = 0;
        while (written < frame_count) {
            const int samples = player.play(batch_size);
            if (samples <= 0) throw std::runtime_error(player.error());
            if (static_cast<size_t>(samples) * channels > buffer.size()) throw std::runtime_error("Mixer buffer is too small");
            unsigned int mixed;
            if (channels == 1) {
                mixed = player.mix(buffer.data(), samples);
            } else {
                // The v3.1.1 SimpleMixer cross-feeds chips; raw buffers preserve separate chip channels: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/simpleMixer.h.
                short *chip_buffers[2] = {nullptr, nullptr};
                player.buffers(chip_buffers);
                if (!chip_buffers[0] || !chip_buffers[1]) throw std::runtime_error("Missing SID chip audio buffer");
                for (int index = 0; index < samples; ++index) {
                    buffer[index * 2] = chip_buffers[0][index];
                    buffer[index * 2 + 1] = chip_buffers[1][index];
                }
                mixed = static_cast<unsigned int>(samples) * channels;
            }
            if (mixed == 0 || mixed > buffer.size() || mixed % channels != 0) throw std::runtime_error("Invalid mixer sample count");
            const unsigned int count = std::min(mixed / channels, frame_count - written);
            for (unsigned int index = 0; index < count * channels; ++index) write_u16(output, static_cast<uint16_t>(buffer[index]));
            written += count;
            trace << std::dec << player.timeMs();
            for (unsigned int sid = 0; sid < sid_count; ++sid) {
                uint8_t registers[32];
                if (!player.getSidStatus(sid, registers)) throw std::runtime_error("SID register snapshot failed");
                trace << '\t';
                for (uint8_t value : registers) trace << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned int>(value);
            }
            trace << '\n';
        }
        output.close();
        trace.close();
        if (!output || !trace) throw std::runtime_error("Unable to finish output files");
        std::cout << "libsidplayfp " << LIBSIDPLAYFP_VERSION_MAJ << '.' << LIBSIDPLAYFP_VERSION_MIN << '.' << LIBSIDPLAYFP_VERSION_LEV
                  << " / SIDLite: " << written << (channels == 1 ? " mono PCM16 samples" : " stereo PCM16 frames") << " at " << rate
                  << " Hz, clock " << (options.clock == SidConfig::PAL ? "PAL" : "NTSC")
                  << ", subtune " << tune_info->currentSong() << " of " << tune_info->songs()
                  << ", SID model " << sid_model_name(player.info().sidModel(0)) << " (";
        if (options.explicit_sid_model) std::cout << "assumed; declared unknown";
        else if (tune_info->sidModel(0) == SidTuneInfo::SIDMODEL_UNKNOWN || tune_info->sidModel(0) == SidTuneInfo::SIDMODEL_ANY) {
            std::cout << "fallback; declared " << sid_model_name(tune_info->sidModel(0));
        } else std::cout << "declared";
        std::cout << ')';
        if (options.explicit_rom_directory) {
            std::cout << ", C64 ROMs: " << player.info().kernalDesc() << "; "
                      << player.info().basicDesc() << "; " << player.info().chargenDesc();
        }
        std::cout << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
