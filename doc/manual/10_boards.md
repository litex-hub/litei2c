# Supported FPGAs and boards {#boards}

This chapter says which FPGAs LiteI2C runs on, which boards use it, and what a board of your own
needs. It is short because the core has one generic PHY and no vendor primitive. The status of
each feature on hardware is in the [status table](#intro-status); this chapter records usage, not
validation.

## Portability {#boards-portability}

The PHY drives SCL and SDA as open-drain lines: it only ever enables the output to pull a line low,
and releases it otherwise ([The PHY](#phy)). It reaches the pins in one of two ways:

| Pads | I/O cell | Used for |
|---------------------------------|---------------------------------------------|-------------------------------|
| `scl`, `sda` (platform record) | One `SDRTristate` per line, LiteX lowering | Every board script |
| `scl_o/oe/i`, `sda_o/oe/i` | None: the signals are exposed | Simulation, custom I/O |

`SDRTristate` is the registered tristate of LiteX (`litex/build/io.py`). LiteX has a vendor lowering
of it for Xilinx, Lattice iCE40, Lattice ECP5 (open-source toolchain), Gowin GW5A, Efinix, Cologne
Chip and Altera Agilex 5 devices, and an inferred one, flip-flops and a tristate buffer, for the
others. LiteI2C therefore builds for every family that LiteX supports, with no option to set. The
registers add one PHY clock cycle on the output and one on the input, which the PHY tolerates (test
`test_stop_release_tolerates_registered_input_delay`, [Simulation and tests](#simulation)).

The core needs no timing constraint beyond the clock of the PHY (`sys`, or `clock_domain`). SCL
is not a clock of the FPGA: the PHY generates it as a level, from a counter of PHY clock cycles,
and samples both lines with the PHY clock.

## Boards and projects using LiteI2C {#boards-users}

| Board | FPGA | Device on the bus | Where |
|------------------------|-------------------------|---------------------------------|------------------------------------|
| GMM-7550 | Cologne Chip GateMate | FUSB303B USB-C controller | LiteX-Boards `gmm7550_usb3`, `--usb pd` |
| LiteX-M2SDR | Xilinx Artix-7 (XC7A200T) | SI5351 clock generator | LiteX-M2SDR `litex_m2sdr.py` |

The GMM-7550 target adds the core with `add_i2c_master(name="i2c", pads=pd, with_irq=True)` on the
`pd` pads of its platform (SCL, SDA and the alert and enable lines of the USB-C controller). It is
the only LiteX-Boards target that uses LiteI2C. Its gateware elaborates without the Cologne Chip
toolchain, which makes it a convenient check after a change of the core:

```sh
python3 -m litex_boards.targets.gmm7550_usb3 --usb pd --build --no-compile
```

LiteX-M2SDR, an Enjoy-Digital SDR board, configures its SI5351 at address `0x60` with a gateware
sequencer at start-up, then from host software over PCIe or Etherbone through the same registers
([Examples](#examples)). Its platform enables the internal pull-ups of the FPGA on both lines
(`Misc("PULLUP=TRUE")`), and the core uses FIFOs of depth 8.

The other targets of LiteX-Boards that have an I2C bus use the bit-banged `I2CMaster` of LiteX,
which the LiteX BIOS and the Linux driver support ([I2C in LiteX](#litex-i2c)). The
`alinx_ax7035` target says so in a comment: it keeps the bit-banged core because the Linux driver
expects its register layout.

## Hardware records {#boards-records}

The history of the repository records one hardware result: writes of more than 4 bytes lost data
until commit `0e47e29` ("Fix multiple sink.ready in TX-PRE-WAIT"), after which the reporter of the
issue wrote 16 bytes in one transaction on hardware.

The pull request that brought the bus timing to the I2C specification records a second one, on a
LambdaConcept ECPIX-5 (Lattice ECP5) with a 50 MHz PHY clock. The two I2C buses of the board
were tested: the TI TUSB322 USB-C controller and the ITE IT6613 HDMI transmitter. On each bus, in
Standard-mode and in Fast-mode, 500 register reads with a repeated START returned the expected
bytes with 0 errors, and an absent address returned a NACK.

A logic analyzer in the FPGA sampled SCL and SDA at the pins every 20 ns. The table gives the
measured timings against the minimums of the specification:

| Timing | Standard-mode | Minimum | Fast-mode | Minimum |
|--------------------------------|----------------:|--------:|----------------:|--------:|
| START hold, repeated START setup, STOP setup | 7.52 to 7.60 µs | 4.0 to 4.7 µs | 1.98 to 2.04 µs | 0.6 µs |
| SCL low, tLOW | 4.96 to 5.04 µs | 4.7 µs | 1.34 to 1.36 µs | 1.3 µs |
| SCL high, tHIGH | 5.04 µs | 4.0 µs | 1.36 µs | 0.6 µs |
| Data setup, tSU;DAT | 2.48 µs | 0.25 µs | 0.66 µs | 0.1 µs |
| SCL frequency, mean | 98 kHz | | 362 to 365 kHz | |

The test covers neither Fast-mode Plus nor a bus with two controllers. The
[status table](#intro-status) gives the maintainers' status of each feature.

## Adding LiteI2C to a board {#boards-new}

A board needs pads, pull-ups, a speed and the call in its target. Check them in this order.

1. **Pads.** Declare a record with `scl` and `sda` subsignals in the platform, named as the core
   (`i2cmaster` by default) or passed with `pads=`. Both pins need a bidirectional I/O standard of
   the bank voltage of the devices, such as `LVCMOS33`.
2. **Pull-ups.** Nothing drives a released line high, so each line needs a pull-up resistor
   ([I2C in a nutshell](#i2c-primer)). Use the resistors of the board when it has them. The
   internal pull-ups of the FPGA (`Misc("PULLUP=TRUE")` on Xilinx devices) are weak: they suit a
   short bus at Standard-mode.
3. **Speed.** Start at Standard-mode, the reset value of `phy_speed_mode`. Move to Fast-mode or
   Fast-mode Plus only when every device on the bus supports it.
4. **Target.** Call `add_i2c_master()` behind an option of the target, with the name that the
   software uses ([Integration](#integration)).

Then check the result from build to hardware:

```sh
# Elaborate without vendor tools: catches pad and parameter errors
python3 -m litex_boards.targets.<target> --build --no-compile
# Build and load the bitstream in the FPGA (volatile)
python3 -m litex_boards.targets.<target> --build --load
```

Look for the registers of the core in the `csr.csv` of the build (`<name>_phy_speed_mode`,
`<name>_master_*`; `i2cmaster_` by default, `i2c_` on the GMM-7550), then scan the bus from the
CPU or from a host ([Probe and scan](#ex-probe)). A scan that finds nothing, or a `bus_error` on
every address, is covered in [Debugging](#debugging).

## Where to go next {#boards-next}

[Integration](#integration) for the parameters of `add_i2c_master`; [Examples](#examples) for the
first accesses; [Debugging](#debugging) when the bus does not answer.
