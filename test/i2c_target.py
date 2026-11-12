#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

"""Behavioral I2C target and PHY stream driver for the Migen simulations.

``I2CTarget`` is a register-pointer device (as an I2C EEPROM or most sensors): the first byte of a
write sets the pointer, the next bytes are written at the pointer, reads return the bytes at the
pointer; the pointer increments after each byte. It sits on split pads (``scl_i/o/oe``,
``sda_i/o/oe``) and builds the wired-AND bus from the controller and target drivers, so it also
records the bus (``trace``) and the decoded events (``events``) for checks and timing measurements.
"""

from migen import *
from migen.sim import passive

# I2C Pads -----------------------------------------------------------------------------------------

class I2CPads:
    def __init__(self):
        self.scl_i  = Signal(reset=1)
        self.scl_o  = Signal()
        self.scl_oe = Signal()
        self.sda_i  = Signal(reset=1)
        self.sda_o  = Signal()
        self.sda_oe = Signal()

# I2C Target ---------------------------------------------------------------------------------------

class I2CTarget:
    """Register-pointer I2C target on a simulated open-drain bus.

    Parameters
    ----------
    pads : I2CPads
        Controller side pads; the target drives ``scl_i``/``sda_i`` with the bus level.

    addr : int
        7-bit target address.

    mem : list of int
        Initial memory content (256 bytes by default).

    stretch : int
        Clock cycles the target holds SCL low after each ACK/NACK bit (0: no clock stretching).
    """
    def __init__(self, pads, addr=0x50, mem=None, stretch=0):
        self.pads    = pads
        self.addr    = addr
        self.mem     = list(mem) if mem is not None else [(0xa1 + 0x11*i) & 0xff for i in range(256)]
        self.stretch = stretch
        self.ptr     = 0
        self.events  = [] # (cycle, event).
        self.trace   = [] # (cycle, scl, sda) on each bus change.

    def event_names(self):
        return [e for _, e in self.events]

    @passive
    def generator(self):
        cycle     = 0
        prev_scl  = 1
        prev_sda  = 1
        state     = "idle"
        bit       = 0      # SCL rising edges seen in the current 9-bit frame.
        byte      = 0
        rw        = 0
        first     = False  # Next written byte is the register pointer.
        ack       = False  # Controller ACK of the last read byte.
        out       = 0      # Byte being read by the controller.
        sda_drive = False  # Target pulls SDA low.
        scl_hold  = 0      # Cycles the target still holds SCL low.
        while True:
            # Wired-AND bus (the PHY only drives low: pads.*_oe = 1 drives 0).
            scl = int(not (yield self.pads.scl_oe) and not scl_hold)
            sda = int(not (yield self.pads.sda_oe) and not sda_drive)
            yield self.pads.scl_i.eq(scl)
            yield self.pads.sda_i.eq(sda)
            if not self.trace or self.trace[-1][1:] != (scl, sda):
                self.trace.append((cycle, scl, sda))
            if scl_hold:
                scl_hold -= 1

            # START/STOP: SDA changes while SCL is high.
            if prev_scl and scl and prev_sda and not sda:
                self.events.append((cycle, "START"))
                state, bit, byte, sda_drive = "addr", 0, 0, False
            elif prev_scl and scl and not prev_sda and sda:
                self.events.append((cycle, "STOP"))
                state, sda_drive = "idle", False

            # SCL rising edge: sample SDA.
            elif not prev_scl and scl and state in ["addr", "write", "read"]:
                if bit < 8:
                    byte = (byte << 1) | sda
                elif state == "read":
                    ack = (sda == 0)
                    self.events.append((cycle, "RD 0x%02x %s" % (out, "ACK" if ack else "NACK")))
                bit += 1

            # SCL falling edge: update the target SDA driver.
            elif prev_scl and not scl and state in ["addr", "write", "read"]:
                if bit == 8:
                    if state == "addr":
                        rw = byte & 1
                        self.events.append((cycle, "ADDR 0x%02x %s" % (byte >> 1, "R" if rw else "W")))
                        if (byte >> 1) == self.addr:
                            sda_drive = True
                            first     = True
                        else:
                            state = "wait"
                    elif state == "write":
                        self.events.append((cycle, "WR 0x%02x" % byte))
                        if first:
                            self.ptr = byte
                            first    = False
                        else:
                            self.mem[self.ptr] = byte
                            self.ptr = (self.ptr + 1) % len(self.mem)
                        sda_drive = True
                    else:
                        sda_drive = False # Release SDA for the controller ACK/NACK.
                elif bit == 9:
                    bit, byte = 0, 0
                    scl_hold  = self.stretch
                    sda_drive = False
                    load = False
                    if state == "addr":
                        state = "read" if rw else "write"
                        load  = (state == "read")
                    elif state == "read":
                        if ack:
                            load = True
                        else:
                            state = "wait" # NACK: last byte, wait for STOP/repeated START.
                    if load:
                        out       = self.mem[self.ptr]
                        self.ptr  = (self.ptr + 1) % len(self.mem)
                        sda_drive = not (out >> 7) & 1
                elif state == "read":
                    sda_drive = not (out >> (7 - bit)) & 1
            prev_scl, prev_sda = scl, sda
            cycle += 1
            yield

# PHY Stream Driver --------------------------------------------------------------------------------

def phy_transfer(phy, elements, statuses, speed_mode=0, timeout=200000):
    """Send ``elements`` (dicts of ``i2c_core2phy_layout`` fields) to ``phy.sink`` and append each
    status (dict of ``i2c_phy2core_layout`` fields) to ``statuses``."""
    yield phy.speed_mode.storage.eq(speed_mode)
    for _ in range(4):
        yield
    yield phy.active.eq(1)
    yield phy.source.ready.eq(1)
    yield
    expected = len(elements)
    for element in elements:
        for name in ["data", "addr", "len_tx", "len_rx", "recover"]:
            yield getattr(phy.sink, name).eq(element.get(name, 0))
        yield phy.sink.valid.eq(1)
        while True:
            yield
            if (yield phy.source.valid):
                statuses.append(dict(
                    data          = (yield phy.source.data),
                    nack          = (yield phy.source.nack),
                    bus_error     = (yield phy.source.bus_error),
                    unfinished_tx = (yield phy.source.unfinished_tx),
                    unfinished_rx = (yield phy.source.unfinished_rx),
                ))
            if (yield phy.sink.ready):
                break
        yield phy.sink.valid.eq(0)
    for _ in range(timeout):
        if len(statuses) >= expected:
            break
        yield
        if (yield phy.source.valid):
            statuses.append(dict(
                data          = (yield phy.source.data),
                nack          = (yield phy.source.nack),
                bus_error     = (yield phy.source.bus_error),
                unfinished_tx = (yield phy.source.unfinished_tx),
                unfinished_rx = (yield phy.source.unfinished_rx),
            ))
    # Let the bus settle (STOP, bus free time).
    for _ in range(256):
        yield

# Master CSR Driver --------------------------------------------------------------------------------

def master_transfer(master, elements, statuses, timeout=200000):
    """Run ``elements`` through the ``LiteI2CMaster`` registers, as software does: set ``active``,
    write ``settings``/``addr``, write ``rxtx`` when ``tx_ready``, then read ``rxtx`` when ``rx_ready``
    for each status. Statuses are appended to ``statuses`` as dicts."""
    status = master._status.fields
    yield master._active.storage.eq(1)
    yield
    for element in elements:
        # Without a CSR bank the field signals are not driven from the storage: drive them directly.
        for name in ["len_tx", "len_rx", "recover"]:
            yield getattr(master._settings.fields, name).eq(element.get(name, 0))
        yield master._addr.storage.eq(element.get("addr", 0))
        while not (yield status.tx_ready):
            yield
        yield master._rxtx.r.eq(element.get("data", 0))
        yield master._rxtx.re.eq(1)
        yield
        yield master._rxtx.re.eq(0)
        for _ in range(timeout):
            if (yield status.rx_ready):
                break
            yield
        statuses.append(dict(
            data          = (yield master._rxtx.w),
            nack          = (yield status.nack),
            bus_error     = (yield status.bus_error),
            unfinished_tx = (yield status.tx_unfinished),
            unfinished_rx = (yield status.rx_unfinished),
        ))
        yield master._rxtx.we.eq(1)
        yield
        yield master._rxtx.we.eq(0)
        yield
    yield master._active.storage.eq(0)
    # Let the bus settle (STOP, bus free time).
    for _ in range(256):
        yield
