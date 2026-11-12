#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The I2C bus: two shared lines, SCL and SDA, pulled up to VDD by one resistor each; the
# controller and every target only pull a line low (wired-AND); each target has its own address.
# Dots mark the connections; lines crossing without a dot are not connected.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 255)
    scl_y, sda_y, vdd_y = 115, 145, 25
    d.add(Text(15, vdd_y, "VDD", size=13, anchor="start"))
    d.add(Bus([(55, vdd_y), (300, vdd_y)], kind="control"))
    for x, y in ((180, scl_y), (250, sda_y)):
        r = d.add(Box(x - 20, 45, 40, 36, label="Rp", fill=COLOR_FILL, size=13))
        d.add(Bus([(x, vdd_y), (x, 45)], kind="control"))
        d.add(Bus([(x, 81), (x, y)], kind="control"))
        d.add(Mark(x, y, color=COLOR_STREAM, r=3))
    d.add(Box(10, 95, 115, 70, label="Controller\n(FPGA)", fill=COLOR_ACCENT))
    d.add(Bus([(125, scl_y), (745, scl_y)], kind="data"))
    d.add(Bus([(125, sda_y), (745, sda_y)], kind="data"))
    d.add(Text(745, scl_y - 10, "SCL", size=13, anchor="end"))
    d.add(Text(745, sda_y - 10, "SDA", size=13, anchor="end"))
    for x, label in ((320, "EEPROM\n0x50"), (460, "Sensor\n0x48"), (600, "Clock chip\n0x60")):
        d.add(Box(x, 185, 110, 55, label=label, fill=COLOR_HARDWARE))
        d.add(Bus([(x + 35, scl_y), (x + 35, 185)], kind="control"))
        d.add(Bus([(x + 75, sda_y), (x + 75, 185)], kind="control"))
        d.add(Mark(x + 35, scl_y, color=COLOR_STREAM, r=3))
        d.add(Mark(x + 75, sda_y, color=COLOR_STREAM, r=3))
    return d
