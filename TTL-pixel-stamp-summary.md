# TTL Pixel Stamping: Implementation Summary

## Problem

The Miniscope V4 DAQ has a TTL input (SMA connector, GPIO 21 / `TRIG_RECORD_EXT`) but no mechanism to record its state during imaging. For IRIG-B UTC time encoding, we need each video frame to carry the TTL state at the moment it was captured, with timing precision better than one frame period (~33ms at 30fps).

## Why the FX3 DAQ firmware?

The ATmega328 MCU firmware (Miniscope-v4 repo) was considered first but ruled out: it has no access to pixel data. The Cypress FX3 DAQ firmware is the right place because it sits between the GPIF pixel capture engine and USB commit, giving it both GPIO access and direct access to DMA pixel buffers.

## What changed

Three files in `Miniscope_DAQ/` were modified on the `IRIG-dev` branch:

### `miniscope.h` / `miniscope.c` — new global flag

Added `CyBool_t isFirstBufferOfFrame`, initialized to `CyTrue`. This flag tracks whether the next DMA buffer to arrive is the first buffer of a new video frame. It is necessary because each frame spans multiple DMA buffers (~16KB each for a 608x608x16bpp image), and we only want to sample the TTL and stamp pixels once per frame.

### `uvc.c` — DMA callback modification

Two insertions in `CyFxUvcApplnDmaCallback()`:

1. **TTL sampling and pixel stamping** (before the header-adding logic): When `isFirstBufferOfFrame` is true and the buffer contains at least 3 full image rows, the code:
   - Reads GPIO 21 (`TRIG_RECORD_EXT`) via `CyU3PGpioSimpleGetValue()`
   - Sets the top-left 3x3 pixel block to all-white (`0xFF`) if TTL is high, or all-black (`0x00`) if low
   - Clears the flag so subsequent buffers in the same frame are untouched

2. **Flag reset on end-of-frame**: When a partial DMA buffer signals end-of-frame (the `else` branch where `endOfFrame = CyTrue`), `isFirstBufferOfFrame` is reset to `CyTrue` so the next frame's first buffer will be stamped.

## Pixel layout details

| Parameter | Value |
|---|---|
| Image dimensions | 608 x 608 |
| Bits per pixel | 16 |
| Bytes per line | 1216 (608 x 2) |
| DMA buffer size | ~16KB |
| Lines per DMA buffer | ~13 |
| Stamped region | Top-left 3x3 pixels (bytes 0-5 on rows 0, 1, 2) |

The stamped region is well within the first DMA buffer. Setting both bytes of each 16-bit pixel to the same value (0xFF or 0x00) produces a valid extreme value regardless of whether the pixel format is interpreted as UYVY, raw Bayer, or 10-bit-in-16-bit.

## Timing precision

The TTL is sampled inside the DMA produce-event callback, which fires within microseconds of the GPIF engine delivering the first pixel data from the deserializer. This gives sub-millisecond precision — roughly 1000x better than the ~33ms frame period requirement.

## How to verify

1. Build with the Cypress FX3 SDK / EZ USB Suite
2. Connect a known TTL signal (e.g., 1Hz square wave) to the DAQ SMA input
3. Record video with the Miniscope DAQ Qt software
4. Inspect the top-left 3x3 pixels of each frame — they should alternate white/black in sync with the TTL signal
5. Check debug output for any DMA errors or frame drops
