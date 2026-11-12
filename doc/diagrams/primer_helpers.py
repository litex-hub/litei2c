#
# This file is part of LiteI2C.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Shared helpers of the primer and LiteX figures (no build(): not a figure).
#
# Timing rows: one horizontal row per signal (a name on the left, a level line or adjoining cells
# on a common time axis), dotted ticks for the instants the text refers to, spans for durations.

from svgdiag import *


def row_name(d, x, y, name, size=13):
    """Signal name, right-aligned, left of a row starting at x and centred on y."""
    d.add(Text(x - 10, y, name, size=size, anchor="end"))


def cells(d, x, y, items, h=24, size=13):
    """Row of adjoining square cells: items is a list of (width, label, fill); fill None = gap."""
    out = []
    for w, label, fill in items:
        if fill is not None:
            out.append(d.add(Box(x, y - h/2, w, h, label=label, radius=0, fill=fill, size=size)))
        x += w
    return out


def wave(d, x0, x1, y, edges, start=1, h=20, color=None):
    """Level line from x0 to x1 centred on y: starts at level start (1 high, 0 low) and toggles at
    each x of edges (vertical edges, as a logic analyser draws an open-drain line)."""
    hi, lo = y - h/2, y + h/2
    lvl = start
    pts = [(x0, hi if lvl else lo)]
    for x in edges:
        pts.append((x, hi if lvl else lo))
        lvl ^= 1
        pts.append((x, hi if lvl else lo))
    pts.append((x1, hi if lvl else lo))
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 0.5 or abs(p[1] - out[-1][1]) > 0.5:
            out.append(p)
    d.add(Bus(out, kind="control", color=color))


def span(d, x0, x1, y, label, kind="control", side="above"):
    """Double-headed horizontal arrow from x0 to x1 at y, with its label above or below."""
    d.add(Arrow((x0, y), (x1, y), kind=kind, heads="both", label=label, label_side=side))


def tick(d, x, y0, y1):
    """Dotted vertical marker (a time reference) from y0 to y1."""
    d.add(Bus([(x, y0), (x, y1)], dash="2,3", color="#9a9a9a"))


def note(d, x, y, text, anchor="middle", size=12):
    """Short label of an instant or an interval (one to three words)."""
    d.add(Text(x, y, text, size=size, anchor=anchor))
