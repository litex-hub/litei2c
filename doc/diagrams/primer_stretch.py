#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Clock stretching: the controller releases SCL, but the target keeps pulling it low; the line
# (wired-AND of both) stays low until the target lets go, and the controller waits for SCL to be
# high before it counts the high time.

from primer_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 215)
    x0, x1 = 180, 745
    row_name(d, x0, 45, "Controller drives")
    wave(d, x0, x1, 45, [230, 290, 350, 410, 570, 630, 690])
    row_name(d, x0, 100, "Target drives")
    wave(d, x0, x1, 100, [350, 510])
    row_name(d, x0, 155, "SCL on the bus")
    wave(d, x0, x1, 155, [230, 290, 350, 510, 570, 630, 690], color=COLOR_CYAN)
    tick(d, 410, 25, 170)
    tick(d, 510, 25, 170)
    span(d, 410, 510, 190, None)
    note(d, 460, 205, "stretch")
    note(d, 410, 16, "controller releases")
    note(d, 540, 16, "target releases", anchor="start")
    return d
