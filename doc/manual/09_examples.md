# Examples {#examples}

This chapter shows what the functions of [Bare-metal software](#integ-baremetal) put on the bus:
the bus sequence of each recipe, the byte order of the elements, long transfers, bus recovery and
the meaning of each status. It ends with the gateware sequencer of the public LiteX-M2SDR project,
which configures its SI5351 clock generator through LiteI2C. The C code, the host script and the
interrupt handler are in [Integration](#integration); the status of each feature on hardware is
in the [status table](#intro-status).

## Bus notation {#ex-notation}

The recipes write the bus sequence on one line, in the order the bytes appear on SDA. `S` is a
START, `Sr` a repeated START and `P` a STOP. `0x50+W` and `0x50+R` are the address byte with the
R/W bit, `A` an ACK and `N` a NACK. A byte written by the controller is followed by the ACK of the
target; a byte read is followed by the ACK or NACK of LiteI2C. The primer explains these
conditions ([I2C in a nutshell](#i2c-primer)).

## Probe and scan {#ex-probe}

`i2c_probe()` sends one element with both lengths at 0, so the address alone: `S 0x50+W A P` when
a target answers, `S 0x50+W N P` when none does. The status then has `nack` set. `i2c_scan()`
probes `0x08` to `0x77` and skips the reserved addresses `0x00` to `0x07` and `0x78` to `0x7f`.

`master_addr` holds 7 bits: write `0x50`, not the 8-bit form `0xa0` of some datasheets, which the
register truncates to `0x20`.

## Registers {#ex-register}

Most I2C devices expose registers behind an address pointer: the first byte written sets the
pointer, the next bytes are written at the pointer, and a read returns the bytes from the pointer
on. `i2c_write_reg()` is a 2-byte write; `i2c_read_regs()` is a write of the pointer followed by a
read, joined by a repeated START.

A register write gives `S 0x50+W A reg A value A P`. A read of one register gives
`S 0x50+W A reg A Sr 0x50+R A value N P`: the last byte read is always followed by a NACK, which
tells the target to release SDA.

The bytes of an element are packed most significant first, in both directions. In a write of
`len_tx` bytes, the first byte on the bus is the most significant of those bytes, so the data `(reg
<< 8) | value` sends `reg` first. In a read, the last byte received lands in bits 7:0: a read of two
bytes returns the first byte in bits 15:8. The LiteX-M2SDR library packs its bursts the same way
(`m2sdr_si5351_i2c.c`, "MSB-first").

## Long transfers {#ex-long}

An element carries at most 4 bytes. A `len_tx` or `len_rx` of 5, 6 or 7 means "4 bytes now, more
follow": the PHY transfers 4 bytes, returns a status with `tx_unfinished` or `rx_unfinished` set,
and holds SCL low until the next element arrives. The next element continues the same transaction
without a new START or address, and its length counts from 0 again
([Architecture](#architecture)). `i2c_xfer()` splits any length this way.

A write of 9 bytes takes three elements, with `len_tx` 5, 5 and 1, and gives one transaction:
`S 0x50+W A b0 A b1 A [...] b8 A P`. A read of 6 bytes takes two elements: the first writes the
pointer and reads 4 bytes (`len_tx=1`, `len_rx=5`), the second reads the last 2 (`len_rx=2`). Its
bus sequence is `S 0x50+W A reg A Sr 0x50+R A d0 A d1 A d2 A d3 A d4 A d5 N P`.

Software must wait for each status before it pushes the next element, as `i2c_xfer()` does. If the
target NACKs a byte of a long write, the PHY ends the transaction with a STOP and consumes the
current element: an element pushed after it would start a new transaction with the rest of the
data. The LiteX-M2SDR burst write also checks that `tx_unfinished` matches what it expects.

## Bus recovery {#ex-recover}

A target reset in the middle of a read can keep SDA low, and the next transaction then fails with
`bus_error` before any bit is sent. `i2c_recover()` sends one element with the `recover` bit set:
a START, ten SCL pulses with SDA released, then a repeated START and a STOP. Nine pulses are
enough for any target to finish the byte it was sending ([I2C in a nutshell](#i2c-primer)); the
tenth is harmless.

The address and the data of a recovery element are ignored. `nack` set in its status means that
the bus is not free after the STOP: SDA or SCL is held low by something that the clock
pulses do not release.

## Error handling {#ex-errors}

The status of the last element of a transaction tells how it ended:

| `nack` | `bus_error` | Meaning | Usual action |
|--------|----------------|----------------------------------------|-------------------------------------|
| 0 | 0 | Every byte acknowledged | None |
| 1 | 0 | The target NACKed the address or a written byte | Check the address; the target may be busy |
| 1 | 1 | Bus not free at START or after STOP, stretch timeout or arbitration loss | Recover the bus, then retry once |

A bus error always sets `nack` too, so testing `nack` alone catches every failure; `i2c_check()`
tests `bus_error` first to tell the two cases apart. [Debugging](#debugging) lists the causes of
each case and the checks to make.

## A gateware sequencer {#ex-sequencer}

A device that must be configured before the CPU runs, such as a clock generator, can be written by
gateware. LiteX-M2SDR does this for its SI5351 (`litex_m2sdr/gateware/si5351.py`): it instantiates
`LiteI2C` with FIFOs of depth 8 and adds a small state machine, `LiteI2CSequencer`, as a Wishbone
master of the SoC bus. The sequencer writes the same registers as software would.

| Step | Register access |
|-----------------------------|----------------------------------------------------|
| Flush the old statuses | Read `master_status`, pop `master_rxtx` while `rx_ready` is 1, at most 63 times |
| Wait for room | Read `master_status` until `tx_ready` is 1 |
| Configure | Write `master_active` 1, `master_settings` 2 (`len_tx=2`), `master_addr` `0x60` |
| Send one register | Write `master_rxtx` from a ROM: register in bits 15:8, value in 7:0 |
| Next entry | Back to the flush, until the last entry of the ROM, then `done` |

The ROM holds one 16-bit word per register of the SI5351 table, so each entry is one 2-byte write
at the default Standard-mode. The sequencer finds the register addresses from the base of the
bank, given by `self.get_csr_address("si5351")` in the target, plus the offsets of the
[Register reference](#registers) (`+0x04` for `master_active` to `+0x14` for `master_status`).
It does not check `nack`: a write that the target refuses goes unnoticed, and its `done`
output, read through a status register of the SI5351 module, only says that the table was sent.

A gateware user can also skip the registers and drive the core streams directly, through a crossbar
port added with `add_i2c_device()` ([Gateware users](#integ-gateware)). The element and status
layouts are then those of [Architecture](#architecture). No public user of a gateware port is known;
the [status table](#intro-status) gives the state of the multi-port crossbar.

## Where to go next {#ex-next}

[The register master](#master) for the FIFO contract behind the functions; [Debugging](#debugging)
when a recipe returns `nack`; [Performance and resources](#performance) for the duration of each
transaction.
