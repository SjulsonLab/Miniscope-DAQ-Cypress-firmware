# Plan: Stamp TTL State into Corner Pixels of Each Frame

## Context

The Miniscope DAQ has a TTL input (GPIO 21 / `TRIG_RECORD_EXT`, SMA connector) that is not recorded during imaging. The goal is to encode UTC timing information: an external TTL signal encodes time, and by sampling it per-frame and stamping it into the image, each frame gets objective timing data. Timing precision must be better than one frame period (~33ms at 30fps).

The Miniscope V4 MCU firmware (ATmega328, Miniscope-v4 repo) cannot do this — it has no access to pixel data. The Cypress FX3 DAQ firmware **can**, because it has both the TTL GPIO input and access to pixel data buffers between GPIF capture and USB commit.

## Target Repository

`Miniscope-DAQ-Cypress-firmware` (branch: `IRIG-dev`)

## Files to Modify

1. **`Miniscope_DAQ/miniscope.h`** — declare new global flag
2. **`Miniscope_DAQ/miniscope.c`** — initialize new global
3. **`Miniscope_DAQ/uvc.c`** — core change: stamp pixels in DMA callback

## Implementation

### 1. Add a frame-tracking flag (`miniscope.h` + `miniscope.c`)

Add a global `CyBool_t isFirstBufferOfFrame` initialized to `CyTrue`. This tracks whether the next DMA buffer is the first buffer of a new frame.

**miniscope.h** — add declaration near the other `extern CyBool_t` lines:

```c
extern CyBool_t isFirstBufferOfFrame;
```

**miniscope.c** — add initialization near the other globals:

```c
CyBool_t isFirstBufferOfFrame = CyTrue;
```

### 2. Modify `CyFxUvcApplnDmaCallback()` in `uvc.c` (line ~684)

Inside the `while (status == CY_U3P_SUCCESS)` loop, **before** `CyFxUVCAddHeader`:

**a) On first buffer of each frame, sample TTL and stamp pixels:**

```c
if (isFirstBufferOfFrame && dmaBuffer.count >= 3 * WIDTH * 2) {
    /* Sample TTL state */
    CyBool_t ttlState;
    CyU3PGpioSimpleGetValue(TRIG_RECORD_EXT, &ttlState);

    /* Set top-left 3x3 pixels to white (0xFF) or black (0x00) */
    uint8_t val = ttlState ? 0xFF : 0x00;
    uint16_t bytesPerLine = WIDTH * 2;  /* 608 * 2 = 1216 */
    for (uint16_t row = 0; row < 3; row++) {
        CyU3PMemSet(dmaBuffer.buffer + (row * bytesPerLine), val, 6);  /* 3 pixels x 2 bytes */
    }
    isFirstBufferOfFrame = CyFalse;
}
```

**b) On end-of-frame (partial buffer), reset the flag:**

In the `else` branch where `endOfFrame = CyTrue` is set (line ~694), add:

```c
isFirstBufferOfFrame = CyTrue;
```

### 3. Pixel layout rationale

- Image: 608x608, 16 bits/pixel -> 1216 bytes/line
- DMA buffers: ~16KB each -> first buffer holds ~13 lines
- Top-left 3x3 block = bytes [0..5] on rows 0, 1, 2 -> all within first buffer
- Setting both bytes of each pixel to 0xFF (white) or 0x00 (black) works regardless of whether the format is true UYVY or raw 10-bit-in-16-bit

### 4. Timing precision

The TTL is sampled in the DMA callback triggered by the first GPIF buffer of each frame. This fires within microseconds of the first pixel data arriving from the deserializer — sub-millisecond precision, far exceeding the ~33ms requirement.

## Verification

1. Build the firmware with the Cypress FX3 SDK / EZ USB Suite
2. Connect a known TTL signal (e.g., 1Hz square wave) to the DAQ SMA input
3. Record video with Miniscope DAQ Qt software
4. Inspect the top-left 3x3 pixels of each frame — they should alternate white/black in sync with the TTL signal
5. Verify no frame drops or DMA errors in the debug output
