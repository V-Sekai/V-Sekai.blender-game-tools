import bpy
from bpy.types import AddonPreferences
from bpy.props import FloatVectorProperty, IntProperty, BoolProperty
import os
from bpy.utils import register_class, unregister_class
from .operators import MESH_OT_ProjectMoveOperator
import numpy as np


def addon_name():
    return os.path.basename(os.path.dirname(os.path.realpath(__file__)))

class ProjectMovePreferences(AddonPreferences):
    """Custom preferences and associated UI for add on properties."""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = addon_name()

    line_color : FloatVectorProperty(name="Preview Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1, .5, 0, 0.8])

    line_thickness : IntProperty(name="Line thickness",
                                description="Thickness of perspective lines",
                                default=1,
                                min=0)

    show_axis : BoolProperty(
        name = "Display Axis Guides",
        description="Display Axis Guids when placing",
        default=False)

    x_axis_color : FloatVectorProperty(name="X Axis Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1, 0, 0, 0.5])


    y_axis_color : FloatVectorProperty(name="Y Axis Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[0, 1, 0, 0.5])


    z_axis_color : FloatVectorProperty(name="Z Axis Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[0, 0, 1, 0.5])

    axis_thickness : IntProperty(name="Line thickness",
                                description="Thickness of perspective line",
                                default=1,
                                min=0)         

    horizon_line_color : FloatVectorProperty(name="Horizon Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1, .5, 0, 0.8])


    horizon_line_thickness : IntProperty(name="Line thickness",
                                description="Thickness of horizon line",
                                default=1,
                                min=0)

    grid_point_color : FloatVectorProperty(name="Grid Point Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1, 1, 1, 0.5])

    grid_point_size : IntProperty(name="Grid Point Size",
                                description="size of grid point",
                                default=8,
                                min=0)



    principal_point_color : FloatVectorProperty(name="Principal Point Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1, .5, 0, 0.8])


    principal_point_size : IntProperty(name="Principal Point thickness",
                                description="Thickness of Principal Point",
                                default=1,
                                min=0)


    measurement_line_color : FloatVectorProperty(name="Measurement Line Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[0, .7, 1, 0.8])


    measurement_line_thickness : IntProperty(name="Line thickness",
                                description="Thickness of horizon line",
                                default=2,
                                min=0)

    sensitivity_axis_point : IntProperty(
        name="Axis Point Sensitivity",
        description="How close to the Axis Point the mouse needs to be",
        default=10,
        subtype='PIXEL',
        min=0
    )

    sensitivity_grid_point : IntProperty(
        name="Grid Point Sensitivity",
        description="How close to the Grid Point the mouse needs to be",
        default=10,
        subtype='PIXEL',
        min=0
    )

    sensitivity_principal_point : IntProperty(
        name="Principal Point Sensitivity",
        description="How close to the Principal Point the mouse needs to be",
        default=10,
        subtype='PIXEL',
        min=0
    )

    sensitivity_measuring_point : IntProperty(
        name="Measuring Point Sensitivity",
        description="How close to the Measuring Point the mouse needs to be",
        default=20,
        subtype='PIXEL',
        min=0
    )

    def draw(self, context):
        layout = self.layout
        # layout.label(text="Colors:")
        col = layout.column()
        col.alignment = 'CENTER'


        box = col.box()
        box.label(text="Axis Display")

        

        box_col = box.column(align=True)
        row = box_col.row(align=True)
        row.label(text='X Axis Line Color:')
        row.prop(self, "x_axis_color", text='')

        row = box_col.row(align=True)
        row.label(text='Y Axis Line Color:')
        row.prop(self, "y_axis_color", text='')

        row = box_col.row(align=True)
        row.label(text='Z Axis Line Color:')
        row.prop(self, "z_axis_color", text='')

        row = box_col.row(align=True)
        row.label(text='Axis Thickness:')
        row.prop(self, "axis_thickness", text='')
        
        box_col.separator()

        row = box_col.row(align=True)
        row.label(text='Horizon Line Color:')
        row.prop(self, "horizon_line_color", text='')

        row = box_col.row(align=True)
        row.label(text='Horizon Line Thickness:')
        row.prop(self, "horizon_line_thickness", text='')

        box_col.separator()
        
        row = box_col.row(align=True)
        row.label(text='Grid Point Color:')
        row.prop(self, "grid_point_color", text='')

        row = box_col.row(align=True)
        row.label(text='Grid Point Size:')
        row.prop(self, "grid_point_size", text='')

        box_col.separator()

        row = box_col.row(align=True)
        row.label(text='Principal Point Color:')
        row.prop(self, "principal_point_color", text='')

        row = box_col.row(align=True)
        row.label(text='Principal Point Size:')
        row.prop(self, "principal_point_size", text='')

        box_col.separator()

        row = box_col.row(align=True)
        row.label(text='Measurement Line Color:')
        row.prop(self, "measurement_line_color", text='')

        row = box_col.row(align=True)
        row.label(text='Measurement Line Thickness:')
        row.prop(self, "measurement_line_thickness", text='')

        box = col.box()
        box.label(text="Move Along View")
        box_col = box.column(align=True)

        kc = context.window_manager.keyconfigs.addon
        km = kc.keymaps['3D View']
        kmis = km.keymap_items
        if MESH_OT_ProjectMoveOperator.bl_idname in km.keymap_items:
            kmi = km.keymap_items[MESH_OT_ProjectMoveOperator.bl_idname]
            row = box_col.row(align=True)
            row.label(text='Keyboard Shortcut:')
            row.prop(kmi, 'type', text='', full_event=True)
        else:
            col.alert = True
            col = box_col.column()
            row = col.row()
            row.alignment = 'CENTER'
            row.label(text="Hotkey entry not found")
            col = col.column()
            row = col.row()
            row.alignment = 'CENTER'
            row.label(text="restore hotkeys from Keymap tab")

            


        row = box_col.row(align=True)
        row.label(text='Line Color:')
        row.prop(self, "line_color", text='')
        row = box_col.row(align=True)
        row.label(text='Line Thickness:')
        row.prop(self, "line_thickness", text='')
        row = box_col.row(align=True)
        row.label(text='Show Axis Guides:')
        row.prop(self, "show_axis", text='')
        
        box = col.box()
        box.label(text="Mouse Sensitivity")
        box_col = box.column(align=True)


        row = box_col.row(align=True)
        row.label(text='Axis Point Sensitivity:')
        row.prop(self, "sensitivity_axis_point", text='')

        row = box_col.row(align=True)
        row.label(text='Grid Point Sensitivity:')
        row.prop(self, "sensitivity_grid_point", text='')

        row = box_col.row(align=True)
        row.label(text='Principal Point Sensitivity:')
        row.prop(self, "sensitivity_principal_point", text='')

        row = box_col.row(align=True)
        row.label(text='Measuring Point Sensitivity:')
        row.prop(self, "sensitivity_measuring_point", text='')



classes = [
    ProjectMovePreferences]


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in classes:
        unregister_class(cls)