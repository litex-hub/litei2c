#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# PHY state machine, states grouped by role: from idle, START, then the address byte with its R/W
# bit, then write bytes, a repeated START and read bytes, or a recovery; every path ends with STOP,
# the release check and the bus-free time, which return the status element and go back to idle.

from arch_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 360)
    idle    = d.add(Box(20,  40, 100, 50, label="Idle"))
    start   = d.add(Box(160, 40, 100, 50, label="START", fill=COLOR_ACCENT_LIGHT))
    addr    = d.add(Box(300, 40, 110, 50, label="Address\nand R/W", fill=COLOR_ACCENT))
    write   = d.add(Box(460, 40, 100, 50, label="Write\nbytes", fill=COLOR_ACCENT))
    rstart  = d.add(Box(610, 40, 130, 50, label="Repeated\nSTART", fill=COLOR_ACCENT_LIGHT))
    recover = d.add(Box(160, 170, 100, 50, label="Recovery\n10 clocks", fill=COLOR_FILL))
    read    = d.add(Box(460, 170, 100, 50, label="Read\nbytes", fill=COLOR_ACCENT))
    stop    = d.add(Box(300, 280, 110, 50, label="STOP and\nbus free", fill=COLOR_ACCENT_LIGHT))
    d.add(Arrow((idle, "r"), (start, "l"), kind="data"))
    d.add(Arrow((start, "r"), (addr, "l"), kind="data"))
    d.add(Arrow((addr, "r"), (write, "l"), kind="data", label="W"))
    d.add(Arrow((write, "r"), (rstart, "l"), kind="data"))
    d.add(Arrow((start, "b"), (recover, "t"), kind="control", label="recover",
        label_side="right"))
    d.add(Arrow((393, 90), (490, 170), via=[(393, 140), (490, 140)], kind="data", label="R",
        label_pos=(442, 130)))
    d.add(Arrow((addr, "b", 0.3), (stop, "t", 0.3), kind="control", label="probe, NACK",
        label_pos=(345, 160), label_anchor="end"))
    d.add(Arrow((rstart, "t"), (start, "t"), via=[(675, 18), (210, 18)], kind="data"))
    d.add(Arrow((recover, "b"), (stop, "l"), kind="control"))
    d.add(Arrow((read, "b"), (410, 295), via=[(510, 295)], kind="data"))
    d.add(Arrow((540, 90), (410, 318), via=[(540, 150), (600, 150), (600, 318)], kind="data"))
    d.add(Arrow((stop, "b"), (idle, "b"), via=[(355, 345), (70, 345)], kind="feedback",
        label="status", label_pos=(110, 337)))
    return d
