# SPDX-License-Identifier: GPL-2.0-or-later


def init():
    from ..dom import root

    from .renderer import on_draw_start

    root.add_event_listener("xr_start", lambda self, name, context: on_draw_start(context))
