#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The three I2C controllers of LiteX by the work left to the CPU: the bit-banged core moves each
# SCL and SDA edge in software, the Wishbone core one byte or condition per access, LiteI2C a
# whole transaction (or a 4-byte chunk of it) per register access.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 265)
    d.add(Box(10, 15, 740, 45, label="CPU and software", fill=COLOR_FILL))
    cores = (
        (30,  "Bit-banged core\n(pin registers)", COLOR_ACCENT_LIGHT, "each SCL edge"),
        (285, "Wishbone core\n(byte machine)",    COLOR_ACCENT_LIGHT, "each byte"),
        (540, "LiteI2C\n(PHY and master)",        COLOR_ACCENT,       "each transaction"),
    )
    for x, label, fill, access in cores:
        d.add(Box(x, 115, 190, 60, label=label, fill=fill))
        d.add(Arrow((x + 95, 60), (x + 95, 115), kind="control", heads="both", label=access,
            label_side="right"))
        d.add(Arrow((x + 95, 175), (x + 95, 215), kind="accent", heads="both"))
    d.add(Box(10, 215, 740, 40, label="SCL and SDA", fill=COLOR_HARDWARE))
    return d
