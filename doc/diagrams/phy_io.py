#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Open-drain pins: the PHY only ever drives a low level (output enable with a constant 0 output);
# the pull-up resistor makes the high level, so a target pulling low wins (wired-AND); the PHY
# reads the line back through the input of the same tristate buffer.

from arch_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 190)
    phy  = d.add(Box(20,  90, 130, 60, label="PHY\noe, input", fill=COLOR_ACCENT))
    tri  = d.add(Box(230, 90, 140, 60, label="SDRTristate\no = 0", fill=COLOR_ACCENT_LIGHT))
    pad  = d.add(Box(450, 90, 100, 60, label="SCL or SDA\nline", fill=COLOR_FILL))
    pup  = d.add(Box(450, 10, 100, 44, label="Pull-up", fill=COLOR_HARDWARE))
    tgt  = d.add(Box(630, 90, 110, 60, label="Targets", fill=COLOR_HARDWARE))
    d.add(Arrow((phy, "r", 0.3), (tri, "l", 0.3), kind="control", label="oe: pull low"))
    d.add(Arrow((tri, "l", 0.75), (phy, "r", 0.75), kind="control", label="registered input",
        label_pos=(190, 166)))
    d.add(Arrow((tri, "r"), (pad, "l"), kind="data", heads="both"))
    d.add(Arrow((pup, "b"), (pad, "t"), kind="control", label="high level",
        label_side="right"))
    d.add(Arrow((tgt, "l"), (pad, "r"), kind="data", label="pull low"))
    return d
