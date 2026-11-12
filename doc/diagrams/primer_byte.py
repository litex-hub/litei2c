#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# One byte on the bus: nine SCL pulses, eight data bits most significant first and an ACK bit.
# The sender of the byte drives SDA for the data bits; the receiver drives it for the ACK.

from primer_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 215)
    x0, p, n = 150, 64, 9
    xs = x0 + 4
    row_name(d, x0, 40, "SCL")
    edges = []
    for i in range(n):
        edges += [xs + i*p + p/2, xs + (i + 1)*p]
    wave(d, x0, xs + n*p + 12, 40, edges, start=0)
    row_name(d, x0, 95, "SDA")
    bits = [(p, f"bit {7 - i}", COLOR_ACCENT if i % 2 == 0 else COLOR_ACCENT_LIGHT) for i in range(8)]
    cells(d, xs + p/4, 95, bits + [(p, "ACK", COLOR_FILL)])
    row_name(d, x0, 145, "Write: driver")
    cells(d, xs + p/4, 145, [(8*p, "controller", COLOR_ACCENT), (p, "target", COLOR_HARDWARE)])
    row_name(d, x0, 185, "Read: driver")
    cells(d, xs + p/4, 185, [(8*p, "target", COLOR_HARDWARE), (p, "controller", COLOR_ACCENT)])
    return d
