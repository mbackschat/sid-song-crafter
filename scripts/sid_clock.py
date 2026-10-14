"""Explicit PAL and 263-line NTSC timing for native composition targets."""

from dataclasses import dataclass


# libsidplayfp 3.1.1 src/c64/c64.h and c64.cpp define these model clocks and VIC geometries.
PAL_CLOCK = 17734475 / 18
NTSC_CLOCK = 14318181.82 / 14
PAL_FRAME_CYCLES = 312 * 63
NTSC_FRAME_CYCLES = 263 * 65


@dataclass(frozen=True)
class ClockSpec:
    name: str
    clock_hz: float
    frame_cycles: int

    @property
    def ticks_per_second(self):
        return self.clock_hz / self.frame_cycles


_CLOCKS = {
    "pal": ClockSpec("pal", PAL_CLOCK, PAL_FRAME_CYCLES),
    "ntsc": ClockSpec("ntsc", NTSC_CLOCK, NTSC_FRAME_CYCLES),
}


def clock_spec(clock="pal"):
    if not isinstance(clock, str) or clock not in _CLOCKS:
        raise ValueError("Composition clock must be pal or ntsc (263-line NTSC)")
    return _CLOCKS[clock]
