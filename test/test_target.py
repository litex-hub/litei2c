#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litei2c import LiteI2C
from litei2c.phy.generic import LiteI2CPHYCore

from i2c_target import I2CPads, I2CTarget, phy_transfer, master_transfer

# Transfers with a simulated I2C target ------------------------------------------------------------

class TestLiteI2CTarget(unittest.TestCase):
    sys_clk_freq = 4e6 # 10 sys clock cycles per quarter SCL period at 100 kHz.

    def run_phy(self, elements, stretch=0, speed_mode=0):
        pads     = I2CPads()
        dut      = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=self.sys_clk_freq)
        target   = I2CTarget(pads, stretch=stretch)
        statuses = []
        run_simulation(dut, [phy_transfer(dut, elements, statuses, speed_mode=speed_mode), target.generator()])
        return target, statuses

    def check_status(self, status, data=0, nack=0, bus_error=0, unfinished_tx=0, unfinished_rx=0):
        self.assertEqual(status, dict(data=data, nack=nack, bus_error=bus_error,
            unfinished_tx=unfinished_tx, unfinished_rx=unfinished_rx))

    def test_address_probe(self):
        target, statuses = self.run_phy([dict(addr=0x50)])
        self.assertEqual(target.event_names(), ["START", "ADDR 0x50 W", "STOP"])
        self.check_status(statuses[0])

    def test_address_nack(self):
        target, statuses = self.run_phy([dict(addr=0x51, data=0x01, len_tx=1)])
        self.assertEqual(target.event_names(), ["START", "ADDR 0x51 W", "STOP"])
        self.check_status(statuses[0], nack=1)

    def test_write(self):
        target, statuses = self.run_phy([dict(addr=0x50, data=0x021122, len_tx=3)])
        self.assertEqual(target.event_names(), ["START", "ADDR 0x50 W", "WR 0x02", "WR 0x11", "WR 0x22", "STOP"])
        self.assertEqual(target.mem[2:4], [0x11, 0x22])
        self.check_status(statuses[0])

    def test_read(self):
        # Read without a register write: from the target pointer (0).
        target, statuses = self.run_phy([dict(addr=0x50, len_rx=2)])
        self.assertEqual(target.event_names(), ["START", "ADDR 0x50 R", "RD 0xa1 ACK", "RD 0xb2 NACK", "STOP"])
        self.check_status(statuses[0], data=0xa1b2)

    def test_write_then_read_with_repeated_start(self):
        target, statuses = self.run_phy([dict(addr=0x50, data=0x02, len_tx=1, len_rx=3)])
        self.assertEqual(target.event_names(), [
            "START", "ADDR 0x50 W", "WR 0x02",
            "START", "ADDR 0x50 R", "RD 0xc3 ACK", "RD 0xd4 ACK", "RD 0xe5 NACK",
            "STOP"])
        self.check_status(statuses[0], data=0xc3d4e5)

    def test_write_over_4_bytes(self):
        # 6 bytes in one transaction: len_tx > 4 sends 4 bytes and holds SCL low for the next element.
        target, statuses = self.run_phy([
            dict(addr=0x50, data=0x00010203, len_tx=5),
            dict(addr=0x50, data=0x0405,     len_tx=2),
        ])
        self.assertEqual(target.event_names(), ["START", "ADDR 0x50 W"] + ["WR 0x%02x" % i for i in range(6)] + ["STOP"])
        self.assertEqual(target.mem[0:5], [0x01, 0x02, 0x03, 0x04, 0x05])
        self.check_status(statuses[0], unfinished_tx=1)
        self.check_status(statuses[1])

    def test_read_over_4_bytes(self):
        # 6 bytes in one transaction: len_rx > 4 returns 4 bytes and holds SCL low for the next element.
        target, statuses = self.run_phy([
            dict(addr=0x50, data=0x01, len_tx=1, len_rx=5),
            dict(addr=0x50, len_rx=2),
        ])
        self.assertEqual(target.event_names(), [
            "START", "ADDR 0x50 W", "WR 0x01", "START", "ADDR 0x50 R",
            "RD 0xb2 ACK", "RD 0xc3 ACK", "RD 0xd4 ACK", "RD 0xe5 ACK", "RD 0xf6 ACK", "RD 0x07 NACK",
            "STOP"])
        self.check_status(statuses[0], data=0xb2c3d4e5, unfinished_rx=1)
        self.check_status(statuses[1], data=0xf607)

    def test_read_with_clock_stretching(self):
        target, statuses = self.run_phy([dict(addr=0x50, data=0x01, len_tx=1, len_rx=2)], stretch=80)
        self.assertEqual(target.event_names(), [
            "START", "ADDR 0x50 W", "WR 0x01", "START", "ADDR 0x50 R", "RD 0xb2 ACK", "RD 0xc3 NACK", "STOP"])
        self.check_status(statuses[0], data=0xb2c3)

    def test_master_registers_write_then_read(self):
        # Same transfers through LiteI2C (crossbar + LiteI2CMaster registers).
        pads     = I2CPads()
        dut      = LiteI2C(self.sys_clk_freq, pads=pads)
        target   = I2CTarget(pads)
        statuses = []
        elements = [
            dict(addr=0x50, data=0x00010203, len_tx=5),
            dict(addr=0x50, data=0x0405,     len_tx=2),
            dict(addr=0x50, data=0x01,       len_tx=1, len_rx=5),
            dict(addr=0x50,                  len_rx=2),
        ]
        run_simulation(dut, [master_transfer(dut.master, elements, statuses), target.generator()])
        self.assertEqual(target.mem[0:5], [0x01, 0x02, 0x03, 0x04, 0x05])
        self.check_status(statuses[0], unfinished_tx=1)
        self.check_status(statuses[1])
        self.check_status(statuses[2], data=0x02030405, unfinished_rx=1)
        self.check_status(statuses[3], data=0xf607)


if __name__ == "__main__":
    unittest.main()
