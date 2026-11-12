# Simulation and tests {#simulation}

This chapter describes how LiteI2C is checked without a board: the Migen test suite of the core,
what it covers and what it does not, how to look at the waveforms, and how to add a test for a new
case. It is for contributors who change the core, and for users who want to see a transaction
before building a bitstream.

## Verification strategy {#sim-strategy}

An I2C controller fails on the bus, not in its streams: a line released one cycle late, a STOP that
the PHY reads back before the pull-up has raised the line, a target holding SCL low. The test suite
therefore runs the real PHY and plays the bus around it, cycle by cycle, from Python generators.

| Level | What runs | Bus side |
|----------------|-------------------------------------------------------|---------------------------------|
| PHY, faults | `LiteI2CPHYCore` with split pads (`test_phy.py`) | Pads generator per test |
| PHY and core, transactions | `LiteI2CPHYCore`, or `LiteI2C` with its register master (`test_target.py`, `test_clock_domain.py`) | `I2CTarget`, a register-pointer target on a wired-AND bus |
| Clock generator | `LiteI2CClkGen` divider per speed mode (`test_clkgen.py`) | None |
| Elaboration | A LiteX-Boards target with LiteI2C, no toolchain | None |
| Hardware | A board, not in CI | Real devices and pull-ups |

The first three levels are the tests of `test/`, run by the CI. The target model lives in
`test/i2c_target.py`.

The [status table](#intro-status) gives, for each feature, whether a test, a simulation or a
hardware record backs it.

## Running the tests {#sim-run}

The tests are Python `unittest` classes collected by pytest. They need Migen and LiteX and no
simulator besides the Migen one.

```sh
# Whole suite, as the CI runs it
python3 -m pytest -v
# One test
python3 -m pytest -v test/test_phy.py -k recovery
```

The suite has 29 tests and runs in under a minute. [Getting started](#getting-started) shows a run.

## The test benches {#sim-bench}

The figure below shows the bench of the PHY fault tests. A host generator drives the stream
interface of the PHY: it raises `active`, presents one element and waits for its status. The PHY
uses split pads, so its output enables and its inputs are separate signals. A second generator
plays the bus: at every cycle it sets `scl_i` and `sda_i` from what the PHY drives and from the
state of the PHY FSM.

![PHY test bench of `test/test_phy.py` (fault tests). The host generator sends elements and reads the statuses;
the pads generator reads the output enables and the FSM state of the PHY, and returns the line
levels.](sim_bench.svg)

The pads generator is not an I2C target: it does not decode the address. It pulls SDA low while
the FSM is in `ADDR-ACK` or `TX-ACK` to acknowledge, and applies the fault of the test (a stuck
line, a late release, a stretch). This keeps each test short and makes the fault exact to the
cycle. The PHY runs at a `sys_clk_freq` of 1 MHz, which gives a short SCL period in system cycles;
each test stops after a bounded number of cycles and fails if no status came back.

`test_target.py` replaces the pads generator by `I2CTarget`, which decodes the address and the
bytes from the bus levels only, with no access to the FSM, and records the bus events. Its
helpers drive the PHY streams, or the registers of `LiteI2C` as software does, so the same
transactions run at both levels.

## What the tests cover {#sim-coverage}

| Area | Tests | What is checked |
|----------------------|-------|------------------------------------------------------|
| Address and write | 2 | ACKed address probe; 3-byte write without `nack` or `bus_error` |
| Release after STOP | 2 | SDA read back high 1 or 8 cycles after the STOP is not an error |
| Stuck lines | 6 | SDA or SCL low before START, after START or at STOP: `nack`, and `bus_error` for a bus not free |
| Target NACK | 1 | `nack` without `bus_error` |
| Bus recovery | 2 | Nine `tx` strobes counted; `nack` while SDA stays low |
| Clock stretching | 1 | A stretch of 256 cycles delays the status |
| Arbitration loss | 2 | SDA low while released during the address: `nack` and `bus_error` |
| Master | 1 | `bus_error` field at bit 9 of `master_status` |
| Transactions with a target | 8 | Probe, address NACK, write, read, write-then-read with repeated START, writes and reads over 4 bytes, read with an 80-cycle stretch: bus events and status data |
| Register master | 1 | The same chunked write and write-then-read through the `LiteI2C` registers |
| Clock domain | 1 | `clock_domain="i2c"`: transfers through the asynchronous FIFOs, SCL period from the i2c clock |
| Speed modes | 2 | Divider of modes 0, 1 and 2; mode 3 decoded as Standard-mode |

The test names say the same in words, such as `test_slave_nack_does_not_report_bus_error` or
`test_recovery_stuck_sda_reports_nack`; `python3 -m pytest --collect-only -q` lists them.

The suite does not cover the stretch timeout, the crossbar with several ports or the interrupt,
and checks the Fast-mode and Fast-mode Plus dividers but not their bus timing. These paths are
described in Part II from the code.

## Looking at the waveforms {#sim-vcd}

`run_simulation` writes a VCD file when given a name. Add the argument in the test you are
studying, run that test alone, and open the file with GTKWave:

```python
run_simulation(dut, [host_gen(), pads_gen()], vcd_name="i2c.vcd")
```

The signals to look at first are the FSM state of the PHY, the output enables `pads.scl_oe` and
`pads.sda_oe`, the inputs `pads.scl_i` and `pads.sda_i`, and the strobes `clkgen.tx` and
`clkgen.rx`. `tx` marks the middle of SCL low, where SDA changes, and `rx` the middle of SCL high,
where SDA is sampled ([The PHY](#phy)).

## Writing a test {#sim-new-test}

Bus robustness is where I2C controllers fail on hardware, and the repository rule (`AGENTS.md`) is
to add a simulation test for each new case. The test below checks that a NACK on a written byte
reports `nack` without `bus_error`. A test of a whole transaction uses `I2CTarget`; this one is
shorter. Instead of a pads generator, it models the bus with
combinatorial statements: each line is the wired-AND of the PHY output and the target, and the
target pulls SDA low only on the address ACK.

```python
import unittest

from migen import *

from litei2c.phy.generic import LiteI2CPHYCore


class _I2CPads:
    def __init__(self):
        for n in ["scl", "sda"]:
            setattr(self, n + "_i",  Signal(reset=1))
            setattr(self, n + "_o",  Signal())
            setattr(self, n + "_oe", Signal())


class TestDataNack(unittest.TestCase):
    def test_data_nack_reports_nack_only(self):
        pads = _I2CPads()
        dut  = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=1e6)
        addr_ack = Signal()
        dut.comb += [
            addr_ack.eq(dut.fsm.ongoing("ADDR-ACK")),
            # Wired-AND bus: the target pulls SDA low on the address ACK only.
            pads.scl_i.eq(~pads.scl_oe),
            pads.sda_i.eq(~pads.sda_oe & ~addr_ack),
        ]
        statuses = []

        def host():
            yield dut.active.eq(1)
            yield dut.source.ready.eq(1)
            yield dut.sink.addr.eq(0x50)
            yield dut.sink.data.eq(0x1234)
            yield dut.sink.len_tx.eq(2)
            yield dut.sink.valid.eq(1)
            for _ in range(4096):
                if (yield dut.source.valid):
                    statuses.append(((yield dut.source.nack), (yield dut.source.bus_error)))
                    break
                yield
            yield dut.sink.valid.eq(0)

        run_simulation(dut, host())
        self.assertEqual(statuses, [(1, 0)])
```

The test passes on this revision, and fails if the target also acknowledges the data bytes, which
shows that it checks what it claims. A few rules keep such tests reliable:

- Call `fsm.ongoing()` before the simulation starts: the FSM is finalized when the simulation
  builds, and a later call raises `FinalizeError`.
- Derive `scl_i` and `sda_i` from the output enables, never set them to 1 while the PHY pulls the
  line low: a contradiction looks like an arbitration loss.
- Bound every loop and fail when no status comes back, as the existing tests do.

## Continuous integration {#sim-ci}

Two workflows run on every push and pull request:

| Workflow | Steps |
|----------------------------------|------------------------------------------------------------|
| `ci` (`ci.yml`) | Install LiteX with `litex_setup.py`, install LiteI2C, check the register appendix, run `python3 -m pytest -v` |
| `doc` (`doc.yml`) | Check the figures and the manual sources ([Maintaining this manual](#maintenance)) |

The register check elaborates the reference design of the [Register reference](#registers) and
fails when the register definitions of the gateware no longer match the appendix. Regenerate it
with the two commands of that check, without `--check`, after a change of a register:

```sh
python3 doc/manual/tools/csr_doc.py dump
python3 doc/manual/tools/csr_doc.py generate
```

## A SoC with a CPU {#sim-litex-sim}

`litex_sim --with-i2c` simulates a full SoC in Verilator with an I2C bus and an EEPROM model, but
it uses the bit-banged `I2CMasterSim` of LiteX, not LiteI2C ([I2C in LiteX](#litex-i2c)). LiteI2C
has no `litex_sim` option on this revision: CPU-level tests of a driver need a board, or a Migen
bench of the master and the PHY such as `test_target.py` or the script of
[Getting started](#gs-sim).

## Where to go next {#sim-next}

[The PHY](#phy) for the states and strobes seen in the waveforms; [Debugging](#debugging) for
the cases met on hardware.
