#
# This file is part of LiteI2C.
#
# Copyright (c) 2024 Fin Maaß <f.maass@vogl-electronic.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.gen import *

import math

from litex.build.io import SDRTristate


# SCL low/high minimums (tLOW, tHIGH) of the I2C-bus specification (NXP UM10204), in seconds.
i2c_scl_timings = {
    100000  : (4.7e-6, 4.0e-6),  # Standard-mode.
    400000  : (1.3e-6, 0.6e-6),  # Fast-mode.
    1000000 : (0.5e-6, 0.26e-6), # Fast-mode Plus.
}

def freq_to_div(sys_clk_freq, freq):
    # The SCL period is 4 phases of (div + 1) sys_clk cycles, SCL low and high last 2 phases each:
    # a phase covers a quarter of the SCL period and half of the tLOW/tHIGH minimums (SCL can then
    # be slightly below freq, ex 384.6 kHz in Fast-mode for the 1.3us tLOW).
    t_low, t_high = i2c_scl_timings.get(freq, (0, 0))
    cycles = max(
        math.ceil(sys_clk_freq / (4*freq)),
        math.ceil(round(sys_clk_freq * t_low  / 2, 6)),
        math.ceil(round(sys_clk_freq * t_high / 2, 6)),
    )
    return cycles - 1

class LiteI2CClkGen(LiteXModule):
    """I2C Clock generator

    The ``LiteI2CClkGen`` class provides a generic I2C clock generator.

    Parameters
    ----------
    pads : Object
        I2C pads description.

    i2c_speed_mode : Signal(2), in
        I2C speed mode.
    
    sys_clk_freq : int
        System clock frequency.

    Attributes
    ----------
    en : Signal(), in
        Clock enable input, output clock will be generated if set to 1, 0 resets the core.

    tx : Signal(), out
        Strobe in the middle of the SCL low time: SDA can change (transmit).

    rx : Signal(), out
        Strobe in the SCL high time, once SCL is seen high: SDA is sampled (receive).

    keep_low : Signal(), in
        Forces the clock to be low, when the clock is disabled.

    suppress : Signal(), in
        Disables the clock output.
    """
    def __init__(self, pads, i2c_speed_mode, sys_clk_freq):
        self.tx         = tx         = Signal()
        self.rx         = rx         = Signal()
        self.en         = en         = Signal()
        self.keep_low   = keep_low   = Signal()
        self.suppress   = suppress   = Signal()
        self.scl_i      = scl_i      = Signal(reset=1)
        self.timeout    = timeout    = Signal()
    
        cnt_width = bits_for(freq_to_div(sys_clk_freq, 100000))
        stretch_timeout_cycles = max(1, math.ceil(sys_clk_freq / 40))
    
        self.div     = div     = Signal(cnt_width)
        self.cnt     = cnt     = Signal(cnt_width)
        self.sub_cnt = sub_cnt = Signal(2)
        self.clk     = clk     = Signal(reset=1)
        stretch_cnt  = Signal(max=stretch_timeout_cycles + 1)
        stretching    = Signal()

        self.comb += [
            Case(i2c_speed_mode, {
                0 : div.eq(freq_to_div(sys_clk_freq, 100000)),  #  100 kHz (Standard Mode)
                1 : div.eq(freq_to_div(sys_clk_freq, 400000)),  #  400 kHz (Fast Mode)
                2 : div.eq(freq_to_div(sys_clk_freq, 1000000)), # 1000 kHz (Fast Mode Plus)
                # Reserved (3): 100 kHz (Standard Mode), slowest/safest.
                "default" : div.eq(freq_to_div(sys_clk_freq, 100000)),
            })]

        # SCL is released in phase 3 but held low by a target (clock stretching) or still rising:
        # the phase 3 counter restarts until SCL is seen high, so the SCL high time (phases 3 and 0)
        # is counted from the SCL rise.
        self.comb += [
            tx.eq(en & (sub_cnt == 0b01) & (cnt == div)),
            rx.eq(en & (sub_cnt == 0b11) & (((cnt == div) & scl_i) | timeout)),
            stretching.eq(en & (sub_cnt == 0b11) & ~scl_i),
            timeout.eq(stretching & (stretch_cnt == stretch_timeout_cycles)),
        ]

        self.sync += [
            If(stretching & ~timeout,
                stretch_cnt.eq(stretch_cnt + 1),
            ).Else(
                stretch_cnt.eq(0),
            ),
            If(en,
                If(stretching & ~timeout,
                    cnt.eq(0),
                ).Elif((cnt < div) & ~timeout,
                    cnt.eq(cnt+1),
                ).Else(
                    cnt.eq(0),
                    clk.eq(sub_cnt[1]),
                    If(sub_cnt < 3,
                        sub_cnt.eq(sub_cnt+1),
                    ).Else(
                        sub_cnt.eq(0),
                    )
                )
            ).Else(
                clk.eq(~keep_low),
                cnt.eq(0),
                sub_cnt.eq(0),
            )
        ]

        # SCL drive handling
        self.scl_o  = Constant(0) # I2C uses Pull-ups, only drive low.
        self.scl_oe = Signal()

        self.comb += self.scl_oe.eq(~clk & ~suppress) # Drive when scl is low and not suppressed.

        if not (hasattr(pads, "scl_o") and hasattr(pads, "scl_oe")):
            # Drive SCL through SDRSTristate.
            self.specials += SDRTristate(
                io = pads.scl,
                o  = self.scl_o,
                oe = self.scl_oe,
                i  = scl_i,
            )
        else:
            # Drive SCL O/OE directly.
            self.comb += [
                pads.scl_o.eq(self.scl_o),
                pads.scl_oe.eq(self.scl_oe),
            ]
            if hasattr(pads, "scl_i"):
                self.comb += scl_i.eq(pads.scl_i)
