# I2C in LiteX {#litex-i2c}

LiteX offers three I2C controllers, and LiteI2C is only one of them. This chapter describes the
two others, the bit-banged core and the Wishbone core, compares the three and says which one to
choose. Read it before adding an I2C bus to a SoC: the choice decides which software can drive
the bus.

The three cores differ mainly in what they leave to the CPU, as the figure below shows. The
bit-banged core leaves everything, the Wishbone core leaves the sequence of bytes, and LiteI2C
leaves only the description of the transaction.

![The three I2C controllers of LiteX, by the work left to the CPU. Software moves each edge of
SCL and SDA through the registers of the bit-banged core, sends each byte or condition to the
Wishbone core, and describes a whole transaction, or a 4-byte chunk of it, to
LiteI2C.](litex_compare.svg)

## The bit-banged core {#litex-bitbang}

The bit-banged core gives software direct control of the two lines (`I2CMaster` in
`litex/soc/cores/bitbang.py`). A write register drives SCL, SDA and the SDA output enable; a
read register returns the levels of both lines. Both lines are open drain: writing a 1 releases
the line, writing a 0 pulls it low.

Everything else is software. The LiteX library `libbase/i2c.c` builds the conditions, bytes and
acknowledges from register accesses and waits a quarter of the SCL period between them. The
period comes from `I2C_FREQ_HZ`, 50 kHz by default. After it releases SCL, the library reads it
back and waits up to about 35 ms for a target that stretches the clock.

This core has the widest software support of LiteX:

- The LiteX BIOS offers the commands `i2c_reset`, `i2c_write`, `i2c_read`, `i2c_scan` and
  `i2c_dev`, for every bit-banged instance of the SoC.
- `add_init` records writes that the BIOS sends at boot, for example to configure a clock chip
  or a codec before anything else runs.
- The device tree generator `litex_json2dts_linux.py` describes it as a `litex,i2c` node for
  Linux, and `litex_json2dts_zephyr.py` maps it for Zephyr.
- `litex_sim --with-i2c` adds a simulation variant, `I2CMasterSim`, connected to a model of an
  SPD EEPROM.

The cost is CPU time and timing accuracy. Each bit takes several register accesses and delays,
so the CPU is busy for the whole transaction, and the bus timing depends on the software. The
core also needs a CPU: a design without one cannot use it.

## The Wishbone core {#litex-wishbone}

The Wishbone core comes from MiSoC, an ancestor of LiteX (`I2CMaster` in
`litex/soc/cores/i2c.py`). It is a Wishbone slave with two words: a configuration word sets the
clock divider, and each write to the transfer word asks for one action. The action is a START, a
byte write, a byte read with its acknowledge, or a STOP.

Software polls an idle bit, or waits for an interrupt, before it sends the next action. The
state machine drives SCL from its divider, reads SCL back only to time SDA changes, and does
not wait for a target that stretches the clock.

No LiteX software drives this core; inside LiteX, the OV5640 camera core
(`litex/soc/cores/ov5640.py`) uses it to configure the sensor.

## LiteI2C {#litex-litei2c}

LiteI2C runs a whole transaction in hardware. Software or a gateware user writes one element:
the 7-bit address, the numbers of bytes to write and to read, up to 4 each, and the bytes to
write. The PHY runs the transaction and returns one status element with the received bytes and
the errors.

The PHY reads SCL back, so it follows a target that stretches the clock, up to 25 ms. It checks
that the bus is free before each START and reports a stuck bus as a bus error. The `recover` bit
runs a bus recovery. A register selects the speed: 100 kHz, 400 kHz or 1 MHz.

The crossbar lets gateware users share the bus with the master, so a design can run an I2C
sequence without a CPU. `add_i2c_master` adds the core to a LiteX SoC, with an interrupt
when `with_irq=True` is passed, or when the SoC reserves an IRQ for `<name>`. [Architecture](#architecture) describes the
core.

## Comparison {#litex-compare}

The table below compares the three cores. The last row counts the board scripts and extensions
of LiteX-Boards that use each one.

| | Bit-banged core | Wishbone core | LiteI2C |
|---------------------|-------------------------|-------------------------|-------------------------|
| Access by the CPU | Each SCL edge | Each byte or condition | Each transaction or chunk |
| Bus timing | Software delays | Hardware divider | Hardware divider |
| Clock stretching | Software wait | Not followed | Hardware wait |
| Error report | NACK, by software | ACK bit | NACK, bus error |
| Bus recovery | `i2c_reset` command | None | `recover` bit |
| Without a CPU | No | Gateware bus master | Crossbar port |
| LiteX software | BIOS, init tables, Linux, Zephyr | None | None |
| Simulation | LiteX simulator | Unit test | Unit tests |
| LiteX-Boards users | 29 files | None | 1 board script |

The software row is the main difference in practice. The LiteX BIOS, the boot-time init tables
and the device tree generators all expect the register layout of the bit-banged core. LiteI2C
has its own register layout, and software drives it directly ([Examples](#examples)).

## How to choose {#litex-choose}

- Keep the bit-banged core when the BIOS or Linux must reach the devices: the BIOS commands, the
  init tables and the Linux driver work only with it. The `alinx_ax7035` board script makes this
  choice for its temperature sensor and EEPROM.
- Use LiteI2C when gateware must configure a device without a CPU, when the bus timing must not
  depend on software, or when bare-metal software should not spend its time on each bit. The
  LiteX-M2SDR design uses it to configure its clock generator.
- Use the Wishbone core only for the designs that already use it, such as the OV5640 camera core.

A SoC can hold several I2C cores, each on its own pads. A LiteI2C instance and a bit-banged
instance can coexist, for example one for a gateware sequencer and one for the BIOS.

## Device tree naming {#litex-naming}

The Linux device tree generator emits one `litex,i2c` node for every register bank named `i2c`
followed by a number, such as `i2c0`, whatever the core behind it. The Zephyr generator does the
same for `i2c0`. Both nodes describe the register layout of the bit-banged core.

A LiteI2C instance must therefore not be named `i2c0`, `i2c1` and so on in a SoC whose device
tree is generated: the operating system would drive its registers as a bit-banged core. The
default name of `add_i2c_master`, `i2cmaster`, and the name `i2c` used by the GMM-7550 board
script both avoid the problem ([Integration](#integration)).
