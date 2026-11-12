#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The two stream elements between the core and the PHY: the element (one transaction or one chunk
# of up to 4 bytes) and the status element the PHY returns for each of them.

from arch_helpers import *


def build():
    d  = Diagram(CANVAS_WIDTH, 210)
    x0 = 40
    d.add(Text(x0, 25, "Element, core to PHY (sink of the PHY)", size=15, anchor="start"))
    cells(d, x0, 65, [
        (300, "data\n32 bits", COLOR_ACCENT),
        (110, "addr\n7 bits",  COLOR_ACCENT_LIGHT),
        (95,  "len_tx\n3 bits", COLOR_ACCENT_LIGHT),
        (95,  "len_rx\n3 bits", COLOR_ACCENT_LIGHT),
        (95,  "recover\n1 bit", COLOR_FILL),
    ], h=44)
    d.add(Text(x0, 120, "Status element, PHY to core (source of the PHY)", size=15, anchor="start"))
    cells(d, x0, 160, [
        (300, "data\n32 bits", COLOR_ACCENT),
        (95,  "nack\n1 bit", COLOR_FILL),
        (100, "bus_error\n1 bit", COLOR_FILL),
        (100, "unfinished_tx\n1 bit", COLOR_ACCENT_LIGHT),
        (100, "unfinished_rx\n1 bit", COLOR_ACCENT_LIGHT),
    ], h=44)
    return d
