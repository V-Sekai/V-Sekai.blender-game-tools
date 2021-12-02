
import bpy

from . import draw_utils
from ..core import faceit_utils as futils
from ..landmarks import landmarks_data as lm_data
from .ui import FACEIT_PT_Base


class FACEIT_PT_BaseRig(FACEIT_PT_Base):
    UI_TAB = 'CREATE'


class FACEIT_PT_Landmarks(FACEIT_PT_BaseRig, bpy.types.Panel):
    bl_label = 'Landmarks'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Landmarks'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            return True  # futils.get_object('facial_landmarks')

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        rig = futils.get_faceit_armature(force_original=True)
        landmarks_obj = futils.get_object('facial_landmarks')

        adaption_state = -1

        main_obj = futils.get_main_faceit_object()

        if main_obj:
            adaption_state = 0
        else:
            col = layout.column()
            row = col.row()
            row.alert = True
            op = row.operator('faceit.go_to_tab', text='Can\'t find Main Group. Complete Setup First...')
            op.tab = 'SETUP'

        col = layout.column(align=True)

        if not rig:
            # landmarks setup
            text = 'Generate Landmarks'
            if landmarks_obj:
                state = landmarks_obj.get('state')
                if state:
                    if state == 0:
                        text = 'Locate Chin'
                    elif state == 1:
                        text = 'Scale Height'
                    elif state == 2:
                        text = 'Scale Width'
                    elif state == 3:
                        text = 'Project Landmarks'

                    adaption_state += state

            if adaption_state in range(0, 3):
                row = col.row()
                row.label(text='Landmarks')

                draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/landmarks/')

                col.prop(scene, 'faceit_asymmetric', text='Asymmetry', icon='MOD_MIRROR')
                # col.prop(scene, 'faceit_asymmetric', text='Asymmetry (Experimental)', icon='EXPERIMENTAL')
                op = col.operator('faceit.facial_landmarks', text=text, icon='TRACKER')

            elif landmarks_obj:

                # Return to Landmarks
                row = col.row()
                row.label(text='Return')

                draw_utils.draw_web_link(
                    row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#back-to-landmarks')

                row = col.row(align=True)
                row.operator('faceit.reset_facial_landmarks', icon='BACK')
                row = col.row(align=True)
                row.operator('faceit.edit_landmarks', icon='EDITMODE_HLT')
                row.operator('faceit.finish_edit_landmarks', text='', icon='X')

                # Adapt Landmarks:
                if scene.faceit_asymmetric:
                    row = col.row(align=True)
                    row.label(text='Edit')
                    row = col.row(align=True)
                    row.prop(landmarks_obj.data, 'use_mirror_x', text='', icon='MOD_MIRROR')
                    row.separator()
                    row.operator('faceit.mirror_selected_verts', icon='ARROW_LEFTRIGHT')
                    if context.mode != 'EDIT_MESH':
                        row.enabled = False
                if adaption_state in range(2, 4):
                    # facial projection
                    col.label(text='Landmarks')
                    col.operator('faceit.facial_project', icon='MOD_SHRINKWRAP')
                else:
                    row = col.row()
                    row.label(text='Optional')
                    row = col.row(align=True)

                    if any([n in bpy.data.objects for n in lm_data.locators]):
                        if not scene.show_locator_empties:
                            op = row.operator('faceit.edit_locator_empties', text='Show Locators',
                                              icon='HIDE_ON')
                            op.hide_value = False
                        else:
                            op = row.operator('faceit.edit_locator_empties', text='Hide Locators',
                                              icon='HIDE_OFF')
                            op.hide_value = True

                        op_remove = row.operator('faceit.edit_locator_empties', text='', icon='X')
                        op_remove.remove = True
                    else:
                        row.operator('faceit.generate_locator_empties', icon='EMPTY_DATA')

                    # Generate Rig
                    row = col.row()
                    row.label(text='Generate')

                    draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/')

                    row = col.row()
                    col.operator('faceit.generate_rig', text='Generate Faceit Rig', icon='ARMATURE_DATA')

        else:
            row = col.row()
            row.label(text='Return')

            draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#1-generate-rig')

            row = col.row(align=True)
            op = row.operator('faceit.reset_to_landmarks', icon='BACK')
            row = col.row(align=True)
            row.operator('faceit.edit_landmarks', icon='EDITMODE_HLT')
            row.operator('faceit.finish_edit_landmarks', text='', icon='X')


# START ####################### VERSION 2 ONLY #######################

        if not landmarks_obj and scene.faceit_version == 2:

            col.separator()

            row = col.row(align=True)
            row.prop(scene, 'faceit_use_rigify_armature', icon='ARMATURE_DATA')
            # row = col.row(align=True)
            # row.label(text='Use existing Rigify Armature')

            if scene.faceit_use_rigify_armature:
                row = col.row(align=True)
                row.prop_search(scene, 'faceit_armature', bpy.data, 'objects', text='')

# END ######################### VERSION 2 ONLY #######################


class FACEIT_PT_Rigging(FACEIT_PT_BaseRig, bpy.types.Panel):
    bl_label = 'Rig and Bind'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Rigging'

    faceit_predecessor = 'FACEIT_PT_Landmarks'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            return futils.get_faceit_armature(force_original=True)
            # return futils.get_faceit_armature()

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)

        # rig = futils.get_faceit_armature()
        landmarks_obj = futils.get_object('facial_landmarks')

        # binding
        if futils.get_faceit_armature(force_original=True):

            row = col.row()
            row.label(text='Bind')

            draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#2-bind-weights')

            row = col.row(align=True)
            op = row.operator('faceit.smart_bind', text='Bind', icon='OUTLINER_OB_ARMATURE')

            row = col.row()
            row.label(text='Correct Bind')

            draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#4-corrective-smooth')

            row = col.row()
            op = row.operator('faceit.smooth_correct', icon='MOD_SMOOTH')

# START ####################### VERSION 2 ONLY #######################

        if not landmarks_obj and scene.faceit_version == 2:

            col.separator()

            row = col.row(align=True)
            row.prop(scene, 'faceit_use_rigify_armature', icon='ARMATURE_DATA')
            # row = col.row(align=True)
            # row.label(text='Use existing Rigify Armature')

            if scene.faceit_use_rigify_armature:
                row = col.row(align=True)
                row.prop_search(scene, 'faceit_armature', bpy.data, 'objects', text='')
# END ######################### VERSION 2 ONLY #######################
