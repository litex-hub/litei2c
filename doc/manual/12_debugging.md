# Debugging {#debugging}

This chapter helps when a target does not answer, a transfer stops half way, or the bus stays
stuck. It gives a method, a table of symptoms with their causes, the register accesses to run from
a host, the signals worth probing with LiteScope, and the known limitations of this revision.

## Method {#debug-method}

Most I2C problems are a pin, a missing pull-up, a wrong address or a misuse of the FIFOs. They show
up in the status of the first element, so the registers come before a logic analyzer.

1. Check the build: the pads and the name of the core in the target, and the registers of the
   core in the `csr.csv` (`<name>_phy_speed_mode`, `<name>_master_*`; `i2cmaster_` by default,
   `i2c_` on the GMM-7550).
2. Read `master_status` with nothing in flight: `tx_ready` set and `rx_ready` clear is the idle
   state; the other fields mean something only while `rx_ready` is 1.
3. Probe one address from the host and read the status of that element
   ([Talking to the bus from the host](#debug-host)).
4. Change one thing at a time: the address, the speed, the length of the element.
5. Only then probe the PHY with LiteScope, or measure the lines with a scope.

The same element can often be reproduced without a board: the test bench of
[Simulation and tests](#simulation) runs the real PHY against a model of the bus.

## Symptoms {#debug-symptoms}

| Symptom | Likely causes | What to check |
|--------------------------------|------------------------------------------|--------------------------------------------|
| `nack` on every address, no `bus_error` | 8-bit address written, target not powered or in reset, wrong pins | Write the 7-bit address (`0x50`, not `0xa0`); the supply and reset of the target; scan the bus |
| `nack` and `bus_error` on every element | A line held low before the START: no pull-up, a target stuck after a reset | Both lines high at idle; a recovery element ([Bus recovery](#ex-recover)) |
| Bytes lost on writes longer than one element | `master_rxtx` written while `tx_ready` was 0 | Poll `tx_ready` before each write ([Bare-metal software](#integ-baremetal)) |
| Bus hangs with SCL low | Status of a chunk not popped; `master_active` dropped between chunks; next element never pushed | Pop each status; keep `master_active` at 1 for the whole transaction |
| A new speed has no effect | `phy_speed_mode` written while `master_active` was 1 | Write `master_active` 0, the speed, then `master_active` 1 |
| `bus_error` with a slow target | Clock stretching longer than 25 ms | The target datasheet; the stretch timeout ([The PHY](#phy)) |
| Errors on a long bus only, or with one target | Slow rising edges, short START and STOP timings | Pull-up values; the lines on a scope; [Known limitations](#debug-known) |
| Read returns the bytes of an earlier read | Data of a write status taken as a result | Use the data of a status only after a read |

`master_addr` is 7 bits wide, so an 8-bit address is truncated: `0xa0` becomes `0x20`. A status
with `nack` alone means that a target refused the address or a byte; the PHY has sent a STOP and
the bus is free. A status with `bus_error` means that the bus itself misbehaved: a line not free
before the START or after the STOP, a stretch timeout, or an arbitration loss. The PHY reports a
bus that is low before the START without driving either line.

A long transfer is the case to watch. Between two chunks the PHY holds SCL low and waits, first for
the RX FIFO to accept its status (immediately, unless an earlier status is unread), then for the
next element while `master_active` is 1. A program that stops in between leaves the bus held: every
other device on it is blocked until the transaction ends ([Long transfers](#ex-long)).

## Talking to the bus from the host {#debug-host}

The master registers let a host run any element through a bridge (UARTBone, JTAGBone or
Etherbone) with `litex_server` and `litex_cli`. Start with the identifier and the registers of the
core. The commands below use the default name `i2cmaster`; use the name of the core, such as `i2c`
on the GMM-7550:

```sh
# Identifier of the SoC, then the I2C registers
litex_cli --ident
litex_cli --regs --filter i2cmaster
```

`--regs` skips `i2cmaster_master_rxtx`, whose read pops the RX FIFO; it reads it only when the
filter names it exactly. The sequence below probes the address `0x50`, as the `i2c_probe()` recipe
does ([Probe and scan](#ex-probe)):

```sh
litex_cli --write i2cmaster_master_active 1
litex_cli --write i2cmaster_master_addr 0x50
# len_tx=0, len_rx=0: address only
litex_cli --write i2cmaster_master_settings 0
litex_cli --write i2cmaster_master_rxtx 0
# Status of the element, then pop it
litex_cli --read i2cmaster_master_status
litex_cli --read i2cmaster_master_rxtx
```

The status read gives `0x3` (`tx_ready` and `rx_ready`) when the target acknowledged, `0x103`
with `nack`, and `0x303` with `nack` and `bus_error`. A status of `0x1` means that no status has
arrived: the element is in progress, or `master_active` is 0. A register read of a target is
the same sequence with `master_settings` set to `0x101` (`len_tx=1`, `len_rx=1`) and the register
number written to `master_rxtx`; the value is in bits 7:0 of the second read.

## Probing with LiteScope {#debug-litescope}

When the registers do not explain a failure, capture the PHY with LiteScope. The signals below
show the bus as the PHY sees it and the elements it receives. LiteX-M2SDR has such a probe for its
SI5351 bus (`add_si5351_i2c_probe` in `litex_m2sdr.py`).

| Signal | What it shows |
|-----------------------------|--------------------------------------------------------------|
| `phy.fsm` | State of the PHY: address, write, read, STOP, recovery |
| `phy.clkgen.scl_oe` | SCL pulled low by the PHY |
| `phy.clkgen.scl_i` | SCL level on the pin |
| `phy.sda_oe`, `phy.sda_o` | SDA driven by the PHY; it pulls the line low when `sda_o` is 0 |
| `phy.sda_i` | SDA level on the pin |
| `phy.clkgen.tx`, `rx` | Middle of SCL low (SDA changes), middle of SCL high (SDA sampled) |
| `master.source`, `sink` | Elements to the crossbar, statuses back from it |

The names are attributes of the core, `self.<name>` in a SoC that calls `add_i2c_master()`:
`self.i2cmaster` with the default name, `self.i2c` on the GMM-7550.

A line that the PHY releases while the pin stays low is driven by a target, or has no pull-up.
`scl_i` low while `scl_oe` is 0 is clock stretching. The FSM state at the `rx` strobe where an
error appears tells which phase failed.

The bus is slow compared with the system clock, so a capture needs subsampling. At a 100 MHz
system clock in Standard-mode, a quarter of an SCL period lasts 250 cycles. With
`litescope_cli --subsampling 16`, a capture of 4096 samples covers 655 µs, about 65 SCL periods,
enough for a register read (computed, [Performance and resources](#performance)). Trigger on the
FSM leaving its idle state or on the first rising edge of `sda_oe`; `litescope_cli --list` gives
the names of the signals in the capture.

## Known limitations {#debug-known}

The table lists the behaviours of this revision that a user may meet on hardware. They come from
the code; the [status table](#intro-status) gives the validation of each feature.

| Behaviour | Effect | Where |
|--------------------------------|------------------------------------------------------|---------------------------|
| START hold, repeated START setup and STOP setup last about one quarter of the SCL period | Below the minimums of the I2C specification in Standard-mode (START hold 2.5 µs for 4.0 µs) and Fast-mode Plus (250 ns for 260 ns); fix pending (PR #13) | `phy/generic.py`, `clkgen.py` |
| SCL low and high each last half of the period | In Fast-mode, SCL low lasts 1.25 µs, below the minimum of 1.3 µs; fix pending (PR #13) | `clkgen.py` |
| SCL high after a stretch lasts one quarter of the period | Shorter high time after a target releases SCL, and short repeated START and STOP setup when the stretch falls on them; fix pending (PR #13) | `clkgen.py` |
| An arbitration loss leads to a STOP | The losing controller keeps driving SDA and SCL: only one controller per bus; fix pending (PR #15) | `phy/generic.py` |
| No TX FIFO overflow protection | A write of `master_rxtx` while `tx_ready` is 0 is lost | `core/master.py` |
| Data of a write status not cleared | It repeats the last bytes received | `phy/generic.py` |

The speed mode scales these timings with the SCL period, so a lower speed does not bring them
back to the specification. [Bus timing](#phy-timing) gives the timings of each mode.

## Where to go next {#debug-next}

[Examples](#examples) for correct register sequences; [The PHY](#phy) for the error detection;
[Simulation and tests](#simulation) to reproduce a failure without a board.
