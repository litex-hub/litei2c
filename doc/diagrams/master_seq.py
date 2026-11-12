#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Register read with the master (write the register pointer, then read 2 bytes): software sets the
# address and the lengths, pushes one element through rxtx, waits for rx_ready, reads the status
# and pops the returned bytes.

from arch_helpers import *


def build():
    rows = 10
    d  = Diagram(CANVAS_WIDTH, 16 + 46 + 40*(rows + 0.3) + 10)
    ll = Lifelines(d, ["Software", "Master and PHY", "Target"], [110, 400, 670],
        [COLOR_ACCENT_LIGHT, COLOR_ACCENT, COLOR_HARDWARE], rows=rows, bw=160)
    ll.msg(0, 0, 1, "speed_mode, active = 1")
    ll.msg(1, 0, 1, "addr = 0x50, settings: 1 TX, 2 RX")
    ll.msg(2, 0, 1, "tx_ready? rxtx = 0x10")
    ll.msg(3, 1, 2, "START, 0x50 W, 0x10", kind="data")
    ll.msg(4, 1, 2, "repeated START, 0x50 R", kind="data")
    ll.msg(5, 2, 1, "2 bytes", kind="data")
    ll.msg(6, 1, 2, "ACK, NACK, STOP", kind="data")
    ll.msg(7, 1, 0, "rx_ready = 1 (polled)")
    ll.msg(8, 0, 1, "read status, read rxtx")
    ll.msg(9, 0, 1, "active = 0")
    return d
