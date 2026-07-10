#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litei2c.phy.generic import LiteI2CPHYCore


class _I2CPads:
    def __init__(self):
        self.scl_i  = Signal(reset=1)
        self.scl_o  = Signal()
        self.scl_oe = Signal()
        self.sda_i  = Signal(reset=1)
        self.sda_o  = Signal()
        self.sda_oe = Signal()


class TestLiteI2CPHY(unittest.TestCase):
    @staticmethod
    def _run_address_only_transfer(
        sda_stuck_low    = False,
        scl_stuck_low    = False,
        sda_low_after_start = False,
        sda_low_after_stop  = False,
        scl_low_after_stop  = False,
    ):
        pads = _I2CPads()
        dut  = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=1e6)
        start    = Signal()
        addr_ack = Signal()
        stop     = Signal()
        dut.comb += [
            start.eq(dut.fsm.ongoing("START")),
            addr_ack.eq(dut.fsm.ongoing("ADDR-ACK")),
            stop.eq(dut.fsm.ongoing("STOP")),
        ]
        nacks = []
        done  = []

        def host_gen():
            yield dut.active.eq(1)
            yield dut.sink.valid.eq(1)
            yield dut.sink.addr.eq(0x50)
            yield dut.sink.len_tx.eq(0)
            yield dut.sink.len_rx.eq(0)
            yield dut.source.ready.eq(1)

            for _ in range(32768):
                if (yield dut.source.valid):
                    nacks.append((yield dut.source.nack))
                    done.append(True)
                    break
                yield

            yield dut.sink.valid.eq(0)

        def pads_gen():
            started      = False
            stop_started = False
            for _ in range(32768):
                if done:
                    break
                if (yield start):
                    started = True
                if (yield stop):
                    stop_started = True

                yield pads.scl_i.eq(0 if (scl_stuck_low or (scl_low_after_stop and stop_started)) else 1)
                if sda_stuck_low or (sda_low_after_start and started) or (sda_low_after_stop and stop_started):
                    yield pads.sda_i.eq(0)
                elif (yield addr_ack):
                    yield pads.sda_i.eq(0)
                else:
                    yield pads.sda_i.eq(1)
                yield

        run_simulation(dut, [host_gen(), pads_gen()])
        if not nacks:
            raise AssertionError("transfer did not complete")
        return nacks[0]

    @staticmethod
    def _run_recovery(release_after_clocks=None):
        pads = _I2CPads()
        dut  = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=1e6)
        recover = Signal()
        dut.comb += recover.eq(dut.fsm.ongoing("RECOVER-1"))
        nacks         = []
        recover_clocks = []

        def host_gen():
            yield dut.active.eq(1)
            yield dut.sink.valid.eq(1)
            yield dut.sink.recover.eq(1)
            yield dut.source.ready.eq(1)

            for _ in range(1024):
                if (yield dut.source.valid):
                    nacks.append((yield dut.source.nack))
                    break
                yield

            yield dut.sink.valid.eq(0)
            yield dut.sink.recover.eq(0)

        def pads_gen():
            clock_count = 0
            for _ in range(1024):
                yield pads.scl_i.eq(1)
                if (release_after_clocks is not None) and (clock_count >= release_after_clocks):
                    yield pads.sda_i.eq(1)
                else:
                    yield pads.sda_i.eq(0)

                if (yield recover) and (yield dut.clkgen.tx):
                    clock_count += 1
                yield

            recover_clocks.append(clock_count)

        run_simulation(dut, [host_gen(), pads_gen()])
        if not nacks:
            raise AssertionError("recovery did not complete")
        if not recover_clocks:
            raise AssertionError("recovery clock monitor did not complete")
        return nacks[0], recover_clocks[0]

    @staticmethod
    def _run_address_transfer_with_scl_stretch(stretch_cycles=256):
        pads = _I2CPads()
        dut  = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=1e6)
        start       = Signal()
        addr_ack    = Signal()
        stretch_done = Signal()
        dut.comb += [
            start.eq(dut.fsm.ongoing("START")),
            addr_ack.eq(dut.fsm.ongoing("ADDR-ACK")),
        ]
        nacks                    = []
        completed_before_release = []

        def host_gen():
            yield dut.active.eq(1)
            yield dut.sink.valid.eq(1)
            yield dut.sink.addr.eq(0x50)
            yield dut.source.ready.eq(1)

            for _ in range(2048):
                if (yield dut.source.valid):
                    nacks.append((yield dut.source.nack))
                    completed_before_release.append(not (yield stretch_done))
                    break
                yield

            yield dut.sink.valid.eq(0)

        def pads_gen():
            started      = False
            saw_scl_low  = False
            stretching   = False
            stretch_count = 0
            for _ in range(2048):
                if (yield start):
                    started = True

                scl_driven_low = (yield pads.scl_oe)
                if started and scl_driven_low:
                    saw_scl_low = True
                if saw_scl_low and not scl_driven_low and not (yield stretch_done):
                    stretching = True

                if stretching and (stretch_count < stretch_cycles):
                    yield pads.scl_i.eq(0)
                    stretch_count += 1
                else:
                    yield pads.scl_i.eq(0 if scl_driven_low else 1)
                    if stretching:
                        yield stretch_done.eq(1)

                if (yield addr_ack):
                    yield pads.sda_i.eq(0)
                else:
                    yield pads.sda_i.eq(1)
                yield

        run_simulation(dut, [host_gen(), pads_gen()])
        if not nacks:
            raise AssertionError("stretched transfer did not complete")
        if not completed_before_release:
            raise AssertionError("stretch completion monitor did not complete")
        return nacks[0], completed_before_release[0]

    def test_address_ack_without_stuck_lines(self):
        self.assertEqual(self._run_address_only_transfer(), 0)

    def test_sda_stuck_low_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(sda_stuck_low=True), 1)

    def test_scl_stuck_low_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(scl_stuck_low=True), 1)

    def test_sda_stuck_low_after_start_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(sda_low_after_start=True), 1)

    def test_sda_stuck_low_at_stop_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(sda_low_after_stop=True), 1)

    def test_scl_stuck_low_at_stop_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(scl_low_after_stop=True), 1)

    def test_recovery_released_sda_reports_ack(self):
        nack, recover_clocks = self._run_recovery(release_after_clocks=3)
        self.assertEqual(nack, 0)
        self.assertGreaterEqual(recover_clocks, 3)

    def test_recovery_stuck_sda_reports_nack(self):
        nack, recover_clocks = self._run_recovery()
        self.assertEqual(nack, 1)
        self.assertEqual(recover_clocks, 9)

    def test_scl_clock_stretch_delays_transfer_completion(self):
        nack, completed_before_release = self._run_address_transfer_with_scl_stretch()
        self.assertEqual(nack, 0)
        self.assertFalse(completed_before_release)


if __name__ == "__main__":
    unittest.main()
