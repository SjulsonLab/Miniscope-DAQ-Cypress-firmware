# Miniscope DAQ Firmware: Build & Install Instructions

This guide walks through setting up a Windows machine to compile the Miniscope DAQ firmware from source and flash it onto the DAQ hardware.

## Part 1: Software Installation

You need three things installed: the Cypress FX3 SDK, the ARM GCC toolchain, and Git.

### 1. Install the Cypress EZ-USB FX3 SDK

This is the main SDK that includes the IDE (EZ USB Suite), firmware libraries, the `elf2img` utility, and Cypress Control Center (used for flashing).

1. Go to the Infineon/Cypress website and download the **EZ-USB FX3 SDK**:
   https://www.infineon.com/cms/en/design-support/tools/sdk/usb-controllers-sdk/ez-usb-fx3-software-development-kit/
   (You may need to create a free Infineon account to download it.)
2. Run the installer. Use the **default install path** (e.g., `C:\Program Files (x86)\Cypress\EZ-USB FX3 SDK\1.3.4`). The exact version number in the path may vary.
3. During installation, make sure all components are selected, especially:
   - EZ USB Suite (Eclipse-based IDE)
   - Firmware source and libraries
   - GPIF II Designer
   - Cypress USB Control Center
4. The installer should also install the **Cypress USB drivers** needed for the DAQ bootloader. If prompted, allow the driver installation.

### 2. Install the ARM GCC Toolchain

The firmware is compiled with the GNU ARM Embedded Toolchain (arm-none-eabi-gcc).

1. Download **GNU Arm Embedded Toolchain** from:
   https://developer.arm.com/downloads/-/gnu-rm
   (Get a version in the 4.x or 5.x series for best compatibility with the FX3 SDK, e.g., `gcc-arm-none-eabi-5_4-2016q3-20160926-win32.exe`. Newer versions may also work but are less tested.)
2. Run the installer. At the end, **check the box** to "Add path to environment variable" so the tools are on your system PATH.
3. Note the install path (e.g., `C:\Program Files (x86)\GNU Tools ARM Embedded\5.4 2016q3`). You will need this later.

### 3. Install Git

1. Download Git for Windows from https://git-scm.com/download/win
2. Install with default settings.

## Part 2: Getting the Source Code

1. Open **Git Bash** (or any terminal with git).
2. Clone the repository:
   ```
   git clone https://github.com/Aharoni-Lab/Miniscope-DAQ-Cypress-firmware.git
   ```
3. If you need a specific branch (e.g., `IRIG-dev`), check it out:
   ```
   cd Miniscope-DAQ-Cypress-firmware
   git checkout IRIG-dev
   ```

## Part 3: Setting Up the Project in EZ USB Suite

### 1. Launch EZ USB Suite

- Find it in your Start menu under the Cypress folder, or navigate to the SDK install directory and run the Eclipse executable.
- When prompted for a workspace, you can use the default or pick any folder.

### 2. Import the Project

1. Go to **File > Import...**
2. Select **General > Existing Projects into Workspace** and click Next.
3. Click **Browse...** next to "Select root directory" and navigate to the `Miniscope_DAQ` folder inside the cloned repo (e.g., `C:\Users\Alexa\Miniscope-DAQ-Cypress-firmware\Miniscope_DAQ`).
4. The project should appear in the list. Make sure it is checked, then click **Finish**.

### 3. Configure SDK and Toolchain Paths

The project uses two environment variables that need to point to the correct locations on your machine:

1. Right-click the project in the **Project Explorer** and select **Properties**.
2. Go to **C/C++ Build > Environment**.
3. Set or verify these variables:
   - `FX3_INSTALL_PATH` = path to the FX3 SDK (e.g., `C:/Program Files (x86)/Cypress/EZ-USB FX3 SDK/1.3.4`)
   - `ARMGCC_INSTALL_PATH` = path to your ARM GCC install (e.g., `C:/Program Files (x86)/GNU Tools ARM Embedded/5.4 2016q3`)
   - `ARMGCC_VERSION` = the GCC version string (e.g., `5.4.1`). You can find this by running `arm-none-eabi-gcc --version` in a terminal.

   **Note:** Use forward slashes (`/`) in the paths, not backslashes.

### 4. Verify the Post-Build Step (elf2img)

This is the step that converts the compiled ELF binary into a `.img` file that can be flashed to the DAQ.

1. Right-click the project > **Properties** > **C/C++ Build > Settings**.
2. On the **Build Steps** tab, check the **Post-build steps** command. For the **Release** configuration it should look like:
   ```
   '${FX3_INSTALL_PATH}/util/elf2img/elf2img.exe' -i ${ProjName}.elf -o ${ProjName}_128K_EEPROM.img -i2cconf 0x1E
   ```
   This generates the firmware image for 128K EEPROMs. If you also need the 256K version, you can add a second command separated by `&&`:
   ```
   '${FX3_INSTALL_PATH}/util/elf2img/elf2img.exe' -i ${ProjName}.elf -o ${ProjName}_128K_EEPROM.img -i2cconf 0x1E && '${FX3_INSTALL_PATH}/util/elf2img/elf2img.exe' -i ${ProjName}.elf -o ${ProjName}_256K_EEPROM.img -i2cconf 0x1C
   ```

   The difference:
   - `-i2cconf 0x1E` = 128K EEPROM (v3.2 DAQ boards with the socketed EEPROM chip)
   - `-i2cconf 0x1C` = 256K EEPROM (v3.3 DAQ / MiniDAQ boards with the surface-mount EEPROM)

## Part 4: Building the Firmware

1. In EZ USB Suite, make sure the **Release** build configuration is selected:
   - Go to **Project > Build Configurations > Set Active > Release**.
2. Build the project: **Project > Build Project** (or press `Ctrl+B`).
3. Watch the **Console** panel at the bottom for build output. A successful build will end with the `elf2img` step and produce `.img` file(s) in the `Release` folder of the project.
4. If you get errors:
   - **"arm-none-eabi-gcc not found"**: Your ARM GCC path or `ARMGCC_INSTALL_PATH` is wrong.
   - **"No such file or directory" for SDK headers**: Your `FX3_INSTALL_PATH` is wrong, or the SDK version folder (`1_3_3` vs `1_3_4`) doesn't match. Check that `${FX3_INSTALL_PATH}/fw_lib/1_3_3/inc` (or `1_3_4`) exists. You may need to update the `FX3SDKVERSION` macro in the project properties to match your installed version.
   - **"elf2img.exe not found"**: Check that `${FX3_INSTALL_PATH}/util/elf2img/elf2img.exe` exists.

## Part 5: Flashing the Firmware onto the DAQ

### Step 1: Set the DAQ Jumpers to "Boot from USB"

On the DAQ PCB, locate the three 2-pin jumpers labeled **K1**, **K2**, and **K3** (near the right-center of the board).

- Place jumpers on **K1** and **K2**.
- Leave **K3 empty** (no jumper).

This puts the DAQ into USB bootloader mode.

### Step 2: Connect the DAQ

Plug the DAQ into your computer using a **USB 3.0** cable. The board will power on. In **Device Manager**, it should appear as **"Cypress USB Bootloader"** (under Universal Serial Bus controllers or similar).

If the device is not recognized, you may need to install the Cypress USB driver manually from the SDK folder.

### Step 3: Open Cypress USB Control Center

Find it in your Start menu under the Cypress folder, or look for `CyControl.exe` in the SDK install directory (typically under `application/c_sharp/controlcenter/bin/Release/`).

### Step 4: Program the EEPROM

1. In the left panel of Control Center, select **"Cypress USB Bootloader"**.
2. Click **Program > I2C EEPROM**.
3. Navigate to the `.img` file you built (in the project's `Release` folder) and select the correct one:
   - **`*_128K_EEPROM.img`** if your DAQ has a v3.2 board (socketed 4x2 DIP EEPROM chip).
   - **`*_256K_EEPROM.img`** if your DAQ has a v3.3 board or MiniDAQ (small surface-mount EEPROM).
4. Wait about 10 seconds. The status bar at the bottom of Control Center should say programming was successful.

### Step 5: Restore the Jumpers and Power Cycle

1. **Remove the jumpers** from K1 and K2 (returning them to the "Boot from EEPROM" configuration, i.e., no jumpers on any of K1/K2/K3).
2. Unplug and replug the DAQ USB cable.
3. The DAQ should now appear in **Device Manager** as **"MINISCOPE"** under **Cameras** or **Imaging Devices**.

If it still shows up as "Cypress Bootloader", double-check that the jumpers are removed and try power cycling again.

## Quick Reference

| Item | Details |
|------|---------|
| SDK | Cypress EZ-USB FX3 SDK (includes EZ USB Suite IDE) |
| Compiler | arm-none-eabi-gcc (GNU ARM Embedded Toolchain) |
| IDE | EZ USB Suite (Eclipse-based, bundled with SDK) |
| Firmware output | `.img` file (converted from `.elf` by `elf2img.exe`) |
| Flashing tool | Cypress USB Control Center (bundled with SDK) |
| 128K EEPROM flag | `-i2cconf 0x1E` (v3.2 DAQ) |
| 256K EEPROM flag | `-i2cconf 0x1C` (v3.3 DAQ / MiniDAQ) |
| Source files | `uvc.c`, `miniscope.c`, `cyfxuvcdscr.c`, `cyfxtx.c` |
| Key config header | `definitions.h` (device/resolution selection) |
