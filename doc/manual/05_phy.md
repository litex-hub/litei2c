# The PHY {#phy}

This chapter describes the PHY: the block that turns elements into SCL and SDA activity and
reports what happened on the bus. Read it to choose a speed, to understand the status flags or to
check the bus timing of a design. START, STOP, ACK and clock stretching are explained in
[I2C in a nutshell](#i2c-primer).

## At a glance {#phy-glance}

| Item | Value |
|---------------------|-----------------------------------------------------------------------|
| Classes | `LiteI2CPHYCore` (`litei2c/phy/generic.py`), `LiteI2CClkGen` (`litei2c/clkgen.py`) |
| Input | Elements: address, up to 4 bytes out, up to 4 bytes in, recover bit |
| Output | One status element per element |
| Speed register | `speed_mode`: 0 = 100 kHz, 1 = 400 kHz, 2 = 1 MHz, 3 = 100 kHz (reserved) |
| SCL duty cycle | 50 %: four quarter phases, two low, two high |
| Clock stretching | Checked in the middle of each SCL high time, 25 ms timeout per stretch |
| Pins | Open drain, through `SDRTristate` or split `_o`/`_oe`/`_i` pads |
| Pull-ups | External, on the board or in the FPGA pin settings |
| Errors | NACK, bus not free, stretch timeout, arbitration lost, bus not released |
| Bus recovery | START, 10 clocks with SDA released, repeated START, STOP |
| Vendor primitives | None: any FPGA family that LiteX supports |

## Clock generator {#phy-clkgen}

The clock generator divides the PHY clock, `sys` unless `clock_domain` names another one, into
SCL periods of four quarter phases. SCL is low during phases 1 and 2 and released during phases 3
and 0.

The generator also pulses two strobes: `tx` at the end of phase 1, in the middle of the low time,
and `rx` at the end of phase 3, in the middle of the high time.

The PHY changes SDA on `tx` and samples it on `rx`, so that SDA is stable while SCL is high, as
I2C requires. The figure below shows a quarter phase of three cycles of the PHY clock.

![Clock generator. Follow the dotted lines: SDA changes on the tx strobe, in the middle of the
low time, and is sampled on the rx strobe, in the middle of the high time.](phy_clkgen.svg)

A quarter phase lasts `div + 1` cycles of the PHY clock, with
`div = ceil(sys_clk_freq / (4 x f)) - 1` for the nominal frequency `f` of the speed mode. The SCL
period is therefore 4 x (`div` + 1) cycles, and SCL never runs faster than nominal.

The table below gives the divisor and the resulting SCL frequency for common PHY clock
frequencies, computed from this formula.

| PHY clock | 100 kHz mode | 400 kHz mode | 1 MHz mode |
|-----------:|---------------------:|---------------------:|---------------------:|
| 25 MHz | 62: 99.2 kHz | 15: 390.6 kHz | 6: 892.9 kHz |
| 50 MHz | 124: 100.0 kHz | 31: 390.6 kHz | 12: 961.5 kHz |
| 100 MHz | 249: 100.0 kHz | 62: 396.8 kHz | 24: 1000.0 kHz |
| 125 MHz | 312: 99.8 kHz | 78: 395.6 kHz | 31: 976.6 kHz |

The divisors are constants computed at build time, and the speed register picks one of them.
Speed code 3 is reserved and selects the 100 kHz divisor, the slowest one. The counter is sized
for the 100 kHz divisor, the largest one.

The PHY applies a new speed only while its `active` input is 0. Write the speed register before
software sets `active` ([The register master](#master)); a speed written while `active` is 1
takes effect at the next release of the bus.

## Clock stretching {#phy-stretch}

A target slows the bus down by holding SCL low after the controller releases it. The clock
generator checks SCL at the end of phase 3, where it expects SCL high. If SCL is low at that point, the
generator stops in phase 3 and waits. When the target releases SCL, the `rx` strobe fires and the
bit is sampled.

A stretch lasts at most 25 ms, counted from the end of phase 3: `ceil(sys_clk_freq / 40)` cycles
of the PHY clock. After that, the generator goes on as if SCL were high, the PHY completes the
transaction, and the status element reports a bus error.

Each stretch has its own timeout, so a target that stretches every bit is never cut off as long
as each stretch stays under 25 ms.

After a stretch, SCL stays high for one quarter phase, the remaining phase 0: shorter than the
tHIGH minimum ([Bus timing](#phy-timing)). Stretching detection needs the SCL input: with split pads, the PHY sees SCL high at all times when `scl_i`
is missing, and does not detect stretching.

## Open-drain pins {#phy-io}

I2C lines are open drain: a device pulls a line low or releases it, and a pull-up resistor brings
it high ([I2C in a nutshell](#i2c-primer)). The PHY follows this rule on both lines: it drives the
output enable of the pin with a constant 0 as output, and never drives a high level. The figure
below shows the arrangement.

![Open-drain pins. Look at the pull-up: it is the only source of the high level, so a target that
pulls the line low always wins.](phy_io.svg)

With a pads record holding `scl` and `sda`, the PHY instantiates one `SDRTristate` per line. Its
input is registered, which delays what the PHY sees by a cycle or two of the PHY clock; the PHY
tolerates that delay.

With split pads, the PHY drives the outputs and reads the inputs itself, and an external buffer
or a simulation model builds the line:

- `scl_o`, `scl_oe`: SCL output (always 0) and output enable.
- `sda_o`, `sda_oe`: SDA output and output enable.
- `scl_i`, `sda_i`: the levels read back.

The core configures no pull-up. Put pull-up resistors on the board, sized for the bus capacitance
and the speed, or enable the pull-ups of the FPGA pins in the platform file for short, slow buses.
[Integration](#integ-pads) shows both.

## State machine {#phy-fsm}

The PHY is one state machine of 31 states. The figure below groups them by role; the
table after it maps the groups to the states of the code.

![PHY state machine by group. Follow a write-then-read: START, the address with W, the written
bytes, a repeated START back to START and the address with R, the read bytes, then STOP and the
return of the status element to idle.](phy_fsm.svg)

| Group | States | Role |
|----------------|---------------------------------------------|---------------------------------|
| Idle | `WAIT-DATA` | Wait for `active` and an element, check the bus is free |
| START | `START` | SDA low while SCL is high |
| Address | `ADDR`, `ADDR-RW`, `ADDR-ACK` | 7 address bits, R/W, target ACK |
| Write | `PRE-TX`, `TX`, `TX-ACK`, `TX-BEFORE-NEXT` | Bytes out, target ACK per byte |
| Write chunk | `TX-PRE-WAIT`, `TX-WAIT-SEND-STATUS`, `TX-WAIT` | Status, SCL held low |
| Repeated START | `REPEATED-START-1`, `REPEATED-START-2` | Release SDA, then a new START |
| Read | `PRE-RX`, `RX`, `RX-PRE-ACK`, `RX-ACK`, `RX-NACK` | Bytes in, ACK or final NACK |
| Read chunk | `RX-WAIT-SEND-STATUS`, `RX-WAIT` | Status with data, SCL held low |
| STOP | `STOP-PRE`, `STOP`, `XFER-END-SETTLE`, `XFER-END-WAIT-BUS` | STOP, wait for release |
| End | `XFER-END`, `SEND-STATUS-DATA`, `BUS-FREE` | Status element, bus-free time |
| Errors | `NACK-ERROR` | NACK seen: go to STOP |
| Recovery | `RECOVER-1`, `RECOVER-2` | 10 clocks, repeated START, then STOP |

The PHY accepts the element at the end of the transaction, or at the end of a 4-byte chunk. A
user stream therefore holds the element valid until the PHY has finished with it. The status
element follows at once.

After the STOP, the PHY waits for both lines to read high, for at most one SCL period, or 25 ms
when SCL stays low (the stretch timeout). This absorbs the rise time of the pull-ups and the
registered inputs.

It then returns the status
element and keeps the bus idle for one more SCL period before it accepts the next element.

## Errors {#phy-errors}

The status element has two error flags. `nack` says that the transaction did not complete;
`bus_error` says that the bus itself misbehaved. A bus error always sets `nack` too. The figure
below shows the sources of each flag.

![Error flags. Look at the left column: a target NACK is the only source of nack alone; every
other source is a bus error.](phy_errors.svg)

| Condition | Detection | Flags | Bus activity |
|----------------------------|--------------------------------------|---------------------|------------------|
| Target NACK | SDA high at the ACK of the address or a written byte | `nack` | STOP |
| Bus not free | SCL or SDA low when an element arrives | `nack`, `bus_error` | None |
| Stretch timeout | SCL low for 25 ms from the middle of the high time | `nack`, `bus_error` | Transaction completes |
| Arbitration lost | SDA low while the PHY sends a 1 | `nack`, `bus_error` | STOP |
| Bus not released | SCL or SDA low after the STOP | `nack`, `bus_error` | None |

A NACK on the address is the normal answer of an absent device: an address probe uses it.
Software tests `bus_error` first, then `nack`, to tell a stuck or noisy bus from a missing
device.

Arbitration loss is checked during the address, the written bytes, the repeated START and the
final NACK of a read. When it is detected, the PHY moves to its STOP sequence, which drives SDA
low and clocks SCL.

A controller that loses arbitration should release the bus instead
([I2C in a nutshell](#i2c-primer)), so LiteI2C is meant for buses where it is the only controller
([What it is not](#intro-limits)).

## Bus recovery {#phy-recovery}

A target reset in the middle of a read may hold SDA low, waiting for clocks that never come. The
bus is then stuck: every element ends with a "bus not free" error. An element with the `recover`
bit set skips the bus-free check and runs the recovery sequence instead of a transaction.

The PHY drives a START, then ten clock pulses with SDA released, a repeated START and a STOP.
The pulses let a target finish the byte it was sending and see a NACK; UM10204 asks for nine, and
one more is harmless. The status element then reports whether the bus is free: `nack` at 0 means
the recovery worked.

Recovery cannot clear a bus where a target holds SCL low: each pulse then waits for the 25 ms
stretch timeout, and the status reports a bus error.

## Bus timing {#phy-timing}

All the bus timings of the PHY are whole quarter phases. With `q` = (`div` + 1) / `sys_clk_freq`,
the code gives the values below, computed for a 100 MHz PHY clock. Rise times add to them on a
real bus.

| Timing (UM10204 name) | Value | 100 kHz, `q` = 2.5 µs | 400 kHz, `q` = 625 ns | 1 MHz, `q` = 250 ns |
|---------------------------------|----------------------|----------:|----------:|----------:|
| SCL low, tLOW | 2 `q` | 5 µs | 1.25 µs | 500 ns |
| SCL high, tHIGH | 2 `q` | 5 µs | 1.25 µs | 500 ns |
| START hold, tHD;STA | `q` | 2.5 µs | 625 ns | 250 ns |
| Repeated START setup, tSU;STA | `q` | 2.5 µs | 625 ns | 250 ns |
| STOP setup, tSU;STO | `q` less one PHY clock cycle | 2.49 µs | 615 ns | 240 ns |
| Bus free, tBUF | At least 4 `q` | 10 µs | 2.5 µs | 1 µs |

The quarter-phase values assume a PHY clock that divides exactly, such as 100 MHz at 100 kHz.
The minimums of the I2C-bus specification (NXP UM10204, characteristics of the SDA and SCL bus
lines) are 4.0 µs for the START hold and the STOP setup in Standard-mode. The repeated START
setup needs 4.7 µs.

In Fast-mode, tLOW must be at least 1.3 µs and the three other minimums are 600 ns. In Fast-mode
Plus, the three minimums are 260 ns. The START hold, the repeated START setup and the STOP setup
of the PHY are therefore below the minimums in Standard-mode and Fast-mode Plus.

In Fast-mode, tLOW is below its minimum, and the STOP setup is also under 600 ns when the PHY clock is below
40 MHz.

A target that stretches the clock shortens the next high time. The generator waits at the end
of phase 3; when the target releases SCL, only phase 0 is left, so SCL stays high for one
quarter phase.

When the stretch falls on the pulse of a repeated START or a STOP, the SDA edge
follows the SCL rise after one or two cycles of the PHY clock, far under tSU;STA and tSU;STO.

These limits are known, and a fix is pending ([What it is not](#intro-limits)). The
[status](#intro-status) table records the speeds used on hardware; when a target misbehaves at
one speed, try the next lower speed mode ([Debugging](#debugging)).

## In the code {#phy-code}

| Class or function | File and role |
|--------------------|-----------------------------------------------------------------------|
| `LiteI2CPHYCore` | `litei2c/phy/generic.py`: speed register, SDA pin, state machine, errors |
| `LiteI2CClkGen` | `litei2c/clkgen.py`: quarter phases, strobes, stretching, SCL pin |
| `freq_to_div` | `litei2c/clkgen.py`: divisor of a speed mode |
| `ResyncReg` | `litei2c/common.py`: brings the speed register into the PHY domain |

Next: [The register master](#master) to drive the PHY from software.
