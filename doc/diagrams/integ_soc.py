#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# LiteI2C in a LiteX SoC: the CPU reaches its registers through the CSR bus, the optional
# interrupt goes to the CPU, gateware users can share the bus through a crossbar port, and the
# SCL and SDA pads need pull-up resistors on the board.

from arch_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 250)
    cpu  = d.add(Box(10,  40, 110, 50, label="CPU"))
    csr  = d.add(Box(170, 40, 120, 50, label="CSR bus\nregisters"))
    i2c  = d.add(Box(340, 40, 130, 50, label="LiteI2C", fill=COLOR_ACCENT))
    seq  = d.add(Box(340, 170, 130, 50, label="Gateware\nuser", fill=COLOR_ACCENT_LIGHT))
    pads = d.add(Box(520, 40, 100, 50, label="Pads\nSCL, SDA"))
    pup  = d.add(Box(520, 170, 100, 50, label="Pull-ups", fill=COLOR_HARDWARE))
    dev  = d.add(Box(660, 40, 90, 50, label="Targets", fill=COLOR_HARDWARE))
    d.add(Arrow((cpu, "r"), (csr, "l"), kind="data", heads="both"))
    d.add(Arrow((csr, "r"), (i2c, "l"), kind="data", heads="both"))
    d.add(Arrow((i2c, "r"), (pads, "l"), kind="data", heads="both"))
    d.add(Arrow((pads, "r"), (dev, "l"), kind="data", heads="both"))
    d.add(Arrow((pup, "t"), (pads, "b"), kind="control"))
    d.add(Arrow((seq, "t"), (i2c, "b"), kind="data", heads="both", label="crossbar port",
        label_side="right"))
    d.add(Arrow((i2c, "b", 0.15), (cpu, "b"), via=[(359.5, 130), (65, 130)], kind="control",
        label="interrupt, optional", label_pos=(210, 120)))
    return d
