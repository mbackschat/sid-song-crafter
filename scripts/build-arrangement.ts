import { readFile, mkdir, writeFile } from "node:fs/promises";
import { basename, dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assemblyToPrgDetailed } from "../.tools/c64bridge/src/tools/translation/assembler.ts";

export const PAL_CLOCK_HZ = 17734475 / 18;
export const PAL_CYCLES_PER_FRAME = 312 * 63;
export const PAL_TICKS_PER_SECOND = PAL_CLOCK_HZ / PAL_CYCLES_PER_FRAME;

export type Instrument = {
  waveform: number;
  attackDecay: number;
  sustainRelease: number;
  pulseWidth?: number;
};
export type ScoreEvent = { startBeat: number; durationBeats: number; midi: number | null };
export type Score = {
  title: string;
  composer: string;
  quarterBpm: number;
  totalBeats: number;
  tailTicks?: number;
  volume?: number;
  voices: { instrument: Instrument; events: ScoreEvent[] }[];
};
export type Event = ScoreEvent & {
  voice: number;
  startTick: number;
  durationTicks: number;
  frequencyWord: number;
  gateOffTick: number | null;
};
export type RegisterWrite = { tick: number; address: number; value: number };

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function integer(value: number, name: string, min: number, max: number): void {
  if (!Number.isInteger(value) || value < min || value > max) throw new Error(`${name} must be an integer in ${min}..${max}`);
}

function positive(value: number, name: string): void {
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be positive and finite`);
}

function metadata(value: string, name: string): void {
  if (typeof value !== "string" || value.length > 31 || /[^\x20-\x7e]/.test(value)) throw new Error(`${name} must be at most 31 printable ASCII characters`);
}

export function compileScore(score: Score) {
  metadata(score.title, "title");
  metadata(score.composer, "composer");
  positive(score.quarterBpm, "quarterBpm");
  positive(score.totalBeats, "totalBeats");
  const tailTicks = score.tailTicks ?? 25;
  const volume = score.volume ?? 15;
  integer(tailTicks, "tailTicks", 1, 65535);
  integer(volume, "volume", 1, 15);
  if (!Array.isArray(score.voices) || score.voices.length !== 3) throw new Error("Score must contain exactly three voices");
  const quantize = (beat: number) => Math.round(beat * 60 / score.quarterBpm * PAL_TICKS_PER_SECOND);
  const scoreTicks = quantize(score.totalBeats);
  integer(scoreTicks, "quantized totalBeats", 1, Number.MAX_SAFE_INTEGER - tailTicks);
  const totalTicks = scoreTicks + tailTicks;
  const writes: (RegisterWrite & { order: number })[] = [];
  const events: Event[] = [];
  let order = 0;
  const addWrite = (tick: number, address: number, value: number) => writes.push({ tick, address, value, order: order++ });
  const voices = score.voices.map((voice, index) => {
    const instrument = voice.instrument;
    if (!instrument || ![16, 32, 64].includes(instrument.waveform)) throw new Error(`Voice ${index} waveform must be triangle (16), sawtooth (32), or pulse (64)`);
    integer(instrument.attackDecay, `Voice ${index} attackDecay`, 0, 255);
    integer(instrument.sustainRelease, `Voice ${index} sustainRelease`, 0, 255);
    integer(instrument.pulseWidth ?? 0x800, `Voice ${index} pulseWidth`, 0, 4095);
    if (!Array.isArray(voice.events)) throw new Error(`Voice ${index} events must be an array`);
    let previousEnd = 0;
    const compiledEvents = voice.events.map((event, eventIndex): Event => {
      if (!Number.isFinite(event.startBeat) || event.startBeat < 0) throw new Error(`Voice ${index} event ${eventIndex} startBeat must be nonnegative and finite`);
      positive(event.durationBeats, `Voice ${index} event ${eventIndex} durationBeats`);
      const endBeat = event.startBeat + event.durationBeats;
      if (event.startBeat + 1e-9 < previousEnd) throw new Error(`Voice ${index} events overlap or are not ordered`);
      if (endBeat > score.totalBeats + 1e-9) throw new Error(`Voice ${index} event exceeds totalBeats`);
      previousEnd = endBeat;
      const startTick = quantize(event.startBeat);
      const endTick = quantize(endBeat);
      const durationTicks = endTick - startTick;
      if (durationTicks < 1) throw new Error(`Voice ${index} event ${eventIndex} must quantize to at least one PAL tick`);
      let frequencyWord = 0;
      let gateOffTick: number | null = null;
      if (event.midi !== null) {
        integer(event.midi, `Voice ${index} event ${eventIndex} midi`, 0, 127);
        frequencyWord = Math.round(440 * 2 ** ((event.midi - 69) / 12) * 2 ** 24 / PAL_CLOCK_HZ);
        integer(frequencyWord, `Voice ${index} SID frequency for midi ${event.midi}`, 1, 65535);
        // Absolute boundaries avoid rounding drift; one-frame grace notes retain their pitch without an invented rest.
        const releaseGap = durationTicks === 1 ? 0 : Math.min(2, Math.max(1, Math.round(durationTicks * 0.1)));
        gateOffTick = endTick - releaseGap;
        const base = 0xd400 + index * 7;
        addWrite(startTick, base, frequencyWord & 255);
        addWrite(startTick, base + 1, frequencyWord >> 8);
        addWrite(startTick, base + 4, instrument.waveform | 1);
        addWrite(gateOffTick, base + 4, instrument.waveform);
      }
      const compiled = { voice: index, midi: event.midi, startBeat: event.startBeat, durationBeats: event.durationBeats, startTick, durationTicks, frequencyWord, gateOffTick };
      events.push(compiled);
      return compiled;
    });
    return { instrument: { ...instrument, pulseWidth: instrument.pulseWidth ?? 0x800 }, events: compiledEvents };
  });
  for (let voice = 0; voice < 3; voice++) addWrite(totalTicks, 0xd404 + voice * 7, voices[voice].instrument.waveform);
  addWrite(totalTicks, 0xd418, 0);
  writes.sort((a, b) => a.tick - b.tick || a.order - b.order);
  const registerWrites: RegisterWrite[] = writes.map(({ tick, address, value }) => ({ tick, address, value }));
  let previousTick = 0;
  const stream: number[] = [];
  for (const write of registerWrites) {
    const delay = write.tick - previousTick;
    integer(delay, "16-bit delay between register writes", 0, 65535);
    stream.push(delay & 255, delay >> 8, write.address - 0xd400, write.value);
    previousTick = write.tick;
  }
  stream.push(0, 0, 255, 0);
  return { quarterBpm: score.quarterBpm, volume, scoreTicks, totalTicks, durationSeconds: totalTicks / PAL_TICKS_PER_SECOND, voices, events, writes: registerWrites, stream };
}

function byteTable(label: string, bytes: number[]): string {
  const lines = [];
  for (let i = 0; i < bytes.length; i += 32) lines.push(`    .byte ${bytes.slice(i, i + 32).join(", ")}`);
  return `${label}:\n${lines.join("\n")}\n${label}_end:\n`;
}

export async function buildArrangement({ source, output = join(root, "build"), name = basename(source, ".json") }: { source: string; output?: string; name?: string }) {
  if (!/^[A-Za-z0-9_-]+$/.test(name)) throw new Error("Output name must contain only letters, numbers, underscores or hyphens");
  const score: Score = JSON.parse(await readFile(source, "utf8"));
  const compiled = compileScore(score);
  const assembly = [
    `VOLUME = ${compiled.volume}`,
    ...compiled.voices.flatMap(({ instrument }, index) => [
      `VOICE_${index}_WAVEFORM = ${instrument.waveform}`,
      `VOICE_${index}_ATTACK_DECAY = ${instrument.attackDecay}`,
      `VOICE_${index}_SUSTAIN_RELEASE = ${instrument.sustainRelease}`,
      `VOICE_${index}_PULSE_LOW = ${instrument.pulseWidth & 255}`,
      `VOICE_${index}_PULSE_HIGH = ${instrument.pulseWidth >> 8}`,
    ]),
    await readFile(join(root, "songs/player-three-voice.asm"), "utf8"),
    byteTable("event_stream", compiled.stream),
  ].join("\n");
  const assembled = assemblyToPrgDetailed(assembly, { fileName: `${name}.asm` });
  const symbols = Object.fromEntries(assembled.symbols);
  const loadAddress = assembled.prg.readUInt16LE(0);
  const payloadEndAddress = loadAddress + assembled.prg.length - 2;
  if (payloadEndAddress > 0xa000) throw new Error(`Arrangement payload ends at $${payloadEndAddress.toString(16)}; it must fit below BASIC ROM at $A000`);
  const payload = assembled.prg.subarray(2 + 0x1000 - loadAddress);
  const header = Buffer.alloc(0x7c);
  header.write("PSID");
  header.writeUInt16BE(2, 4);
  header.writeUInt16BE(0x7c, 6);
  header.writeUInt16BE(0x1000, 8);
  header.writeUInt16BE(symbols.init, 10);
  header.writeUInt16BE(symbols.play, 12);
  header.writeUInt16BE(1, 14);
  header.writeUInt16BE(1, 16);
  // HVSC PSID v2NG flags select PAL and MOS8580; speed zero selects VBI scheduling.
  header.writeUInt16BE(0x24, 118);
  header.write(score.title, 22, "ascii");
  header.write(score.composer, 54, "ascii");
  header.write("2026 three voice arrangement", 86, "ascii");
  const { stream, ...timing } = compiled;
  const manifest = {
    title: score.title,
    composer: score.composer,
    target: "PAL 6569 / one MOS8580 at $D400",
    clockHz: PAL_CLOCK_HZ,
    ticksPerSecond: PAL_TICKS_PER_SECOND,
    ...timing,
    payloadEndAddress,
    symbols,
  };
  await mkdir(output, { recursive: true });
  for (const [extension, data] of [
    ["prg", assembled.prg],
    ["sid", Buffer.concat([header, payload])],
    ["asm", assembly],
    ["events.json", JSON.stringify(manifest, null, 2) + "\n"],
  ] as const) await writeFile(join(output, `${name}.${extension}`), data);
  return manifest;
}

if (import.meta.main) {
  if (process.argv.length < 3 || process.argv.length > 5) throw new Error("Usage: bun scripts/build-arrangement.ts <score.json> [output-directory] [name]");
  const source = resolve(process.argv[2]);
  const output = process.argv[3] ? resolve(process.argv[3]) : join(root, "build");
  const name = process.argv[4] ?? basename(source, ".json");
  const result = await buildArrangement({ source, output, name });
  console.log(`Built ${join(output, name)}.{prg,sid,asm,events.json}: ${result.events.length} events, ${result.totalTicks} PAL ticks (${result.durationSeconds.toFixed(3)} s), payload ends at $${result.payloadEndAddress.toString(16)}.`);
}
