import bpy


def draw_panel_dropdown_expander(layout, data, prop, custom_text):
    if data.get(prop) == 0:
        icon = 'TRIA_RIGHT'
    else:  # data.get(prop) == 1:
        icon = 'TRIA_DOWN'
    # icon = 'TRIA_DOWN' if data.get(prop) else 'TRIA_RIGHT',
    layout.prop(data, str(prop), text=custom_text, icon=icon, icon_only=True, emboss=False
                )


def draw_web_link(layout, link, text_ui='', show_always=False):
    '''Draws a Web @link in the given @layout. Optionally with plain @text_ui'''
    if bpy.context.preferences.addons['faceit'].preferences.web_links or show_always:
        web = layout.operator('faceit.open_web', text=text_ui, icon='QUESTION')
        web.link = link
