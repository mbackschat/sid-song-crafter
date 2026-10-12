#include <sidplayfp/SidConfig.h>
#include <sidplayfp/SidTune.h>
#include <sidplayfp/SidTuneInfo.h>
#include <sidplayfp/builders/sidlite.h>
#include <sidplayfp/sidplayfp.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
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

static bool has_dual_sid_header(const char *path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Unable to open the SID input");
    std::array<unsigned char, 124> header{};
    input.read(reinterpret_cast<char *>(header.data()), header.size());
    const bool sid_header = std::string(reinterpret_cast<char *>(header.data()), 4) == "PSID"
        || std::string(reinterpret_cast<char *>(header.data()), 4) == "RSID";
    const unsigned int version = header[4] << 8 | header[5];
    if (!sid_header || input.gcount() < 124 || version < 2) return false;
    if (header[123] != 0) throw std::runtime_error("This renderer supports one or two SID chips");
    if (header[122] == 0) return false;
    // PSID parsers may discard invalid extra-SID addresses; validate the original declaration before loading.
    if (std::string(reinterpret_cast<char *>(header.data()), 4) != "PSID" || version != 3) {
        throw std::runtime_error("Two-SID rendering requires PSID v3");
    }
    if (header[122] != 0x42) throw std::runtime_error("Two-SID rendering requires SID bases $D400/$D420");
    const unsigned int flags = header[118] << 8 | header[119];
    if (flags != 0xa4 && flags != 0x54) throw std::runtime_error("Two-SID rendering requires explicit PAL and two same-model MOS6581 or MOS8580 chips without MUS/PlaySID flags");
    if (std::any_of(header.begin() + 18, header.begin() + 22, [](unsigned char value) { return value != 0; })) {
        throw std::runtime_error("Two-SID rendering requires VBI timing for every subtune");
    }
    return true;
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

int main(int argc, char **argv) {
    try {
        if (argc != 4 && (argc != 6 || std::string(argv[4]) != "--voices")) throw std::runtime_error("Usage: render-sid INPUT.sid OUTPUT.wav SECONDS [--voices 1,2,3|none] (PAL, 0 < seconds <= 600; voices is a one-SID control-mask diagnostic)");
        const bool voice_diagnostic = argc == 6;
        const std::array<bool, 3> voices = voice_diagnostic ? selected_voices(argv[5]) : std::array<bool, 3>{true, true, true};
        size_t parsed = 0;
        const double seconds = std::stod(argv[3], &parsed);
        if (parsed != std::string(argv[3]).size() || !std::isfinite(seconds) || seconds <= 0 || seconds > 600) {
            throw std::runtime_error("Seconds must be greater than zero and at most 600");
        }
        constexpr uint32_t rate = 44100;
        constexpr unsigned int cycles = 312 * 63;
        const uint32_t frame_count = std::max(1L, std::lround(seconds * rate));
        SIDLiteBuilder builder("SIDLite");
        const bool declared_dual = has_dual_sid_header(argv[1]);
        SidTune tune(argv[1]);
        if (!tune.getStatus()) throw std::runtime_error(tune.statusString());
        // SidTune starts unselected; psiddrv passes currentSong()-1 to init (libsidplayfp v3.1.1 src/psiddrv.cpp).
        if (tune.selectSong(0) == 0) throw std::runtime_error("Unable to select the SID's default subtune");
        const SidTuneInfo *tune_info = tune.getInfo();
        const unsigned int sid_count = tune_info->sidChips();
        unsigned int channels;
        switch (sid_count) {
            case 1:
                if (declared_dual) throw std::runtime_error("The declared second SID was not loaded");
                channels = 1;
                break;
            case 2:
                if (!declared_dual || tune_info->sidChipBase(0) != 0xd400 || tune_info->sidChipBase(1) != 0xd420
                    || tune_info->clockSpeed() != SidTuneInfo::CLOCK_PAL || tune_info->songSpeed() != SidTuneInfo::SPEED_VBI
                    || (tune_info->sidModel(0) != SidTuneInfo::SIDMODEL_6581 && tune_info->sidModel(0) != SidTuneInfo::SIDMODEL_8580)
                    || tune_info->sidModel(0) != tune_info->sidModel(1)) {
                    throw std::runtime_error("Unsupported two-SID playback contract");
                }
                channels = 2;
                break;
            default:
                throw std::runtime_error("This renderer supports one or two SID chips");
        }
        if (voice_diagnostic && sid_count != 1) throw std::runtime_error("Voice diagnostics require one SID chip");
        sidplayfp player;
        SidConfig config = player.config();
        config.frequency = rate;
        config.defaultC64Model = SidConfig::PAL;
        config.forceC64Model = true;
        config.defaultSidModel = SidConfig::MOS8580;
        // SidConfig::MAX_POWER_ON_DELAY defines larger values as randomized startup.
        config.powerOnDelay = 0;
        config.sidEmulation = &builder;
        if (!player.config(config) || !player.load(&tune)) throw std::runtime_error(player.error());
        if (player.installedSIDs() != sid_count) throw std::runtime_error("Installed SID count differs from the declared tune");
        if (voice_diagnostic) {
            // v3.1.1 sidemu masks GATE/waveform writes; true mutes despite the public header's enable wording: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/sidemu.cpp.
            for (unsigned int voice = 0; voice < voices.size(); ++voice) player.mute(0, voice, !voices[voice]);
        }
        player.initMixer(channels == 2);
        // v3.1.1 returns samples despite the header saying bytes: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591.
        const int buffer_size = player.getBufSize(cycles);
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
            const int samples = player.play(cycles);
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
                  << " / SIDLite: " << written << (channels == 1 ? " mono PCM16 samples" : " stereo PCM16 frames") << " at " << rate << " Hz\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
