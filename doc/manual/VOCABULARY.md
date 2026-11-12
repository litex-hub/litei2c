# Vocabulary of the LiteI2C manual

Project-specific writing rules, completing the generic `STYLE.md` of the manual kit.

## Names of the parts

- *LiteI2C* is the project; *the core* is the `LiteI2C` wrapper (PHY, crossbar and master), the
  module that `add_i2c_master` adds to a SoC.
- *the PHY* is `LiteI2CPHYCore`: the state machine that runs a transaction on the bus, its speed
  register and its SDA driver. *the clock generator* is `LiteI2CClkGen`, inside the PHY: it
  makes SCL and the transmit and receive strobes.
- *the master* is the register frontend, `LiteI2CMaster`: registers and FIFOs for software. The
  word "master" names this module only; the I2C role is *controller* (below).
- *the crossbar* is `LiteI2CCrossbar`; *a port* is one of its user interfaces (the master, or a
  gateware user added by `add_i2c_device`). *a gateware user* is a module of the design that
  drives a port, such as a register sequencer.
- *an element* is one element of the core-to-PHY stream (`data`, `addr`, `len_tx`, `len_rx`,
  `recover`): one transaction, or one *chunk* of up to 4 bytes of a longer one. *a status
  element* is the element the PHY returns for each element (`data`, `nack`, `bus_error`,
  `unfinished_tx`, `unfinished_rx`).
- *register* in prose, never "CSR", except for the bus name "CSR bus". The registers inside an
  I2C device (an EEPROM, a sensor) are *device registers*.
- *the bit-banged core* is `I2CMaster` of `litex/soc/cores/bitbang.py`; *the Wishbone core* is
  `I2CMaster` of `litex/soc/cores/i2c.py`. Both are LiteX cores, not part of LiteI2C.
- *target* is the I2C role (below), so a LiteX-Boards target script is called a *board script*
  (`litex_boards/targets/<board>.py`); *board* is the hardware.

## Protocol names

- I2C roles as UM10204 (revision 7) names them: *controller* (drives SCL, starts transactions)
  and *target* (answers to its address). Code identifiers keep their names (`LiteI2CMaster`,
  `i2cmaster`, "slave" in comments and test names).
- Signals: *SCL* (serial clock) and *SDA* (serial data); pads `scl` and `sda`, or `scl_o`,
  `scl_oe`, `scl_i`, `sda_o`, `sda_oe`, `sda_i` for split pads.
- Conditions in capitals: *START*, *repeated START*, *STOP*; *ACK* and *NACK*; *the R/W bit*.
- *a transaction* runs from a START to a STOP, repeated STARTs included. *a write* sends bytes
  to the target, *a read* receives bytes from it, *a write-then-read* is a write followed by a
  repeated START and a read. *an address probe* is a transaction with no data byte.
- *7-bit address*: the address as datasheets and LiteI2C give it (`0x50`), without the R/W bit.
  The *address byte* is the 7-bit address shifted left with the R/W bit (`0xa0`, `0xa1`).
- *speed mode*: *Standard-mode* (Sm, 100 kHz), *Fast-mode* (Fm, 400 kHz), *Fast-mode Plus* (Fm+,
  1 MHz), *High-speed mode* (Hs-mode) and *Ultra Fast-mode* (UFm), with their hyphens. The
  *speed code* is the value of the `speed_mode` register.
- *clock stretching* (a target holds SCL low), *arbitration* and *arbitration loss*, *bus error*
  (the `bus_error` status bit and the conditions it reports), *bus recovery* (the ten clock
  pulses and repeated START of the `recover` bit; UM10204 calls it *bus clear*), *bus free time*.
- Timing parameters with the symbols of UM10204: tLOW, tHIGH, tHD;STA, tSU;STA, tSU;STO, tBUF,
  tSU;DAT, tHD;DAT, tr; the bus capacitance Cb.
- *SMBus* for the System Management Bus; *open drain* as a noun, *open-drain* as an adjective;
  *pull-up*.

## Placeholders

- `<board>` is a LiteX-Boards board script name without `.py`, such as `gmm7550_usb3`;
  `<name>` is the name given to `add_i2c_master` (`i2cmaster` by default). Both are defined once
  in the Conventions of the front matter.

## Hardware names

- FPGA families as LiteX names them: Xilinx 7-Series, Lattice iCE40, Lattice ECP5, Gowin,
  Efinix, Cologne Chip GateMate.
- Boards as LiteX-Boards names them (GMM-7550); products by their project name (LiteX-M2SDR).
- I2C devices by their part number when a source names it (SI5351 clock generator), otherwise by
  their kind (EEPROM, temperature sensor, USB-C power delivery controller).
