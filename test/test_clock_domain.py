#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litex.gen import *

from litei2c import LiteI2C

from i2c_target import I2CPads, I2CTarget, master_transfer

# LiteI2C with the PHY in its own clock domain -----------------------------------------------------

class _DUT(LiteXModule):
    def __init__(self, pads, i2c_clk_freq):
        self.cd_sys = ClockDomain()
        self.cd_i2c = ClockDomain()
        self.i2c    = LiteI2C(i2c_clk_freq, pads=pads, clock_domain="i2c")


class TestLiteI2CClockDomain(unittest.TestCase):
    def test_phy_in_i2c_clock_domain(self):
        # sys_clk (registers) period 10, i2c clock (PHY) period 14: SCL timings from the i2c clock.
        i2c_clk_freq = 4e6
        pads     = I2CPads()
        dut      = _DUT(pads, i2c_clk_freq)
        target   = I2CTarget(pads) # Runs in the i2c clock domain: cycles are i2c clock cycles.
        statuses = []
        elements = [
            dict(addr=0x50, data=0x00010203, len_tx=5),
            dict(addr=0x50, data=0x0405,     len_tx=2),
            dict(addr=0x50, data=0x01,       len_tx=1, len_rx=5),
            dict(addr=0x50,                  len_rx=2),
        ]
        run_simulation(dut,
            generators = {
                "sys" : [master_transfer(dut.i2c.master, elements, statuses)],
                "i2c" : [target.generator()],
            },
            clocks = {"sys": 10, "i2c": 14},
        )
        # Transfers.
        self.assertEqual(target.event_names(), [
            "START", "ADDR 0x50 W"] + ["WR 0x%02x" % i for i in range(6)] + ["STOP",
            "START", "ADDR 0x50 W", "WR 0x01", "START", "ADDR 0x50 R",
            "RD 0x02 ACK", "RD 0x03 ACK", "RD 0x04 ACK", "RD 0x05 ACK", "RD 0xf6 ACK", "RD 0x07 NACK",
            "STOP"])
        self.assertEqual([(s["data"], s["nack"], s["unfinished_tx"], s["unfinished_rx"]) for s in statuses], [
            (0x00000000, 0, 1, 0),
            (0x00000000, 0, 0, 0),
            (0x02030405, 0, 0, 1),
            (0x0000f607, 0, 0, 0),
        ])
        # SCL period in i2c clock cycles: 4 x 10 (100 kHz at 4 MHz) + SCL rise seen 1 cycle later.
        rises  = [c for (c, scl, _), (_, pscl, _) in zip(target.trace[1:], target.trace) if scl and not pscl]
        period = min(b - a for a, b in zip(rises, rises[1:]))
        self.assertIn(period, [40, 41])


if __name__ == "__main__":
    unittest.main()
