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
    def _run_address_only_transfer(sda_stuck_low=False, scl_stuck_low=False):
        pads = _I2CPads()
        dut  = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=1e6)
        addr_ack = Signal()
        dut.comb += addr_ack.eq(dut.fsm.ongoing("ADDR-ACK"))
        nacks = []

        def host_gen():
            yield dut.active.eq(1)
            yield dut.sink.valid.eq(1)
            yield dut.sink.addr.eq(0x50)
            yield dut.sink.len_tx.eq(0)
            yield dut.sink.len_rx.eq(0)
            yield dut.source.ready.eq(1)

            for _ in range(512):
                if (yield dut.source.valid):
                    nacks.append((yield dut.source.nack))
                    break
                yield

            yield dut.sink.valid.eq(0)

        def pads_gen():
            for _ in range(512):
                yield pads.scl_i.eq(0 if scl_stuck_low else 1)
                if sda_stuck_low:
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

    def test_address_ack_without_stuck_lines(self):
        self.assertEqual(self._run_address_only_transfer(), 0)

    def test_sda_stuck_low_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(sda_stuck_low=True), 1)

    def test_scl_stuck_low_reports_nack(self):
        self.assertEqual(self._run_address_only_transfer(scl_stuck_low=True), 1)


if __name__ == "__main__":
    unittest.main()
