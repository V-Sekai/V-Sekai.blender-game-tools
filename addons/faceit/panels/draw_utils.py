import bpy
import blf
from bpy.types import UILayout, Context
import textwrap


def draw_web_link(layout, link, text_ui='', show_always=False):
    '''Draws a Web @link in the given @layout. Optionally with plain @text_ui'''
    if bpy.context.preferences.addons['faceit'].preferences.web_links or show_always:
        web = layout.operator('faceit.open_web', text=text_ui, icon='QUESTION')
        web.link = link


def wrap_text(text: str, context: Context, in_operator=False):
    # https://gist.github.com/semagnum/b881b3b4d11c1514dac079af5bda8f7f
    return_text = []
    row_text = ''
    system = context.preferences.system
    ui_scale = system.ui_scale
    if in_operator:
        width = 750 * (ui_scale / 2)
    else:
        width = context.region.width
    width = (4 / (5 * ui_scale)) * width
    # dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11)
    # text = "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet."
    line_len = 50
    for word in text.split():
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)
        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word
    if row_text:
        return_text.append(row_text)
    return return_text


def draw_text_block(context: Context, layout: UILayout, text='', heading='', heading_icon='ERROR', alert=False, in_operator=False) -> UILayout:
    '''wrap a block of text into multiple lines'''
    box = layout.box()
    col = box.column(align=True)
    if alert:
        col.alert = True
    if heading:
        row = col.row(align=True)
        row.label(text=heading, icon=heading_icon)
    for txt_row in wrap_text(text, context, in_operator=in_operator):
        row = col.row(align=True)
        row.label(text=txt_row)
    return col


def draw_shapes_action_layout(layout, context, split=True):
    if split:
        row = layout.row()
        sub = row.split(factor=0.4)
        sub.alignment = 'RIGHT'
        sub.label(text="Shapes Action")
    else:
        sub = layout
    sub.template_ID(
        context.scene,
        "faceit_mocap_action",
        new='faceit.new_action',
        unlink='faceit.unlink_shapes_action'
    )


def draw_head_targets_layout(layout: UILayout, scene=None, show_head_action=True):
    if scene is None:
        scene = bpy.context.scene

    split_layout = layout.use_property_split
    layout.use_property_split = True
    layout.use_property_decorate = False
    head_obj = scene.faceit_head_target_object
    row = layout.row(align=True)
    row.prop(scene, "faceit_head_target_object")
    if head_obj:
        row = layout.row(align=True)
        if head_obj.type == "ARMATURE":
            row.prop_search(
                scene,
                "faceit_head_sub_target",
                head_obj.data,
                "bones"
            )
        if show_head_action:
            draw_head_action_layout(layout, head_obj)
    layout.use_property_split = split_layout


def draw_head_action_layout(layout, head_obj):
    row = layout.row()
    sub = row.split(factor=0.4)
    sub.alignment = 'RIGHT'
    sub.label(text="Head Action")
    sub.template_ID(head_obj.animation_data, "action", new='faceit.new_head_action')


def draw_eye_targets_layout(layout: UILayout, context, show_eye_action=True):
    scene = context.scene
    split_layout = layout.use_property_split
    layout.use_property_split = True
    layout.use_property_decorate = False
    row = layout.row(align=True)
    row.prop(scene, "faceit_eye_target_rig")
    eye_rig = scene.faceit_eye_target_rig
    if eye_rig:
        row = layout.row(align=True)
        row.prop_search(
            scene,
            "faceit_eye_L_sub_target",
            eye_rig.data,
            "bones"
        )
        row = layout.row(align=True)
        row.prop_search(
            scene,
            "faceit_eye_R_sub_target",
            eye_rig.data,
            "bones"
        )
        if show_eye_action:
            draw_eye_action_layout(layout, eye_rig)
    layout.use_property_split = split_layout


def draw_eye_action_layout(layout: UILayout, eye_rig):
    row = layout.row()
    sub = row.split(factor=0.4)
    sub.alignment = 'RIGHT'
    sub.label(text="Eyes Action")
    sub.template_ID(eye_rig.animation_data, "action", new='faceit.new_eye_action')


def draw_ctrl_rig_action_layout(layout: UILayout, ctrl_rig):
    row = layout.row()
    sub = row.split(factor=0.4)
    sub.alignment = 'RIGHT'
    sub.label(text="Ctrl Rig Action")
    sub.template_ID(ctrl_rig.animation_data, "action", new='faceit.new_ctrl_rig_action')
