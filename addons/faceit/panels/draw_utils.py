import bpy
from bpy.types import UILayout
import textwrap


def draw_web_link(layout, link, text_ui='', show_always=False):
    '''Draws a Web @link in the given @layout. Optionally with plain @text_ui'''
    if bpy.context.preferences.addons['faceit'].preferences.web_links or show_always:
        web = layout.operator('faceit.open_web', text=text_ui, icon='QUESTION')
        web.link = link


def draw_text_block(layout, self=None, code='', text='', heading='', heading_icon='ERROR', draw_in_op=False,
                    chars_per_row=50, alert=False) -> UILayout:
    '''wrap a block of text into multiple lines'''
    if draw_in_op:
        chars_per_row = 45
    box = layout.box()
    col = box.column(align=True)
    if alert:
        col.alert = True
    if heading:
        row = col.row(align=True)
        row.label(text=heading, icon=heading_icon)
    for i, txt_row in enumerate(textwrap.wrap(text, chars_per_row)):
        row = col.row(align=True)
        if heading:
            row.label(text=txt_row)
        else:
            row.label(text=txt_row, icon=heading_icon if i == 0 else 'BLANK1')
    if code:
        row = col.row(align=True)
        exec(code)
    return col


def draw_anime_style_eyes(layout, scene=None):
    '''Draw anime eyes layout'''
    draw_split = layout.use_property_split
    draw_dec = layout.use_property_decorate
    row = layout.row(align=True)
    row.prop(scene, "faceit_use_eye_pivots", icon='LIGHT_HEMI')
    if scene.faceit_use_eye_pivots:
        layout.use_property_split = True
        layout.use_property_decorate = False
        # row = layout.row(align=True)
        # row.prop(scene, "faceit_body_armature")
        body_rig = scene.faceit_body_armature
        if body_rig:
            row = layout.row(align=True)
            row.prop_search(scene, 'faceit_anime_ref_eyebone_l',
                            body_rig.data, 'bones', text='Left Eye Bone')
            row = layout.row(align=True)
            row.prop_search(scene, 'faceit_anime_ref_eyebone_r',
                            body_rig.data, 'bones', text='Right Eye Bone')
        if scene.faceit_anime_ref_eyebone_l and scene.faceit_anime_ref_eyebone_r:
            col = layout.column(align=True)
            col.operator_context = 'EXEC_DEFAULT'
            row = col.row(align=True)
            if any([n in bpy.data.objects for n in ['eye_locator_L', 'eye_locator_R']]):
                if not scene.show_locator_empties:
                    op = row.operator('faceit.edit_locator_empties', text='Show Locators',
                                      icon='HIDE_ON')
                    op.hide_value = False
                else:
                    op = row.operator('faceit.edit_locator_empties', text='Hide Locators',
                                      icon='HIDE_OFF')
                    op.hide_value = True

                op_remove = row.operator('faceit.edit_locator_empties', text='Remove Locators', icon='X')
                op_remove.remove = True
            else:
                op = row.operator("faceit.generate_locator_empties",
                                  text='Show Pivot Locators', icon='OUTLINER_DATA_EMPTY')
                op.eye_locators = True
                op.teeth_locators = False
                op.jaw_locator = False

    layout.use_property_split = draw_split
    layout.use_property_decorate = draw_dec


def draw_head_targets_layout(layout, scene=None, show_head_action=True):
    if scene is None:
        scene = bpy.context.scene

    split_layout = layout.use_property_split
    layout.use_property_split = True
    layout.use_property_decorate = False
    # row = layout.row(align=True)
    # row.label(text="Head Target")
    head_obj = scene.faceit_head_target_object
    row = layout.row(align=True)
    row.prop(scene, "faceit_head_target_object")
    if head_obj:
        row = layout.row(align=True)
        if head_obj.type == "ARMATURE":
            row.prop_search(scene, "faceit_head_sub_target",
                            head_obj.data, "bones")
        if show_head_action:
            row = layout.row(align=True)
            if scene.faceit_head_action:
                row.prop_search(scene,
                                'faceit_head_action', bpy.data, 'actions', text="Head Action")
                mocap_action = scene.faceit_head_action
                if mocap_action:
                    row.prop(mocap_action, "use_fake_user", text="", icon='FAKE_USER_OFF')
                row.operator('faceit.new_head_action', text="", icon='ADD')
            else:
                row.operator('faceit.new_head_action', text="Create Head Action", icon='ADD')
            # TODO New in UI popups for warnings and tips.
            # split.separator(factor=10)
            # split.label(text="")
        if head_obj.type != "ARMATURE":
            # split = row.split()
            row = layout.row(align=True)
            draw_text_block(
                layout=row,
                text='Choose an Armature for Bone animation!',
                # heading='NOTE'
            )
    layout.use_property_split = split_layout
