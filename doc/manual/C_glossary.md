# Glossary {#glossary}

The terms of I2C and of LiteI2C used in this manual, in alphabetical order. Each entry points to
the chapter that explains it.

| Term | Meaning |
|--------------------------|--------------------------------------------------------------------------|
| 7-bit address | Address of a target, sent with the R/W bit in the first byte of a transaction; the only form LiteI2C sends. See [I2C in a nutshell](#i2c-primer) |
| 10-bit address | Extended address sent in two bytes, the first starting with `11110`; not supported by LiteI2C. See [I2C in a nutshell](#i2c-primer) |
| ACK | Acknowledge: the receiver of a byte pulls SDA low during the ninth clock. See [I2C in a nutshell](#i2c-primer) |
| Arbitration | Resolution of two controllers that start together: the one that reads SDA low while releasing it has lost. See [I2C in a nutshell](#i2c-primer) |
| Bus error | Status bit set when the bus is not free before a START or after a STOP, on a stretch timeout or on an arbitration loss (`bus_error`). See [The PHY](#phy) |
| Bus recovery | START, ten SCL pulses with SDA released, then a repeated START and a STOP, sent to free a target that holds SDA low (`recover` bit). See [Examples](#examples) |
| Chunk | Up to 4 bytes of a longer transaction, carried by one element whose length is 5 to 7. See [Architecture](#architecture) |
| Clock stretching | A target holding SCL low to slow the controller down; LiteI2C waits up to 25 ms. See [The PHY](#phy) |
| Controller | The device that drives SCL and starts transactions; LiteI2C is a controller only. The code says *master* |
| Crossbar | `LiteI2CCrossbar`: shares the PHY between the register master and gateware ports, one at a time. See [Architecture](#architecture) |
| Element | One entry of the stream from the core to the PHY: data, address, lengths and `recover` bit. See [Architecture](#architecture) |
| Fast-mode | I2C speed mode up to 400 kHz (`phy_speed_mode` 1). See [I2C in a nutshell](#i2c-primer) |
| Fast-mode Plus | I2C speed mode up to 1 MHz (`phy_speed_mode` 2). See [I2C in a nutshell](#i2c-primer) |
| General call | Address `0x00`, addressed to every target. See [I2C in a nutshell](#i2c-primer) |
| High-speed mode | I2C speed mode up to 3.4 MHz; not supported by LiteI2C. See [I2C in a nutshell](#i2c-primer) |
| NACK | Not acknowledge: SDA left high during the ninth clock, by a target that refuses, or by the controller after the last byte read. See [I2C in a nutshell](#i2c-primer) |
| Open drain | Output that can only pull a line low; a pull-up resistor brings it high. See [I2C in a nutshell](#i2c-primer) |
| Port | Access of one user to the crossbar, with its streams and its `active` signal. See [Architecture](#architecture) |
| Pull-up | Resistor from a line to the supply, the only source of a high level on the bus. See [Supported FPGAs and boards](#boards) |
| R/W bit | Last bit of the address byte: 0 for a write, 1 for a read. See [I2C in a nutshell](#i2c-primer) |
| Register master | `LiteI2CMaster`: registers and FIFOs through which a CPU or a host sends elements. See [The register master](#master) |
| Repeated START | A START sent without a STOP before it, to turn a write into a read in one transaction. See [I2C in a nutshell](#i2c-primer) |
| SCL | Serial clock line, driven by the controller and held low by a stretching target. See [I2C in a nutshell](#i2c-primer) |
| SDA | Serial data line, stable while SCL is high except for START and STOP. See [I2C in a nutshell](#i2c-primer) |
| SMBus | System Management Bus, a profile of I2C with timeouts and extra protocols; LiteI2C implements none of them. See [I2C in a nutshell](#i2c-primer) |
| Speed mode | Value of `phy_speed_mode`, selecting the SCL divider. See [The PHY](#phy) |
| Standard-mode | I2C speed mode up to 100 kHz (`phy_speed_mode` 0, the reset value). See [I2C in a nutshell](#i2c-primer) |
| START | SDA falling while SCL is high: begins a transaction. See [I2C in a nutshell](#i2c-primer) |
| Status element | Entry returned by the PHY for each element: received data, `nack`, `bus_error` and the unfinished flags. See [Architecture](#architecture) |
| STOP | SDA rising while SCL is high: ends a transaction and frees the bus. See [I2C in a nutshell](#i2c-primer) |
| Target | A device that answers its address; the code says *slave*. See [I2C in a nutshell](#i2c-primer) |
| tBUF | Bus free time between a STOP and the next START. See [I2C in a nutshell](#i2c-primer) |
| tHD;STA | Hold time of a START: from SDA falling to SCL falling. See [I2C in a nutshell](#i2c-primer) |
| tHIGH, tLOW | High and low periods of SCL. See [I2C in a nutshell](#i2c-primer) |
| Transaction | Everything from a START to the STOP, one or several elements. See [Architecture](#architecture) |
| tSU;STA | Setup time of a repeated START: from SCL rising to SDA falling. See [I2C in a nutshell](#i2c-primer) |
| tSU;STO | Setup time of a STOP: from SCL rising to SDA rising. See [I2C in a nutshell](#i2c-primer) |
| Ultra Fast-mode | Unidirectional I2C mode up to 5 MHz; not supported by LiteI2C. See [I2C in a nutshell](#i2c-primer) |
