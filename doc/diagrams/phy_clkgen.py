#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Clock generator: each SCL period is four quarter phases of div + 1 sys clock cycles (3 here);
# SCL is low during phases 1 and 2; the tx strobe ends phase 1 (the PHY changes SDA in the middle
# of the low time), the rx strobe ends phase 3 (the PHY samples SDA in the middle of the high time).

from arch_helpers import *


def build():
    d  = Diagram(CANVAS_WIDTH, 260)
    x0 = 130
    c  = 20             # px per sys clock cycle.
    q  = 3*c            # One quarter phase: div + 1 = 3 cycles.
    n  = 8              # Quarter phases shown.
    x1 = x0 + n*q
    row_name(d, x0, 30, "sys clock")
    wave(d, x0, x1, 30, [(x0 + k*c, x0 + k*c + c/2) for k in range(n*3)])
    row_name(d, x0, 70, "phase")
    cells(d, x0, 70, [(q, str(k % 4), COLOR_ACCENT if k % 4 in (1, 2) else COLOR_ACCENT_LIGHT)
        for k in range(n)])
    row_name(d, x0, 115, "SCL")
    wave(d, x0, x1, 115, [(x0, x0 + q), (x0 + 3*q, x0 + 5*q), (x0 + 7*q, x1)], h=20)
    row_name(d, x0, 155, "tx strobe")
    wave(d, x0, x1, 155, [(x0 + 2*q - c, x0 + 2*q), (x0 + 6*q - c, x0 + 6*q)])
    row_name(d, x0, 190, "rx strobe")
    wave(d, x0, x1, 190, [(x0 + 4*q - c, x0 + 4*q), (x0 + 8*q - c, x0 + 8*q)])
    row_name(d, x0, 230, "SDA")
    cells(d, x0, 230, [(2*q, "bit n", COLOR_FILL), (4*q, "bit n + 1", COLOR_ACCENT_LIGHT),
        (2*q, "bit n + 2", COLOR_FILL)])
    for x in (x0 + 2*q, x0 + 6*q):
        tick(d, x, 140, 215)
    for x in (x0 + 4*q, x0 + 8*q):
        tick(d, x, 175, 215)
    return d
