#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# LiteI2C in a SoC: the CPU reaches its registers on the CSR bus and gets an optional interrupt;
# open-drain I/O only pulls SCL and SDA low; the pull-ups and the devices are on the board.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 230)
    d.add(Container(10, 15, 440, 205, title="FPGA", title_pos="bl"))
    d.add(Container(520, 15, 230, 205, title="Board", title_pos="bl"))
    cpu  = d.add(Box(30, 40, 95, 120, label="CPU", fill=COLOR_FILL))
    i2c  = d.add(Box(195, 40, 110, 120, label="LiteI2C", fill=COLOR_ACCENT))
    io   = d.add(Box(335, 40, 100, 120, label="Open-drain\nI/O", fill=COLOR_ACCENT_LIGHT))
    pull = d.add(Box(540, 40, 190, 40, label="Pull-ups to VDD", fill=COLOR_HARDWARE))
    dev  = d.add(Box(610, 120, 120, 75, label="I2C devices", fill=COLOR_HARDWARE))
    d.add(Arrow((125, 75), (195, 75), kind="control", heads="both", label="CSR bus"))
    d.add(Arrow((195, 130), (125, 130), kind="control", label="IRQ"))
    d.add(Arrow((305, 100), (335, 100), kind="data", heads="both"))
    d.add(Arrow((435, 157), (610, 157), kind="accent", heads="both", label="SCL, SDA",
        label_pos=(485, 147)))
    d.add(Bus([(580, 80), (580, 157)], kind="data"))
    return d
