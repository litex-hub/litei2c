#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Test bench of test/test_phy.py: a host generator drives the PHY streams, the PHY drives split
# pads, and a pads generator plays the bus (ACKs, stuck lines, stretching, slow release) from the
# FSM state and the output enables of the PHY.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 300)
    d.add(Container(10, 10, 740, 280, title="Migen simulation", title_pos="bl"))
    host  = d.add(Box(30,  60, 150, 56, label="Host generator", fill=COLOR_FILL))
    phy   = d.add(Box(300, 60, 160, 56, label="LiteI2CPHYCore", fill=COLOR_ACCENT))
    pads  = d.add(Box(580, 60, 150, 56, label="Split pads", fill=COLOR_FILL))
    model = d.add(Box(580, 190, 150, 56, label="Pads generator", fill=COLOR_ACCENT_LIGHT))
    d.add(Arrow((host, "r"), (phy, "l"), kind="data", heads="both", label="elements, status",
        label_pos=(240, 48)))
    d.add(Arrow((phy, "r"), (pads, "l"), kind="accent", heads="end", label="scl_oe, sda_oe",
        label_pos=(520, 48)))
    d.add(Arrow((pads, "b"), (model, "t"), kind="accent", heads="both", label="scl_i, sda_i",
        label_pos=(700, 153)))
    d.add(Arrow((phy, "b"), (model, "l"), kind="control", via=[(380, 218)], label="FSM state",
        label_pos=(470, 206)))
    return d
