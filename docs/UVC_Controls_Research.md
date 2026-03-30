# UVC Processing Unit & Camera Terminal Controls: Image Quality Research

## Executive Summary

This document provides a complete reference for UVC (USB Video Class) Processing Unit
and Camera Terminal controls, their bitmap definitions, practical effects on image quality,
and strategies for improving cheap webcam output through firmware-level descriptor
modification. The focus is on enabling disabled controls in bmControls bitmaps to unlock
image processing capabilities that exist in hardware but are not advertised to the host OS.

---

## 1. Processing Unit (PU) bmControls Bitmap

The Processing Unit Descriptor (bDescriptorSubtype = 0x05) contains a `bmControls` field
that advertises which image processing controls are available. Each bit enables a specific
control. The host OS driver (uvcvideo on Linux, UVC class driver on Windows) reads this
bitmap to determine which controls to expose to applications.

### 1.1 Bit Definitions (UVC 1.1 / 1.5)

| Bit | Byte:Bit | Hex Mask | Control Name | Value Type | Description |
|-----|----------|----------|-------------------------------|------------|---------------------------------------------|
| D0  | 0:0      | 0x01     | Brightness                    | signed 16  | Overall image brightness offset             |
| D1  | 0:1      | 0x02     | Contrast                      | unsigned 16| Difference between light and dark areas     |
| D2  | 0:2      | 0x04     | Hue                           | signed 16  | Color phase rotation (degrees x100)         |
| D3  | 0:3      | 0x08     | Saturation                    | unsigned 16| Color intensity/vividness                   |
| D4  | 0:4      | 0x10     | Sharpness                     | unsigned 16| Edge enhancement level                      |
| D5  | 0:5      | 0x20     | Gamma                         | unsigned 16| Luminance transfer function curve           |
| D6  | 0:6      | 0x40     | White Balance Temperature     | unsigned 16| Color temperature in Kelvin                 |
| D7  | 0:7      | 0x80     | White Balance Component       | signed 32  | Blue/Red component balance (bue,red pair)   |
| D8  | 1:0      | 0x01     | Backlight Compensation        | unsigned 16| Compensate for backlit subjects             |
| D9  | 1:1      | 0x02     | Gain                          | unsigned 16| Signal amplification level                  |
| D10 | 1:2      | 0x04     | Power Line Frequency          | unsigned 8 | Anti-flicker: 0=disabled,1=50Hz,2=60Hz      |
| D11 | 1:3      | 0x08     | Hue, Auto                     | unsigned 8 | Automatic hue adjustment (on/off)           |
| D12 | 1:4      | 0x10     | White Balance Temp, Auto      | unsigned 8 | Automatic white balance (on/off)            |
| D13 | 1:5      | 0x20     | White Balance Comp, Auto      | unsigned 8 | Auto white balance component mode           |
| D14 | 1:6      | 0x40     | Digital Multiplier             | unsigned 16| Digital zoom level                          |
| D15 | 1:7      | 0x80     | Digital Multiplier Limit       | unsigned 16| Maximum allowed digital zoom                |
| D16 | 2:0      | 0x01     | Analog Video Standard         | unsigned 8 | NTSC/PAL/SECAM selection (UVC 1.1+)         |
| D17 | 2:1      | 0x02     | Analog Video Lock Status      | unsigned 8 | Lock status of analog video (UVC 1.1+)      |
| D18 | 2:2      | 0x04     | Contrast, Auto                | unsigned 8 | Automatic contrast adjustment (UVC 1.5)     |

### 1.2 bControlSize Field

- UVC 1.0: `bControlSize` = 2 bytes (D0-D15 defined)
- UVC 1.1: `bControlSize` = 2 or 3 bytes (D16-D17 added, plus `bmVideoStandards` byte)
- UVC 1.5: `bControlSize` = 3 bytes (D18 added)

**Important**: Many cheap cameras declare UVC 1.0 but some host drivers tolerate 3-byte
bmControls anyway. The Windows inbox UVC driver is particularly tolerant of this mismatch.

### 1.3 Descriptor Binary Layout

```
Offset  Field                  Size    Example (Logitech C920)
0       bLength                1       0x0B (11 bytes)
1       bDescriptorType        1       0x24 (CS_INTERFACE)
2       bDescriptorSubtype     1       0x05 (VC_PROCESSING_UNIT)
3       bUnitID                1       0x03
4       bSourceID              1       0x01
5-6     wMaxMultiplier         2       0x4000 (16384 = 163.84x)
7       bControlSize           1       0x02
8       bmControls[0]          1       0x5B  (D0,D1,D3,D4,D6 = Bright,Contrast,Sat,Sharp,WB Temp)
9       bmControls[1]          1       0x17  (D8,D9,D10,D12 = Backlight,Gain,PowerLine,WB Auto)
10      iProcessing            1       0x00
[11     bmVideoStandards       1       0x1B  -- only in UVC 1.1+]
```

---

## 2. Camera Terminal (CT) bmControls Bitmap

The Camera Terminal Descriptor (bDescriptorSubtype = 0x02, wTerminalType = 0x0201)
contains its own `bmControls` field for mechanical/optical controls.

### 2.1 Bit Definitions (UVC 1.1 / 1.5)

| Bit | Byte:Bit | Hex Mask | Control Name | Value Type | Description |
|-----|----------|----------|-------------------------------|------------|---------------------------------------------|
| D0  | 0:0      | 0x01     | Scanning Mode                 | unsigned 8 | 0=interlaced, 1=progressive                 |
| D1  | 0:1      | 0x02     | Auto-Exposure Mode            | unsigned 8 | Manual/auto/shutter/aperture priority       |
| D2  | 0:2      | 0x04     | Auto-Exposure Priority        | unsigned 8 | Framerate vs exposure tradeoff              |
| D3  | 0:3      | 0x08     | Exposure Time (Absolute)      | unsigned 32| Exposure in 100us units                     |
| D4  | 0:4      | 0x10     | Exposure Time (Relative)      | signed 8   | Step exposure up/down                       |
| D5  | 0:5      | 0x20     | Focus (Absolute)              | unsigned 16| Focal distance setting                      |
| D6  | 0:6      | 0x40     | Focus (Relative)              | signed 8+8 | Step focus + speed                          |
| D7  | 0:7      | 0x80     | Iris (Absolute)               | unsigned 16| Aperture f-number x100                      |
| D8  | 1:0      | 0x01     | Iris (Relative)               | signed 8   | Step iris up/down                           |
| D9  | 1:1      | 0x02     | Zoom (Absolute)               | unsigned 16| Optical zoom level                          |
| D10 | 1:2      | 0x04     | Zoom (Relative)               | signed 8+8+8| Zoom direction + digital + speed           |
| D11 | 1:3      | 0x08     | PanTilt (Absolute)            | signed 32+32| Pan + Tilt in arc-seconds                  |
| D12 | 1:4      | 0x10     | PanTilt (Relative)            | signed 8x4 | Pan/tilt direction + speed                  |
| D13 | 1:5      | 0x20     | Roll (Absolute)               | signed 16  | Roll angle in degrees                       |
| D14 | 1:6      | 0x40     | Roll (Relative)               | signed 8+8 | Roll direction + speed                      |
| D15 | 1:7      | 0x80     | Reserved                      | -          | Reserved in UVC 1.1                         |
| D16 | 2:0      | 0x01     | Focus, Auto                   | unsigned 8 | Autofocus on/off                            |
| D17 | 2:1      | 0x02     | Privacy                       | unsigned 8 | Privacy shutter (UVC 1.1+)                  |
| D18 | 2:2      | 0x04     | Focus, Simple                 | unsigned 8 | Simple focus range (UVC 1.5)                |
| D19 | 2:3      | 0x08     | Window                        | -          | Digital window (UVC 1.5)                    |
| D20 | 2:4      | 0x10     | Region of Interest            | -          | ROI for AE/AF (UVC 1.5)                    |

### 2.2 Auto-Exposure Mode Values

| Value | Mode | Description |
|-------|------|-------------|
| 1     | Manual | Manual exposure, manual iris |
| 2     | Auto | Auto exposure, auto iris |
| 4     | Shutter Priority | Manual exposure, auto iris |
| 8     | Aperture Priority | Auto exposure, manual iris |

---

## 3. Real-World Reference: Logitech C920 Descriptors

The Logitech C920 is a well-documented UVC camera. Its descriptor values serve as a
reference for what a "well-configured" webcam looks like:

### Camera Terminal bmControls: 0x00020a2e
```
D1  = 1  Auto-Exposure Mode
D2  = 1  Auto-Exposure Priority
D3  = 1  Exposure Time (Absolute)
D5  = 1  Focus (Absolute)
D9  = 1  Zoom (Absolute)
D11 = 1  PanTilt (Absolute)
D16 = 1  Focus, Auto
```

### Processing Unit bmControls: 0x175b
```
Byte 0 = 0x5B:
  D0 = 1  Brightness
  D1 = 1  Contrast
  D3 = 1  Saturation
  D4 = 1  Sharpness
  D6 = 1  White Balance Temperature

Byte 1 = 0x17:
  D8  = 1  Backlight Compensation
  D9  = 1  Gain
  D10 = 1  Power Line Frequency
  D12 = 1  White Balance Temperature, Auto
```

### Typical C920 Control Ranges (via v4l2-ctl)

| Control | Min | Max | Step | Default |
|---------|-----|-----|------|---------|
| brightness | -64 | 64 | 1 | 0 |
| contrast | 0 | 64 | 1 | 32 |
| saturation | 0 | 128 | 1 | 64 |
| hue | -40 | 40 | 1 | 0 |
| white_balance_temperature | 2800 | 6500 | 1 | 4600 |
| gamma | 72 | 500 | 1 | 100 |
| gain | 0 | 100 | 1 | 0 |
| sharpness | 0 | 6 | 1 | 3 |
| backlight_compensation | 0 | 2 | 1 | 1 |
| exposure_absolute | 1 | 5000 | 1 | 157 |
| power_line_frequency | 0 | 2 | 1 | 1 |

---

## 4. Practical Effects of Each Control on Image Quality

### 4.1 High-Impact Controls (Enable These First)

**Brightness (D0)**
- Shifts overall luminance of the image up or down
- Essential for compensating for poor lighting
- Implemented as digital offset in the ISP pipeline
- Typical default: 0 (center), range: -64 to +64

**Contrast (D1)**
- Adjusts the difference between darkest and lightest areas
- Higher values increase dynamic range visibility
- Too high causes clipping; too low looks washed out
- Typical default: 32, range: 0-64

**White Balance Temperature (D6) + Auto (D12)**
- Single most important control for color accuracy
- Controls color temperature compensation in Kelvin
- Range typically 2800K (warm/tungsten) to 6500K (cool/daylight)
- Auto mode (D12) lets the ISP adjust continuously
- Enabling both D6 and D12 is critical: auto for general use, manual for consistent results
- If only one WB control exists, use Temperature (not Component)

**Gamma (D5)**
- Controls the luminance transfer function
- Value of 100 = gamma 1.0 (linear), higher values darken midtones
- Lower gamma brightens dark areas, revealing shadow detail
- Critical for compensating cheap sensor poor dynamic range
- Higher gamma (200-300) can reduce perceived noise in shadows

**Gain (D9)**
- Signal amplification level
- Higher gain = brighter image but more noise
- Keep as low as possible; use exposure time instead when possible
- Essential for low-light scenarios
- Typical range: 0-100

### 4.2 Medium-Impact Controls

**Saturation (D3)**
- Color intensity/vividness
- Low saturation = washed out colors, high = oversaturated
- Can mask poor color reproduction on cheap sensors
- Typical default: 64, range: 0-128

**Sharpness (D4)**
- Edge enhancement (unsharp mask) in the ISP
- Higher values increase perceived detail but also noise/artifacts
- Keep moderate (2-4 on 0-6 scale) for best results
- Too high creates ugly halos around edges

**Backlight Compensation (D8)**
- Adjusts exposure to compensate for bright backgrounds
- Very useful for video conferencing where screen/window is behind subject
- Values: 0=off, 1=low, 2=high
- Implemented via ISP metering region adjustment

**Power Line Frequency (D10)**
- Anti-flicker compensation for fluorescent/LED lighting
- 0=disabled, 1=50Hz (Europe/Asia), 2=60Hz (Americas)
- Eliminates rolling bands under artificial lighting
- No quality cost; must match local electrical frequency

### 4.3 Exposure Controls (Camera Terminal)

**Auto-Exposure Mode (CT D1)**
- Most critical CT control
- Value 2 (Auto) = camera handles everything
- Value 1 (Manual) = full manual control
- Value 4 (Shutter Priority) = you set exposure, camera adjusts iris
- Enabling this gives host software control over exposure behavior

**Exposure Time Absolute (CT D3)**
- Direct control of shutter speed in 100-microsecond units
- Value 157 = 15.7ms (approximately 1/60 second)
- Lower values = less motion blur, darker image
- Higher values = more light, more motion blur
- Must disable auto-exposure first to use manual values

**Auto-Exposure Priority (CT D2)**
- Trades framerate for exposure when in auto mode
- When enabled: camera may reduce FPS for brighter image
- When disabled: camera maintains constant FPS
- Important for video calls vs machine vision applications

### 4.4 Lower-Impact Controls

**Hue (D2) + Hue Auto (D11)**
- Rotates color wheel (phase shift)
- Rarely needed; mainly for correcting specific color cast
- Default of 0 is correct for most situations

**Digital Multiplier (D14) / Limit (D15)**
- Digital zoom (crop and scale)
- Reduces effective resolution; avoid unless necessary
- Limit sets maximum zoom level allowed

---

## 5. MJPEG Quality and the Probe/Commit Controls

### 5.1 Probe/Commit Data Structure

The Video Probe and Commit Controls negotiate streaming parameters. The relevant
quality-related fields are:

| Offset | Field | Size | Description |
|--------|-------|------|-------------|
| 0 | bmHint | 2 | Bitfield indicating which fields are fixed |
| 2 | bFormatIndex | 1 | Video format index |
| 3 | bFrameIndex | 1 | Video frame index |
| 4 | dwFrameInterval | 4 | Frame interval in 100ns units |
| 8 | wKeyFrameRate | 2 | Key frame rate for temporal encoding |
| 10 | wPFrameRate | 2 | P-frame rate |
| 12 | wCompQuality | 2 | **Compression quality (0-10000)** |
| 14 | wCompWindowSize | 2 | Compression window size |
| 16 | wDelay | 2 | Internal video latency in ms |
| 18 | dwMaxVideoFrameSize | 4 | Maximum video frame size in bytes |
| 22 | dwMaxPayloadTransferSize | 4 | Maximum payload transfer size |

### 5.2 wCompQuality Field

- Range: 0 to 10000 (abstract quality scale)
- Higher values = better quality, larger frames
- Only meaningful for compressed formats (MJPEG, H.264)
- Value of 0 typically means "device default"
- Not all devices honor this field
- Many cheap webcams ignore wCompQuality entirely and use fixed internal tables

### 5.3 MJPEG Quality in Practice

**Key findings from research:**

1. Most cheap webcams **do not expose** wCompQuality control to the host
2. MJPEG quality is typically controlled internally by the camera ISP
3. The camera auto-adjusts JPEG quantization tables to hit target bitrate
4. v4l2 exposes `V4L2_CID_JPEG_COMPRESSION_QUALITY` but few UVC cameras support it
5. The Logitech C920 reportedly supports quality range 50-87 via v4l2-ctl
6. `dwMaxVideoFrameSize` indirectly affects quality -- larger allowed frame = higher quality

**Strategies for improving MJPEG quality:**

- Lower resolution at same bandwidth = higher quality per pixel
- Lower framerate = more bits per frame = better quality
- If wCompQuality is supported, set to maximum
- Increase `dwMaxVideoFrameSize` in the descriptor if possible
- Use YUV/uncompressed format if bandwidth allows (eliminates JPEG artifacts)

### 5.4 dwMaxVideoFrameSize Impact

The `dwMaxVideoFrameSize` in the frame descriptor sets the upper bound for a single
compressed frame. If this value is too small, the camera must use aggressive compression
(lower quality). Increasing this value in the firmware descriptor can directly improve
MJPEG output quality.

For MJPEG at 1920x1080:
- Minimum useful: ~100KB (aggressive compression, poor quality)
- Typical: ~200-400KB (acceptable quality)
- High quality: ~500KB-1MB+ (near-lossless)
- Uncompressed YUY2 equivalent: ~4MB per frame

---

## 6. Improving Cheap Webcam Quality Through Descriptor Modification

### 6.1 Understanding the Approach

Cheap webcams (particularly Generalplus-based cameras like USB ID 1b3f:xxxx) often have
hardware ISP capabilities that are not advertised in the UVC descriptors. The camera
firmware contains the descriptor tables, and by modifying the `bmControls` bitmaps, we can
enable controls that the ISP hardware supports but the firmware does not expose.

### 6.2 What to Modify in Processing Unit Descriptor

**Minimum recommended PU bmControls for quality improvement:**

```
bmControls[0] = 0x7F  (enable D0-D6)
  D0 = 1  Brightness
  D1 = 1  Contrast
  D2 = 1  Hue
  D3 = 1  Saturation
  D4 = 1  Sharpness
  D5 = 1  Gamma
  D6 = 1  White Balance Temperature

bmControls[1] = 0x17  (enable D8-D10, D12)
  D8  = 1  Backlight Compensation
  D9  = 1  Gain
  D10 = 1  Power Line Frequency
  D12 = 1  White Balance Temperature, Auto

Combined: 0x7F, 0x17 (or 0x177F as 16-bit LE)
```

**More aggressive (enable everything sensible):**

```
bmControls[0] = 0x7F  (D0-D6 all enabled)
bmControls[1] = 0x1F  (D8-D12 all enabled)

Combined: 0x7F, 0x1F (or 0x1F7F as 16-bit LE)
```

### 6.3 What to Modify in Camera Terminal Descriptor

**Minimum recommended CT bmControls:**

```
bmControls[0] = 0x0E  (enable D1-D3)
  D1 = 1  Auto-Exposure Mode
  D2 = 1  Auto-Exposure Priority
  D3 = 1  Exposure Time (Absolute)

bmControls[1] = 0x00
bmControls[2] = 0x00
```

**With focus and zoom (if hardware supports):**

```
bmControls[0] = 0x2E  (D1-D3, D5)
  D1 = 1  Auto-Exposure Mode
  D2 = 1  Auto-Exposure Priority
  D3 = 1  Exposure Time (Absolute)
  D5 = 1  Focus (Absolute)

bmControls[1] = 0x00
bmControls[2] = 0x01  (D16)
  D16 = 1  Focus, Auto
```

### 6.4 Critical Caveats

1. **Hardware must support the control**: Enabling a bit in bmControls only tells the host
   driver to issue GET/SET requests. The firmware must actually handle those requests.
   If the firmware does not have handlers, the device will return STALL and the host will
   log errors like "Failed to query (GET_INFO) UVC control X on unit Y: -32"

2. **GET_MIN/MAX/DEF/RES must be implemented**: For each enabled control, the device must
   respond to GET_CUR, GET_MIN, GET_MAX, GET_RES, GET_DEF, and GET_INFO requests.
   If these are not implemented in firmware, the control will appear but fail.

3. **ISP pipeline must support it**: Even if the firmware handles the request, the ISP
   hardware must actually implement the processing. Brightness/contrast are almost always
   supported in silicon. Gamma and white balance depend on the ISP capabilities.

4. **Generalplus-specific**: Generalplus GP chips (common in sub-$10 webcams) typically have
   ISP blocks for brightness, contrast, saturation, and sometimes gamma/WB. The firmware
   often disables these in descriptors to simplify QC testing or reduce firmware complexity.

### 6.5 Step-by-Step Modification Process

1. **Dump current descriptors**: Use `lsusb -v` (Linux) or USBTreeView (Windows) to capture
   the current descriptor layout
2. **Locate PU descriptor**: Find `bDescriptorSubtype = 0x05` in the binary
3. **Locate CT descriptor**: Find `bDescriptorSubtype = 0x02` with `wTerminalType = 0x0201`
4. **Identify bmControls offset**: Count bytes from descriptor start
5. **Modify bmControls bytes**: Set desired bits
6. **Update bLength if needed**: If changing bControlSize
7. **Update wTotalLength**: In the VC Interface Header Descriptor (sum of all VC descriptors)
8. **Flash modified firmware**

### 6.6 Verification After Modification

**Linux:**
```bash
# Check if controls are visible
v4l2-ctl -d /dev/video0 --list-ctrls

# Test specific control
v4l2-ctl -d /dev/video0 --set-ctrl=brightness=10

# Full descriptor dump
lsusb -v -d XXXX:XXXX
```

**Check for errors in dmesg:**
```bash
dmesg | grep uvcvideo
# Look for:
# "Failed to query (GET_INFO) UVC control X" = firmware doesn't handle the control
# "UVC non compliance" = descriptor issues
```

---

## 7. Recommended Settings for Quality Optimization

### 7.1 General Purpose (Video Conferencing)

```bash
v4l2-ctl -d /dev/video0 \
  --set-ctrl=brightness=0 \
  --set-ctrl=contrast=32 \
  --set-ctrl=saturation=64 \
  --set-ctrl=sharpness=3 \
  --set-ctrl=gamma=100 \
  --set-ctrl=white_balance_temperature_auto=1 \
  --set-ctrl=backlight_compensation=1 \
  --set-ctrl=power_line_frequency=2 \
  --set-ctrl=exposure_auto=3
```

### 7.2 Low Light Optimization

```bash
v4l2-ctl -d /dev/video0 \
  --set-ctrl=brightness=15 \
  --set-ctrl=contrast=40 \
  --set-ctrl=saturation=50 \
  --set-ctrl=sharpness=2 \
  --set-ctrl=gamma=200 \
  --set-ctrl=gain=50 \
  --set-ctrl=white_balance_temperature_auto=0 \
  --set-ctrl=white_balance_temperature=4600 \
  --set-ctrl=exposure_auto=1 \
  --set-ctrl=exposure_absolute=2000 \
  --set-ctrl=backlight_compensation=0
```

### 7.3 Maximum Quality / Color Accuracy

```bash
v4l2-ctl -d /dev/video0 \
  --set-ctrl=brightness=0 \
  --set-ctrl=contrast=35 \
  --set-ctrl=saturation=70 \
  --set-ctrl=sharpness=2 \
  --set-ctrl=gamma=120 \
  --set-ctrl=gain=0 \
  --set-ctrl=white_balance_temperature_auto=0 \
  --set-ctrl=white_balance_temperature=5500 \
  --set-ctrl=exposure_auto=1 \
  --set-ctrl=exposure_absolute=500 \
  --set-ctrl=backlight_compensation=0 \
  --set-ctrl=power_line_frequency=2
```

### 7.4 Key Principles

1. **Disable auto-exposure** and set manually when lighting is controlled
2. **Disable auto white balance** and set temperature for consistent color
3. **Keep gain as low as possible** -- use exposure time instead
4. **Keep sharpness moderate** -- ISP sharpening adds artifacts
5. **Raise gamma slightly** (120-200) to reveal shadow detail on cheap sensors
6. **Set power line frequency** to eliminate flicker under artificial light
7. **Disable backlight compensation** when not needed (it reduces overall contrast)

---

## 8. Generalplus Webcam Specifics

### 8.1 Known Generalplus USB IDs

| VID:PID | Description |
|---------|-------------|
| 1b3f:2002 | GENERAL WEBCAM (older) |
| 1b3f:2247 | GENERAL WEBCAM (common) |
| 1b3f:8350 | Generalplus generic |

### 8.2 Common Issues with Generalplus Cameras

1. **Duplicate entity IDs**: Some Generalplus cameras report multiple units with the same
   ID, causing "Found multiple Units with ID 5" errors in recent Linux kernels (6.12+)
2. **Missing GET_DEF support**: Common error: "UVC non compliance - GET_DEF(PROBE) not
   supported. Enabling workaround."
3. **Failed control queries**: "Failed to query (GET_INFO) UVC control 2 on unit 1: -32"
   indicates bmControls advertises a control that firmware doesn't handle
4. **Low clock frequency**: Often reports 6MHz (dwClockFrequency: 6.000000MHz) vs typical
   48MHz on better cameras

### 8.3 Safe Modifications for Generalplus

Based on reports from users with Generalplus cameras:

- **Brightness**: Usually supported in ISP even when not in descriptors
- **Contrast**: Usually supported
- **Saturation**: Often supported
- **Auto-Exposure**: Usually has firmware handler
- **Gamma**: May or may not be supported; test carefully
- **White Balance**: Less likely to be fully supported in cheapest models
- **Sharpness**: Usually supported (simple kernel in ISP)
- **Focus**: Only if hardware has motorized lens (most fixed-focus cheap cameras lack this)

---

## 9. Summary: Priority Actions for Image Quality Improvement

### Tier 1 -- Highest Impact (enable in PU bmControls)
1. White Balance Temperature + Auto (D6, D12) -- color accuracy
2. Gamma (D5) -- dynamic range and shadow detail
3. Gain (D9) -- exposure management

### Tier 2 -- Significant Impact (enable in PU bmControls)
4. Brightness (D0) + Contrast (D1) -- basic tone control
5. Backlight Compensation (D8) -- scene-dependent exposure
6. Power Line Frequency (D10) -- flicker elimination

### Tier 3 -- Moderate Impact
7. Saturation (D3) -- color vividness
8. Sharpness (D4) -- perceived detail

### Camera Terminal Priority
1. Auto-Exposure Mode (CT D1) -- exposure automation control
2. Exposure Time Absolute (CT D3) -- manual exposure setting
3. Auto-Exposure Priority (CT D2) -- framerate vs brightness tradeoff

### MJPEG Quality
- Increase dwMaxVideoFrameSize in frame descriptors
- Lower framerate to increase per-frame bit budget
- Use wCompQuality if device supports it

---

## Sources

- USB Video Class 1.1 Specification (June 1, 2005) -- cajunbot.com mirror
- USB Video Class 1.5 Specification (August 9, 2012) -- nvidia developer forum mirror
- FTDI AN_435 FT602 UVC Chip Configuration Guide v1.2
- FTDI AN_414 FT90x UVC WebCam Application Note
- Linux UVC Gadget Driver documentation (kernel.org)
- Linux UVC Gadget configfs ABI (kernel.org)
- Logitech C920 lsusb descriptor dump (deviwiki.com)
- Infineon community: bControlSize usage in UVC 1.0 vs 1.1
- Linux kernel patch: "usb: gadget: uvc: add different uvc versions support"
- libuvc video capture and processing control reference
- NXP community: Brightness control from UVC endpoint
- Kurokesu: Manual USB camera settings in Linux, UVC camera exposure timing
- GitHub: showmewebcam issue #74 (MJPEG quality improvement)
- GitHub: CachyOS issue #596 (Generalplus webcam regression in kernel 6.17.4)
- Arch Linux forums: Generalplus GENERAL WEBCAM issues
- Linux Mint forums: Generalplus webcam control failures
- Stack Overflow: JPEG compression quality in v4l2
- UVC Device Class FAQ 1.1
