import bpy
from mathutils import Vector
from operator import attrgetter
from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy_extras import view3d_utils

from ..rigging import rig_utils
from . import landmarks_data as lm_data
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..core import shape_key_utils as sk_utils


class FACEIT_OT_FacialLandmarks(bpy.types.Operator):
    '''
imports the facial landmark reference and starts the interactive fitting process
1 - set the facial position to chin
2/3 - set width/height of landmark mesh
3 - refine positions by editting the landmarks mesh
    '''

    bl_idname = 'faceit.facial_landmarks'
    bl_label = 'facial_landmarks'
    bl_options = {'UNDO', 'INTERNAL'}

    # @state : the state of landmark fitting
    state: bpy.props.IntProperty(default=0)

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return futils.get_main_faceit_object()

    def __init__(self):
        # for right/left click query
        self.mouse_select = None
        self.mouse_deselect = None
        # safety counter needed as a workaround for multitrigger events
        self.safety_timer = 3
        # initial cursor position to scale with mouse movement
        self.initial_mouse_scale = 0
        # to check if the scale has been initialized
        self.set_init_scale = False
        # the initial dimensions used abort scaling operation
        self.initial_dimensions = (0, 0, 0)

    def cancel(self, context):
        print('cancel')
        context.preferences.themes[0].view_3d.vertex_size = context.scene.faceit_vertex_size

    def execute(self, context):

        scene = context.scene

        if context.object:
            if not futils.get_hide_obj(context.object):  # context.object.hide_viewport == False:
                bpy.ops.object.mode_set(mode='OBJECT')

        # create the collection that holds faceit objects
        faceit_collection = futils.get_faceit_collection()

        futils.clear_object_selection()
        main_obj = futils.get_main_faceit_object()
        futils.set_active_object(main_obj.name)
        # frame the object to be rigged
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                override = context.copy()
                override['area'] = area
                bpy.ops.view3d.view_selected(use_all_regions=False)
                bpy.ops.view3d.view_axis(override, type='FRONT')
                shading = area.spaces.active.shading
                shading.type = 'SOLID'
                shading.show_xray = False
                shading.show_xray_wireframe = False
                break

        # load the landmarks object
        filepath = fdata.get_landmarks_file()

        # load the objects data in the file
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            data_to.objects = data_from.objects

        # add the objects in the scene
        for obj in data_to.objects:
            if obj.type == 'MESH':
                if scene.faceit_asymmetric:
                    if obj.name == 'facial_landmarks_asymmetric':
                        faceit_collection.objects.link(obj)
                        lm_obj = futils.get_object('facial_landmarks_asymmetric')
                    else:
                        bpy.data.objects.remove(obj)
                else:
                    if obj.name == 'facial_landmarks':
                        faceit_collection.objects.link(obj)
                        lm_obj = futils.get_object('facial_landmarks')
                    else:
                        bpy.data.objects.remove(obj)
        lm_obj.name = 'facial_landmarks'

        futils.clear_object_selection()
        futils.set_active_object(lm_obj.name)

        # initialize the state prop
        if lm_obj:
            if not hasattr(lm_obj, '["state"]'):
                lm_obj['state'] = self.state

        self.reset_scale(context)

        return {'FINISHED'}

    def reset_scale(self, context):
        obj = futils.get_object('facial_landmarks')
        face_obj = futils.get_main_faceit_object()

        if hasattr(obj, '["state"]'):
            if obj['state'] == 0:
                obj.dimensions[2] = face_obj.dimensions[2]/2
                obj.scale = [obj.scale[2], obj.scale[2], obj.scale[2]]
            else:
                mw = face_obj.matrix_world
                # get the global coordinates
                global_v_co = [mw @ v.co for v in face_obj.data.vertices]
                # get the highest point in head mesh (temple)
                v_highest = max([co.z for co in global_v_co])
                # get distance from chin to temple
                head_height = obj.location[2] - v_highest
                # apply scale
                obj.dimensions[2] = head_height
                obj.scale = [obj.scale[2], obj.scale[2], obj.scale[2]]

    def set_face_pos(self, context, event):
        obj = futils.get_object('facial_landmarks')
        if not obj:
            return
        _region = context.region
        _region_3d = context.space_data.region_3d
        coord = 0, event.mouse_region_y
        obj.location = view3d_utils.region_2d_to_location_3d(_region, _region_3d, coord, obj.location)
        obj.location[0] = 0
        obj.location[1] = 0

    def set_face_scale(self, context, event, axis=2):

        obj = bpy.data.objects.get('facial_landmarks')
        if obj == None:
            return

        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        _region = context.region
        _region_3d = context.space_data.region_3d
        mouse_pos = view3d_utils.region_2d_to_origin_3d(_region, rv3d, coord)

        # initialize reference scale
        if not self.set_init_scale:
            # get the initial dimensions before altering - used to reset
            self.initial_dimensions = obj.dimensions[:]
            # set the initial relative mouse position for scaling
            self.initial_mouse_scale = mouse_pos[axis] - obj.dimensions[axis]

            self.set_init_scale = True

        # get the distance from initial mouse
        face_dim = mouse_pos[axis] - self.initial_mouse_scale
        # apply the dimension on x axis
        obj.dimensions[axis] = face_dim

    # modal operations depending on current state
    def modal(self, context, event):
        obj = futils.get_object('facial_landmarks')
        if not obj:
            self.report({'WARNING'}, 'No landmarks object, could not finish')
            return {'CANCELLED'}

        # safety counter needed as a workaround for multitrigger events
        if self.safety_timer >= 0:
            self.safety_timer = self.safety_timer - 1

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:  # 'MIDDLEMOUSE'
            # allow navigation
            return {'PASS_THROUGH'}

        # modal operations: move, scale height, scale width
        if event.type == 'MOUSEMOVE':
            if obj['state'] == 0:
                self.set_face_pos(context, event)
            elif obj['state'] == 1:
                self.set_face_scale(context, event, axis=2)
            elif obj['state'] == 2:
                self.set_face_scale(context, event, axis=0)

        # go into next state / finish
        elif event.type == self.mouse_select and event.value == 'RELEASE':

            if obj['state'] == 0:
                obj['state'] = 1
                self.set_init_scale = False
                # scale to the right dimensions:
                self.reset_scale(context)
                futils.set_active_object(obj.name)
                # frame the object to be rigged
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        override = context.copy()
                        override['area'] = area
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                        bpy.ops.view3d.view_axis(override, type='FRONT')
                        break
                self.safety_timer = 3

            if obj['state'] == 1 and self.safety_timer <= 0:
                self.set_init_scale = False
                obj['state'] = 2
                self.safety_timer = 3

            if obj['state'] == 2 and self.safety_timer <= 0:
                final_mat = obj.matrix_world
                obj.matrix_world = final_mat
                futils.set_active_object(obj.name)
                obj['state'] = 3

                # Make big vertices
                context.preferences.themes[0].view_3d.vertex_size = 8
                # enable vertex selection only
                context.tool_settings.mesh_select_mode = (True, False, False)
                bpy.ops.object.mode_set(mode='EDIT')
                return {'FINISHED'}

        # go into previous state / cancel
        elif event.type in {self.mouse_deselect, 'ESC'} and event.value == 'RELEASE':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.preferences.themes[0].view_3d.vertex_size = context.scene.faceit_vertex_size

            if self.safety_timer <= 0:
                if obj['state'] == 0:
                    bpy.data.objects.remove(obj)
                    return {'CANCELLED'}
                if obj['state'] == 2:
                    self.set_init_scale = False
                if obj['state'] > 0:
                    obj['state'] = obj['state'] - 1
                self.safety_timer = 3

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.execute(context)

        context.scene.tool_settings.use_snap = False

        # first time launch
        # get mouse selection from user pref
        self.mouse_deselect = 'RIGHTMOUSE'
        self.mouse_select = 'LEFTMOUSE'

        if futils.get_mouse_select() == 'RIGHT':
            self.mouse_select = 'RIGHTMOUSE'
            self.mouse_deselect = 'LEFTMOUSE'

        self.set_face_pos(context, event)
        # get the vertex size user settings - reset after face adaption
        context.scene.faceit_vertex_size = context.preferences.themes[0].view_3d.vertex_size
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class FACEIT_OT_ResetFacial(bpy.types.Operator):
    '''	Discard Landmarks and start over '''
    bl_idname = 'faceit.reset_facial_landmarks'
    bl_label = 'Reset Landmarks'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        # if bpy.data.objects.get('facial_landmarks'):
        return True

    def execute(self, context):
        obj = futils.get_object('facial_landmarks')
        # delete face
        if obj != None:
            bpy.data.objects.remove(obj)

        # Remove locators
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', remove=True)

        context.preferences.themes[0].view_3d.vertex_size = context.scene.faceit_vertex_size
        return {'FINISHED'}


class FACEIT_OT_SetThemeVertexSize(bpy.types.Operator):
    '''	Resets the vertex size to the given value @vertex_size '''
    bl_idname = 'faceit.set_theme_vertex_size'
    bl_label = 'Set Vertex Size'
    bl_options = {'UNDO', 'INTERNAL'}

    vertex_size: FloatProperty(
        name='Vertex Size',
        default=3.0,

    )

    def execute(self, context):

        context.preferences.themes[0].view_3d.vertex_size = self.vertex_size
        return{'FINISHED'}


class FACEIT_OT_ProjectFacial(bpy.types.Operator):
    '''Project facial markers '''
    bl_idname = 'faceit.facial_project'
    bl_label = 'Project Landmarks'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        if bpy.data.objects.get('facial_landmarks'):
            return True

    def get_far_point(self, obj, direction):
        # world matrix
        mat = obj.matrix_world
        far_distance = 0
        far_point = direction

        for v in obj.data.vertices:
            point = mat @ v.co
            temp = direction.dot(point)
            # new high?
            if far_distance < temp:
                far_distance = temp
                far_point = point
        return far_point

    def execute(self, context):

        scene = context.scene

        proj_obj = futils.get_object('facial_landmarks')
        if proj_obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # duplicate the object
        bpy.ops.object.select_all(action='DESELECT')
        futils.set_active_object(proj_obj.name)

        # get the face object
        surface_obj = futils.get_main_faceit_object()
        # move in front of face
        if surface_obj:
            proj_obj.location.y = self.get_far_point(
                obj=surface_obj, direction=Vector((0, -1, 0)))[1] - proj_obj.dimensions[1]
        else:
            self.report({'ERROR'}, 'Faceit was not able to find a MAIN object. Did you register it properly?')
            return{'CANCELLED'}

        # projection modifier
        mod = proj_obj.modifiers.new(name='ShrinkWrap', type='SHRINKWRAP')
        mod.target = surface_obj
        mod.wrap_method = 'PROJECT'
        mod.use_project_y = True
        mod.use_positive_direction = True
        mod.show_on_cage = True
        # apply the modifier
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # go to edit mode and refine the positions1

        # Go to Side view
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                override = bpy.context.copy()
                override['area'] = area
                bpy.ops.view3d.view_selected(use_all_regions=False)
                bpy.ops.view3d.view_axis(override, type='RIGHT')
                break

        chin_vert = 0 if scene.faceit_asymmetric else 1
        obj_origin = proj_obj.matrix_world @ proj_obj.data.vertices[chin_vert].co
        context.scene.cursor.location = obj_origin
        proj_obj['state'] = 4
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        scene.tool_settings.use_snap = True
        scene.tool_settings.snap_elements = {'FACE'}
        scene.tool_settings.snap_target = 'CLOSEST'
        scene.tool_settings.use_snap_project = True

        bpy.ops.ed.undo_push()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        return {'FINISHED'}


class FACEIT_OT_MirrorSelectedVerts(bpy.types.Operator):
    '''Mirror selected Landmarks Vertices - In case MirrorX fails'''
    bl_idname = 'faceit.mirror_selected_verts'
    bl_label = 'Mirror Selected Vertices'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    mirror_dir: bpy.props.EnumProperty(
        items=[
            ('L_R', 'Left to Right', 'left to right side mirror (x+ -> x-)'),
            ('R_L', 'Right to Left', 'right to left side mirror (x- -> x+)'),
        ],
        name='Mirror Direction'
    )

    @classmethod
    def poll(self, context):
        if context.object.name == 'facial_landmarks' and context.mode == 'EDIT_MESH':
            return True

    def execute(self, context):

        obj = futils.get_object('facial_landmarks')
        bpy.ops.object.mode_set(mode='OBJECT')
        mirror_dict = lm_data.landmarks_mirror_vertices_dict
        m_world = obj.matrix_world
        m_loc = m_world.inverted()

        left_verts_indices = mirror_dict.keys()
        left_verts = [v for v in obj.data.vertices if v.index in left_verts_indices]
        right_verts_indices = mirror_dict.values()
        right_verts = [v for v in obj.data.vertices if v.index in right_verts_indices]
        selected_verts = [v for v in obj.data.vertices if v.select]

        if all(v in left_verts for v in selected_verts):
            self.mirror_dir = 'L_R'
        elif all(v in right_verts for v in selected_verts):
            self.mirror_dir = 'R_L'
        else:
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, 'Select either Left or Right Side Vertices')
            return{'FINISHED'}

        for left_vert, right_vert in zip(left_verts, right_verts):
            if self.mirror_dir == 'L_R':
                if not left_vert.select:
                    continue
                mirror_co = left_vert.co @ m_world
                mirror_co[0] = mirror_co[0] * -1
                right_vert.co = mirror_co @ m_loc
            else:
                if not right_vert.select:
                    continue
                mirror_co = right_vert.co @ m_world
                mirror_co[0] = mirror_co[0] * -1
                left_vert.co = mirror_co @ m_loc

        bpy.ops.object.mode_set(mode='EDIT')
        return{'FINISHED'}


class FACEIT_OT_EditLocatorEmpties(bpy.types.Operator):
    '''	Edit Locator Empties visibility or remove'''
    bl_idname = 'faceit.edit_locator_empties'
    bl_label = 'Show Locator Empties'
    bl_options = {'UNDO', 'INTERNAL'}

    remove: BoolProperty(
        name='Remove All',
        default=False,
        options={'SKIP_SAVE'}
    )

    hide_value: BoolProperty(
        name='Hide/Show',
        default=False,
        options={'SKIP_SAVE'}
    )

    @classmethod
    def poll(self, context):
        return True
        # return any([n in bpy.data.objects for n in lm_utils.locators])

    def execute(self, context):

        for n in lm_data.locators:
            loc_obj = futils.get_object(n)
            if loc_obj:
                if self.remove:
                    bpy.data.objects.remove(loc_obj, do_unlink=True)
                    continue
                futils.set_hidden_state_object(loc_obj, self.hide_value, self.hide_value)
                # loc_obj.hide_viewport = self.hide_value

        if self.remove:
            context.scene.show_locator_empties = True
        else:
            context.scene.show_locator_empties = not self.hide_value

        return {'FINISHED'}


class FACEIT_OT_GenerateLocatorEmpties(bpy.types.Operator):
    '''	Create empties at relevant locations to be used as new target for the bones in creating the rig '''
    bl_idname = 'faceit.generate_locator_empties'
    bl_label = 'Create Locator Empties'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT' and bpy.data.objects.get('facial_landmarks')
        # return True

    def execute(self, context):
        lm_obj = futils.get_object('facial_landmarks')
        faceit_collection = futils.get_faceit_collection(force_access=True, create=False)
        if not faceit_collection:
            return

        faceit_objects = futils.get_faceit_objects_list()

        # Remove Empties that exist already
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', remove=True)

        futils.clear_object_selection()

        def create_empty_from_bounds(name, bounds, position):
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = 'PLAIN_AXES'
            faceit_collection.objects.link(obj)
            obj.location = position
            size = (bounds[0].z - bounds[1].z)/2
            obj.empty_display_size = size
            obj.show_name = True
            obj.select_set(state=True)
            obj.show_in_front = True

        # ----------------- LEFT EYE LOCATOR --------------------

        vgroup_name = 'faceit_left_eyeball'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            # Get vertices
            vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs = [obj.matrix_world @ v.co for v in vs]

            bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
            pos = futils.get_median_pos(bounds)

            create_empty_from_bounds('eye_locator_L', bounds, pos)

        else:
            self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        # ----------------- RIGHT EYE LOCATOR --------------------

        vgroup_name = 'faceit_right_eyeball'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            # Get vertices
            vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs = [obj.matrix_world @ v.co for v in vs]

            bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
            pos = futils.get_median_pos(bounds)

            create_empty_from_bounds('eye_locator_R', bounds, pos)
        else:
            self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        # ----------------- TEETH UPPER LOCATOR --------------------

        vgroup_name = 'faceit_upper_teeth'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            # Get vertices
            vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs = [obj.matrix_world @ v.co for v in vs]

            bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
            bounds.append(min(global_vs, key=attrgetter('y')))

            pos = futils.get_median_pos(bounds)
            pos.x = 0

            create_empty_from_bounds('teeth_upper_locator', bounds, pos)
        else:
            self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        # ----------------- TEETH UPPER LOCATOR --------------------

        vgroup_name = 'faceit_lower_teeth'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            # Get vertices
            vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs = [obj.matrix_world @ v.co for v in vs]

            bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
            bounds.append(min(global_vs, key=attrgetter('y')))

            pos = futils.get_median_pos(bounds)
            pos.x = 0

            create_empty_from_bounds('teeth_lower_locator', bounds, pos)
        else:
            self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        # ----------------- TONGUE LOCATORS --------------------
        # | - 3 Tongue bones distributed between tip and rear
        # ------------------------------------------------------

        # # apply same offset to all tongue bones
        # tip_tongue = rig_utils.get_median_position_from_vert_grp('faceit_tongue')
        # if tip_tongue:
        #     vec = l_mat @ tip_tongue - edit_bones['tongue'].head
        #     for b in vert_dict[108]['all']:
        #         bone = edit_bones[b]
        #         bone.translate(vec)
        # else:
        #     self.report({'WARNING'}, 'could not find tongue,   define teeth group first!')
        #     for b in vert_dict[108]['all']:
        #         bone = edit_bones[b]
        #         edit_bones.remove(bone)

        # tongue_0 = futils.get_object('tongue_0_locator')
        # if tongue_0:
        #     bpy.data.objects.remove(tongue_0)
        # tongue_1 = futils.get_object('tongue_1_locator')
        # if tongue_1:
        #     bpy.data.objects.remove(tongue_1)
        # tongue_2 = futils.get_object('tongue_2_locator')
        # if tongue_2:
        #     bpy.data.objects.remove(tongue_2)

        # vgroup_name = 'faceit_tongue'
        # obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        # if obj:

        #     # Get vertices
        #     vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
        #     global_vs = [obj.matrix_world @ v.co for v in vs]

        #     position = min(global_vs, key=attrgetter('y'))
        #     # bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
        #     # bounds.extend(rig_utils.get_bounds_from_locations(global_vs, 'y'))
        #     for i in range(3):

        #     eye_R_empty = bpy.data.objects.new('teeth_lower_locator', None)
        #     eye_R_empty.empty_display_type = 'PLAIN_AXES'
        #     faceit_collection.objects.link(eye_R_empty)
        #     eye_R_empty.location = position

        #     up_dim = (bounds[0].z - bounds[1].z)/2
        #     eye_R_empty.empty_display_size = up_dim  # (up_dim,)*3

        return {'FINISHED'}


class FACEIT_OT_ResetToLandmarks(bpy.types.Operator):
    '''Go back to editing the landmarks'''
    bl_idname = 'faceit.reset_to_landmarks'
    bl_label = 'Back to Landmarks'
    bl_options = {'UNDO', 'INTERNAL'}

    keep_weights: BoolProperty(
        name='Keep Binding Weights',
        description='Keep all Binding Vertex Groups to Restore with the Rig',
        default=False,
    )

    keep_expressions: BoolProperty(
        name='Keep Expressions',
        description='Keep all generated expressions.',
        default=False,
    )

    keep_corrective_shape_keys: BoolProperty(
        name='Keep Corrective Shape Keys',
        description='Keep all corrective Shape Keys and try to apply them on a new expression.',
        default=True,
    )

    expressions_generated = False
    rig_bound = False
    corr_sk = False

    @classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature()

        if rig and context.mode == 'OBJECT' and rig.hide_viewport == False:
            return True

    def invoke(self, context, event):
        if context.scene.faceit_expression_list:
            self.expressions_generated = True
        rig = futils.get_faceit_armature()
        if rig:
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
            all_registered_objects_vgroups = vg_utils.get_vertex_groups_from_objects()
            if any(grp in deform_groups for grp in all_registered_objects_vgroups):
                self.rig_bound = True

        self.corr_sk = any([sk_name.startswith('faceit_cc_')
                            for sk_name in sk_utils.get_shape_key_names_from_objects()])

        if self.expressions_generated or self.rig_bound:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout

        row = layout.row()

        if self.expressions_generated:
            row.prop(self, 'keep_expressions')
        if self.rig_bound:
            row.prop(self, 'keep_weights')
        if self.corr_sk:
            row = layout.row()
            row.prop(self, 'keep_corrective_shape_keys')

    def execute(self, context):
        scene = context.scene

        sh_action = bpy.data.actions.get('faceit_shape_action')
        ow_action = bpy.data.actions.get('overwrite_shape_action')
        if self.keep_expressions:
            if sh_action:
                sh_action.use_fake_user = True
            if ow_action:
                ow_action.use_fake_user = True
            context.scene.faceit_expressions_restorable = True

        else:
            if sh_action:
                bpy.data.actions.remove(sh_action)
            if ow_action:
                bpy.data.actions.remove(ow_action)
            context.scene.faceit_expression_list.clear()
            context.scene.faceit_expressions_restorable = False

        if self.corr_sk:
            faceit_objects = futils.get_faceit_objects_list()

            # Keep corrective shape keys

            corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys', None)

            for obj in faceit_objects:

                if sk_utils.has_shape_keys(obj):
                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name.startswith('faceit_cc_'):
                            # mute corrective shapes!
                            if self.keep_corrective_shape_keys:
                                sk.mute = True
                                scene.faceit_corrective_sk_restorable = True
                            else:
                                obj.shape_key_remove(sk)
                                scene.faceit_corrective_sk_restorable = False

                    if obj.data.shape_keys.animation_data:
                        if obj.data.shape_keys.animation_data.action == corrective_sk_action:
                            obj.data.shape_keys.animation_data.action = None

                    if len(obj.data.shape_keys.key_blocks) == 1:
                        obj.shape_key_clear()

        bpy.ops.faceit.unbind_facial(remove_deform_groups=not self.keep_weights)
        scene.faceit_weights_restorable = self.keep_weights
        # remove rig
        rig = futils.get_faceit_armature()
        bpy.data.objects.remove(rig)

        # turn on landmarks visibility
        lm = bpy.data.objects.get('facial_landmarks')
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', hide_value=False)

        if lm:
            futils.set_hidden_state_object(lm, False, False)
        else:
            self.report({'WARNING'}, 'Landmarks mesh does not exist anymore.')

        scene.faceit_vertex_size = context.preferences.themes[0].view_3d.vertex_size
        context.preferences.themes[0].view_3d.vertex_size = 8

        # if bpy.app.version >= (2, 83, 0):
        bpy.ops.outliner.orphans_purge()
        return{'FINISHED'}


class FACEIT_OT_EditLandmarks(bpy.types.Operator):
    '''Edit the landmarks'''
    bl_idname = 'faceit.edit_landmarks'
    bl_label = 'Edit Landmarks'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bpy.data.objects.get('facial_landmarks')

    def execute(self, context):
        scene = context.scene

        # turn on landmarks visibility
        lm = bpy.data.objects.get('facial_landmarks')
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', hide_value=False)

        if lm:
            futils.set_hidden_state_object(lm, False, False)
        else:
            self.report({'WARNING'}, 'Landmarks mesh does not exist anymore.')

        scene.faceit_vertex_size = context.preferences.themes[0].view_3d.vertex_size
        context.preferences.themes[0].view_3d.vertex_size = 8

        futils.set_active_object(lm.name)
        bpy.ops.object.mode_set(mode='EDIT')

        # if bpy.app.version >= (2, 83, 0):
        # bpy.ops.outliner.orphans_purge()
        return{'FINISHED'}


class FACEIT_OT_FinishEditLandmarks(bpy.types.Operator):
    '''Edit the landmarks'''
    bl_idname = 'faceit.finish_edit_landmarks'
    bl_label = 'Edit Landmarks'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.object.name == 'facial_landmarks' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        scene = context.scene

        lm = bpy.data.objects.get('facial_landmarks')
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', hide_value=True)

        # turn off landmarks visibility
        if lm:
            futils.set_hidden_state_object(lm, True, False)

        context.preferences.themes[0].view_3d.vertex_size = scene.faceit_vertex_size

        bpy.ops.object.mode_set(mode='OBJECT')
        return{'FINISHED'}
