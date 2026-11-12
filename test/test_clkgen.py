#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litei2c.clkgen import LiteI2CClkGen, freq_to_div


class _I2CPads:
    def __init__(self):
        self.scl_i  = Signal(reset=1)
        self.scl_o  = Signal()
        self.scl_oe = Signal()


class TestLiteI2CClkGen(unittest.TestCase):
    def speed_mode_div(self, speed_mode, sys_clk_freq=16e6):
        mode   = Signal(2)
        dut    = LiteI2CClkGen(_I2CPads(), mode, sys_clk_freq)
        values = []
        def gen():
            yield mode.eq(speed_mode)
            yield
            values.append((yield dut.div))
        run_simulation(dut, gen())
        return values[0]

    def test_speed_modes(self):
        for speed_mode, freq in [(0, 100e3), (1, 400e3), (2, 1e6)]:
            with self.subTest(speed_mode=speed_mode):
                self.assertEqual(self.speed_mode_div(speed_mode), freq_to_div(16e6, freq))

    def test_reserved_speed_mode_uses_standard_mode(self):
        # Speed mode 3 is reserved: Standard-mode (100 kHz) instead of a sys_clk_freq/4 SCL.
        self.assertEqual(self.speed_mode_div(3), freq_to_div(16e6, 100e3))


if __name__ == "__main__":
    unittest.main()
