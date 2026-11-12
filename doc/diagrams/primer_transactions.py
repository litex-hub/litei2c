#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The three transaction shapes as frame strips: a write, a read, and a write-then-read (register
# pointer write, repeated START, read). Cyan cells are driven by the controller, grey cells by the
# target.

from primer_helpers import *

C, T = COLOR_ACCENT, COLOR_HARDWARE


def build():
    d = Diagram(CANVAS_WIDTH, 210)
    x0 = 150
    S, A, B, P = 34, 34, 76, 34
    row_name(d, x0, 35, "Write")
    cells(d, x0, 35, [(S, "S", C), (B, "Addr + W", C), (A, "A", T), (B, "Register", C), (A, "A", T),
        (B, "Data", C), (A, "A", T), (P, "P", C)])
    row_name(d, x0, 80, "Read")
    cells(d, x0, 80, [(S, "S", C), (B, "Addr + R", C), (A, "A", T), (B, "Data", T), (A, "A", C),
        (B, "Data", T), (A, "N", C), (P, "P", C)])
    row_name(d, x0, 125, "Write-then-read")
    cells(d, x0, 125, [(S, "S", C), (B, "Addr + W", C), (A, "A", T), (B, "Register", C), (A, "A", T),
        (S, "Sr", C), (B, "Addr + R", C), (A, "A", T), (B, "Data", T), (A, "N", C), (P, "P", C)])
    cells(d, x0, 180, [(30, "", C)])
    note(d, x0 + 40, 180, "driven by the controller", anchor="start", size=13)
    cells(d, x0 + 230, 180, [(30, "", T)])
    note(d, x0 + 270, 180, "driven by the target", anchor="start", size=13)
    return d
