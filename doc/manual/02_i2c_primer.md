# I2C in a nutshell {#i2c-primer}

This chapter explains the I2C bus for an FPGA engineer who has never read the I2C specification.
It starts from the two wires and their pull-ups, builds a byte, then a transaction, and ends
with the cases where the bus misbehaves: clock stretching, arbitration and a stuck bus.

The reference is UM10204, the I2C-bus specification and user manual. Its revision 7 names the
roles *controller* and *target*, as this manual does. Each section gives the idea, then the
mechanism, and ends with the part of LiteI2C that implements it.

## Two wires and pull-ups {#primer-bus}

I2C connects the devices of a board with two shared lines: SCL, the serial clock, and SDA, the
serial data. Each line has one pull-up resistor to the supply, VDD. No device drives a line
high: it pulls the line low or releases it, and the resistor brings a released line back high,
as the figure below shows.

![An I2C bus. The controller and three targets share SCL and SDA; one pull-up resistor (Rp) per
line brings a released line to VDD. Each target answers to its own address, here example
addresses of an EEPROM, a temperature sensor and a clock generator. Dots mark the
connections.](primer_bus.svg)

This *open-drain* connection makes the bus a wired-AND: a line is high only when every device
releases it, and low as soon as one device pulls it. Two devices can therefore drive the same
line at the same time without a short circuit. Clock stretching and arbitration, described
below, rely on this.

The price is speed. A pulled-down line falls fast, but a released line rises through the pull-up
and the capacitance of the bus, the traces and the pins of every device, Cb. The specification
limits this rise time, tr, for each speed mode: a large bus needs a smaller pull-up, and a weak
driver needs a larger one.

UM10204 gives both bounds. The smallest pull-up is set by the current a device can sink while
keeping its low level: Rp(min) = (VDD - VOL(max)) / IOL. The largest is set by the rise time:
Rp(max) = tr / (0.8473 x Cb). Any value in between works; the datasheets give VOL and IOL, and
the board layout gives Cb.

In LiteI2C, SCL and SDA are open-drain outputs: the PHY only enables the output buffer to drive
a low level. The core configures no internal pull-up, so the board, or the I/O settings of the
platform file, must provide them ([Integration](#integration)).

## Controller and targets {#primer-roles}

A *controller* starts every transaction and drives the clock. A *target* answers when the
controller calls its address. Most buses have a single controller, such as a CPU or an FPGA, and
several targets: EEPROMs, temperature sensors, clock generators, power controllers, camera
sensors. Each target has a 7-bit address that is unique on its bus.

The specification allows several controllers on one bus, and gives them a way to share it
([Arbitration and clock synchronisation](#primer-arbitration)). A device may also be both, a
controller at one time and a target at another.

In LiteI2C, the core is a controller only. It cannot answer to an address, and it expects to be
the only controller of its bus.

## START, STOP and repeated START {#primer-conditions}

When the bus is idle, both lines are high. Data bits change SDA only while SCL is low, and SDA
is stable while SCL is high. An SDA edge while SCL is high is therefore not data: it is a
*condition*, as the figure below shows.

![The conditions of the bus. A falling SDA edge while SCL is high is a START; a data bit changes
SDA while SCL is low and keeps it stable while SCL is high; a START without a STOP before it is
a repeated START; a rising SDA edge while SCL is high is a STOP. Time is compressed: the bits
between the conditions are not drawn.](primer_conditions.svg)

A *START* (SDA falls while SCL is high) begins a transaction and makes the bus busy. A *STOP*
(SDA rises while SCL is high) ends it and frees the bus. A *repeated START* is a START sent
before the STOP: the controller keeps the bus and begins a new transfer, usually to change
direction.

In LiteI2C, the PHY generates all three conditions. It checks that SCL and SDA are both high
before it sends a START, and reports a bus error without touching the bus when they are not. It
sends a repeated START only between the write part and the read part of a write-then-read.

## Bits, bytes and acknowledges {#primer-byte}

Data moves in bytes, most significant bit first, one bit per SCL pulse. After the eighth bit,
the receiver answers with a ninth bit, the *acknowledge*. A byte therefore takes nine clock
pulses, as the figure below shows. The controller drives every pulse, whichever side sends the
data.

![One byte on the bus. Eight data bits, most significant first, then the acknowledge bit, each
stable while SCL is high. For a write the controller sends the bits and the target acknowledges;
for a read the target sends the bits and the controller acknowledges.](primer_byte.svg)

The receiver acknowledges by pulling SDA low during the ninth pulse: an *ACK*. If it leaves SDA
high, the sender sees a *NACK*. A target sends a NACK when it is absent, busy or refuses the
byte. A controller sends a NACK after the last byte it reads: the target then releases SDA for
the STOP.

In LiteI2C, the PHY sends and receives the bytes most significant bit first. It reports a NACK
from the target, on the address or on a data byte, in the `nack` bit of the status, and stops
the transaction. When it reads, it sends an ACK after each byte but the last, and a NACK after
the last one.

## Addressing {#primer-address}

The first byte after a START is the *address byte*: the 7-bit address of the target, then the
R/W bit, 0 to write and 1 to read. The 7-bit address `0x50` gives the address byte `0xa0` for a
write and `0xa1` for a read. Datasheets use both forms. The figure below shows the address
bytes.

![Address bytes. A 7-bit address (A6 to A0) and the R/W bit fill one byte. A 10-bit address
starts with the reserved prefix 11110, the two high address bits and the R/W bit, then a second
byte carries the eight low bits. An acknowledge bit follows each byte.](primer_address.svg)

Sixteen of the 128 addresses are reserved. The addresses `0x00` to `0x07` hold the general call
(`0x00` with a write, a broadcast to every target that supports it), the START byte, the CBUS
address, the Hs-mode controller codes and codes reserved for other bus formats.

The addresses `0x78` to `0x7f` hold the device ID and the 10-bit addressing prefix. Targets use the 112 addresses from `0x08` to `0x77`.

A 10-bit address extends the space to 1024 targets. Its first byte starts with the reserved
prefix 11110, which 7-bit targets ignore, and a second byte carries the rest of the address.
Few devices use it.

In LiteI2C, the address is the 7-bit address, written in the `addr` register; the PHY adds the
R/W bit. There is no 10-bit addressing, and the PHY does not filter the reserved addresses.

## Transactions {#primer-transactions}

A transaction runs from a START to a STOP. The figure below shows the three shapes that cover
almost every device. A *write* sends bytes to the target. A *read* receives bytes from it. A
*write-then-read* writes, then turns the bus around with a repeated START and reads.

![Three transactions. S is a START, Sr a repeated START, P a STOP, A an ACK and N a NACK. A write
sends the address and data bytes; a read receives data bytes and ends with a NACK; a
write-then-read writes a register number, then reads from that register after a repeated
START.](primer_transactions.svg)

Most devices hold *device registers* and a register pointer. A write starts with the register
number and continues with the data, which the device stores from that register on. A read uses
a write-then-read: the write part sets the pointer, the read part returns the contents.
EEPROMs work the same way with a memory address of one or two bytes.

A transaction with an address byte and no data is an *address probe*: the ACK tells whether a
target answers to that address. Bus scan commands probe every address in turn.

In LiteI2C, one element of the core describes one transaction: the address, a number of bytes
to write and a number of bytes to read, up to 4 each. Both zero is an address probe; both
non-zero is a write-then-read. A longer transfer is split into chunks of 4 bytes, and the PHY
holds SCL low between two chunks ([Architecture](#architecture)).

## Clock stretching {#primer-stretch}

A target that needs time, to fetch data or finish an internal operation, may hold SCL low after
the controller releases it. The wired-AND keeps the line low, and the controller must wait until
SCL is really high before it counts the high time of the pulse. This is *clock stretching*,
shown in the figure below.

![Clock stretching. The controller releases SCL, but the target keeps pulling it low; the line
stays low until the target releases it, and the controller then counts the high time of the
pulse from that point.](primer_stretch.svg)

A controller supports clock stretching only if it reads SCL back. One that drives SCL blindly
sends the next bit while the target is not ready, and the transfer is corrupted. A target that
holds SCL low forever hangs the bus, so controllers usually bound the wait with a timeout.

In LiteI2C, the clock generator reads SCL and waits while a target holds it low, then counts
the high time from the rise it reads. A stretch longer than 25 ms, counted from the release of
SCL by the PHY, ends the wait: the transaction goes on and the status reports a bus error.
With split pads and no SCL input, the PHY cannot see a stretch and does not wait.

## Speeds and timing {#primer-timing}

The speed modes of I2C differ in their maximum clock frequency and in the electrical limits that
make it possible: Standard-mode up to 100 kHz, Fast-mode up to 400 kHz and Fast-mode Plus up to
1 MHz. Every device supports Standard-mode; the datasheet gives the fastest mode it accepts.

Two faster modes exist. High-speed mode (Hs-mode) reaches 3.4 Mbit/s after a controller code
sent at Fast-mode speed or below. Ultra Fast-mode (UFm) reaches 5 Mbit/s on a unidirectional push-pull bus
without acknowledges. Both need dedicated devices and are rare.

The frequency is a maximum, not a contract: a controller may run slower, and the clock has no
minimum frequency. What a device needs are minimum durations around each edge, given in the
table below for the three common modes.

| Parameter | Meaning | Standard-mode | Fast-mode | Fast-mode Plus |
|------------|--------------------------------|-----------------|------------|----------------|
| fSCL | SCL frequency, maximum | 100 kHz | 400 kHz | 1 MHz |
| tLOW | SCL low time, minimum | 4.7 µs | 1.3 µs | 0.5 µs |
| tHIGH | SCL high time, minimum | 4.0 µs | 0.6 µs | 0.26 µs |
| tHD;STA | START hold time, minimum | 4.0 µs | 0.6 µs | 0.26 µs |
| tSU;STA | Repeated START setup time, minimum | 4.7 µs | 0.6 µs | 0.26 µs |
| tSU;DAT | Data setup time, minimum | 250 ns | 100 ns | 50 ns |
| tSU;STO | STOP setup time, minimum | 4.0 µs | 0.6 µs | 0.26 µs |
| tBUF | Bus free time between STOP and START, minimum | 4.7 µs | 1.3 µs | 0.5 µs |
| tr | Rise time of SCL and SDA, maximum | 1000 ns | 300 ns | 120 ns |
| Cb | Capacitance of each line, maximum | 400 pF | 400 pF | 550 pF |

The START hold time runs from the SDA edge of a START to the next falling SCL edge; the setup
times run from a rising SCL edge to the SDA edge of the condition. tLOW is larger than tHIGH: a
400 kHz clock with a 50 % duty cycle has a low phase of 1.25 µs, under the Fast-mode tLOW.

In LiteI2C, the `speed_mode` register selects Standard-mode, Fast-mode or Fast-mode Plus. The
PHY divides the system clock (or the clock of the PHY domain) into equal low and high times that
also cover tLOW and tHIGH, which caps the Fast-mode SCL at 384.6 kHz. The START hold, repeated
START setup and STOP setup times are three quarters of the SCL period. [Bus timing](#phy-timing)
compares the resulting timing with this table.

## Arbitration and clock synchronisation {#primer-arbitration}

When two controllers start at the same time, the wired-AND decides. Each controller reads SDA
back after it writes a bit. A controller that sends a 1 but reads a 0 knows that another one
sends a 0: it has lost the *arbitration*. It releases SDA at once, and must retry once the bus
is free.

The winner never sees the conflict, since the bus carried its bits. The loser may keep
generating clock pulses until the end of the byte, but it must not drive SDA again. Arbitration
usually ends within the address byte, since two controllers rarely address the same target.

The clocks of the two controllers merge in the same way. SCL is low as long as one controller
holds it low, and high only when both release it. The longest low phase and the shortest high
phase win: this is *clock synchronisation*, the same mechanism as clock stretching.

In LiteI2C, the PHY reads SDA back while it sends the address, the R/W bit, the data bytes, the
repeated START and the final NACK of a read. A read-back mismatch is reported as a bus error.

After the loss, the PHY releases SDA and SCL at once and sends no STOP, so the transaction of
the winner goes on. Software retries the element later ([Errors](#phy-errors)).

## Stuck bus and bus recovery {#primer-recovery}

A target can be left in the middle of a byte, for example when the controller resets during a
read. The target then keeps SDA low to send a 0, and waits for clock pulses that never
come. The bus looks busy forever: no START is possible while SDA is low.

UM10204 calls the fix a *bus clear*. The controller sends up to nine clock pulses with SDA
released. The target shifts out the rest of its byte, releases SDA by the acknowledge bit at the
latest, and the controller sends a STOP. If SDA stays low after nine pulses, only a reset or a
power cycle of the device helps.

In LiteI2C, setting the `recover` bit of an element makes the PHY send a START, ten clock
pulses with SDA released, a repeated START and a STOP. The status reports a NACK and a bus error
if the bus is not free after it.

Recovery cannot clear a bus where a target holds SCL low: each
pulse then waits for the 25 ms stretch timeout.

## SMBus {#primer-smbus}

SMBus, the System Management Bus, is a profile of I2C for battery, power and system monitoring
chips. It uses the same wires and transactions, with stricter rules. The best known one is the
timeout: a device that sees SCL held low for more than 25 ms may abandon the transfer, and must
have done so after 35 ms.

SMBus also sets a minimum clock frequency of 10 kHz, and adds an optional CRC byte (packet error
checking) and an alert line. An SMBus device works on a plain I2C bus as long as the controller
never holds SCL low for longer than the timeout.

In LiteI2C, the 25 ms clock stretching timeout matches the SMBus minimum, but the core has no
other SMBus feature. The PHY holds SCL low between the chunks of a long transfer until the next
chunk arrives, so software must keep up when it talks to an SMBus device.
