# Integration {#integration}

This chapter adds LiteI2C to a LiteX SoC and drives it: the SoC method, the pads and pull-ups,
several buses, the bare-metal functions for firmware, a host script and a gateware user. Read it
once the simulation of [Getting started](#getting-started) runs. The registers are described in
[The register master](#master).

## In a LiteX SoC {#integ-soc}

A LiteX SoC adds the core with `add_i2c_master()`, as the figure below shows. The CPU reaches the
registers over the CSR bus, the interrupt is optional, and a gateware user can share the bus
through its own crossbar port.

![LiteI2C in a LiteX SoC. Look at the pull-ups: the core drives the pads open drain, so the
high level of SCL and SDA comes from the board.](integ_soc.svg)

```python
# In the SoC of a target, with a platform that defines an "i2c" resource.
self.add_i2c_master(name="i2c", pads=platform.request("i2c"))
```

The method imports LiteI2C, builds it with the `sys` frequency of the SoC and adds it under
`name`, which prefixes its registers. The table below lists its parameters and the main keyword
arguments it passes to `LiteI2C` ([Architecture](#arch-glance)).

| Parameter | Role, default |
|----------------------------------------|-----------------------------------------------------|
| `name` | Name of the core and prefix of its registers (default `"i2cmaster"`) |
| `pads` | Pads; `None` requests the platform resource `name` (default `None`) |
| `with_irq` | Adds the interrupt of the master (default: see below) |
| `i2c_master_tx_fifo_depth` | Elements the master can queue (default `1`) |
| `i2c_master_rx_fifo_depth` | Status elements the master can hold (default `1`) |

With the default name, `pads=None` requests a resource called `i2cmaster`, which platforms do not
define: their I2C resources are named `i2c`. Pass the pads, or use `name="i2c"`.

The interrupt is added when `with_irq=True` is passed and the SoC has an interrupt controller.
Without the argument, the method enables it only when `name` already has a reserved interrupt
number in the SoC. Pass `with_irq=True` to get it in the usual case, as the GMM-7550 target does.

## Pads and pull-ups {#integ-pads}

The pads are a record with `scl` and `sda` subsignals, the same as the bit-banged I2C core of
LiteX uses. The PHY drives each of them through an `SDRTristate`, open drain. Another subsignal
in the record, such as a reset or an alert line, is ignored by the core.

Both lines need a pull-up resistor. A board that carries I2C devices usually has them; the value
depends on the bus capacitance and the speed ([I2C in a nutshell](#i2c-primer)). For a short bus at
100 kHz, the pull-ups of the FPGA pins are enough, set in the platform file. The KC705 platform of
LiteX-Boards does it this way:

```python
("i2c", 0,
    Subsignal("scl", Pins("K21"), Misc("PULLUP=True")),
    Subsignal("sda", Pins("L21"), Misc("PULLUP=True")),
    IOStandard("LVCMOS25")
),
```

The attribute that enables a pin pull-up depends on the toolchain of the FPGA family. Some
boards, such as the Arty, route extra pins to switchable pull-ups: drive them as the board
documentation says.

With split pads, the record holds `scl_o`, `scl_oe`, `scl_i`, `sda_o`, `sda_oe` and `sda_i`, and
the PHY drives them directly ([Open-drain pins](#phy-io)). Use them with an external buffer or in
simulation. Without `scl_i`, clock stretching is not detected.

## Direct instantiation {#integ-direct}

`LiteI2C` is an ordinary LiteX module, so a design can also build it itself. Its registers then
appear under the name of the attribute, prefixed by the names of the enclosing modules, like
every LiteX module with registers:

```python
from litei2c import LiteI2C

class ClockChip(LiteXModule):
    def __init__(self, pads, sys_clk_freq):
        self.i2c = LiteI2C(sys_clk_freq, pads=pads,
            i2c_master_tx_fifo_depth = 8,
            i2c_master_rx_fifo_depth = 8,
        )
```

LiteX-M2SDR builds LiteI2C this way inside the module of its SI5351 clock generator, with FIFO
depths of 8. To connect the interrupt of a core built by hand, pass `with_irq=True` and expose the
event manager at the top of the module (`self.ev = self.i2c.ev`). Then call
`self.irq.add("<attribute name>")` in the SoC: LiteX connects the `ev` of the SoC attribute of
that name.

## Several buses {#integ-several}

Each I2C bus needs its own core: one LiteI2C drives one pair of pins. Add one core per bus,
each with its own name and pads:

```python
self.add_i2c_master(name="i2c_sensors", pads=platform.request("i2c", 0))
self.add_i2c_master(name="i2c_power",   pads=platform.request("i2c", 1))
```

Firmware then uses the accessors of each name, such as `i2c_sensors_master_rxtx_write()`. Several
devices on one bus need no extra core: they share it by address.

## Names, BIOS and operating systems {#integ-naming}

LiteX has no BIOS command and no Linux driver for LiteI2C: the BIOS `i2c_*` commands and the
`litex,i2c` Linux binding are for the bit-banged core ([I2C in LiteX](#litex-i2c)). LiteI2C is
driven by firmware through its registers, or by gateware.

The device tree generator of LiteX describes every register bank named `i2c` followed by a number,
such as `i2c0`, as a bit-banged core. Do not give such a name to a LiteI2C core in a SoC that
boots Linux: use `i2c`, or a descriptive name.

## Timing constraints {#integ-timing}

By default the core runs in `sys` and needs no constraint beyond the `sys` clock. SCL and SDA
change at most once per quarter phase, many clock cycles apart, so the I/O paths of the pins need
no input or output delay constraint.

With `clock_domain`, the PHY and the pins run in that domain: constrain its clock as well. The
crossing to the registers goes through the asynchronous FIFOs of the crossbar and a `MultiReg`,
which LiteX constrains.

## Bare-metal software {#integ-baremetal}

The C functions below drive the master through the accessors that LiteX generates in `csr.h`, for
a core named `i2c`, as in [Getting started](#gs-soc). With another name, change the `i2c_` prefix
of the accessors and the `CSR_I2C_` prefix of the field macros; the default name `i2cmaster` gives
`i2cmaster_master_status_read()`. They follow the register sequence of
[One transaction step by step](#master-transaction). [Examples](#examples) gives the bus sequence
of each function.

Three rules of the master shape `i2c_element()` ([The FIFO contract](#master-fifo)):

- **Order of the writes.** The master copies `master_settings` and `master_addr` into the element
  when `master_rxtx` is written, so both are written first.
- **TX FIFO room.** A write of `master_rxtx` while `tx_ready` is 0 is lost: the master has no
  overflow protection.
- **Status before data.** The fields `nack`, `bus_error`, `tx_unfinished` and `rx_unfinished`
  describe the status element at the head of the RX FIFO. Read `master_status` while `rx_ready` is
  1, then pop the element by reading `master_rxtx`.

The data of the status of a pure write is not cleared: it repeats the last bytes received, so
`i2c_xfer()` uses it only after a read.

```c
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <generated/csr.h>

#define I2C_TX_READY  (1 << CSR_I2C_MASTER_STATUS_TX_READY_OFFSET)
#define I2C_RX_READY  (1 << CSR_I2C_MASTER_STATUS_RX_READY_OFFSET)
#define I2C_NACK      (1 << CSR_I2C_MASTER_STATUS_NACK_OFFSET)
#define I2C_BUS_ERROR (1 << CSR_I2C_MASTER_STATUS_BUS_ERROR_OFFSET)
#define I2C_MORE      5 /* Length of a chunk followed by another one. */

/* speed: 0 = 100 kHz, 1 = 400 kHz, 2 = 1 MHz. */
void i2c_init(int speed)
{
    i2c_master_active_write(0);
    i2c_phy_speed_mode_write(speed);         /* Applied while active is 0. */
    while (i2c_master_status_read() & I2C_RX_READY)
        i2c_master_rxtx_read();              /* Drop stale status elements. */
    i2c_master_active_write(1);
}

/* One element; returns the status, stores the returned bytes in *rx. */
static uint32_t i2c_element(uint8_t addr, uint32_t data, int len_tx, int len_rx,
                            int recover, uint32_t *rx)
{
    uint32_t status;
    i2c_master_addr_write(addr);
    i2c_master_settings_write(
        (len_tx  << CSR_I2C_MASTER_SETTINGS_LEN_TX_OFFSET) |
        (len_rx  << CSR_I2C_MASTER_SETTINGS_LEN_RX_OFFSET) |
        (recover << CSR_I2C_MASTER_SETTINGS_RECOVER_OFFSET));
    while (!(i2c_master_status_read() & I2C_TX_READY));
    i2c_master_rxtx_write(data);
    do {
        status = i2c_master_status_read();
    } while (!(status & I2C_RX_READY));
    *rx = i2c_master_rxtx_read();            /* Pops the status element. */
    return status;
}

/* 0: done, -1: NACK, -2: bus error. */
static int i2c_check(uint32_t status)
{
    if (status & I2C_BUS_ERROR)
        return -2;
    if (status & I2C_NACK)
        return -1;
    return 0;
}

/* Write wlen bytes, then read rlen bytes, in one transaction (any length). */
int i2c_xfer(uint8_t addr, const uint8_t *wbuf, int wlen, uint8_t *rbuf, int rlen)
{
    uint32_t data;
    int i, n, len_tx, len_rx, ret;

    /* Write chunks; the last one also carries the first read length. */
    do {
        n = wlen > 4 ? 4 : wlen;
        data = 0;
        for (i = 0; i < n; i++)
            data = (data << 8) | *wbuf++;    /* First byte most significant. */
        wlen  -= n;
        len_tx = wlen ? I2C_MORE : n;
        len_rx = wlen ? 0 : (rlen > 4 ? I2C_MORE : rlen);
        ret = i2c_check(i2c_element(addr, data, len_tx, len_rx, 0, &data));
        if (ret)
            return ret;
    } while (wlen);

    /* Read chunks: data holds up to 4 bytes, first byte most significant. */
    while (rlen) {
        n = rlen > 4 ? 4 : rlen;
        for (i = 0; i < n; i++)
            *rbuf++ = data >> (8*(n - 1 - i));
        rlen -= n;
        if (!rlen)
            break;
        ret = i2c_check(i2c_element(addr, 0, 0, rlen > 4 ? I2C_MORE : rlen, 0, &data));
        if (ret)
            return ret;
    }
    return 0;
}

/* 1 when a target ACKs addr. */
int i2c_probe(uint8_t addr)
{
    return i2c_xfer(addr, NULL, 0, NULL, 0) == 0;
}

/* Registers with an 8-bit pointer: write one, read len from reg on. */
int i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t value)
{
    uint8_t buf[2] = {reg, value};
    return i2c_xfer(addr, buf, 2, NULL, 0);
}

int i2c_read_regs(uint8_t addr, uint8_t reg, uint8_t *buf, int len)
{
    return i2c_xfer(addr, &reg, 1, buf, len);
}

/* START, 10 clocks with SDA released, repeated START, STOP; 0 when the bus is free again. */
int i2c_recover(void)
{
    uint32_t data;
    return i2c_check(i2c_element(0, 0, 0, 0, 1, &data));
}
```

`i2c_xfer()` covers every shape of transaction. The table below lists the elements and the bus
sequence of each helper for a target at `0x50` and a register pointer `0x10`; S is a START, Sr a
repeated START, P a STOP.

| Call | Elements | Bus sequence |
|----------------------------|-------------------------|--------------------------------------------|
| `i2c_probe` | `len_tx` 0, `len_rx` 0 | S, `0x50` W, P |
| `i2c_write_reg`, 1 value | `len_tx` 2 | S, `0x50` W, `0x10`, value, P |
| `i2c_read_regs`, 2 bytes | `len_tx` 1, `len_rx` 2 | S, `0x50` W, `0x10`, Sr, `0x50` R, 2 bytes, P |
| `i2c_xfer`, write 6 | `len_tx` 5, then 2 | S, `0x50` W, 6 bytes, P |
| `i2c_xfer`, write 1, read 9 | `len_tx` 1 with `len_rx` 5, then `len_rx` 5, then 1 | S, `0x50` W, 1 byte, Sr, `0x50` R, 9 bytes, P |
| `i2c_xfer`, read 3 | `len_rx` 3 | S, `0x50` R, 3 bytes, P |
| `i2c_recover` | `recover` 1 | S, 10 clocks, Sr, P |

A scan of the bus probes every non-reserved 7-bit address:

```c
void i2c_scan(void)
{
    for (int addr = 0x08; addr < 0x78; addr++)
        if (i2c_probe(addr))
            printf("0x%02x\n", addr);
}
```

These functions compile against the `csr.h` of [Getting started](#gs-soc). The same chunking is
exercised by `test_write_over_4_bytes`, `test_read_over_4_bytes` and
`test_master_registers_write_then_read` of `test/test_target.py`
([Simulation and tests](#simulation)).

### Error handling {#integ-errors}

A return value of -1 is a NACK: the target is absent, busy, or refused a byte. Retrying is the
usual answer for an EEPROM during its internal write cycle, which NACKs its address until the
write completes. A return value of -2 is a bus error: a line is stuck low, a target stretched SCL
for more than 25 ms, or another device drove SDA ([Errors](#phy-errors)).

After a bus error, call `i2c_recover()`, then retry the transaction once. A bus that stays in
error after a recovery has a hardware problem: a missing pull-up, a target without power or a
short ([Debugging](#debugging)).

The polling loops have no timeout. The PHY always returns a status element, within 25 ms per
stretch, but a production driver may bound the loops. It may also yield to other tasks
between whole transactions; it should not yield between the chunks of one transaction, which
hold the bus ([Long transfers](#master-long)).

### With the interrupt {#integ-irq}

With `with_irq=True`, the driver writes the element, then waits for the event instead of polling
`rx_ready`. The event fires on the rising edge of "RX FIFO not empty" ([Interrupt](#master-irq)).
Enable it once in the core and unmask the interrupt line of the core in the CPU:

```c
#include <irq.h>

void i2c_irq_enable(void)
{
    i2c_master_ev_pending_write(1);
    i2c_master_ev_enable_write(1);
    irq_setmask(irq_getmask() | (1 << I2C_INTERRUPT));
}

void i2c_isr(void)
{
    uint32_t status, data;
    /* Clear first: a status arriving after the last pop raises a new event. */
    i2c_master_ev_pending_write(1);
    while ((status = i2c_master_status_read()) & I2C_RX_READY) {
        data = i2c_master_rxtx_read();       /* Pops the status element. */
        /* Hand status and data to the driver here. */
        (void)data;
    }
}
```

The handler clears the event before it pops the status elements. Cleared after, a status that
arrives between the last pop and the clear would leave the RX FIFO not empty with no event. With
an RX FIFO deeper than 1, a second status that arrives before the first is popped raises no new
event, which is why the handler pops every status present. The CPU interrupt dispatcher calls
`i2c_isr()`; how it does depends on the CPU support of LiteX.

## From a host {#integ-host}

On a board with a LiteX bridge (UART, Ethernet or PCIe), the same registers are reachable from a
host with the `RemoteClient` of LiteX, which names them from the `csr.csv` of the build. The
script below scans the bus; it expects `litex_server` to run and `csr.csv` in the current
directory.

```python
from litex import RemoteClient

bus = RemoteClient()
bus.open()
regs = bus.regs

def i2c_element(addr, data=0, len_tx=0, len_rx=0):
    regs.i2c_master_addr.write(addr)
    regs.i2c_master_settings.write(len_tx | (len_rx << 8))
    while not (regs.i2c_master_status.read() & 0x1):  # tx_ready.
        pass
    regs.i2c_master_rxtx.write(data)
    while not ((status := regs.i2c_master_status.read()) & 0x2):  # rx_ready.
        pass
    return status, regs.i2c_master_rxtx.read()

regs.i2c_master_active.write(0)
regs.i2c_phy_speed_mode.write(0)  # 100 kHz.
regs.i2c_master_active.write(1)
for addr in range(0x08, 0x78):
    status, _ = i2c_element(addr)
    if not (status & 0x100):  # nack.
        print(f"0x{addr:02x}")
regs.i2c_master_active.write(0)

bus.close()
```

The constants are the field offsets of the [Register reference](#registers): `tx_ready` bit 0,
`rx_ready` bit 1, `nack` bit 8, and `len_rx` at bit 8 of the settings. A register read is
`i2c_element(addr, reg, len_tx=1, len_rx=1)`, the value in bits 7:0 of the second result. Single
accesses with `litex_cli` are covered in [Debugging](#debugging).

Each register access crosses the bridge, so a transaction from the host is much slower than from
firmware. Keep long transfers in firmware: a host that stops between two chunks holds SCL low.

## Gateware users {#integ-gateware}

Gateware can run I2C transactions without the CPU, for example to configure a clock chip before
the CPU boots. There are two ways: a port of the crossbar, or a bus master that writes the
registers of the master.

A crossbar port is the direct way. `add_i2c_device()` takes a module with the interface of
`LiteI2CCore` and gives it its own port ([Sharing the bus](#arch-crossbar)). The module below
writes a table of register values to one target, then stops:

```python
from migen import *

from litei2c import LiteI2CCore

class I2CInit(LiteI2CCore):
    """Writes (register, value) pairs to one target, then releases the bus."""
    def __init__(self, addr, regs):
        LiteI2CCore.__init__(self)
        self.done = Signal()
        mem  = Memory(16, len(regs), init=[r << 8 | v for r, v in regs])
        port = mem.get_port(async_read=True)
        self.specials += mem, port
        self.submodules.fsm = fsm = FSM(reset_state="SEND")
        self.comb += [
            self.source.addr.eq(addr),
            self.source.len_tx.eq(2),
            self.source.data.eq(port.dat_r),
            self.sink.ready.eq(1),
        ]
        fsm.act("SEND",
            self.active.eq(1),
            self.source.valid.eq(1),
            If(self.source.ready, NextState("WAIT")),
        )
        fsm.act("WAIT",
            self.active.eq(1),
            If(self.sink.valid,
                If(port.adr == len(regs) - 1,
                    NextState("DONE"),
                ).Else(
                    NextValue(port.adr, port.adr + 1),
                    NextState("SEND"),
                ),
            ),
        )
        fsm.act("DONE", self.done.eq(1))
```

Connect it to a core named `i2c` from the SoC:

```python
self.i2c_init = I2CInit(addr=0x50, regs=[(0x10, 0x5a), (0x20, 0xa5)])
self.i2c.add_i2c_device(self.i2c_init)
```

The module holds the element valid until the PHY accepts it, at the end of the transaction, then
waits for the status element. This example ignores the error flags of the status element; a real
sequencer checks `sink.nack` and retries or reports. Added to the simulation of
[Getting started](#gs-sim) with these two pairs, it writes them in two transactions and raises
`done`.

The other way keeps the master as the only port: a small state machine writes the master
registers over the SoC bus, as software would, and shares the master with software. LiteX-M2SDR
initialises its SI5351 clock generator this way; [A gateware sequencer](#ex-sequencer) describes
its steps.

Next: [Examples](#examples) for complete designs, [Debugging](#debugging) when a transaction
fails.
