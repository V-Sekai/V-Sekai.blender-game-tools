import bpy
import webbrowser


class LicenseButton(bpy.types.Operator):
    bl_idname = 'rsl.info_license'
    bl_label = 'License'
    bl_description = 'Opens the license in the browser'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        webbrowser.open('https://github.com/fire/skeletal-motion-retarget-blender/blob/main/LICENSE.md')
        self.report({'INFO'}, 'Opened license.')
        return {'FINISHED'}
