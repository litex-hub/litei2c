```{=latex}
\part{The core}
```

```{=html}
<h1 class="part">Part II. The core</h1>
```

# Architecture {#architecture}

This chapter describes how LiteI2C is built: its blocks, the stream elements that travel between
them and how several users share one bus. Read it before the PHY and master chapters, or before
you connect your own gateware to the core. The I2C bus itself is explained in
[I2C in a nutshell](#i2c-primer).

## At a glance {#arch-glance}

| Item | Value |
|-------------------|----------------------------------------------------------------------------|
| Top-level class | `LiteI2C` (`litei2c/__init__.py`) |
| Parts | PHY, crossbar, optional register master |
| Role on the bus | Controller only, 7-bit addresses, one controller per bus |
| Unit of work | One element: a whole transaction, or a chunk of up to 4 bytes of it |
| Answer | One status element per element: returned bytes and error flags |
| Speeds | 100 kHz, 400 kHz, 1 MHz, chosen by a register |
| Clock | Registers in `sys`; PHY in `clock_domain` (`sys` by default), SCL divisors from `sys_clk_freq` |
| Software access | Master registers (`with_master=True`, default) |
| Gateware access | Crossbar ports (`add_i2c_device`) |
| Status | See [status](#intro-status) |

The constructor takes the parameters below. The master FIFO depths and the interrupt are
described in [The register master](#master).

| Parameter | Role, default |
|----------------------------------------|-----------------------------------------------------|
| `sys_clk_freq` | Frequency in Hz of the PHY clock (`sys`, or `clock_domain`), used for the SCL divisors |
| `pads` | I2C pads; required when `phy` is not given (default `None`) |
| `phy` | An existing PHY; `None` builds `LiteI2CPHYCore` (default `None`) |
| `clock_domain` | Clock domain of the PHY (default `"sys"`, see [Clock domain](#arch-clock-domain)) |
| `with_master` | Adds the register master (default `True`) |
| `i2c_master_tx_fifo_depth` | Elements the master can queue (default `1`) |
| `i2c_master_rx_fifo_depth` | Status elements the master can hold (default `1`) |
| `with_irq` | Adds an interrupt on a returned status element (default `False`) |

## Blocks {#arch-blocks}

LiteI2C has three blocks in a row, as the figure below shows. The register master turns register
writes from the CPU into elements. The crossbar gives the PHY to one user at a time: the master or
a gateware user. The PHY runs the transaction on SCL and SDA and answers with a status element.

![LiteI2C blocks. Follow the cyan path between the crossbar and the PHY: every user, software
through the master registers or gateware through its own port, reaches the bus through the same
element and status element streams.](arch_blocks.svg)

The PHY holds all the I2C knowledge: clock generation, START, STOP, ACK, clock stretching and
error detection ([The PHY](#phy)). The master and the crossbar only move elements and status
elements. A gateware user therefore drives the bus with the same elements as software, without
the CPU.

## Elements and status elements {#arch-element}

The whole core rests on one pair of streams. The user sends an *element* that describes what to
do; the PHY does it and sends back one *status element*. The figure below shows the fields of both.

![The element and the status element. Look at the data field: 32 bits, up to 4 bytes in each
direction; the two length fields that follow describe a whole transaction, write then read, in one
element.](arch_element.svg)

| Field | Bits | Meaning |
|-------------------|-----:|---------------------------------------------------------------|
| `data` | 32 | Bytes to write, in the low `len_tx` bytes |
| `addr` | 7 | 7-bit target address, without the R/W bit |
| `len_tx` | 3 | Bytes to write: 0 to 4; 5 to 7 means 4 bytes now and more to come |
| `len_rx` | 3 | Bytes to read: 0 to 4; 5 to 7 means 4 bytes now and more to come |
| `recover` | 1 | Run a bus recovery instead of a transaction |

The status element answers with the fields below.

| Field | Bits | Meaning |
|-------------------|-----:|---------------------------------------------------------------|
| `data` | 32 | Bytes read, in the low bytes; not meaningful after a write |
| `nack` | 1 | The transaction failed: a NACK or a bus error |
| `bus_error` | 1 | The bus misbehaved: not free, stretch timeout, arbitration lost |
| `unfinished_tx` | 1 | 4 bytes written, the PHY waits for the next element |
| `unfinished_rx` | 1 | 4 bytes read, the PHY waits for the next element |

The two lengths decide the shape of the transaction. The table below lists the four shapes; the
PHY chooses the R/W bit of the address byte from them.

| `len_tx` | `len_rx` | Bus sequence |
|---------:|---------:|---------------------------------------------------------------------|
| 0 | 0 | START, address + W, STOP: an address probe |
| > 0 | 0 | START, address + W, bytes, STOP: a write |
| 0 | > 0 | START, address + R, bytes, NACK on the last one, STOP: a read |
| > 0 | > 0 | Write, repeated START, address + R, read, STOP: a write-then-read |

The write-then-read is the usual way to read a register of a sensor or an EEPROM. The written
bytes set the register pointer, and the read returns the content without releasing the bus in
between ([I2C in a nutshell](#i2c-primer)).

## Byte order {#arch-byte-order}

Bytes travel most significant first in both directions. A write of `len_tx` bytes sends the low
`len_tx` bytes of `data`, the highest of them first: `len_tx = 2` with `data = 0x1122` sends
`0x11`, then `0x22`.

A read returns the bytes in the low bytes of `data`, the first byte received in the highest of
them: three bytes `0xa1`, `0xb2`, `0xc3` come back as `0x00a1b2c3`. A one-byte register pointer
followed by one value byte is therefore written as `(reg << 8) | value`.

## Long transfers in chunks {#arch-chunks}

An element carries at most 4 bytes in each direction, so a longer transfer is split into chunks
inside one I2C transaction. A length of 5 to 7 tells the PHY that more bytes follow. The PHY
moves 4 bytes, returns a status element with an unfinished flag set, and holds SCL low until the
next element arrives.

Holding SCL low is legal on I2C: the target simply waits for the next clock. The figure below
shows a 6-byte write, a register pointer and 5 data bytes, as the simulation of
[Getting started](#getting-started) runs it.

![A 6-byte write in two chunks. Look at the grey cell: between the two elements the PHY keeps
SCL low, so the transaction continues with 0xdd without a new START. Software writes settings and
rxtx for each chunk; "pop" means reading status, then rxtx, after each status
element.](arch_chunks.svg)

Each chunk counts its bytes again from 0: the second element of the figure has `len_tx = 2`. The
last element of a long write may also carry a `len_rx`, which turns the transaction into a
write-then-read.

A long read is a series of chunks too: 4 bytes with `unfinished_rx` set, then the
rest, the last byte being the one the PHY NACKs.

The user must send the next element after a status element with an unfinished flag. Until it
does, SCL stays low and the bus is blocked for every device on it.

## Sharing the bus {#arch-crossbar}

The crossbar connects several users to the one PHY. Each user gets a *port*: an element stream
towards the PHY, a status element stream back and an `active` signal. A user raises `active` to
request the bus and keeps it high for as long as it needs the bus.

A round-robin arbiter grants the bus to one requesting user and keeps the grant while that user
holds `active`. The granted user's `active` becomes the `active` input of the PHY, which starts a
transaction only while it is high. The other users wait, their elements held in their streams.

The register master is the first port when `with_master` is `True`. Its `active` register is the
request of software. Software that leaves it at 1 keeps the bus, and no gateware user is served
until it writes 0.

Gateware users get their port with `add_i2c_device()`. It takes an object with the interface of
`LiteI2CCore`: an element `source`, a status element `sink` and an `active` signal.
[Integration](#integration) gives a complete example; the [status](#intro-status) table gives the
status of buses shared by several ports.

## Clock domain {#arch-clock-domain}

The PHY runs in the clock domain named by `clock_domain`, `sys` by default. The registers stay
in `sys`: the crossbar crosses the elements and status elements with two asynchronous FIFOs of 32
entries, and the speed register and the `active` signal are resynchronised into the PHY domain.

`sys_clk_freq` is then the frequency of that domain, since it sets the SCL divisors.

`add_i2c_master` passes the SoC `sys_clk_freq`: with another domain, build `LiteI2C` directly
with the frequency of that domain. The FIFOs of the crossbar also queue up to 32 elements, so the
FIFO contract of [The register master](#master-fifo) no longer blocks the PHY after one unread
status element. The option is tested in simulation only ([status](#intro-status)).

## In the code {#arch-code}

| Class | File and role |
|----------------------|---------------------------------------------------------------------|
| `LiteI2C` | `litei2c/__init__.py`: PHY, crossbar, master, `add_i2c_device` |
| `LiteI2CCore` | `litei2c/__init__.py`: interface of a gateware user |
| `LiteI2CCrossbar` | `litei2c/crossbar.py`: ports, round-robin arbiter, optional CDC |
| `LiteI2CMaster` | `litei2c/core/master.py`: registers and FIFOs |
| `LiteI2CPHYCore` | `litei2c/phy/generic.py`: bus sequences and errors |
| `LiteI2CClkGen` | `litei2c/clkgen.py`: SCL generation and clock stretching |
| Stream layouts | `litei2c/common.py`: `i2c_core2phy_layout`, `i2c_phy2core_layout` |

Next: [The PHY](#phy) for the bus sequences, [The register master](#master) for software.
