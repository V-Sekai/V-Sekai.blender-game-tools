import bpy

import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Button, Grid2D
from bl_xr.utils import get_mesh_mode, apply_haptic_feedback, to_blender_axis_system

from mathutils import Vector

from ..gizmos import toggle_gizmo
from ..utils import set_mode, set_tool, set_default_cursor as set_cursor
from ..settings_manager import settings
from .. import tools, gizmos

SUBMENU_Y_OFFSET = 0.0
SUBMENU_Z_OFFSET = 0.005
BUTTON_SIZE = 0.05
MODE_PANEL_BUTTON_SIZE = BUTTON_SIZE * 2 / 3

submenus = {}


def set_edit_type(type):
    ob = bpy.context.view_layer.objects.active
    if ob and ob.type == "MESH":
        bpy.ops.mesh.select_mode(type=type)

    return True


def set_option(name, value):
    settings[name] = value
    return True


def toggle_option(name):
    settings[name] = not settings.get(name, False)
    return True


def set_transform_space(value):
    bpy.context.scene.transform_orientation_slots[0].type = value


def buzz():
    apply_haptic_feedback(hand="alt")
    return True


def toggle_proportional_edit():
    tool_settings = bpy.context.scene.tool_settings
    tool_settings.use_proportional_edit = not tool_settings.use_proportional_edit
    return True


def reset_world_scale():
    actual_location = xr_session.session_state.viewer_pose_location
    actual_rotation = to_blender_axis_system(xr_session.session_state.viewer_pose_rotation)

    actual_rotation = actual_rotation.to_euler()
    actual_rotation.x = actual_rotation.y = 0
    actual_rotation = actual_rotation.to_quaternion()

    xr_session.session_settings.base_scale = 1
    xr_session.session_settings.base_pose_location = Vector()
    xr_session.session_settings.base_pose_angle = 0

    xr_session.session_state.navigation_scale = 1
    xr_session.session_state.navigation_location = Vector(actual_location)
    xr_session.session_state.navigation_rotation = actual_rotation


Node.STYLESHEET.update(
    {
        ".main_menu_btn": {
            "scale": Vector((BUTTON_SIZE,) * 3),
        },
        ".mode_menu_btn": {
            "scale": Vector((MODE_PANEL_BUTTON_SIZE,) * 3),
        },
    }
)

main_menu = Grid2D(
    id="main_menu",
    class_name="menu_items panel",
    num_cols=2,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/hull.png",
            tooltip="HULL",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.hull") and set_mode("OBJECT") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.hull",
        ),
        Button(
            icon=None,
            class_name="main_menu_btn",
        ),
        Button(
            icon="images/erase.png",
            tooltip="ERASE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("erase") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "erase",
        ),
        Button(
            id="shape",
            icon="images/shape_cube.png",
            tooltip="SHAPE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.shape") and set_mode("OBJECT") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.shape",
        ),
        Button(
            icon="images/select.png",
            tooltip="SELECT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("select") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "select",
        ),
        Button(
            icon="images/pen.png",
            tooltip="PEN",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
            and set_option("stroke.type", "pen")
            and set_mode("OBJECT")
            and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.stroke",
        ),
    ],
)

submenus["PEN"] = Grid2D(
    id="submenu_pen",
    class_name="controller_submenu menu_items",
    num_cols=1,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/straight_line.png",
            tooltip="STRAIGHT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("stroke.straight_line") and buzz(),
            highlight_checker=lambda *x: settings["stroke.straight_line"],
        ),
        Button(
            icon="images/pipe.png",
            tooltip="PIPE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("stroke.type", "pipe") and set_cursor("pipe") and buzz(),
            highlight_checker=lambda *x: settings["stroke.type"] == "pipe",
        ),
        Button(
            icon="images/annotate.png",
            tooltip="ANNOTATE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
            and set_option("stroke.type", "annotation")
            and set_cursor("pen")
            and buzz(),
            highlight_checker=lambda *x: settings["stroke.type"] == "annotation",
        ),
        Button(
            icon="images/pen_thin.png",
            tooltip="PEN",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
            and set_option("stroke.type", "pen")
            and set_cursor("pen")
            and buzz(),
            highlight_checker=lambda *x: settings["stroke.type"] == "pen",
        ),
    ],
)

submenus["SHAPE"] = Grid2D(
    id="submenu_shape",
    class_name="controller_submenu menu_items",
    num_cols=2,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/shape_monkey.png",
            tooltip="MONKEY",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "monkey") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "monkey",
        ),
        Button(
            icon="images/shape_torus.png",
            tooltip="TORUS",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "torus") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "torus",
        ),
        Button(
            icon="images/shape_cylinder.png",
            tooltip="CYLINDER",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cylinder") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cylinder",
        ),
        Button(
            icon="images/shape_cone.png",
            tooltip="CONE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cone") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cone",
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="CUBE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cube") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cube",
        ),
        Button(
            icon="images/shape_sphere.png",
            tooltip="SPHERE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "sphere") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "sphere",
        ),
    ],
)


def on_loop_cut_click():
    if tools.active_tool == "edit_mesh.loop_cut":
        set_tool("select")
    else:
        set_tool("edit_mesh.loop_cut")

    buzz()


def on_merge_click():
    bpy.ops.mesh.merge(type="CENTER")

    bpy.ops.ed.undo_push(message="merge")
    buzz()


def on_make_face_click():
    bpy.ops.mesh.edge_face_add()

    bpy.ops.ed.undo_push(message="make face")
    buzz()


submenus["EDIT"] = Grid2D(
    id="submenu_edit",
    class_name="controller_submenu menu_items",
    num_cols=3,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/edit_loop_cut.png",
            tooltip="LOOP CUT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_loop_cut_click(),
            highlight_checker=lambda *x: tools.active_tool == "edit_mesh.loop_cut",
        ),
        Button(
            icon="images/edit_merge.png",
            tooltip="MERGE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_merge_click(),
        ),
        Button(
            icon="images/edit_make_face.png",
            tooltip="MAKE FACE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_make_face_click(),
        ),
        Button(
            icon="images/edit_bevel.png",
            tooltip="BEVEL",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_gizmo("edit_mesh.bevel") and buzz(),
            highlight_checker=lambda *x: "edit_mesh.bevel" in gizmos.active_gizmos,
        ),
        Button(
            icon="images/edit_inset.png",
            tooltip="INSET",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_gizmo("edit_mesh.inset") and buzz(),
            highlight_checker=lambda *x: "edit_mesh.inset" in gizmos.active_gizmos,
        ),
        Button(
            icon="images/edit_extrude.png",
            tooltip="EXTRUDE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("edit.perform_extrude"),
            highlight_checker=lambda *x: settings["edit.perform_extrude"],
        ),
        Button(
            icon="images/edit_vert.png",
            tooltip="VERT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("VERT") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "VERT",
        ),
        Button(
            icon="images/edit_edge.png",
            tooltip="EDGE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("EDGE") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "EDGE",
        ),
        Button(
            icon="images/edit_face.png",
            tooltip="FACE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("FACE") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "FACE",
        ),
    ],
)


submenus["SELECT"] = Grid2D(
    id="submenu_select",
    class_name="controller_submenu menu_items",
    num_cols=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((-main_menu.bounds_local.max.x * 0.4, SUBMENU_Y_OFFSET, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            id="transform_button",
            icon="images/scale.png",
            tooltip="SCALE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "scale"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "scale",
        ),
        Button(
            id="transform_button",
            icon="images/rotate.png",
            tooltip="ROTATE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "rotate"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "rotate",
        ),
        Button(
            id="transform_button",
            icon="images/translate.png",
            tooltip="MOVE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "translate"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "translate",
        ),
        Button(
            id="transform_button",
            icon="images/select.png",
            tooltip="FREE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", None),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] is None,
        ),
    ],
)

submenus["TRANSFORM_SPACE"] = Grid2D(
    id="submenu_select",
    class_name="controller_submenu menu_items",
    num_cols=2,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((-main_menu.bounds_local.max.x * 0.74, SUBMENU_Y_OFFSET + 0.14, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            id="transform_button",
            icon="images/transform_global.png",
            tooltip="GLOBAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_transform_space("GLOBAL"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and bpy.context.scene.transform_orientation_slots[0].type == "GLOBAL",
        ),
        Button(
            id="transform_button",
            icon="images/transform_local.png",
            tooltip="LOCAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_transform_space("LOCAL"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and bpy.context.scene.transform_orientation_slots[0].type == "LOCAL",
        ),
    ],
)


def toggle_auto_key():
    prev = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = not prev

    return True


def on_key_frame_insert():
    ob = bpy.context.view_layer.objects.active
    ob.keyframe_insert(data_path="location")
    ob.keyframe_insert(data_path="rotation_euler")
    ob.keyframe_insert(data_path="scale")

    return True


def on_prev_frame():
    bpy.context.scene.frame_current -= 1

    return True


def on_next_frame():
    bpy.context.scene.frame_current += 1

    return True


anim_panel = Grid2D(
    id="anim_panel",
    class_name="menu_items panel",
    num_rows=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector((0, 0.035, 0)),
    style={"visible": False},
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/anim_frame_autokey.png",
            tooltip="AUTO KEY",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_auto_key() and buzz(),
            highlight_checker=lambda *x: bpy.context.scene.tool_settings.use_keyframe_insert_auto,
        ),
        Button(
            icon="images/anim_frame_insert.png",
            tooltip="INSERT",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_key_frame_insert() and buzz(),
        ),
        Button(
            icon="images/anim_frame_prev.png",
            tooltip="PREV",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_prev_frame() and buzz(),
        ),
        Button(
            icon="images/anim_frame_next.png",
            tooltip="NEXT",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_next_frame() and buzz(),
        ),
    ],
)

gizmo_panel = Grid2D(
    id="gizmo_panel",
    class_name="panel",
    num_rows=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector(),
    z_offset=0.001,
    child_nodes=[
        Button(
            id="3d_grid_button",
            icon="images/3d_grid.png",
            tooltip="3D GRID",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("3d_grid"),
            highlight_checker=lambda *x: "3d_grid" in gizmos.active_gizmos,
        ),
        Button(
            id="camera_preview_button",
            icon="images/camera.png",
            tooltip="VIEW CAMERA",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("camera_preview"),
            highlight_checker=lambda *x: "camera_preview" in gizmos.active_gizmos,
        ),
        Button(
            id="keyframe_button",
            icon="images/anim_timeline_icon.png",
            tooltip="KEYFRAME",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("joystick_for_keyframe"),
            highlight_checker=lambda *x: "joystick_for_keyframe" in gizmos.active_gizmos,
        ),
        Button(
            id="mirror_button",
            icon="images/mirror.png",
            tooltip="MIRROR",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz()
            and toggle_option("gizmo.mirror.enabled")
            and toggle_gizmo("mirror_plane"),
            highlight_checker=lambda *x: settings["gizmo.mirror.enabled"],
        ),
        Button(
            id="reset_world_scale_button",
            icon="images/scale.png",
            tooltip="RESET SCALE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and reset_world_scale(),
        ),
        Button(
            id="proportional_edit_button",
            icon="images/proportional_edit.png",
            tooltip="PROPORTIONAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_proportional_edit(),
            highlight_checker=lambda *x: bpy.context.scene.tool_settings.use_proportional_edit,
        ),
    ],
)

proportional_edit_button = gizmo_panel.q("#proportional_edit_button")

mirror_panel = Grid2D(
    id="mirror_panel",
    class_name="cmenu_items panel",
    num_cols=3,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((0.135, 0, 0.002)),
    child_nodes=[
        Button(
            icon="images/icon_x.png",
            tooltip="X",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_x"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_x"],
        ),
        Button(
            icon="images/icon_y.png",
            tooltip="Y",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_y"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_y"],
        ),
        Button(
            icon="images/icon_z.png",
            tooltip="Z",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_z"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_z"],
        ),
    ],
)

Node.STYLESHEET.update(
    {
        "#main_menu_group": {
            "fixed_scale": True,
        },
        "#main_menu_panels": {
            "position": Vector((0, 0.035, 0.001)),
        },
        "#3d_grid_button": {
            "position": Vector((0, 0, 0.001)),
        },
        ".controller_submenu": {
            "visible": False,
            "position": Vector((main_menu.bounds_local.max.x, SUBMENU_Y_OFFSET, SUBMENU_Z_OFFSET)),
            "opacity": 0.95,
            "background": (0, 0.005, 0.02, 1),
            "border": (0.002, (0, 0, 0.005, 1)),
            "border_radius": 0.005,
        },
        ".panel": {
            "opacity": 0.95,
            "background": (0, 0.005, 0.02, 1),
            "border": (0.002, (0, 0, 0.005, 1)),
            "border_radius": 0.005,
        },
    }
)

object_mode_btn = Button(
    icon="images/object_mode.png",
    tooltip="OBJECT",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("OBJECT")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "OBJECT",
)
edit_mode_btn = Button(
    icon="images/edit_mode.png",
    tooltip="EDIT",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("EDIT")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "EDIT",
)

pose_mode_btn = Button(
    icon="images/armature.png",
    tooltip="POSE",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("POSE")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "POSE",
)

mode_panel = Grid2D(
    id="mode_panel",
    class_name="menu_items panel",
    num_rows=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector(),
    z_offset=0.001,
    child_nodes=[object_mode_btn, edit_mode_btn, pose_mode_btn],
)
mode_panel.position.y = main_menu.bounds_local.size.y + gizmo_panel.bounds_local.size.y + 0.01


menu_group = Node(
    id="main_menu_group",
    child_nodes=[
        mode_panel,
        Node(
            id="main_menu_panels",
            child_nodes=[main_menu] + list(submenus.values()),
        ),
        anim_panel,
        gizmo_panel,
        mirror_panel,
    ],
)
menu_group.prevent_trigger_events_on_raycast = True
menu_group.style["visible"] = True

submenu_tests = {
    "EDIT": lambda: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "EDIT"
    and bpy.context.view_layer.objects.active.type == "MESH",
    "PEN": lambda: tools.active_tool == "draw.stroke"
    and (not bpy.context.view_layer.objects.active or bpy.context.view_layer.objects.active.mode == "OBJECT"),
    "SHAPE": lambda: tools.active_tool == "draw.shape"
    and (not bpy.context.view_layer.objects.active or bpy.context.view_layer.objects.active.mode == "OBJECT"),
    "SELECT": lambda: tools.active_tool == "select",
    "TRANSFORM_SPACE": lambda: tools.active_tool == "select" and settings["gizmo.transform_handles.type"] is not None,
}
mode_button_tests = {
    "OBJECT": lambda: True,
    "EDIT": lambda: bpy.context.view_layer.objects.active,
    "POSE": lambda: bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.type == "ARMATURE",
}


def on_update(self):
    self.position = xr_session.controller_alt_aim_position
    self.rotation = xr_session.controller_alt_aim_rotation

    for name, submenu in submenus.items():
        visibility_test = submenu_tests[name]
        status = True if visibility_test() else False
        submenu.style["visible"] = status

    for btn in mode_panel.child_nodes:
        btn_name = btn.tooltip.text
        visibility_test = mode_button_tests[btn_name]
        status = True if visibility_test() else False
        btn.style["visible"] = status

    mirror_panel.style["visible"] = settings["gizmo.mirror.enabled"]

    ob = bpy.context.view_layer.objects.active
    proportional_edit_button.style["visible"] = ob and ob.mode == "EDIT" and ob.type == "MESH"


menu_group.update = on_update.__get__(menu_group)


def on_menu_toggle(self, event_name, event):
    menu_group.style["visible"] = not menu_group.style["visible"]


def apply_handedness(hand):
    # mirror the buttons in the main menu
    new_nodes = []
    new_nodes.append(main_menu.child_nodes[0])
    new_nodes.append(main_menu.child_nodes[1])

    for i in range(2, len(main_menu.child_nodes), 2):  # leave the first row alone
        new_nodes.append(main_menu.child_nodes[i + 1])
        new_nodes.append(main_menu.child_nodes[i])

    main_menu.child_nodes.clear()
    main_menu.append_children(new_nodes)

    # move the subpanels to the other side of the main menu
    for submenu in submenus.values():
        p = Vector(submenu.position)
        p.x = main_menu.bounds_local.max.x if hand == "right" else -submenu.bounds_local.max.x
        submenu.position = p


if bl_xr.main_hand != "right":  # assumed "right" while creating the DOM nodes
    apply_handedness(bl_xr.main_hand)


def on_setting_change(self, event_name, change: dict):
    if "app.main_hand" in change:
        apply_handedness(change["app.main_hand"])


def enable():
    root.append_child(menu_group)
    root.add_event_listener("fb.setting_change", on_setting_change)

    root.add_event_listener("button_b_alt_start", on_menu_toggle)


def disable():
    root.remove_child(menu_group)
    root.remove_event_listener("fb.setting_change", on_setting_change)

    root.remove_event_listener("button_b_alt_start", on_menu_toggle)
