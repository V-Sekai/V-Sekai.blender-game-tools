from typing import Union

from bpy.types import UILayout, Context, Menu, Panel


class BaseUI:
    layout: UILayout
    bl_idname: str

    @property
    def layout(self) -> UILayout:
        return self.layout

    def draw(self, context: Context, *args, **kwargs):
        layout: UILayout = self.layout
        self.draw_ui(context, layout)

    def draw_ui(self, context: Context, layout: UILayout, *args, **kwargs):
        pass


class MenuUI(BaseUI):
    @classmethod
    def draw_in_layout(cls, layout: UILayout, label: str = 'Menu'):
        layout.menu(cls.bl_idname, text=label)


class PanelUI(BaseUI):
    @classmethod
    def draw_in_layout(cls, layout: UILayout, label: str = 'Menu', icon: str = 'NONE'):
        layout.popover(cls.bl_idname, text=label, icon=icon)


class DrawExtension: # (BaseUI): # BUG: OverrideUI... BaseUI.draw() takes 2 positional arguments but 3 were given.
    def section(self,
                layout: UILayout,
                title: str,
                icon: str = 'NONE',
                header_scale: float = 0.8,
                content_scale: float = 1.2) -> tuple[UILayout, UILayout]:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.scale_y = header_scale
        header.label(text=title, icon=icon)
        content = section.box().column()
        content.scale_y = content_scale
        return header, content

    def row_scale(self, layout: UILayout, scale: float = 1.4) -> UILayout:
        row = layout.row()
        row.scale_y = scale
        return row


UI_TYPES = Union[BaseUI, MenuUI, PanelUI, DrawExtension]
