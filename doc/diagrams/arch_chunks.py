#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# A 6-byte write (register pointer 0x10, then 0xaa to 0xee) as two elements: the first one sends 4
# bytes and returns a status element with unfinished_tx set; the PHY holds SCL low until software
# pushes the second element, which sends the last 2 bytes and the STOP.

from arch_helpers import *


def build():
    d  = Diagram(CANVAS_WIDTH, 200)
    x0 = 150
    b  = 50
    row_name(d, x0, 30, "Software")
    cells(d, x0, 30, [(110, "settings, rxtx", COLOR_FILL), (4*b - 35, "", None), (110, "pop; settings, rxtx", COLOR_FILL),
        (2*b + 40, "", None), (75, "pop", COLOR_FILL)])
    row_name(d, x0, 75, "Element")
    cells(d, x0, 75, [(75 + 4*b, "len_tx 5: 0x10aabbcc", COLOR_ACCENT), (55, "", None),
        (55 + 2*b + 40, "len_tx 2: 0xddee", COLOR_ACCENT)])
    row_name(d, x0, 120, "Bus")
    cells(d, x0, 120, [(75, "S, 0x50 W", COLOR_ACCENT_LIGHT)] +
        [(b, v, COLOR_ACCENT_LIGHT) for v in ("0x10", "0xaa", "0xbb", "0xcc")] +
        [(110, "SCL held low", COLOR_SHADE)] +
        [(b, v, COLOR_ACCENT_LIGHT) for v in ("0xdd", "0xee")] +
        [(40, "P", COLOR_ACCENT_LIGHT)])
    row_name(d, x0, 165, "Status element")
    cells(d, x0, 165, [(75 + 4*b, "", None), (110, "unfinished_tx", COLOR_FILL),
        (2*b + 40, "", None), (75, "done", COLOR_FILL)])
    return d
