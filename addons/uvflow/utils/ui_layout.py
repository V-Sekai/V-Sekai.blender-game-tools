from bpy.types import UILayout, AnyType


def draw_section(layout: UILayout, title: str, icon: str = 'NONE', align_content: bool = False) -> UILayout:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.label(text=title, icon=icon)
        content = section.box().column(align=align_content)
        content.use_property_split = True
        content.use_property_decorate = False
        return content

def draw_section_panel(toggle_prop: tuple[AnyType, str], layout: UILayout, title: str, icon: str = 'NONE', align_content: bool = False) -> UILayout:
        section = layout.column(align=True)
        # if icon != 'NONE':
        #         header = section.row(align=True)
        #         header.box().label(text='', icon=icon)
        #         header = header.box().row(align=True)
        # else:
        #         header = section.box().row(align=True)
        #         header.alignment='LEFT'
        header = section.row()
        header.alignment='LEFT'
        header.use_property_split = False
        toggle_value = getattr(toggle_prop[0], toggle_prop[1])
        arrow_icon = 'DOWNARROW_HLT' if toggle_value else 'RIGHTARROW_THIN'
        header.prop(*toggle_prop, text=title, icon=arrow_icon, toggle=True, emboss=False)
        if not toggle_value:
                return None
        content = section.box().column(align=align_content)
        content.use_property_split = True
        content.use_property_decorate = False
        return content

def draw_section_h(layout: UILayout, title: str, icon: str = 'NONE', align_content: bool = False) -> UILayout:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.label(text=title, icon=icon)
        content = section.box().column(align=align_content)
        content.use_property_split = True
        content.use_property_decorate = False
        return header, content
