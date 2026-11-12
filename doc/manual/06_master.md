# The register master {#master}

This chapter describes the register master: the part of the core through which software runs I2C
transactions. Read it to write a driver, to drive the bus from a host script, or to choose the
FIFO depths and the interrupt. Each write of the data register sends one element to the PHY
([Architecture](#architecture)), and each read pops one status element.

## At a glance {#master-glance}

| Item | Value |
|-------------------|-------------------------------------------------------------------------------|
| Class | `LiteI2CMaster` (`litei2c/core/master.py`), built by `LiteI2C` with `with_master=True` |
| Registers | `active`, `settings`, `addr`, `rxtx`, `status`; `speed_mode` in the PHY |
| Element | `rxtx` write: data, with the `addr` and `settings` values of that moment |
| Status element | `status` fields and `rxtx` read, which pops it |
| FIFOs | TX and RX, depth 1 by default (`i2c_master_tx_fifo_depth`, `i2c_master_rx_fifo_depth`) |
| Interrupt | Optional, when a status element arrives (`with_irq`) |
| Bus ownership | `active` requests the bus from the crossbar and holds it |
| Status | See [status](#intro-status) |

## Registers {#master-registers}

The master has five registers and the PHY one, plus the three event registers of
[Interrupt](#master-irq). In a LiteX SoC their names carry the name of the
core, then `master_` or `phy_`: `i2c_master_rxtx` for a core named `i2c`. The offsets are in the
[Register reference](#registers).

| Register | Bits | Access | Role |
|-------------------------|-----:|-------------|----------------------------------------------|
| `phy_speed_mode` | 2 | Read-write | Speed: 0 = 100 kHz, 1 = 400 kHz, 2 = 1 MHz, 3 = 100 kHz (reserved) |
| `master_active` | 1 | Read-write | 1 requests the bus and holds it, 0 releases it |
| `master_settings` | 17 | Read-write | Lengths and recover bit of the next elements |
| `master_addr` | 7 | Read-write | 7-bit target address of the next elements |
| `master_rxtx` | 32 | Write, read | Write: push one element. Read: pop one status element |
| `master_status` | 18 | Read-only | FIFO flags and fields of the oldest status element |

The fields of `settings` and `status` are listed below. They map one to one onto the element and
the status element of [Architecture](#arch-element).

| Register | Field | Bits | Meaning |
|-------------|---------------------|------:|-------------------------------------------------|
| `settings` | `len_tx` | 2:0 | Bytes to write, 5 to 7: 4 bytes and more to come |
| | `len_rx` | 10:8 | Bytes to read, 5 to 7: 4 bytes and more to come |
| | `recover` | 16 | Run a bus recovery |
| `status` | `tx_ready` | 0 | The TX FIFO accepts an element |
| | `rx_ready` | 1 | A status element waits in the RX FIFO |
| | `nack` | 8 | Transaction failed: NACK or bus error |
| | `bus_error` | 9 | The bus misbehaved |
| | `tx_unfinished` | 16 | 4 bytes written, the next element is expected |
| | `rx_unfinished` | 17 | 4 bytes read, the next element is expected |

## One transaction step by step {#master-transaction}

A write of `rxtx` builds an element from the written data and the values that `addr` and
`settings` hold at that moment, and pushes it into the TX FIFO. Changing `addr` or `settings` afterwards does not
affect the elements already pushed. Software runs a transaction in the following order:

1. Write `phy_speed_mode`, while `active` is 0, then write 1 to `active`.
2. Write `addr` with the 7-bit address and `settings` with the lengths.
3. Wait for `status.tx_ready`, then write the bytes to send to `rxtx`. Without bytes to send
   (a read or a probe), write any value: the write is what starts the transaction.
4. Wait for `status.rx_ready`. The other fields of `status` now describe the transaction.
5. Read `rxtx`: it returns the bytes read and pops the status element.
6. Repeat from step 2 for the next transaction, or write 0 to `active` to release the bus.

The figure below shows the register read of a target: one byte to set the register pointer, then
two bytes read back.

![Register read with the master. Look at the single rxtx write: one element carries the whole
write-then-read, and the PHY answers with one status element.](master_seq.svg)

The status fields other than `tx_ready` and `rx_ready` show the head of the RX FIFO. They are
valid only while `rx_ready` is 1, and they change when software reads `rxtx`. Read `status` first,
then `rxtx`.

## The FIFO contract {#master-fifo}

Two rules keep software and the PHY in step. First, a write of `rxtx` while `tx_ready` is 0 is
lost without notice: the master pushes into the FIFO without checking that it has room. Poll
`tx_ready` before each write.

Second, every element returns exactly one status element, writes included, and software reads
each one. With the default RX FIFO depth of 1, an unread status element blocks the PHY at the end
of the next transaction. In the middle of a long transfer it blocks with SCL held low.

With `clock_domain` other than `sys`, the crossbar FIFOs add 32 entries in each direction
([Clock domain](#arch-clock-domain)).

With the default depths of 1, software alternates: one `rxtx` write, one status element read. A
long transfer is the same loop, one chunk per iteration ([Long transfers](#master-long)).

Deeper FIFOs let software queue several elements and read the status elements later, which saves
polling round trips over a slow bridge. Software reads every status element all the same, in order.
LiteX-M2SDR, which programs a clock generator from gateware, uses depths of 8.

## Long transfers {#master-long}

A transfer of more than 4 bytes is a series of `rxtx` writes in one transaction, as described in
[Long transfers in chunks](#arch-chunks). For a 6-byte write, software writes `settings` with
`len_tx = 5` and the first 4 bytes to `rxtx`.

It then reads the status element, which has
`tx_unfinished` set, writes `settings` with `len_tx = 2` and the last 2 bytes.

For a long read, each status element with `rx_unfinished` set returns 4 bytes. Software answers
it with one more `rxtx` write whose `len_rx` is the number of bytes left, or 5 to 7 when more than
4 remain. [Integration](#integ-baremetal) gives a C function that handles any length.

Between two chunks the bus is held, with SCL low, until software writes `rxtx`. Keep the CPU busy
on the transfer until it ends: an interrupt routine or a task switch in between stretches the
bus for every device on it.

## Interrupt {#master-irq}

With `with_irq=True`, the master raises an event when a status element arrives in an empty RX
FIFO. The event uses the three event registers of LiteX: `ev_status`, `ev_pending` and
`ev_enable`, each with one field, `rx_ready`. Write 1 to `ev_enable` to enable it, and 1 to
`ev_pending` to clear it after reading the status element.

The event fires on the rising edge of "RX FIFO not empty". With a deeper RX FIFO, a second status
element that arrives before software empties the FIFO does not fire a new event: the handler
reads status elements while `rx_ready` is 1. The interrupt has its status in the
[status](#intro-status) table.

## Sharing the bus with gateware {#master-sharing}

The master is one port of the crossbar ([Sharing the bus](#arch-crossbar)). While software holds
`active` at 1, gateware users of the same core wait. Software that shares the bus with gateware
writes 1 to `active` only around its transactions, and 0 as soon as they end.

Writing 0 to `active` in the middle of a long transfer leaves the PHY waiting for the next chunk
with SCL low. The bus then stays blocked for every user. Release the bus only after the last
status element.

## In the code {#master-code}

| Item | File and role |
|---------------------|-----------------------------------------------------------------------|
| `LiteI2CMaster` | `litei2c/core/master.py`: registers, TX and RX `SyncFIFO`, event manager |
| `speed_mode` | `litei2c/phy/generic.py`: the PHY register |
| Master port | `litei2c/__init__.py`: the master on the first crossbar port |

Next: [Getting started](#getting-started) runs the master in simulation, step by step.
