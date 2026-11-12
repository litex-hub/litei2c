```
                                     ____  
              __   _ __        ____ /___ \  _____
             / /  (_) /____   /  _/ / ___/ / ___/
            / /__/ / __/ -_)  / /  /_____// /__
           /____/_/\__/\__/ /___/        /____/ 

    Copyright (c) 2024, LiteI2C Developers
```
[![](https://github.com/litex-hub/litei2c/workflows/ci/badge.svg)](https://github.com/litex-hub/litei2c/actions) ![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/litex-hub/litei2c)

[> Intro
--------
LiteI2C provides a small footprint and configurable I2C core.

LiteI2C is structured and operates similar to LiteSPI.

LiteI2C is part of LiteX libraries whose aims are to lower entry level of
complex FPGA cores by providing simple, elegant and efficient implementations of components used in
today's SoC such as Ethernet, SATA, PCIe, SDRAM Controller...

Using Migen to describe the HDL allows the core to be highly and easily configurable.

LiteI2C can be used as LiteX library.

[> Features
-----------
PHY:
  - Portable/Generic.
  - Standard/Fast/Fast Plus Mode I2C Bus support.

Core:
  - Dynamic Crossbar.
  - CSR-based read/write accesses.

<!-- [> Getting started
------------------

Examples of integration can be found on various supported boards of [LiteX-Boards](https://github.com/litex-hub/litex-boards) repository.

[> Tests
--------
Unit tests are available in ./test/.
To run all the unit tests:
  ./setup.py test
Tests can also be run individually:
  python3 -m unittest test.test_name -->

[> Documentation
----------------
The **I2C Master Core manual** is the reference of LiteI2C: a nightly
[PDF](https://github.com/litex-hub/litei2c/releases/download/manual-nightly/litei2c_manual.pdf)
and [HTML page](https://github.com/litex-hub/litei2c/releases/download/manual-nightly/litei2c_manual.html)
are published on the [manual-nightly](https://github.com/litex-hub/litei2c/releases/tag/manual-nightly)
release. Sources in [doc/manual](doc/manual/README.md) (build: `python3 doc/manual/build.py`, outputs in
`build/doc/`; pandoc, XeLaTeX and the fonts listed in the README of `doc/manual`):

- **Understand**: [introduction](doc/manual/01_introduction.md), [I2C in a nutshell](doc/manual/02_i2c_primer.md)
  (open drain, START/STOP, ACK/NACK, addressing, clock stretching, speed modes),
  [I2C in LiteX](doc/manual/03_litex_i2c.md).
- **The core**: [architecture](doc/manual/04_architecture.md), [PHY](doc/manual/05_phy.md),
  [register master](doc/manual/06_master.md).
- **Use it**: [getting started](doc/manual/07_getting_started.md), [integration](doc/manual/08_integration.md),
  [examples](doc/manual/09_examples.md), [supported FPGAs and boards](doc/manual/10_boards.md),
  [simulation and tests](doc/manual/11_simulation.md), [debugging](doc/manual/12_debugging.md).
- **Appendices**: [registers](doc/manual/A_registers.md), [build options](doc/manual/B_build_options.md),
  [glossary](doc/manual/C_glossary.md), [performance and resources](doc/manual/D_performance.md),
  [maintaining this manual](doc/manual/E_maintenance.md) (for contributors).

[> License
----------
LiteI2C is released under the very permissive two-clause BSD license. Under
the terms of this license, you are authorized to use LiteI2C for closed-source
proprietary designs.
Even though we do not require you to do so, those things are awesome, so please
do them if possible:
 - tell us that you are using LiteI2C
 - cite LiteI2C in publications related to research it has helped
 - send us feedback and suggestions for improvements
 - send us bug reports when something goes wrong
 - send us the modifications and improvements you have done to LiteI2C.