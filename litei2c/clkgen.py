#
# This file is part of LiteX.
#
# Copyright (c) 2024 Fin Maaß <f.maass@vogl-electronic.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.gen import *

import math

from litex.build.io import SDRTristate


def freq_to_div(sys_clk_freq, freq):
    return math.ceil(sys_clk_freq / (4*freq)) - 1

class LiteI2CClkGen(LiteXModule):
    """I2C Clock generator

    The ``LiteI2CClkGen`` class provides a generic I2C clock generator.

    Parameters
    ----------
    pads : Object
        i2C pads description.

    i2c_speed_mode : Signal(2), in
        I2C speed mode.
    
    sys_clk_freq : int
        System clock frequency.

    Attributes
    ----------
    en : Signal(), in
        Clock enable input, output clock will be generated if set to 1, 0 resets the core.

    tx : Signal(), out
        Outputs 1 when the clock is high and the I2C bus is in the transmit state.

    rx : Signal(), out
        Outputs 1 when the clock is low and the I2C bus is in the receive state.

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
    
        cnt_width = bits_for(freq_to_div(sys_clk_freq, 100000))
    
        self.div     = div     = Signal(cnt_width)
        self.cnt     = cnt     = Signal(cnt_width)
        self.sub_cnt = sub_cnt = Signal(2)
        self.clk     = clk     = Signal(reset=1)

        self.comb += [
            Case(i2c_speed_mode, {
                0 : div.eq(freq_to_div(sys_clk_freq, 100000)),  #  100 kHz (Standard Mode)
                1 : div.eq(freq_to_div(sys_clk_freq, 400000)),  #  400 kHz (Fast Mode)
                2 : div.eq(freq_to_div(sys_clk_freq, 1000000)), # 1000 kHz (Fast Mode Plus)
            })]

        self.comb += [
            tx.eq(en & (sub_cnt == 0b01) & (cnt == div)),
            rx.eq(en & (sub_cnt == 0b11) & (cnt == div)),
        ]

        self.sync += [
            If(en,
                If(cnt < div,
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
        self.scl_o  = Signal()
        self.scl_oe = Signal()
        self.comb += [
            self.scl_o.eq(0),                 # I2C uses Pull-ups, only drive low.
            self.scl_oe.eq(~clk & ~suppress), # Drive when scl is low and not suppressed.
        ]
        if not (hasattr(pads, "scl_o") and hasattr(pads, "scl_oe")):
            # Drive SCL through SDRSTristate.
            self.specials += SDRTristate(
                io = pads.scl,
                o  = self.scl_o,
                oe = self.scl_oe,
            )
        else:
            # Drive SCL O/OE directly.
            self.comb += [
                pads.scl_o.eq(self.scl_o),
                pads.scl_oe.eq(self.scl_oe),
            ]
