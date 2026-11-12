#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Address bytes: a 7-bit address and the R/W bit in one byte; a 10-bit address as a first byte
# with the reserved prefix 11110, the two high address bits and R/W, then a second byte with the
# eight low address bits. Each byte is followed by an ACK bit (not drawn).

from primer_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 175)
    x0, w, gap = 80, 40, 20
    A, L, R = COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_SHADE
    note(d, x0 + 4*w, 20, "address byte", size=13)
    row_name(d, x0, 50, "7-bit")
    cells(d, x0, 50, [(w, f"A{6 - i}", A) for i in range(7)] + [(w, "R/W", L)])
    note(d, x0 + 4*w, 100, "first byte", size=13)
    note(d, x0 + 8*w + gap + 4*w, 100, "second byte", size=13)
    row_name(d, x0, 130, "10-bit")
    cells(d, x0, 130, [(w, b, R) for b in "11110"] + [(w, "A9", A), (w, "A8", A), (w, "R/W", L)])
    cells(d, x0 + 8*w + gap, 130, [(w, f"A{7 - i}", A) for i in range(8)])
    return d
