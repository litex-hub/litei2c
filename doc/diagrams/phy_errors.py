#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Error flags of the status element: a target NACK sets nack only; a bus that is not free, a clock
# stretch timeout, a lost arbitration or a bus not released after STOP set bus_error, which also
# sets nack.

from arch_helpers import *


def build():
    d = Diagram(CANVAS_WIDTH, 300)
    srcs = ["Target NACK", "Bus not free\nat start", "Stretch timeout\n25 ms",
        "Arbitration lost", "Not released\nafter STOP"]
    boxes = [d.add(Box(20, 20 + 55*i, 190, 46, label=s, fill=COLOR_FILL)) for i, s in enumerate(srcs)]
    nack = d.add(Box(590, 20, 140, 46, label="nack", fill=COLOR_ACCENT))
    berr = d.add(Box(420, 80, 140, 205, label="bus_error", fill=COLOR_ACCENT))
    d.add(Arrow((boxes[0], "r"), (nack, "l"), kind="control"))
    for b in boxes[1:]:
        d.add(Arrow((b, "r"), (berr.x, b.cy), kind="control"))
    d.add(Arrow((berr, "r", 0.15), (nack, "b"), kind="control", label="also sets",
        label_pos=(670, 120), label_anchor="start"))
    return d
