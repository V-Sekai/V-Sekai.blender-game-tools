"""
Copyright (C) 2021 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


# Substance Keyboard Shortcuts
# 5/01/2020
import bpy


class Keymap():
    """ The Keymappings and definitions """
    addon_keymaps = []
    kmi_defs = []

    def addKeymap(self, char, cls, name, isOperator, mods, space):
        """ Add a keymap to the list """
        keyMapLabel = space[0] + ':' + name
        kmDefs = Keymap.kmi_defs
        if isOperator:
            kmDefs.append((cls, char, 'PRESS', mods[0], mods[1], mods[2], None, keyMapLabel),)
        else:
            kmDefs.append(('wm.call_menu', char, 'PRESS', mods[0], mods[1], mods[2], (('name', cls),), keyMapLabel),)

        kc = bpy.context.window_manager.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name=space[0], space_type=space[1])
            (identifier, key, action, CTRL, SHIFT, ALT, props, name) = (kmDefs[-1])
            kmi = km.keymap_items.new(identifier, key, action, ctrl=CTRL, shift=SHIFT, alt=ALT)
            if props:
                for prop, value in props:
                    setattr(kmi.properties, prop, value)
            Keymap.addon_keymaps.append((km, kmi))

    def cleanup_hotkey_name(self, punc):
        """ Convert string names to actual characters """
        pairs = (
            ('LEFTMOUSE', "LMB"),
            ('MIDDLEMOUSE', "MMB"),
            ('RIGHTMOUSE', "RMB"),
            ('WHEELUPMOUSE', "Wheel Up"),
            ('WHEELDOWNMOUSE', "Wheel Down"),
            ('WHEELINMOUSE', "Wheel In"),
            ('WHEELOUTMOUSE', "Wheel Out"),
            ('ZERO', "0"),
            ('ONE', "1"),
            ('TWO', "2"),
            ('THREE', "3"),
            ('FOUR', "4"),
            ('FIVE', "5"),
            ('SIX', "6"),
            ('SEVEN', "7"),
            ('EIGHT', "8"),
            ('NINE', "9"),
            ('OSKEY', "Super"),
            ('RET', "Enter"),
            ('LINE_FEED', "Enter"),
            ('SEMI_COLON', ";"),
            ('PERIOD', "."),
            ('COMMA', ","),
            ('QUOTE', '"'),
            ('MINUS', "-"),
            ('SLASH', "/"),
            ('BACK_SLASH', "\\"),
            ('EQUAL', "="),
            ('NUMPAD_1', "Numpad 1"),
            ('NUMPAD_2', "Numpad 2"),
            ('NUMPAD_3', "Numpad 3"),
            ('NUMPAD_4', "Numpad 4"),
            ('NUMPAD_5', "Numpad 5"),
            ('NUMPAD_6', "Numpad 6"),
            ('NUMPAD_7', "Numpad 7"),
            ('NUMPAD_8', "Numpad 8"),
            ('NUMPAD_9', "Numpad 9"),
            ('NUMPAD_0', "Numpad 0"),
            ('NUMPAD_PERIOD', "Numpad ."),
            ('NUMPAD_SLASH', "Numpad /"),
            ('NUMPAD_ASTERIX', "Numpad *"),
            ('NUMPAD_MINUS', "Numpad -"),
            ('NUMPAD_ENTER', "Numpad Enter"),
            ('NUMPAD_PLUS', "Numpad +"),
        )
        cleanup_punc = False
        for (before, after) in pairs:
            if punc == before:
                cleanup_punc = after
                break
        if not cleanup_punc:
            cleanup_punc = punc.replace("_", " ").title()
        return cleanup_punc

    def draw(self, addon, layout):
        """ Draw the hot key list in the preference UI """
        col = layout.column(align=True)
        hotkey_button_name = "Show Hotkey List"
        if addon.show_hotkey_list:
            hotkey_button_name = "Hide Hotkey List"
        col.prop(addon, "show_hotkey_list",
                 text=hotkey_button_name, toggle=True)
        if addon.show_hotkey_list:
            col.prop(addon, "hotkey_list_filter", icon="VIEWZOOM")
            col.separator()
            for hotkey in Keymap.kmi_defs:
                if hotkey[7]:
                    hotkey_name = hotkey[7]
                    self.displayHotkey(addon, hotkey, hotkey_name, col)

    def displayHotkey(self, addon, hotkey, hotkey_name, col):
        """ Display Node Editor Hotkeys """
        if hotkey_name.startswith('Node Editor:'):
            name = hotkey_name.split('Node Editor:', 1)[1]
            if addon.hotkey_list_filter.lower() in name.lower():
                row = col.row(align=True)
                row.label(text=name)
                keystr = self.cleanup_hotkey_name(hotkey[1])
                if hotkey[4]:
                    keystr = "Shift " + keystr
                if hotkey[5]:
                    keystr = "Alt " + keystr
                if hotkey[3]:
                    keystr = "Ctrl " + keystr
                row.label(text=keystr)

    def unregister(self):
        """ Unregister all of the key mappings """
        for km, kmi in Keymap.addon_keymaps:
            km.keymap_items.remove(kmi)
        Keymap.addon_keymaps.clear()
