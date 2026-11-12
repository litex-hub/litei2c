#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# LiteI2C at a glance: software drives the master through registers, gateware users drive their
# own crossbar ports; the crossbar gives the PHY to one port at a time; the PHY runs the
# transaction on SCL and SDA.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 275)
    d.add(Container(170, 15, 395, 185, title="LiteI2C core", title_pos="bl"))
    cpu  = d.add(Box(10, 45, 90, 115, label="CPU", fill=COLOR_FILL))
    mstr = d.add(Box(185, 45, 90, 50, label="Master", fill=COLOR_ACCENT))
    xbar = d.add(Box(315, 45, 90, 115, label="Crossbar", fill=COLOR_ACCENT))
    phy  = d.add(Box(465, 45, 85, 115, label="PHY", fill=COLOR_ACCENT))
    dev  = d.add(Box(640, 45, 110, 115, label="I2C\ntargets", fill=COLOR_HARDWARE))
    user = d.add(Box(295, 225, 130, 40, label="Gateware user", fill=COLOR_FILL))
    d.add(Arrow((100, 70), (185, 70), kind="control", heads="both", label="CSR bus",
        label_pos=(134, 60)))
    d.add(Arrow((275, 70), (315, 70), kind="data", heads="both"))
    d.add(Arrow((230, 95), (100, 131), via=[(230, 131)], kind="control", label="IRQ",
        label_pos=(134, 121)))
    d.add(Arrow((xbar, "r"), (phy, "l"), kind="data", heads="both", label="elements",
        label_pos=(435, 88)))
    d.add(Arrow((phy, "r"), (dev, "l"), kind="accent", heads="both", label="SCL, SDA",
        label_pos=(602, 88)))
    d.add(Arrow((user, "t"), (360, 160), kind="data", heads="both", label="port",
        label_pos=(384, 212)))
    return d
