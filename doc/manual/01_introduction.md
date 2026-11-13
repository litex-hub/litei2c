```{=latex}
\mainmatter
\part{Understand}
```

```{=html}
<h1 class="part">Part I. Understand</h1>
```

# Introduction {#introduction}

This chapter says what LiteI2C is, why it exists, what it does and what it does not do. It gives
the status of each part, the layout of the repository and a map of the manual. Every reader should
start here.

## What the project is {#intro-what}

LiteI2C connects an FPGA design to I2C devices: EEPROMs, sensors, clock generators, power
controllers. It is an I2C controller written in Migen and LiteX. The hardware runs each
transaction on the bus: START, address, data bytes, acknowledges, repeated START and STOP.
Software or gateware only describes the transaction and reads back its result.

The project has four parts, shown in the figure below. The PHY drives SCL and SDA and runs the
transactions. The master gives software access to the PHY through registers. Gateware users,
such as a sequencer that configures a chip at power-up, connect to their own ports. The crossbar
gives the PHY to one port at a time.

![LiteI2C at a glance. The CPU drives the master through registers on the CSR bus and may get an
interrupt from it; a gateware user drives its own port; the crossbar passes the elements of one
port at a time to the PHY, which runs the transactions on SCL and SDA.](intro_overview.svg)

The core is used as a LiteX library, usually through the `add_i2c_master` method of a LiteX SoC
([Integration](#integration)). It generates Verilog through LiteX like any other LiteX core, and
there is no standalone generator.

## Why LiteI2C {#intro-why}

LiteX also has a bit-banged I2C core: two registers that software toggles to move SCL and
SDA. It works with the LiteX BIOS and Linux, but the CPU spends a register access on every
edge of the clock and the bus timing depends on software delays. Without a CPU, a design cannot
use it at all.

LiteI2C moves the bus timing into hardware. Software writes the address, the lengths and up to 4
data bytes, and the PHY produces a transaction with the clock derived from the system clock (or
from the clock of the PHY domain).

A gateware user can do the same through a crossbar port, without a CPU. [I2C in
LiteX](#litex-i2c) compares the I2C cores of LiteX in detail.

The core is portable. It uses only generic LiteX I/O (`SDRTristate`), which LiteX maps on every
FPGA family it supports, and the figure below shows its place in a SoC. The pull-up resistors and
the devices are on the board.

![LiteI2C in a SoC. The CPU reaches the registers on the CSR bus and gets an optional interrupt;
the open-drain I/O only pulls SCL and SDA low; the pull-ups to VDD and the I2C devices are on the
board.](intro_soc.svg)

## Features at a glance {#intro-features}

| Area | Features |
|--------------------|------------------------------------------------------------------------|
| Bus | One I2C bus per instance, LiteI2C as the only controller; open-drain SCL and SDA through `SDRTristate`, or split pads |
| Speed | Standard-mode (100 kHz), Fast-mode (400 kHz) and Fast-mode Plus (1 MHz), selected at run time by a register; SCL derived from the PHY clock (`sys` by default) |
| Transactions | 7-bit addresses; address probe, write, read and write-then-read with a repeated START; up to 4 bytes per element, longer transfers in chunks |
| Robustness | Bus free check before START, clock stretching with a 25 ms timeout, arbitration loss detection with release of the bus, bus release check after STOP, bus recovery with ten clock pulses |
| Status | One status element per element: NACK, bus error, chunk flags, received bytes |
| Master | Registers for software, TX and RX FIFOs of configurable depth, optional interrupt on received status |
| Sharing | Crossbar between the master and gateware users, round-robin arbitration; PHY in its own clock domain as an option |
| Integration | LiteX library through `add_i2c_master` |
| Verification | Simulation tests in `test/`: PHY errors, transfers with a simulated target, bus timing, speed codes, clock domain |

## Status {#intro-status}

The table below gives the status of each part of LiteI2C. It is the only status table of the
manual: the other chapters link to it. The last column says whether a test of `test/` covers the
part in simulation.

| Part | Scope | Status | Simulation test |
|------------------------|-----------------------------------------|----------------------|--------------|
| Writes | Address probe, writes of 1 to 4 bytes | Validated on hardware | Yes |
| Long writes | Writes over 4 bytes, in chunks | Validated on hardware | Yes |
| Reads | Reads and write-then-read, up to 4 bytes | Validated on hardware | Yes |
| Long reads | Reads over 4 bytes, in chunks | In development | Yes |
| Standard-mode | Speed codes 0 and 3 (reserved), 100 kHz | Validated on hardware | Yes |
| Fast-mode | Speed code 1, 384.6 kHz at most | Validated on hardware | Yes |
| Fast-mode Plus | Speed code 2, 1 MHz | In development | Yes |
| Bus timing | START, STOP, SCL low and high times of the I2C specification | Validated on hardware (Standard-mode, Fast-mode) | Yes |
| Master | Registers, FIFOs, status polling | Validated on hardware | Yes |
| Interrupt | `with_irq=True` | In development | No |
| Clock stretching | Detection and 25 ms timeout | In development | Yes |
| Bus errors and recovery | Stuck lines, `recover` bit | In development | Yes |
| Arbitration loss | Detection and release of the bus on a multi-controller bus | In development | Yes |
| Crossbar | Several ports, gateware users | In development | No |
| Clock domain | PHY in a `clock_domain` other than `sys` | In development | Yes |

*Validated on hardware* means that the part is in normal use on real boards and that the
maintainers state that it works. Numbers, such as a transfer rate, are given only where a public
record exists. *In development* means that the code is in the repository but has no recorded use
on hardware: use it, but expect to debug it.

[Supported FPGAs and boards](#boards) lists the boards and the designs that use LiteI2C.

## Who uses it {#intro-users}

`add_i2c_master` of LiteX instantiates LiteI2C. In LiteX-Boards, one board script calls it: the
GMM-7550 script, with its `--usb pd` option, uses it to reach the USB power delivery controller
of the board. The other board scripts with an I2C bus use the bit-banged core of LiteX, which the
LiteX BIOS and Linux drive ([I2C in LiteX](#litex-i2c)).

LiteX-M2SDR, a public Enjoy-Digital SDR board design, configures its SI5351 clock generator
through LiteI2C. A gateware sequencer writes the registers of the master at power-up, and a C
library on the host drives the same registers later. It is the reference example of this manual
([Examples](#examples)).

## What it is not {#intro-limits}

LiteI2C is a controller for one bus where it is the only controller. It leaves out the rest of
the I2C specification:

- No target mode: LiteI2C cannot answer to an address.
- No 10-bit addressing: the address field has 7 bits ([Addressing](#primer-address)).
- No High-speed mode and no Ultra Fast-mode; no SCL frequency other than the three nominal ones,
  at or below which the PHY runs ([Clock generator](#phy-clkgen)).
- No SMBus features: no packet error checking, no alert line, no bus timeout other than the
  clock stretching timeout.
- Not validated on a bus with several controllers. The PHY detects an arbitration loss, releases
  SDA and SCL without a STOP and reports a bus error, and software retries; no hardware record
  covers such a bus ([Errors](#phy-errors)).
- No LiteX software: the LiteX BIOS commands, the boot-time init tables and the Linux driver all
  target the bit-banged core. Software drives LiteI2C through its registers
  ([Examples](#examples)).

The bus timing of the PHY meets the minimums of the I2C specification in the three speed modes.
The price is a Fast-mode SCL of 384.6 kHz at most, for its 1.3 µs low time.
[Bus timing](#phy-timing) gives the values.

## Repository layout {#intro-layout}

| Path | Content |
|------------------------------------------|----------------------------------------------------|
| `litei2c/__init__.py` | The `LiteI2C` wrapper: PHY, crossbar, master, `add_i2c_device` |
| `litei2c/phy/generic.py` | The PHY: speed register, SDA I/O, transaction state machine, errors |
| `litei2c/clkgen.py` | The clock generator of the PHY: SCL, clock stretching, SCL I/O |
| `litei2c/core/master.py` | The master: registers, FIFOs, interrupt |
| `litei2c/crossbar.py` | The crossbar between the ports and the PHY, clock domain crossing |
| `litei2c/common.py` | Stream layouts between the core and the PHY |
| `test/test_phy.py` | PHY errors, recovery, stretching, master status bits |
| `test/test_target.py`, `test/i2c_target.py` | Transfers with a simulated I2C target, through the PHY and the master |
| `test/test_clkgen.py` | Divisors of the speed codes |
| `test/test_clock_domain.py` | PHY in its own clock domain |
| `doc/` | This manual (`doc/manual/`) and its figures (`doc/diagrams/`) |

The integration method `add_i2c_master` is in `litex/soc/integration/soc.py` of the LiteX
repository. LiteX installs LiteI2C with its other cores, through `litex_setup.py`.

## License and credits {#intro-license}

LiteI2C is released under the BSD 2-Clause license. It can be used in closed-source and commercial
designs. The `LICENSE` file gives the full text.

LiteI2C follows the structure of LiteSPI, the SPI flash core of LiteX, and is maintained by
Enjoy-Digital as part of the LiteX ecosystem. The project thanks its contributors, listed in the
`CONTRIBUTORS` file and in the history of the repository.

## How to read this manual {#intro-reading}

If I2C is new to you, read [I2C in a nutshell](#i2c-primer) next, then [I2C in
LiteX](#litex-i2c). Otherwise, the table below sends each question to its chapter.

| Question | Chapter |
|-----------------------------------------------|----------------------------------------|
| How does an I2C transaction work? | [I2C in a nutshell](#i2c-primer) |
| Which I2C core of LiteX should I use? | [I2C in LiteX](#litex-i2c) |
| How is the core organised? | [Architecture](#architecture) |
| How are SCL and SDA generated? | [The PHY](#phy) |
| How does software run a transaction? | [The register master](#master) |
| How do I try it without a board? | [Getting started](#getting-started) |
| How do I add it to my SoC? | [Integration](#integration) |
| How do I read a sensor or write an EEPROM? | [Examples](#examples) |
| Which board can I use? | [Supported FPGAs and boards](#boards) |
| How do I simulate and test? | [Simulation and tests](#simulation) |
| A device does not answer: what now? | [Debugging](#debugging) |
| What does this acronym mean? | [Glossary](#glossary) |
