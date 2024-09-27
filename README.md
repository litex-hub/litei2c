```
                                     ____  
              __   _ __        ____ /___ \  _____
             / /  (_) /____   /  _/ / ___/ / ___/
            / /__/ / __/ -_)  / /  /_____// /__
           /____/_/\__/\__/ /___/        /____/ 

    Copyright (c) 2024, LiteI2C Developers
```
[![](https://github.com/litex-hub/litei2c/workflows/ci/badge.svg)](https://github.com/litex-hub/litei2c/actions) ![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)

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