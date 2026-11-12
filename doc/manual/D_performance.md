# Performance and resources {#performance}

This appendix gives the SCL frequencies, the duration of each kind of transaction, the payload
throughput and a resource estimate of LiteI2C. Each number is labelled: *computed* from the
formulas of the code, *computed in simulation* with the script given here, or *synthesis
estimate* from Yosys. The repository records no measurement on hardware.

## SCL frequency {#perf-scl}

The clock generator divides the system clock by `4 x (div + 1)`, with `div = ceil(sys / (4 x SCL)) -
1` for the nominal SCL of the mode ([The PHY](#phy)). SCL is therefore at most the nominal
frequency, and lower when the system clock is not a multiple of four times it. With `clock_domain`,
read the clock of that domain for the system clock in this appendix.

| System clock | Standard-mode (div) | Fast-mode (div) | Fast-mode Plus (div) |
|--------------|---------------------|---------------------|----------------------|
| 25 MHz | 99.2 kHz (62) | 390.6 kHz (15) | 892.9 kHz (6) |
| 48 MHz | 100.0 kHz (119) | 400.0 kHz (29) | 1000.0 kHz (11) |
| 50 MHz | 100.0 kHz (124) | 390.6 kHz (31) | 961.5 kHz (12) |
| 100 MHz | 100.0 kHz (249) | 396.8 kHz (62) | 1000.0 kHz (24) |
| 125 MHz | 99.8 kHz (312) | 395.6 kHz (78) | 976.6 kHz (31) |

Computed. The stretch timeout is `ceil(sys / 40)` system cycles, 25 ms at any system clock. The
system clock must be at least four times the SCL of the fastest mode used: below that, the divider
is 0 and SCL runs at a quarter of the system clock.

## Duration of a transaction {#perf-duration}

A transaction costs one SCL period per bit and per ACK, nine per byte, plus the START, the STOP
and the bus free time that the PHY waits after the STOP. The table counts the SCL periods from the
element presented to the PHY to the PHY ready for the next one, on an ideal bus whose target
acknowledges every byte.

| Transaction | SCL periods | At 100 kHz | At 400 kHz | At 1 MHz |
|-------------------------------------|-------------|------------|------------|----------|
| Address probe | 11.0 | 110 µs | 27.5 µs | 11 µs |
| Write of 1 byte | 20.0 | 200 µs | 50 µs | 20 µs |
| Write of 2 bytes (one register) | 29.0 | 290 µs | 72.5 µs | 29 µs |
| Write of 4 bytes | 47.0 | 470 µs | 117.5 µs | 47 µs |
| Write of 8 bytes, two elements | 83.6 | 836 µs | 209 µs | 83.6 µs |
| Read of 1 byte | 20.0 | 200 µs | 50 µs | 20 µs |
| Read of 4 bytes | 47.0 | 470 µs | 117.5 µs | 47 µs |
| Write of 1 byte, read of 1 (register read) | 39.0 | 390 µs | 97.5 µs | 39 µs |

Computed in simulation, at a 16 MHz system clock in Standard-mode, where an SCL period is 160
system cycles; the times assume the nominal SCL of each mode. A transaction of `n` bytes takes `11
+ 9 x n` periods; the repeated START of a register read adds 10 periods, for the second address
byte and the repeated START. Between two elements of one transaction, the PHY waits with SCL low:
half a period here, where the next element is ready at once, plus the time software takes to pop
the status and push the next element on a real system.

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
address probe     1766 cycles  11.04 SCL periods
write 1 byte      3206 cycles  20.04 SCL periods
write 2 bytes     4646 cycles  29.04 SCL periods
write 4 bytes     7526 cycles  47.04 SCL periods
write 8 bytes    13368 cycles  83.55 SCL periods
read 1 byte       3206 cycles  20.04 SCL periods
read 4 bytes      7526 cycles  47.04 SCL periods
write 1, read 1   6246 cycles  39.04 SCL periods
```

## Payload throughput {#perf-throughput}

A long transfer moves one byte every nine SCL periods once its address is sent. Short
transactions pay the address, the START and the STOP every time. The table gives both bounds in
kB/s (10^3 bytes per second) at the nominal SCL of each mode.

| Transfer | Standard-mode | Fast-mode | Fast-mode Plus |
|---------------------------------------------|-----------------|-----------|----------------|
| Long transfer, bytes after the address | 11.1 kB/s | 44.4 kB/s | 111 kB/s |
| Transactions of 4 bytes, back to back | 8.5 kB/s | 34.0 kB/s | 85.1 kB/s |
| One register write per transaction (1 data byte) | 3.4 kB/s | 13.8 kB/s | 34.5 kB/s |

Computed from the durations above. Software lowers these figures: each element costs a few
register accesses, and with FIFOs of depth 1 the master holds one element at a time. Deeper FIFOs
(`i2c_master_tx_fifo_depth`, `i2c_master_rx_fifo_depth`) let a program queue the elements of
independent transactions ([The register master](#master)).

## Resources {#perf-resources}

The table gives the resources of a `LiteI2C` core with the register master, FIFOs of depth 1 and
no interrupt, with its register bank, for a 100 MHz system clock.

| Family (Yosys flow) | LUTs | Flip-flops | Carry cells |
|------------------------------|------------------|------------|---------------|
| Lattice iCE40 (`synth_ice40`) | 436 `SB_LUT4` | 277 | 55 `SB_CARRY` |
| Xilinx 7-Series (`synth_xilinx`) | 290 (LUT2 to LUT6) | 277 | 14 `CARRY4` |

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
