```{=latex}
\part{Use it}
```

```{=html}
<h1 class="part">Part III. Use it</h1>
```

# Getting started {#getting-started}

This chapter takes you from a fresh machine to a LiteX SoC that contains LiteI2C, without a board.
It runs the tests, then a simulation of real transactions against a simulated target, then
builds the register map of a SoC. Each step gives the commands, what you should see, and where to
go when you do not.

## Prerequisites {#gs-install}

LiteI2C is a Python package built on Migen and LiteX, and needs Python 3. The installation script
of LiteX (`litex_setup.py`, see the installation page of the LiteX wiki) installs Migen, LiteX,
LiteX-Boards and the cores, LiteI2C included. To work on a clone of the repository, install it in
development mode:

```sh
git clone https://github.com/litex-hub/litei2c
cd litei2c
pip3 install -e .
```

The steps of this chapter need no FPGA tool and no RISC-V toolchain: only Python, pytest, Migen
and LiteX. A board needs the toolchain of its FPGA family ([Supported FPGAs and boards](#boards)).

## Step 1: run the tests {#gs-tests}

The test suite runs the PHY, the clock generator and the whole core in Migen simulation, against
a simulated I2C target, with no board and no FPGA tool. It runs in under a minute, as the
continuous integration of the repository does:

```sh
python3 -m pytest -v
```

The run ends with every test passed:

```console
$ python3 -m pytest -v
[...]
collecting ... collected 29 items

test/test_clkgen.py::TestLiteI2CClkGen::test_reserved_speed_mode_uses_standard_mode PASSED [  3%]
[...]
test/test_target.py::TestLiteI2CTarget::test_write_then_read_with_repeated_start PASSED [100%]

==================== 29 passed, 3 subtests passed in 22.08s ====================
```

A failure at import time means that Migen or LiteX is missing or too old for the checkout: update
them with `litex_setup.py`. [Simulation and tests](#simulation) describes what each test covers.

## Step 2: simulate transactions {#gs-sim}

The repository has a simulated target: `test/i2c_target.py` models a register-pointer device on
the wired-AND bus (`I2CTarget`) and drives the PHY or the register master as software does.
`test/test_target.py` runs probes, writes, reads, a write-then-read with a repeated START and
transfers over 4 bytes against it:

```sh
python3 -m pytest -v test/test_target.py
```

The script below runs the same kind of transactions and prints them, with the register accesses
that firmware makes. It runs LiteI2C with its register bank against its own small target model, so
that it runs from any directory. Save it as `i2c_sim.py`.

The target answers at address `0x50` and behaves like a small EEPROM: the first byte written sets
a register pointer, the next bytes are stored from there, and reads return them. The software side
probes two addresses, writes 6 bytes in two chunks, then reads 5 bytes back with a
write-then-read. The `sys` clock is 4 MHz to keep the simulation short; the speed is 100 kHz.

```python
#!/usr/bin/env python3
# Migen simulation of LiteI2C (PHY, crossbar, register master) with a behavioural
# EEPROM-like target at address 0x50: probe, long write, write-then-read.

from migen import *

from litex.soc.interconnect.csr import AutoCSR
from litex.soc.interconnect.csr_bus import CSRBankArray

from litei2c import LiteI2C

SYS_CLK_FREQ = 4e6

class Pads:
    def __init__(self):
        for name in ["scl", "sda"]:
            setattr(self, name + "_o",  Signal())
            setattr(self, name + "_oe", Signal())
            setattr(self, name + "_i",  Signal(reset=1))

# LiteI2C and its register bank, as a LiteX SoC builds them (32-bit registers).
class Top(Module, AutoCSR):
    def __init__(self, pads):
        self.submodules.i2c = LiteI2C(SYS_CLK_FREQ, pads=pads)
        self.submodules.csrbanks = CSRBankArray(self,
            address_map = lambda name, memory: 0,
            data_width  = 32)
        self.bus = self.csrbanks.get_buses()[0]

pads = Pads()
dut  = Top(pads)
now  = [0]

def log(msg):
    print(f"{now[0]/SYS_CLK_FREQ*1e6:9.1f} us  {msg}")

# Behavioural target: ACKs address 0x50, first written byte sets a pointer.
@passive
def target(addr=0x50):
    mem   = [0]*256
    ptr   = 0
    state = "idle" # idle, addr, write, read.
    n, sr, tx, drive, first, after = 0, 0, 0, 0, False, "idle"
    scl_p, sda_p = 1, 1
    while True:
        scl = 0 if (yield pads.scl_oe) else 1
        sda = 0 if ((yield pads.sda_oe) or drive) else 1   # Wired-AND.
        yield pads.scl_i.eq(scl)
        yield pads.sda_i.eq(sda)
        if scl and scl_p and sda_p and not sda:
            log("target: START")
            state, n, sr, drive = "addr", 0, 0, 0
        elif scl and scl_p and not sda_p and sda:
            log("target: STOP")
            state, drive = "idle", 0
        elif state != "idle" and scl and not scl_p:         # SCL rising: sample.
            if n < 8:
                sr = ((sr << 1) | sda) & 0xff
            elif state == "read":
                log(f"target: read 0x{tx:02x}, {'NACK' if sda else 'ACK'}")
                if sda:
                    state = "idle"
            n += 1
        elif state != "idle" and scl_p and not scl:         # SCL falling: drive.
            if n == 8 and state == "addr":
                ok = (sr >> 1) == addr
                log(f"target: address 0x{sr >> 1:02x} {'R' if sr & 1 else 'W'} "
                    f"{'ACK' if ok else 'NACK'}")
                after = ("read" if sr & 1 else "write") if ok else "idle"
                drive, first = int(ok), True
            elif n == 8 and state == "write":
                log(f"target: write 0x{sr:02x}")
                if first:
                    ptr = sr
                else:
                    mem[ptr], ptr = sr, (ptr + 1) % 256
                drive, first = 1, False
            elif n == 8:
                drive = 0                                   # Release for the ACK.
            elif n == 9:
                n, sr, drive = 0, 0, 0
                if state == "addr":
                    state = after
                if state == "read":
                    tx, ptr = mem[ptr], (ptr + 1) % 256
            if state == "read" and n < 8:                   # Read data, MSB first.
                drive = 0 if (tx >> (7 - n)) & 1 else 1
        scl_p, sda_p = scl, sda
        now[0] += 1
        yield

# Software side: the register sequence of the master, as firmware runs it.
# Register offsets in 32-bit words, as in csr.csv (byte offset / 4).
SPEED_MODE, ACTIVE, SETTINGS, ADDR, RXTX, STATUS = range(6)
TX_READY, RX_READY = 1 << 0, 1 << 1

def read(adr):
    yield dut.bus.adr.eq(adr)
    yield dut.bus.re.eq(1)
    yield
    yield dut.bus.re.eq(0)
    yield                                                   # Registered read data.
    return (yield dut.bus.dat_r)

def wait_status(mask):
    while True:
        status = yield from read(STATUS)
        if status & mask:
            return status

def chunk(addr, data, len_tx, len_rx):
    yield from dut.bus.write(ADDR, addr)
    yield from dut.bus.write(SETTINGS, len_tx | (len_rx << 8))
    yield from wait_status(TX_READY)
    yield from dut.bus.write(RXTX, data)
    status = yield from wait_status(RX_READY)
    data   = yield from read(RXTX)
    log(f"master: status 0x{status:05x}, rxtx 0x{data:08x}")

def software():
    yield from dut.bus.write(SPEED_MODE, 0)                 # 100 kHz.
    yield from dut.bus.write(ACTIVE, 1)
    log("master: probe 0x50")
    yield from chunk(0x50, 0, 0, 0)
    log("master: probe 0x51")
    yield from chunk(0x51, 0, 0, 0)
    log("master: write 0x10 (pointer), 0xaa, 0xbb, 0xcc, 0xdd, 0xee")
    yield from chunk(0x50, 0x10aabbcc, 5, 0)                # 4 bytes, more follows.
    yield from chunk(0x50, 0xddee, 2, 0)                    # Last 2 bytes.
    log("master: write 0x10 (pointer), read 5 bytes")
    yield from chunk(0x50, 0x10, 1, 5)                      # Pointer, 4 bytes read, more follow.
    yield from chunk(0x50, 0, 0, 1)                         # Last byte.
    yield from dut.bus.write(ACTIVE, 0)
    for _ in range(100):
        yield

run_simulation(dut, [software(), target()])
```

Run it from any directory:

```sh
python3 i2c_sim.py
```

It prints the bus events seen by the target and the status
elements seen by the software, with the simulated time:

```console
$ python3 i2c_sim.py
      0.5 us  master: probe 0x50
      2.2 us  target: START
     84.8 us  target: address 0x50 W ACK
    102.0 us  target: STOP
    104.2 us  master: status 0x00003, rxtx 0x00000000
    104.2 us  master: probe 0x51
    113.5 us  target: START
    196.0 us  target: address 0x51 W NACK
    213.2 us  target: STOP
    215.5 us  master: status 0x00103, rxtx 0x00000000
    215.5 us  master: write 0x10 (pointer), 0xaa, 0xbb, 0xcc, 0xdd, 0xee
    224.8 us  target: START
    307.2 us  target: address 0x50 W ACK
    397.2 us  target: write 0x10
    487.2 us  target: write 0xaa
    577.2 us  target: write 0xbb
    667.2 us  target: write 0xcc
    680.8 us  master: status 0x10003, rxtx 0x00000000
    765.0 us  target: write 0xdd
    855.0 us  target: write 0xee
    872.2 us  target: STOP
    874.5 us  master: status 0x00003, rxtx 0x00000000
    874.5 us  master: write 0x10 (pointer), read 5 bytes
    883.8 us  target: START
    966.2 us  target: address 0x50 W ACK
   1056.2 us  target: write 0x10
   1073.8 us  target: START
   1156.2 us  target: address 0x50 R ACK
   1251.2 us  target: read 0xaa, ACK
   1341.2 us  target: read 0xbb, ACK
   1431.2 us  target: read 0xcc, ACK
   1521.2 us  target: read 0xdd, ACK
   1529.8 us  master: status 0x20003, rxtx 0xaabbccdd
   1619.0 us  target: read 0xee, NACK
   1631.2 us  target: STOP
   1633.5 us  master: status 0x00003, rxtx 0x000000ee
```

Read the output by blocks. The probe of `0x50` returns status `0x00003`: `tx_ready` and
`rx_ready` set, no error. The probe of `0x51` returns `0x00103`: `nack` (bit 8) is set because no
target answered, and `bus_error` (bit 9) is clear because the bus itself is fine
([Registers](#master-registers)).

The 6-byte write shows the chunks of [Long transfers in chunks](#arch-chunks). After `0xcc`, the
first status element has `tx_unfinished` (bit 16) set, and the transaction goes on with `0xdd`
without a new START. Bytes follow each other every 90 µs, nine SCL periods, except between `0xcc`
and `0xdd`: the few extra microseconds are the time the software takes to read the status
element and push the next element, while the PHY holds SCL low.

The write-then-read sends the pointer `0x10`, then a repeated START and the address with R. The
first status element returns 4 bytes, `0xaabbccdd`, with `rx_unfinished` (bit 17) set; the second
returns the last byte, `0xee`, which the PHY NACKs before the STOP.

To try other cases, edit the end of `software()`: another address, other lengths, or a speed of
1 or 2. The behavioural target is the place to add a misbehaving device, such as one that holds
SDA low ([Simulation and tests](#simulation)).

## Step 3: a SoC with LiteI2C {#gs-soc}

A LiteX SoC adds the core with `add_i2c_master()` ([Integration](#integration)). The GMM-7550
target of LiteX-Boards uses it for the USB-C controller of its USB 3 adapter, with option
`--usb pd`. LiteX elaborates that SoC and writes its register map without the vendor toolchain,
when `--no-compile` stops the build before synthesis and before the software:

```sh
python3 -m litex_boards.targets.gmm7550_usb3 --usb pd --build --no-compile \
    --output-dir build/gmm --csr-csv build/gmm/csr.csv
```

The log lists the interrupt and the register bank of the core, which this target names `i2c`,
and the module tree shows its blocks:

```console
[...]
INFO:SoCIRQHandler:i2c IRQ allocated at Location 2.
[...]
INFO:SoCCSRHandler:i2c CSR allocated at Location 2.
[...]
├── i2c (LiteI2C)
│    ├── phy (LiteI2CPHYCore)
│    │    ├── resyncreg_0 (ResyncReg) [Gen]
│    │    ├── clkgen (LiteI2CClkGen)
│    │    └── fsm (FSM)
│    ├── crossbar (LiteI2CCrossbar)
│    │    ├── rr (RoundRobin)
│    │    ├── tx_mux (Multiplexer)
│    │    └── rx_demux (Demultiplexer)
│    ├── master (LiteI2CMaster)
[...]
```

The registers of the core are in `build/gmm/csr.csv`:

```console
$ grep i2c build/gmm/csr.csv
csr_base,i2c,0xf0001000,,
csr_register,i2c_phy_speed_mode,0xf0001000,1,rw
csr_register,i2c_master_active,0xf0001004,1,rw
csr_register,i2c_master_settings,0xf0001008,1,rw
csr_register,i2c_master_addr,0xf000100c,1,rw
csr_register,i2c_master_rxtx,0xf0001010,1,rw
csr_register,i2c_master_status,0xf0001014,1,ro
csr_register,i2c_master_ev_status,0xf0001018,1,ro
csr_register,i2c_master_ev_pending,0xf000101c,1,rw
csr_register,i2c_master_ev_enable,0xf0001020,1,rw
constant,i2c_interrupt,2,,
```

The order is the same in every SoC: the speed register first, then the master registers in the
order of [Registers](#master-registers), then the event registers when the interrupt is present.
Only the base address changes. The C header `build/gmm/software/include/generated/csr.h` holds the
accessors that firmware uses, such as `i2c_master_rxtx_write()`.

## Step 4: on hardware {#gs-hardware}

On a board, the same register sequence runs from firmware or from a host script. Check three
points before the first transaction: pull-up resistors on SCL and SDA, the 7-bit address of the
target from its datasheet, and a speed it supports.

Start with an address probe of a known device: an ACK (`nack` at 0) proves the pins, the
pull-ups and the address at once. Then read a register with a known value, such as an
identification register. [Integration](#integration) gives the C functions, and
[Debugging](#debugging) the meaning of each failure.

Next: [Integration](#integration) to add LiteI2C to your own SoC.
