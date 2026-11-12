#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litei2c.phy.generic import LiteI2CPHYCore

from i2c_target import I2CPads, I2CTarget, phy_transfer

# I2C Bus Timings ----------------------------------------------------------------------------------

# Minimums of NXP UM10204 (I2C-bus specification and user manual), characteristics of the SDA and
# SCL bus lines (seconds), and maximum SCL frequency (Hz).
um10204 = {
    # Mode  : (fSCL max,  tHD;STA, tSU;STA, tSU;STO, tLOW,   tHIGH,   tBUF,   tSU;DAT).
    0 : (100e3,  4.0e-6,  4.7e-6,  4.0e-6,  4.7e-6, 4.0e-6,  4.7e-6, 250e-9), # Standard-mode.
    1 : (400e3,  0.6e-6,  0.6e-6,  0.6e-6,  1.3e-6, 0.6e-6,  1.3e-6, 100e-9), # Fast-mode.
    2 : (1e6,   0.26e-6, 0.26e-6, 0.26e-6,  0.5e-6, 0.26e-6, 0.5e-6,  50e-9), # Fast-mode Plus.
}

def measure_timings(target, sys_clk_freq):
    """Measure the bus timings from the target bus trace and events (ideal bus: no rise time)."""
    trace  = target.trace
    rises  = [c for (c, scl, sda), (_, pscl, _) in zip(trace[1:], trace) if scl and not pscl]
    falls  = [c for (c, scl, sda), (_, pscl, _) in zip(trace[1:], trace) if not scl and pscl]
    starts = [c for c, e in target.events if e == "START"]
    stops  = [c for c, e in target.events if e == "STOP"]
    t = {k: [] for k in ["t_hd_sta", "t_su_sta", "t_su_sto", "t_low", "t_high", "t_buf", "t_su_dat", "t_scl"]}
    for s in starts:
        t["t_hd_sta"].append(min(f for f in falls if f > s) - s)
        # Repeated START: no STOP since the previous START.
        prev_starts = [p for p in starts if p < s]
        if prev_starts and not [p for p in stops if prev_starts[-1] < p < s]:
            t["t_su_sta"].append(s - max(r for r in rises if r < s))
        prev_stops = [p for p in stops if p < s]
        if prev_stops:
            t["t_buf"].append(s - prev_stops[-1])
    for s in stops:
        t["t_su_sto"].append(s - max(r for r in rises if r < s))
    for f in falls:
        r = [r for r in rises if r > f]
        if r:
            t["t_low"].append(r[0] - f)
    for r in rises:
        f = [f for f in falls if f > r]
        # High time inside a transfer (not the idle time between STOP and START).
        if f and not [s for s in stops if r < s < f[0]]:
            t["t_high"].append(f[0] - r)
    for (c, scl, sda), (_, pscl, psda) in zip(trace[1:], trace):
        if (sda != psda) and not scl and not pscl:
            t["t_su_dat"].append(min(r for r in rises if r > c) - c)
    t["t_scl"] = [b - a for a, b in zip(rises, rises[1:])]
    return {k: min(v)/sys_clk_freq for k, v in t.items() if v}


class TestLiteI2CTiming(unittest.TestCase):
    sys_clk_freq = 16e6

    def check_timings(self, speed_mode, stretch=0):
        pads     = I2CPads()
        dut      = LiteI2CPHYCore(pads, clock_domain="sys", sys_clk_freq=self.sys_clk_freq)
        target   = I2CTarget(pads, stretch=stretch)
        statuses = []
        elements = [
            dict(addr=0x50, data=0x02, len_tx=1, len_rx=2), # Write, repeated START, read.
            dict(addr=0x50),                                # Address probe (bus free time).
        ]
        run_simulation(dut, [phy_transfer(dut, elements, statuses, speed_mode=speed_mode), target.generator()])
        self.assertEqual(target.event_names(), [
            "START", "ADDR 0x50 W", "WR 0x02", "START", "ADDR 0x50 R", "RD 0xc3 ACK", "RD 0xd4 NACK", "STOP",
            "START", "ADDR 0x50 W", "STOP"])
        self.assertEqual(statuses[0]["data"], 0xc3d4)
        f_scl, t_hd_sta, t_su_sta, t_su_sto, t_low, t_high, t_buf, t_su_dat = um10204[speed_mode]
        t = measure_timings(target, self.sys_clk_freq)
        for name, value, minimum in [
            ("tHD;STA",  t["t_hd_sta"], t_hd_sta),
            ("tSU;STA",  t["t_su_sta"], t_su_sta),
            ("tSU;STO",  t["t_su_sto"], t_su_sto),
            ("tLOW",     t["t_low"],    t_low),
            ("tHIGH",    t["t_high"],   t_high),
            ("tBUF",     t["t_buf"],    t_buf),
            ("tSU;DAT",  t["t_su_dat"], t_su_dat),
            ("1/fSCL",   t["t_scl"],    1/f_scl),
        ]:
            with self.subTest(mode=speed_mode, stretch=stretch, timing=name):
                self.assertGreaterEqual(value + 1e-12, minimum,
                    "%s %.3f us < %.3f us" % (name, value*1e6, minimum*1e6))

    def test_standard_mode_timings(self):
        self.check_timings(speed_mode=0)

    def test_fast_mode_timings(self):
        self.check_timings(speed_mode=1)

    def test_fast_mode_plus_timings(self):
        self.check_timings(speed_mode=2)

    def test_standard_mode_timings_with_clock_stretching(self):
        # tHIGH after the target releases SCL.
        self.check_timings(speed_mode=0, stretch=200)

    def test_fast_mode_timings_with_clock_stretching(self):
        self.check_timings(speed_mode=1, stretch=50)


if __name__ == "__main__":
    unittest.main()
