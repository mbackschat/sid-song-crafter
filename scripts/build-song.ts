import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assemblyToPrgDetailed } from "../.tools/c64bridge/src/tools/translation/assembler.ts";

export const PAL_CLOCK_HZ = 17734475 / 18;
export const PAL_CYCLES_PER_FRAME = 312 * 63;
export const PAL_TICKS_PER_SECOND = PAL_CLOCK_HZ / PAL_CYCLES_PER_FRAME;

type Note = { pitch: string | null; sixteenths: number };
type Score = {
  title: string;
  composer: string;
  quarterBpm: number;
  releaseTicks: number;
  tailTicks: number;
  instrument: { waveform: number; attackDecay: number; sustainRelease: number; volume: number };
  notes: Note[];
};

export type Event = {
  pitch: string | null;
  startTick: number;
  durationTicks: number;
  frequencyWord: number;
  gateOffTick: number | null;
};

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function integer(value: number, name: string, min: number, max: number): void {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(`${name} must be an integer in ${min}..${max}`);
  }
}

function frequencyWord(pitch: string | null): number {
  if (pitch === null) return 0;
  const match = /^([A-G])(#|b)?([0-8])$/.exec(pitch);
  if (!match) throw new Error(`Invalid pitch: ${pitch}; use a note such as E5, or null for a rest`);
  const semitones: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const semitone = semitones[match[1]];
  const accidental = match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0;
  const midi = 12 * (Number(match[3]) + 1) + semitone + accidental;
  const word = Math.round(440 * 2 ** ((midi - 69) / 12) * 2 ** 24 / PAL_CLOCK_HZ);
  integer(word, `SID frequency for ${pitch}`, 1, 65535);
  return word;
}

export function compileEvents(score: Score): Event[] {
  if (!Number.isFinite(score.quarterBpm) || score.quarterBpm <= 0) throw new Error("quarterBpm must be positive");
  if (!Array.isArray(score.notes)) throw new Error("notes must be an array");
  integer(score.notes.length, "note/rest count", 1, 254);
  integer(score.releaseTicks, "releaseTicks", 1, 254);
  integer(score.tailTicks, "tailTicks", 1, 255);
  let sixteenths = 0;
  let startTick = 0;
  const events = score.notes.map(note => {
    integer(note.sixteenths, "sixteenths", 1, 255);
    sixteenths += note.sixteenths;
    // Absolute boundaries avoid cumulative rounding drift; see docs/research/02-playback-and-timing.md.
    const endTick = Math.round(sixteenths * 60 * PAL_TICKS_PER_SECOND / (4 * score.quarterBpm));
    const durationTicks = endTick - startTick;
    if (durationTicks <= score.releaseTicks) throw new Error("Note/rest duration must exceed releaseTicks");
    integer(durationTicks, "quantized event duration", 1, 255);
    const word = frequencyWord(note.pitch);
    const event = {
      pitch: note.pitch,
      startTick,
      durationTicks,
      frequencyWord: word,
      gateOffTick: note.pitch === null ? null : endTick - score.releaseTicks,
    };
    startTick = endTick;
    return event;
  });
  events.push({ pitch: null, startTick, durationTicks: score.tailTicks, frequencyWord: 0, gateOffTick: null });
  return events;
}

function table(label: string, bytes: number[]): string {
  return `${label}:\n    .byte ${bytes.join(", ")}\n`;
}

function metadata(header: Buffer, offset: number, text: string): void {
  if (text.length > 31 || /[^\x20-\x7e]/.test(text)) throw new Error("SID metadata must be at most 31 printable ASCII characters");
  header.write(text, offset, "ascii");
}

export async function buildSong({ output = join(root, "build"), source = join(root, "songs/fuer-elise-opening.json") } = {}) {
  const score: Score = JSON.parse(await readFile(source, "utf8"));
  const events = compileEvents(score);
  const { waveform, attackDecay, sustainRelease, volume } = score.instrument;
  if (waveform !== 0x10) throw new Error("This opening arrangement supports the triangle waveform (16)");
  integer(attackDecay, "attackDecay", 0, 255);
  integer(sustainRelease, "sustainRelease", 0, 255);
  integer(volume, "volume", 1, 15);
  const assembly = [
    `EVENT_COUNT = ${events.length}`,
    `RELEASE_TICKS = ${score.releaseTicks}`,
    `WAVEFORM = ${waveform}`,
    `ATTACK_DECAY = ${attackDecay}`,
    `SUSTAIN_RELEASE = ${sustainRelease}`,
    `VOLUME = ${volume}`,
    await readFile(join(root, "songs/player.asm"), "utf8"),
    table("duration_ticks", events.map(event => event.durationTicks)),
    table("frequency_low", events.map(event => event.frequencyWord & 255)),
    table("frequency_high", events.map(event => event.frequencyWord >> 8)),
    table("control", events.map(event => waveform | Number(event.pitch !== null))),
  ].join("\n");
  const assembled = assemblyToPrgDetailed(assembly, { fileName: "fuer-elise-opening.asm" });
  const symbols = Object.fromEntries(assembled.symbols);
  const payload = assembled.prg.subarray(2 + 0x1000 - assembled.prg.readUInt16LE(0));
  const header = Buffer.alloc(0x7c);
  header.write("PSID");
  header.writeUInt16BE(2, 4);
  header.writeUInt16BE(0x7c, 6);
  header.writeUInt16BE(0x1000, 8);
  header.writeUInt16BE(symbols.init, 10);
  header.writeUInt16BE(symbols.play, 12);
  header.writeUInt16BE(1, 14);
  header.writeUInt16BE(1, 16);
  // HVSC PSID v2NG flags: PAL (bit 2), MOS8580 (bit 5); speed zero selects VBI.
  header.writeUInt16BE(0x24, 118);
  metadata(header, 22, score.title);
  metadata(header, 54, score.composer);
  metadata(header, 86, "2026 manual opening arrangement");
  const totalTicks = events.at(-1)!.startTick + score.tailTicks;
  const manifest = {
    target: "PAL 6569 / one MOS8580 at $D400",
    clockHz: PAL_CLOCK_HZ,
    ticksPerSecond: PAL_TICKS_PER_SECOND,
    quarterBpm: score.quarterBpm,
    totalTicks,
    durationSeconds: totalTicks / PAL_TICKS_PER_SECOND,
    symbols,
    events,
  };
  await mkdir(output, { recursive: true });
  for (const [name, data] of [
    ["fuer-elise-opening.prg", assembled.prg],
    ["fuer-elise-opening.sid", Buffer.concat([header, payload])],
    ["fuer-elise-opening.asm", assembly],
    ["fuer-elise-opening.events.json", JSON.stringify(manifest, null, 2) + "\n"],
  ] as const) await writeFile(join(output, name), data);
  return manifest;
}

if (import.meta.main) {
  if (process.argv.length > 2) throw new Error("Usage: bun scripts/build-song.ts");
  const result = await buildSong();
  console.log(`Built build/fuer-elise-opening.{prg,sid,asm,events.json}: ${result.totalTicks} PAL ticks (${result.durationSeconds.toFixed(3)} s).`);
}
