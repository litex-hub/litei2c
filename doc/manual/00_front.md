```{=latex}
\frontmatter
```

# About this document {.unnumbered}

This manual is the reference of the LiteI2C project: an I2C controller core for FPGAs, written in
Migen and LiteX. It covers the PHY, the register master, the crossbar, the integration in a
LiteX SoC and the debugging. It is written for FPGA engineers who need to talk to I2C devices,
and it teaches the I2C bus along the way.

No prior knowledge of I2C is assumed. Part I explains the bus as its specification defines it,
then the I2C cores that LiteX offers and where LiteI2C fits among them. Part II describes the
core: its architecture, the PHY and the register master.

Part III is the user guide: a first simulation, the integration in a LiteX SoC, software
recipes, the supported boards, the tests and the debugging. The appendices hold the register
reference, the build options, the glossary, the performance figures and the maintenance notes of
this manual.

| If you want to | Read |
|------------------------------------------|----------------------------------------------|
| Know what the project does and does not | [Introduction](#introduction) |
| Check what is validated on hardware | [Status](#intro-status) |
| Learn how the I2C bus works | [I2C in a nutshell](#i2c-primer) |
| Choose between the I2C cores of LiteX | [I2C in LiteX](#litex-i2c) |
| Run a first transaction in simulation | [Getting started](#getting-started) |
| Add an I2C bus to your own SoC | [Integration](#integration) |
| Drive a device from software | [Examples](#examples) |
| Understand a device that does not answer | [Debugging](#debugging) |

The manual follows the repository: every name, number and default is taken from the source code,
and the manual is generated from it on the date printed on the title page. When the code and the
manual disagree, the code is right and the manual has a bug.

## Conventions {.unnumbered}

- Numbers: `0x` prefix for hexadecimal, `0b` for binary. I2C addresses are 7-bit addresses,
  such as `0x50`, never the address byte that carries the R/W bit.
- Rates: SCL and system clock frequencies in kHz and MHz; throughputs in kB/s (10^3 bytes per
  second). Times in µs and ns, with the symbols of the I2C specification (tLOW, tHD;STA).
- *Controller* and *target* are the I2C roles, as in the I2C specification. Code names keep
  the older words: the register frontend of LiteI2C is `LiteI2CMaster`, called *the master*.
- *The core* is the `LiteI2C` wrapper; *the PHY* drives SCL and SDA and runs the transactions.
- *An element* is one transaction, or one chunk of up to 4 bytes of a longer one, as the core
  passes it to the PHY; *a status element* is the answer of the PHY to an element.
- A *board script* is a target script of LiteX-Boards (`litex_boards/targets/<board>.py`).
- `<board>` stands for the name of a board script without its extension, such as
  `gmm7550_usb3`.
- `<name>` stands for the name given to `add_i2c_master` in a SoC, `i2cmaster` by default.
- Paths are relative to the repository root. Shell commands are given for a Linux host.
- When the text names a source file, it is the file to open to check or extend the fact.
