# Performance and resources {#performance}

This appendix gives the SCL frequencies, the duration of each kind of transaction, the payload
throughput and a resource estimate of LiteI2C. Each number is labelled: *computed* from the
formulas of the code, *computed in simulation* with the script given here, or *synthesis
estimate* from Yosys. One measurement on hardware is recorded
([Hardware records](#boards-records)).

## SCL frequency {#perf-scl}

The clock generator divides the system clock into quarter phases of `div + 1` cycles, four per
SCL period. A quarter phase covers a quarter of the nominal period of the mode and half of its
tLOW and tHIGH minimums ([The PHY](#phy)). SCL is therefore at most the frequency of the table,
`sys / (4 x (div + 1))`. With `clock_domain`, read the clock of that domain for the system clock
in this appendix.

| System clock | Standard-mode (div) | Fast-mode (div) | Fast-mode Plus (div) |
|--------------|---------------------|---------------------|----------------------|
| 25 MHz | 99.2 kHz (62) | 367.6 kHz (16) | 892.9 kHz (6) |
| 48 MHz | 100.0 kHz (119) | 375.0 kHz (31) | 1000.0 kHz (11) |
| 50 MHz | 100.0 kHz (124) | 378.8 kHz (32) | 961.5 kHz (12) |
| 100 MHz | 100.0 kHz (249) | 384.6 kHz (64) | 1000.0 kHz (24) |
| 125 MHz | 99.8 kHz (312) | 381.1 kHz (81) | 976.6 kHz (31) |

Computed. Fast-mode stays under 400 kHz: its 1.3 µs SCL low time is more than half of a 2.5 µs
period. On a bus, each period also lasts the few system cycles SCL takes to read high after its
release, through the input register and the rise time: 98 kHz and about 363 kHz were measured
at a 50 MHz system clock ([Hardware records](#boards-records)).

The stretch timeout is `ceil(sys / 40)` system cycles, 25 ms at any system clock. The system
clock must be at least four times the SCL of the fastest mode used: below that, the divider is 0
and SCL runs at a quarter of the system clock.

## Duration of a transaction {#perf-duration}

A transaction costs one SCL period per bit and per ACK, nine per byte, plus the START, the STOP
and the bus free time that the PHY waits after the STOP. The table counts the SCL periods from the
element presented to the PHY to the PHY ready for the next one, on an ideal bus whose target
acknowledges every byte.

| Transaction | SCL periods | Standard-mode | Fast-mode | Fast-mode Plus |
|-----------------------------|-------------|------------------|-------------|-------------|
| Address probe | 12.5 | 125 µs | 32.5 µs | 12.5 µs |
| Write of 1 byte | 21.5 | 215 µs | 55.9 µs | 21.5 µs |
| Write of 2 bytes (one register) | 30.5 | 305 µs | 79.3 µs | 30.5 µs |
| Write of 4 bytes | 48.5 | 485 µs | 126.1 µs | 48.5 µs |
| Write of 8 bytes, two elements | 85.1 | 851 µs | 221.1 µs | 85.1 µs |
| Read of 1 byte | 21.5 | 215 µs | 55.9 µs | 21.5 µs |
| Read of 4 bytes | 48.5 | 485 µs | 126.1 µs | 48.5 µs |
| Write of 1 byte, read of 1 (register read) | 41.5 | 415 µs | 107.9 µs | 41.5 µs |

Computed in simulation, at a 16 MHz system clock in Standard-mode, where an SCL period is 160
system cycles. The times assume the SCL periods of a 100 MHz system clock: 10 µs, 2.6 µs and
1 µs. A transaction of `n` bytes takes `12.5 + 9 x n` periods; the repeated START of a register
read adds 11 periods, for the second address byte and the repeated START. Between two elements
of one transaction, the PHY waits with SCL low: half a period here, where the next element is
ready at once, plus the time software takes to pop the status and push the next element on a
real system.

The script below produced the table. Save it at the root of the repository and run `python3
perf.py`; it prints the system cycles and the SCL periods of each case.

```python
# Duration of LiteI2C transactions: Migen simulation of the PHY on an ideal open-drain bus
# whose target acknowledges every byte. Prints system cycles and SCL periods per transaction.
from migen import *
from litei2c.phy.generic import LiteI2CPHYCore

class Pads:
    def __init__(self):
        for n in ["scl", "sda"]:
            for s, r in [("_i", 1), ("_o", 0), ("_oe", 0)]:
                setattr(self, n + s, Signal(reset=r))

def run(elements, sys_clk_freq=16e6):
    pads = Pads()
    dut  = LiteI2CPHYCore(pads, "sys", sys_clk_freq)
    ack, idle = Signal(), Signal()
    dut.comb += [
        ack.eq(dut.fsm.ongoing("ADDR-ACK") | dut.fsm.ongoing("TX-ACK")),
        idle.eq(dut.fsm.ongoing("WAIT-DATA")),
        pads.scl_i.eq(~pads.scl_oe),
        pads.sda_i.eq(~pads.sda_oe & ~ack),
    ]
    cycles = []
    def host():
        yield dut.active.eq(1)
        yield dut.source.ready.eq(1)
        n = 0
        for e in elements:
            for k, v in e.items():
                yield getattr(dut.sink, k).eq(v)
            yield dut.sink.valid.eq(1)
            yield
            n += 1
            while not (yield dut.sink.ready):
                yield
                n += 1
            yield dut.sink.valid.eq(0)
        while not (yield idle):
            yield
            n += 1
        cycles.append(n)
    run_simulation(dut, host())
    return cycles[0]

cases = {
    "address probe"   : [dict(addr=0x50)],
    "write 1 byte"    : [dict(addr=0x50, data=0x01, len_tx=1)],
    "write 2 bytes"   : [dict(addr=0x50, data=0x0102, len_tx=2)],
    "write 4 bytes"   : [dict(addr=0x50, data=0x01020304, len_tx=4)],
    "write 8 bytes"   : [dict(addr=0x50, data=0x01020304, len_tx=5),
                         dict(addr=0x50, data=0x05060708, len_tx=4)],
    "read 1 byte"     : [dict(addr=0x50, len_rx=1)],
    "read 4 bytes"    : [dict(addr=0x50, len_rx=4)],
    "write 1, read 1" : [dict(addr=0x50, data=0x10, len_tx=1, len_rx=1)],
}
period = 4*40 # System cycles per SCL period at 16 MHz in Standard-mode (divider 39).
for name, elements in cases.items():
    c = run(elements)
    print(f"{name:16s} {c:5d} cycles {c/period:6.2f} SCL periods")
```

```console
address probe     2006 cycles  12.54 SCL periods
write 1 byte      3446 cycles  21.54 SCL periods
write 2 bytes     4886 cycles  30.54 SCL periods
write 4 bytes     7766 cycles  48.54 SCL periods
write 8 bytes    13608 cycles  85.05 SCL periods
read 1 byte       3446 cycles  21.54 SCL periods
read 4 bytes      7766 cycles  48.54 SCL periods
write 1, read 1   6646 cycles  41.54 SCL periods
```

## Payload throughput {#perf-throughput}

A long transfer moves one byte every nine SCL periods once its address is sent. Short
transactions pay the address, the START and the STOP every time. The table gives both bounds in
kB/s (10^3 bytes per second) at the SCL of a 100 MHz system clock: 100 kHz, 384.6 kHz and 1 MHz.

| Transfer | Standard-mode | Fast-mode | Fast-mode Plus |
|---------------------------------------------|-----------------|-----------|----------------|
| Long transfer, bytes after the address | 11.1 kB/s | 42.7 kB/s | 111 kB/s |
| Transactions of 4 bytes, back to back | 8.2 kB/s | 31.7 kB/s | 82.5 kB/s |
| One register write per transaction (1 data byte) | 3.3 kB/s | 12.6 kB/s | 32.8 kB/s |

Computed from the durations above. Software lowers these figures: each element costs a few
register accesses, and with FIFOs of depth 1 the master holds one element at a time. Deeper FIFOs
(`i2c_master_tx_fifo_depth`, `i2c_master_rx_fifo_depth`) let a program queue the elements of
independent transactions ([The register master](#master)).

## Resources {#perf-resources}

The table gives the resources of a `LiteI2C` core with the register master, FIFOs of depth 1 and
no interrupt, with its register bank, for a 100 MHz system clock.

| Family (Yosys flow) | LUTs | Flip-flops | Carry cells |
|------------------------------|------------------|------------|---------------|
| Lattice iCE40 (`synth_ice40`) | 470 `SB_LUT4` | 278 | 55 `SB_CARRY` |
| Xilinx 7-Series (`synth_xilinx`) | 301 (LUT2 to LUT6) | 278 | 15 `CARRY4` |

Synthesis estimate, Yosys 0.70, without place and route. The design is written to Verilog by
the script below, then synthesized:

```python
# gen_v.py: LiteI2C and its register bank as a Verilog module, for a resource estimate.
import sys
from migen import *
from migen.fhdl.verilog import convert
from litex.build.generic_platform import Pins, Subsignal
from litex.build.sim.platform import SimPlatform
from litex.soc.interconnect.csr import AutoCSR
from litex.soc.interconnect.csr_bus import CSRBankArray
from litei2c import LiteI2C

class Top(Module, AutoCSR):
    def __init__(self, platform, freq, irq):
        self.pads = pads = platform.request("i2c")
        self.submodules.i2c = LiteI2C(freq, pads=pads, with_irq=irq)
        self.submodules.csrbanks = CSRBankArray(self,
            lambda name, memory: 0 if name == "i2c" else None, data_width=32, address_width=14)
        self.bus = self.csrbanks.get_buses()[0]

p   = SimPlatform("sim", [("i2c", 0, Subsignal("scl", Pins(1)), Subsignal("sda", Pins(1)))])
top = Top(p, int(float(sys.argv[2])), sys.argv[3] == "1")
ios = {top.pads.scl, top.pads.sda, top.bus.adr, top.bus.we, top.bus.dat_w, top.bus.dat_r}
open(sys.argv[1], "w").write(str(convert(top, ios=ios, name="litei2c_top")))
```

```sh
python3 gen_v.py litei2c.v 100e6 0
yosys -p "synth_ice40 -top litei2c_top; stat" litei2c.v
yosys -p "synth_xilinx -top litei2c_top; stat" litei2c.v
```

## Where to go next {#perf-next}

[The PHY](#phy) for the clock generator; [Examples](#examples) for the register sequences whose
duration this appendix gives.
