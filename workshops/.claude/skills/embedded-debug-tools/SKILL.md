---
description: 'Debug and flash commands for nRF52 and STM32 development: OpenOCD, nrfjprog, STM32_Programmer_CLI, and J-Link. Use when flashing firmware, starting debug sessions, reading/writing memory, or connecting to targets.'
user-invocable: true
allowed-tools: Bash
---

# Embedded Debug Tools

Commands for flashing, debugging, and inspecting nRF52 and STM32 targets.

## Tool Overview

| Tool                 | Vendor      | Targets        | Primary Use              |
| -------------------- | ----------- | -------------- | ------------------------ |
| nrfjprog             | Nordic      | nRF51/52/53/91 | Flash, erase, reset      |
| OpenOCD              | Open Source | ARM Cortex-M   | GDB server, flash        |
| STM32_Programmer_CLI | ST          | STM32          | Flash, OTP, option bytes |
| J-Link Commander     | SEGGER      | All ARM        | Flash, RTT, SWO          |

---

## nrfjprog (Nordic)

### Installation

```bash
# Download from Nordic website or use nRF Command Line Tools
# https://www.nordicsemi.com/Products/Development-tools/nRF-Command-Line-Tools

# Linux: Add to PATH after install
export PATH="$PATH:/opt/nrf-command-line-tools/bin"
```

### Common Commands

```bash
# List connected devices
nrfjprog --ids

# Erase all flash
nrfjprog --eraseall

# Program hex file
nrfjprog --program firmware.hex --verify

# Program with specific device (if multiple connected)
nrfjprog --snr 683123456 --program firmware.hex

# Reset target
nrfjprog --reset

# Soft reset (preserve RAM)
nrfjprog --pinreset

# Read device info
nrfjprog --deviceversion
nrfjprog --memrd 0x10000000 --n 16  # Read FICR

# Read memory range
nrfjprog --memrd <address> --n <bytes>

# Write memory
nrfjprog --memwr <address> --val <value>

# Recover locked device (full erase)
nrfjprog --recover
```

### Programming Workflow

```bash
# Full programming sequence
nrfjprog --eraseall && \
nrfjprog --program softdevice.hex --verify && \
nrfjprog --program application.hex --verify && \
nrfjprog --reset
```

### Debug with GDB

```bash
# Start GDB server (in terminal 1)
JLinkGDBServer -device nRF52840_xxAA -if SWD -speed 4000

# Connect GDB (in terminal 2)
arm-none-eabi-gdb build/zephyr/zephyr.elf
(gdb) target remote localhost:2331
(gdb) monitor reset
(gdb) load
(gdb) break main
(gdb) continue
```

---

## OpenOCD

### Installation

```bash
# Ubuntu/Debian
sudo apt install openocd

# macOS
brew install openocd

# From source (for latest)
git clone https://github.com/openocd-org/openocd.git
cd openocd && ./bootstrap && ./configure && make && sudo make install
```

### Configuration Files

```bash
# Location of config files
ls /usr/share/openocd/scripts/

# Common interface configs
interface/stlink.cfg      # ST-Link
interface/jlink.cfg       # J-Link
interface/cmsis-dap.cfg   # CMSIS-DAP

# Common target configs
target/stm32f4x.cfg
target/stm32l4x.cfg
target/nrf52.cfg
```

### Starting OpenOCD

```bash
# STM32F4 with ST-Link
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg

# nRF52 with J-Link
openocd -f interface/jlink.cfg -c "transport select swd" -f target/nrf52.cfg

# Custom config file
openocd -f board/my_board.cfg
```

### OpenOCD Commands (via telnet or GDB)

```bash
# Connect via telnet
telnet localhost 4444

# Commands
> reset halt           # Reset and halt CPU
> flash write_image erase firmware.bin 0x08000000  # Flash binary
> flash write_image erase firmware.hex             # Flash hex (auto address)
> verify_image firmware.bin 0x08000000             # Verify flash
> reset run            # Reset and run
> halt                 # Halt execution
> resume               # Resume execution
> reg                  # Show registers
> mdw 0x20000000 16    # Read 16 words from address
> mww 0x20000000 0x12345678  # Write word to address
```

### GDB with OpenOCD

```bash
# Start OpenOCD (terminal 1)
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg

# Connect GDB (terminal 2)
arm-none-eabi-gdb build/firmware.elf
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
(gdb) load
(gdb) break main
(gdb) continue
```

### OpenOCD Config Example

```tcl
# board/custom_stm32f4.cfg
source [find interface/stlink.cfg]
transport select hla_swd

source [find target/stm32f4x.cfg]

# Set flash size (for auto-detect issues)
set FLASH_SIZE 0x100000

# Increase adapter speed
adapter speed 4000

# Reset configuration
reset_config srst_only srst_nogate
```

---

## STM32_Programmer_CLI

### Installation

Part of STM32CubeProgrammer - download from ST website.

```bash
# Add to PATH (Linux)
export PATH="$PATH:/opt/stm32cubeprogrammer/bin"

# Verify installation
STM32_Programmer_CLI --version
```

### Common Commands

```bash
# List connected devices
STM32_Programmer_CLI --connect port=SWD --list

# Connect and get device info
STM32_Programmer_CLI --connect port=SWD

# Erase full chip
STM32_Programmer_CLI --connect port=SWD --erasechip

# Program hex file
STM32_Programmer_CLI --connect port=SWD --write firmware.hex --verify

# Program binary at specific address
STM32_Programmer_CLI --connect port=SWD --write firmware.bin 0x08000000 --verify

# Read memory to file
STM32_Programmer_CLI --connect port=SWD --read 0x08000000 0x10000 read.bin

# Reset target
STM32_Programmer_CLI --connect port=SWD --hardRst

# Option bytes
STM32_Programmer_CLI --connect port=SWD --optionbytes display  # Display
STM32_Programmer_CLI --connect port=SWD -ob RDP=0xAA           # Set option byte
```

### Programming with Reset Modes

```bash
# Hardware reset after programming
STM32_Programmer_CLI --connect port=SWD --mode UR --write firmware.hex --hardRst

# Connect under reset (for locked devices)
STM32_Programmer_CLI --connect port=SWD --mode UR --reset HWrst
```

### External Loader (for QSPI/external flash)

```bash
# Program external flash
STM32_Programmer_CLI --connect port=SWD \
  --extload "path/to/loader.stldr" \
  --write firmware.bin 0x90000000 --verify
```

---

## J-Link Commander

### Installation

Download from SEGGER website.

```bash
# Start J-Link Commander
JLinkExe

# Or with device specified
JLinkExe -device nRF52840_xxAA -if SWD -speed 4000 -autoconnect 1
```

### Common Commands

```tcl
J-Link> connect              # Interactive connect
J-Link> device nRF52840_xxAA # Set device
J-Link> si SWD               # Select interface
J-Link> speed 4000           # Set speed in kHz

J-Link> r                    # Reset and halt
J-Link> g                    # Go (run)
J-Link> h                    # Halt

J-Link> loadfile firmware.hex     # Load hex file
J-Link> loadbin firmware.bin 0x0  # Load binary at address

J-Link> erase                # Erase flash
J-Link> mem32 0x20000000 16  # Read 16 words
J-Link> w4 0x20000000 0x1234 # Write word

J-Link> rtt start            # Start RTT
J-Link> rtt read 0           # Read from RTT channel 0
```

### Batch Mode

```bash
# Create command file (commands.jlink)
r
loadfile firmware.hex
r
g
exit

# Run batch
JLinkExe -device nRF52840_xxAA -if SWD -speed 4000 -CommandFile commands.jlink
```

### RTT (Real-Time Transfer)

```bash
# Start RTT client
JLinkRTTClient

# Or with RTT Viewer GUI
JLinkRTTViewerExe
```

---

## West (Zephyr Build Tool)

### Build and Flash

```bash
# Build for board
west build -b nrf52840dk_nrf52840 app/

# Flash
west flash

# Flash with specific runner
west flash --runner jlink
west flash --runner nrfjprog
west flash --runner openocd

# Debug
west debug

# Attach to running target
west attach
```

### Useful West Commands

```bash
# List supported boards
west boards | grep nrf

# Build with pristine (clean)
west build -b nrf52840dk_nrf52840 -p auto app/

# Build specific configuration
west build -b nrf52840dk_nrf52840 -- -DCONF_FILE=prj_debug.conf

# Generate compile_commands.json
west build -b nrf52840dk_nrf52840 -- -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

---

## Troubleshooting

### Target Not Found

```bash
# Check USB permissions (Linux)
sudo usermod -a -G dialout $USER
# Create udev rules for debug probes

# Check probe connection
lsusb | grep -i "segger\|stlink\|nordic"

# Reset probe
# ST-Link: unplug/replug
# J-Link: JLinkExe -> usbreset
```

### Flash Verification Failed

```bash
# Ensure target is halted
# Check for flash write protection
# Verify correct start address for binary files
# Try mass erase before programming
```

### Connection Under Reset

```bash
# For locked or crashed devices
# nrfjprog:
nrfjprog --recover

# OpenOCD:
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "init; reset halt; flash write_image erase firmware.hex; reset run; exit"

# STM32_Programmer_CLI:
STM32_Programmer_CLI --connect port=SWD mode=UR reset=HWrst
```

---

## References

- [nRF Command Line Tools Documentation](https://infocenter.nordicsemi.com/topic/ug_nrf_cltools/UG/cltools/nrf_command_line_tools_lpage.html)
- [OpenOCD User's Guide](https://openocd.org/doc/html/index.html)
- [STM32CubeProgrammer User Manual](https://www.st.com/resource/en/user_manual/um2237-stm32cubeprogrammer-software-description-stmicroelectronics.pdf)
- [J-Link User Guide](https://www.segger.com/downloads/jlink/UM08001)
