#include <sidplayfp/SidConfig.h>
#include <sidplayfp/SidTune.h>
#include <sidplayfp/builders/sidlite.h>
#include <sidplayfp/sidplayfp.h>

#include <algorithm>
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

int main(int argc, char **argv) {
    try {
        if (argc != 4) throw std::runtime_error("Usage: render-sid INPUT.sid OUTPUT.wav SECONDS (PAL, one SID, 0 < seconds <= 600)");
        size_t parsed = 0;
        const double seconds = std::stod(argv[3], &parsed);
        if (parsed != std::string(argv[3]).size() || !std::isfinite(seconds) || seconds <= 0 || seconds > 600) {
            throw std::runtime_error("Seconds must be greater than zero and at most 600");
        }
        constexpr uint32_t rate = 44100;
        constexpr unsigned int cycles = 312 * 63;
        const uint32_t sample_count = std::max(1L, std::lround(seconds * rate));
        SIDLiteBuilder builder("SIDLite");
        SidTune tune(argv[1]);
        if (!tune.getStatus()) throw std::runtime_error(tune.statusString());
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
        if (player.installedSIDs() != 1) throw std::runtime_error("This renderer supports one SID chip");
        player.initMixer(false);
        // v3.1.1 returns samples despite the header saying bytes: https://github.com/libsidplayfp/libsidplayfp/blob/v3.1.1/src/player.cpp#L591.
        std::vector<short> buffer(player.getBufSize(cycles));
        std::ofstream output(argv[2], std::ios::binary);
        std::ofstream trace(std::string(argv[2]) + ".registers.tsv");
        if (!output || !trace) throw std::runtime_error("Unable to open output files");
        output.write("RIFF", 4);
        write_u32(output, 36 + sample_count * 2);
        output.write("WAVEfmt ", 8);
        write_u32(output, 16);
        write_u16(output, 1);
        write_u16(output, 1);
        write_u32(output, rate);
        write_u32(output, rate * 2);
        write_u16(output, 2);
        write_u16(output, 16);
        output.write("data", 4);
        write_u32(output, sample_count * 2);
        trace << "time_ms\tregisters_hex\n";
        uint32_t written = 0;
        while (written < sample_count) {
            const int samples = player.play(cycles);
            if (samples <= 0) throw std::runtime_error(player.error());
            if (static_cast<size_t>(samples) > buffer.size()) throw std::runtime_error("Mixer buffer is too small");
            const unsigned int mixed = player.mix(buffer.data(), samples);
            if (mixed == 0 || mixed > buffer.size()) throw std::runtime_error("Invalid mixer sample count");
            const unsigned int count = std::min(mixed, sample_count - written);
            for (unsigned int index = 0; index < count; ++index) write_u16(output, static_cast<uint16_t>(buffer[index]));
            written += count;
            uint8_t registers[32];
            if (!player.getSidStatus(0, registers)) throw std::runtime_error("SID register snapshot failed");
            trace << std::dec << player.timeMs() << '\t';
            for (uint8_t value : registers) trace << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned int>(value);
            trace << '\n';
        }
        output.close();
        trace.close();
        if (!output || !trace) throw std::runtime_error("Unable to finish output files");
        std::cout << "libsidplayfp " << LIBSIDPLAYFP_VERSION_MAJ << '.' << LIBSIDPLAYFP_VERSION_MIN << '.' << LIBSIDPLAYFP_VERSION_LEV
                  << " / SIDLite: " << written << " mono PCM16 samples at " << rate << " Hz\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
