#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# LiteI2C blocks: software reaches the register master over the CSR bus, gateware users get their
# own crossbar ports; the crossbar gives the PHY to one port at a time; the PHY drives SCL and SDA.

from arch_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 250)
    d.add(Container(150, 20, 440, 200, title="LiteI2C", title_pos="bl"))
    cpu    = d.add(Box(10,  45, 110, 50, label="CPU\nCSR bus"))
    gw     = d.add(Box(10, 140, 110, 50, label="Gateware\nuser"))
    master = d.add(Box(175, 45, 110, 50, label="Master\nregisters", fill=COLOR_ACCENT_LIGHT))
    xbar   = d.add(Box(320, 95, 100, 50, label="Crossbar", fill=COLOR_ACCENT_LIGHT))
    phy    = d.add(Box(460, 95, 105, 50, label="PHY", fill=COLOR_ACCENT))
    bus    = d.add(Box(650, 95, 100, 50, label="I2C targets", fill=COLOR_HARDWARE))
    d.add(Arrow((cpu, "r"), (master, "l"), kind="control", heads="both"))
    d.add(Arrow((master, "r"), (xbar, "t"), kind="data", heads="both"))
    d.add(Arrow((gw, "r"), (xbar, "b"), kind="data", heads="both", label="port",
        label_pos=(200, 155)))
    d.add(Arrow((xbar, "r"), (phy, "l"), kind="accent", heads="both"))
    d.add(Arrow((phy, "r"), (bus, "l"), kind="data", heads="both", label="SCL, SDA",
        label_pos=(620, 108)))
    return d
