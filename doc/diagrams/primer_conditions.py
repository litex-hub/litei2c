#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# START, data bit, repeated START and STOP on SCL and SDA (time compressed, address and data bits
# between them left out): data changes only while SCL is low; an SDA edge while SCL is high is a
# START (falling) or a STOP (rising).

from primer_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 200)
    x0, x1, scl_y, sda_y = 120, 745, 75, 130
    row_name(d, x0, scl_y, "SCL")
    wave(d, x0, x1, scl_y, [230, 300, 370, 440, 520, 590])
    row_name(d, x0, sda_y, "SDA")
    wave(d, x0, x1, sda_y, [180, 260, 480, 640])
    for x, label in ((180, "START"), (335, "data bit"), (480, "repeated START"), (640, "STOP")):
        note(d, x, 22, label)
        tick(d, x, 34, 150)
    span(d, 300, 370, 160, None)
    note(d, 335, 180, "SDA stable")
    note(d, 245, 180, "SDA changes")
    tick(d, 260, 145, 168)
    return d
