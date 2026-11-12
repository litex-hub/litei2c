#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Shared helpers of the architecture, PHY, master and integration figures (no build(): not a
# figure).
#
# Timing rows: one horizontal row per signal (a name on the left, adjoining cells or a level line
# on a common time axis) and dotted ticks. Exchange lanes: vertical lifelines with horizontal
# messages between them.

from svgdiag import *


def row_name(d, x, y, name, size=13):
    """Signal name, right-aligned, left of a row whose cells start at x and are centred on y."""
    d.add(Text(x - 10, y, name, size=size, anchor="end"))


def cells(d, x, y, items, h=26, size=13):
    """Row of adjoining square cells: items is a list of (width, label, fill); fill None = gap."""
    out = []
    for w, label, fill in items:
        if fill is not None:
            out.append(d.add(Box(x, y - h/2, w, h, label=label, radius=0, fill=fill, size=size)))
        x += w
    return out


def wave(d, x0, x1, y, highs, h=14):
    """Digital level from x0 to x1 centred on y: high during each (start, end) of highs."""
    hi, lo = y - h/2, y + h/2
    pts = [(x0, lo)]
    for a, b in highs:
        pts += [(a, lo), (a, hi), (b, hi), (b, lo)]
    pts.append((x1, lo))
    clean = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - clean[-1][0]) > 0.5 or abs(p[1] - clean[-1][1]) > 0.5:
            clean.append(p)
    d.add(Bus(clean, kind="control"))


def tick(d, x, y0, y1):
    """Dotted vertical marker (a time reference) from y0 to y1."""
    d.add(Bus([(x, y0), (x, y1)], dash="2,3", color="#9a9a9a"))


class Lifelines:
    """Vertical lifelines with a title box on top of each; messages are horizontal arrows between
    two of them, one per row, the label above the arrow."""
    def __init__(self, d, titles, xs, fills, top=16, row=40, rows=4, bw=170):
        self.d, self.xs, self.row = d, xs, row
        self.y0 = top + 46 + row*0.75
        bottom  = top + 46 + row*(rows + 0.3)
        for title, x, fill in zip(titles, xs, fills):
            d.add(Box(x - bw/2, top, bw, 46, label=title, fill=fill))
            d.add(Bus([(x, top + 46), (x, bottom)], dash="4,3"))

    def y(self, n):
        return self.y0 + n*self.row

    def msg(self, n, a, b, label, kind="control"):
        """Message on row n from lifeline a to lifeline b (indexes)."""
        y  = self.y(n)
        xa = self.xs[a] + (4 if b > a else -4)
        xb = self.xs[b] + (-4 if b > a else 4)
        self.d.add(Arrow((xa, y), (xb, y), kind=kind, label=label,
            label_pos=((xa + xb)/2, y - 9), label_size=12))
