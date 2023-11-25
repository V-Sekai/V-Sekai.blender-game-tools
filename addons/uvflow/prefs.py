import math

from uvflow.addon_utils import Register, Property

from bpy.types import UILayout, Context
from uvflow.operators.op_checker import refresh_checker
from uvflow.operators.op_geo_overlay import UpdateGeoOverlays, set_seam_color
from uvflow.debug.pg import UVEditorDebugOptions
from uvflow.utils.ui_layout import draw_section, draw_section_h


def update_pref(context, func):
    preference_area = context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES'
    if not preference_area:
        func()


class UVFLOW_Preferences:
    ''' Development Settings. '''
    uv_editor_debug: Property.POINTER(UVEditorDebugOptions)

    ''' UV Editor Settings. '''
    uv_editor_alignment: Property.ENUM(
        name="Toggle",
        description="Alignment of the UV Editor relative to the 3D Viewport when using the 'UV Editor' button in the 3d viewport's tool header",
        items=(
            ('VERTICAL', "Left", "Split 3D Viewport horizontally to add a UV Editor at the left"),
            ('HORIZONTAL', "Bottom", "Split 3D Viewport vertically to add a UV Editor at the bottom"),
            ('WINDOW', "New Window", "Opens the UV Editor in a new window rather than splitting the 3D view"),
        ),
        default='VERTICAL'
    )

    ''' UVMap Settings. '''
    use_seam_layers: Property.BOOL(
        name="Seams Per UV Map",
        default=True,
        description="Save different seams for each UV map"
    )

    ''' Overlay Settings. '''
    use_overlays: Property.BOOL(
        name="Use Overlays",
        default=False,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run) or refresh_checker(ctx)
    )
    checker_pattern: Property.ENUM(
        name = 'Pattern',
        description = 'The type of the uv grid to apply to the material',
        items = [
            ('NONE', 'None', "No checker texture is applied"),
            ('SIMPLE_LIGHT', 'Simple Light', "A light checker pattern that's not distracting"),
            ('SIMPLE_DARK', 'Simple Dark', "A dark checker pattern that's not distracting"),
            ('SIMPLE_BLUE', 'Simple Blue', "A blue checker pattern that's not distracting"),
            ('SIMPLE_PINK', 'Simple Pink', "A pink checker pattern that's not distracting"),
            ('CRAFT_DIAMOND', 'Craft Diamond', "A pixellated diamond pattern"),
            ('UV_GRID', 'Blender Grid', "Blender's default grey uv grid"),
            ('COLOR_GRID', 'Blender Color Grid', "Blender's default colorful uv grid")
        ],
        default = 'UV_GRID',
        update=lambda ts, ctx: refresh_checker(ctx)
    )
    checker_custom_resolution: Property.INT_VECTOR(
        name = 'Resolution',
        description = 'The pixel resolution of the uv grid',
        max = 7680,
        subtype = 'XYZ',
        size = 2,
        default = [1024, 1024],
        update=lambda ts, ctx: refresh_checker(ctx)
    )
    checker_preset_resolution: Property.ENUM(
        name = 'Resolution',
        description = 'The pixel resolution of the uv grid',
        items = [
            ('512', '512p', 'A square 512x512 grid'),
            ('1080', '1080p', 'A square 1080x1080 grid'),
            ('4096', '4096p', 'A square 4096x4096 grid')
        ],
        default = '1080',
        update=lambda ts, ctx: refresh_checker(ctx)
    )
    face_highlight: Property.ENUM(
        name = 'Face Color',
        items = [
            ('NONE', 'None', 'No color is applied to the faces of the mesh'),
            ('ANGLE', 'Angle Stretching', 'The amount of stretching based on the angle of the edges'),
            ('AREA', 'Area Stretching', 'The amount of stretching based on the relative size of each face'),
            ('UDIM', 'UDIMs', 'A random color is applied per UDIM tile'),
        ],
        default = 'NONE',
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    udim_seed: Property.INT(
        name = 'Random Seed',
        default = 0,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    use_seam_highlight: Property.BOOL(
        name = 'Solidify',
        default = True,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    seam_color: Property.COLOR_RGB(
        name = 'Color',
        subtype = 'COLOR',
        default = [0.708376, 0.0185, 0.006049],
        update=lambda self, ctx: set_seam_color(ctx)
    )
    seam_brightness: Property.FLOAT(
        name = 'Brightness',
        soft_min = 1,
        soft_max = 25,
        default = 5,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    seam_size: Property.FLOAT(
        name = 'Size',
        min=0.001,
        max = 15,
        default = 3,
        step = 0.5,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    use_pin_highlight: Property.BOOL(
        name = 'Chonky Pins',
        default = False,
        update=lambda self, ctx: update_pref(ctx, UpdateGeoOverlays.run)
    )
    pin_color: Property.COLOR_RGB(
        name = 'Color',
        subtype = 'COLOR',
        default = [1, 0, 1],
        # update=lambda ts, ctx: update_overlays(ctx) if ts.use_overlays else None
    )
    pin_brightness: Property.FLOAT(
        name = 'Brightness',
        soft_min = 0,
        soft_max = 15,
        default = 10,
        # update=lambda ts, ctx: update_overlays(ctx) if ts.use_overlays else None
    )
    pin_size: Property.FLOAT(
        name = 'Size',
        subtype = 'DISTANCE',
        min = 0.0001,
        max = 1,
        default = 0.01,
        # update=lambda ts, ctx: update_overlays(ctx) if ts.use_overlays else None
    )

    ''' Unwrap Settings. '''
    use_auto_unwrap: Property.BOOL(
        name="Auto Unwrap",
        default=False,
        description="Unwrap every time a seam is added or removed. Disable if performance is slow"
    )
    unwrap_method: Property.ENUM(
        name="Method",
        items=(
            ("ANGLE_BASED", "Angle Based", ""),
            ("CONFORMAL", "Conformal", ""),
        ),
        default="ANGLE_BASED"
    )
    alignment_obj: Property.BOOL(
        name="Align Bounds",
        default=True,
        description="Aligns the islands to the U or V axis after unwrapping"
    )
    alignment_edit: Property.ENUM(
        name="Align",
        items=(
            ('NONE', 'None', 'No alignment is applied to the island after unwrapping'),
            ('BOUNDS', 'Bounding Box', "Each island's bounding box is aligned after unwrapping. Best of unwrapping lots of islands at once"),
            ('EDGE', 'Active Edge', "Any island connected to the active edge is aligned based on the active edge. Best when unwrapping one island at a time")
        ),
        default='BOUNDS'
    )
    fill_holes: Property.BOOL(
        name="Fill Holes",
        default=True,
        description="Virtually fill holes before packing to better preserve symmetry and avoid overlaps"
    )
    correct_aspect: Property.BOOL(
        name="Texture Aspect",
        default=True,
        description="Take image aspect ratio into account when mapping UVs"
    )
    correct_scale: Property.BOOL(
        name="Scale",
        default=True,
        description="Apply the object scale to the UVs to avoid stretching when the object is scaled non-uniformly"
    )
    use_subdiv: Property.BOOL(
        name="Subdiv",
        default=False,
        description="Map UVs using vertex position after any Subdivision Surface modifier has been applied"
    )
    symmetrize: Property.BOOL(
        name="Symmetrize",
        default=True,
        description="Force the UV map to be symmetrical if the topology supports it"
    )
    use_sharp: Property.BOOL(
        name="Sharp",
        default=False,
    )
    use_bevel: Property.BOOL(
        name="Bevel",
        description="Weight used by the Bevel modifier",
        default=False,
    )
    edge_bevel_weight: Property.FLOAT(
        name="Bevel Threshold",
        description="Any edge with a bevel weight greater than this value will be marked as a seam",
        default=0.0, min=0.0, max=1
    )
    use_crease: Property.BOOL(
        name="Crease",
        description="Weight used by the Subdivision Surface modifier for creasing",
        default=False,
    )
    edge_crease_weight: Property.FLOAT(
        name="Crease Threshold",
        description="Any edge with a crease greater than this value will be marked as a seam",
        default=0.0, min=0.0, max=1
    )
    use_angle: Property.BOOL(
        name = 'Angle',
        description="The edge angle between 2 connected faces",
        default=False,
    )
    edge_angle: Property.FLOAT(
        name="Edge Angle",
        description="The edge angle between 2 connected faces (negative values for concave join). A value of 0.0 means disabled",
        subtype='ANGLE',
        default=0.78, min=-math.pi, max=math.pi
    )
    use_freestyle_mark: Property.BOOL(
        name="Freestyle Mark",
        description="Edge mark for Freestyle line rendering",
        default=False,
    )
    create_seams: Property.BOOL(
        name="Mark Seams",
        description="Marks any split edges as seams while unwrapping. This does not need to be enabled in order for the below options to act like seams",
        default=False
    )

    ''' Pack Settings. '''
    use_auto_pack: Property.BOOL(default=False, name="Auto Pack")

    edit_pack_includes: Property.ENUM(
        name="Include",
        items=(
            ("FACES", "Selected Faces", "Packs only the selected faces"),
            ("OBJECT", "Selected Objects", "Packs all faces of any object the selection is a part of"),
            ("SELECT_MATERIAL", "Selected Materials", "Packs all faces of all objects belonging to the materials included in the selection")
        ),
        default="FACES"
    )
    object_pack_includes: Property.ENUM(
        name="Include",
        items=(
            ("ACTIVE_MATERIAL", "Active Material", "Packs faces of all objects assigned to the currently active material"),
            ("OBJECT", "Selected Objects", "Packs all faces of all selected objects"),
            ("OBJECT_MATERIAL", "Selected Materials", "Packs all faces of all materials belonging to the selection")
        ),
        default="OBJECT"
    )
    pack_together: Property.ENUM(
        name="Group",
        items=(
            ("ALL", "All Together", "Packs all included faces into the same UV space"),
            ("MATERIAL", "By Material", "Packs all included faces together that share the same material"),
            ("OBJECT", "By Object", "Packs all included faces together that are part of the same object")
        ),
        default="MATERIAL"
    )
    pack_to: Property.ENUM(
        name="Pack To",
        items=(
            ("ACTIVE_UDIM", "Active UDIM", "Packs each island to active UDIM tile or the closest one to the 2D cursor"),
            ("CLOSEST_UDIM", "Closest UDIM", "Packs each island to the closest UDIM tile"),
            ("ORIGINAL_AABB", "Original Bounding Box", "Packs each island to its original space")
        ),
        default="CLOSEST_UDIM"
    )
    average_scale: Property.BOOL(
        name="Average Scale",
        description='Average island scale before packing for uniform texel density',
        default=True
    )
    rotation: Property.ENUM(
        name="Rotation",
        items=(
            ("ANY", "Any", "Any angle is allowed for rotation. Best for the tightest possible packing but worse for drawing pixel perfect lines"),
            ("CARDINAL", "Cardinal", "Only 90 degree rotations are allowed. Best for when the UVs are already straigtened"),
            ("AXIS_ALIGNED", "Axis Aligned", "Rotates the shell to fit the smallest vertical or horizontal rectangle. Best for when the UVs have not been straightened"),
            ("NONE", "None", "No rotation is allowed")
        ),
        default="CARDINAL"
    )
    pack_method: Property.ENUM(
        name="Shape",
        items=(
            ("AABB", "Bounds", "Packs based on the bounding box of each island. Fast, but not very accurate"),
            ("CONVEX", "Convex", "Packs based on the outer shape of each island, ignoring cavities and holes. Medium speed and accuracy"),
            ("CONCAVE", "Concave", "Packs based on the exact shape of each island. Accurate but slow")
        ),
        default="AABB"
    )
    margin: Property.FLOAT(
        name="Amount",
        default=1.6,
        description="""Amount of space between the UV islands as a percentage of the overall image resolution.
            The default of 1.6% is a good compromize between maximizing space and avoiding artifacts during real time rendering""",
        subtype="PERCENTAGE",
        min=0,
        soft_max=10,
        max=100
    )
    margin_method: Property.ENUM(
        name="Method",
        items=(
            ("ADD", "Fast", "Calculates margin quickly based on the scale of the UVs"),
            ("FRACTION", "Exact", "Precisely calculates margin in proportion to the UV space unit square")
        ),
        default="ADD"
    )
    merge_overlapping: Property.BOOL(
        name="Merge Overlapping",
        description="Packs overlapping islands as one. Helpful for mirrored UVs laid directly on top of each other",
        default=False
    )
    lock_pinned: Property.ENUM(
        name="Lock Pinned",
        items=(
            ("LOCKED", "Location, Rotation, and Scale", "Entirely locks pinned islands"),
            ("ROTATION_SCALE", "Rotation and Scale", "Prevents the island from rotating or scaling but allows it to mvoe"),
            ("ROTATION", "Rotation", "Locks only the rotation of the island"),
            ("SCALE", "Scale", "Locks only the scale of the island"),
            ("NONE", "None", "Pinned islands are not locked")
        ),
        default="NONE"
    )

    ''' Dropdown Menus '''
    show_editor_options: Property.BOOL(
        name = 'UV Editor',
        default=False
    )
    show_uv_map_options: Property.BOOL(
        name = 'UV Maps',
        default=False
    )
    show_overlay_options: Property.BOOL(
        name = 'Overlays',
        default = False
    )
    show_uvmap_options: Property.BOOL(
        name = 'UV Maps',
        default = False
    )
    show_unwrap_options: Property.BOOL(
        name = 'Unwrapping',
        default = False
    )
    show_packing_options: Property.BOOL(
        name = 'Packing',
        default = False
    )
    show_developer_options: Property.BOOL(
        name = 'Developer Extras',
        default = False
    )
    show_cutuv_tool_options: Property.BOOL(
        name = 'CutUV Tool Options',
        default = False
    )

    # ----------------------------------------------------------------
    # TOOL ADDITIONAL SETTINGS.

    use_frame_select_uvs: Property.BOOL(
        name="Frame Selection",
        description="When double clicking on a face:\nFrame the selected UVs.\n(Only if a UV Editor is opened)",
        default=True
    )

    use_sync_select_uvs: Property.BOOL(
        name="Sync Selection (View 3D -> UV Editor)",
        description="When double clicking on a face:\nPropagate the 3D viewport selection to the UV editor\n(Only if a UV Editor is opened)",
        default=True
    )

    # ----------------------------------------------------------------

    @property
    def use_split(self) -> bool:
        return self.use_bevel or self.use_angle or self.use_crease or self.use_sharp or self.use_freestyle_mark

    @staticmethod
    def get_prefs(context: Context) -> 'UVFLOW_Preferences':
        return context.preferences.addons[__package__].preferences

    def dropdown_icon(self, is_showing):
        return "DOWNARROW_HLT" if is_showing else "RIGHTARROW_THIN"

    def draw_auto_unwrap_prefs(self, layout, context: Context):
        col = layout.column()
        col.use_property_split=True
        col.use_property_decorate=False
        col.prop(self, 'use_auto_unwrap')

    def draw_unwrap_prefs(self, layout, context: Context):
        col = layout.column()
        col.use_property_split=True
        col.use_property_decorate=False
        # col.label(text='Unwrap')
        col.prop(self, 'unwrap_method')
        if context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES':
            col.prop(self, 'alignment_obj', text='Object Mode Alignment')
            col.prop(self, 'alignment_edit', text='Edit Mode Alignment')
        else:
            if context.mode == 'OBJECT':
                col.prop(self, 'alignment_obj')
            else:
                col.prop(self, 'alignment_edit')
        col.prop(self, 'fill_holes')
        # col.prop(prefs, 'symmetrize')

    def draw_split_seams_prefs(self, layout):
        col = layout.column()
        col.use_property_split=True
        col.use_property_decorate=False
        col.label(text='Split')
        col.prop(self, 'create_seams')

    def draw_split_prefs(self, layout):
        split = layout.column()
        split.use_property_split=True
        split.use_property_decorate=False
        _row = split.row(align=True, heading="Angle")
        _row.prop(self, 'use_angle', text='')
        _row.prop(self, 'edge_angle', text='')
        _row = split.row(align=True, heading="Bevel")
        _row.prop(self, 'use_bevel', text='')
        _row.prop(self, 'edge_bevel_weight', text='')
        _row = split.row(align=True, heading="Crease")
        _row.prop(self, 'use_crease', text='')
        _row.prop(self, 'edge_crease_weight', text='')
        split.prop(self, 'use_sharp', text="Sharp")
        split.prop(self, 'use_freestyle_mark', text='Freestyle Mark')

    def draw_unwrap_apply_prefs(self, layout):
        apply = layout.column()
        apply.use_property_split=True
        apply.use_property_decorate=False
        apply.label(text='Apply')
        apply.prop(self, 'correct_scale')
        apply.prop(self, 'use_subdiv')
        apply.prop(self, 'correct_aspect')

    def draw_packing_prefs(self, layout, context: Context):
        layout.use_property_split=True
        layout.use_property_decorate=False
        # layout.label(text='Pack')
        # layout.prop(self, 'use_auto_pack')
        if context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES':
            layout.prop(self, 'object_pack_includes', text='Object Mode Include')
            layout.prop(self, 'edit_pack_includes', text='Edit Mode Include')
        else:
            if context.mode == 'OBJECT':
                layout.prop(self, 'object_pack_includes')
            else:
                layout.prop(self, 'edit_pack_includes')
        layout.prop(self, 'pack_together')
        layout.prop(self, 'pack_method')
        layout.separator()
        layout.label(text='Transform')
        layout.prop(self, 'pack_to')
        layout.prop(self, 'merge_overlapping')
        layout.prop(self, 'lock_pinned')
        layout.prop(self, 'average_scale')
        layout.prop(self, 'rotation')
        layout.separator()
        margin = layout.column()
        margin.use_property_split=True
        margin.use_property_decorate=False
        margin.label(text='Margin')
        layout.prop(self, 'margin', slider=True)
        layout.row().prop(self, 'margin_method', expand=True)
        layout.separator()

    def draw_overlay_enable_prefs(self, layout, context: Context):
        row = layout.row()
        row.prop(self, 'use_overlays')

    def draw_seam_prefs(self, layout, context: Context):
        enabled =  self.use_overlays == True or context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES'
        layout.use_property_split=True
        layout.use_property_decorate=False
        layout.label(text='Seams')
        layout.prop(self, 'seam_color')
        col = layout.column()
        col.enabled = enabled
        col.use_property_split=True
        col.use_property_decorate=False
        col.prop(self, 'use_seam_highlight')
        if self.use_seam_highlight:
            col.prop(self, 'seam_size')
            col.prop(self, 'seam_brightness', slider=True)
        layout.separator()

    def draw_texture_prefs(self, layout, context: Context):
        enabled =  self.use_overlays == True or context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES'
        col = layout.column()
        col.enabled = enabled
        col.use_property_split=True
        col.use_property_decorate=False
        col.label(text='Checker Texture')
        col.prop(self, 'checker_pattern')
        if self.checker_pattern in ['UV_GRID', 'COLOR_GRID']:
            col.prop(self, 'checker_custom_resolution')
        layout.separator()

    def draw_face_overlay_prefs(self, layout, context: Context):
        enabled =  self.use_overlays == True or context.area.type == 'PREFERENCES' or context.space_data.type == 'PREFERENCES'
        col = layout.column()
        col.enabled = enabled
        col.use_property_split=True
        col.use_property_decorate=False
        col.label(text='UV Info')
        col.prop(self, 'face_highlight')
        if self.face_highlight == 'UDIM':
            col.prop(self, 'udim_seed')
        layout.separator()


    def draw_ui(self, context: Context, layout: UILayout) -> None:
        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_editor_options', emboss=False, icon = self.dropdown_icon(self.show_editor_options))
        if self.show_editor_options:
            box = layout.box()
            content = box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            content.prop(self, 'uv_editor_alignment')
            content.label(text='3D View Cut UV Island Select')
            content.prop(self, 'use_frame_select_uvs', text='Frame-Select UVs')
            content.prop(self, 'use_sync_select_uvs', text='Sync-Select UVs')

        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_uv_map_options', emboss=False, icon = self.dropdown_icon(self.show_uv_map_options))
        if self.show_uv_map_options:
            box = layout.box()
            content = box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            content.prop(self, 'use_seam_layers')

        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_overlay_options', emboss=False, icon = self.dropdown_icon(self.show_overlay_options))
        if self.show_overlay_options:
            overlay_box = layout.box()
            content = overlay_box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            self.draw_overlay_enable_prefs(content, context)
            self.draw_seam_prefs(content, context)
            self.draw_texture_prefs(content, context)
            # self.draw_face_overlay_prefs(content, context)

        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_unwrap_options', emboss=False, icon = self.dropdown_icon(self.show_unwrap_options))
        if self.show_unwrap_options:
            unwrap_box = layout.box()
            content = unwrap_box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            content.prop(self, 'use_auto_unwrap')
            self.draw_unwrap_prefs(content, context)
            self.draw_split_seams_prefs(content)
            self.draw_split_prefs(content)
            self.draw_unwrap_apply_prefs(content)

        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_packing_options', emboss=False, icon = self.dropdown_icon(self.show_packing_options))
        if self.show_packing_options:
            packing_box = layout.box()
            content = packing_box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            content.separator()
            self.draw_packing_prefs(content, context)

        '''
        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_cutuv_tool_options', text='CutUV Tool Extras', emboss=False, icon=self.dropdown_icon(self.show_cutuv_tool_options))
        if self.show_cutuv_tool_options:
            content = layout.column()
            _sub = draw_section(content, 'Double-Clicking a Face will...', icon='FACE_MAPS')
            _sub.prop(self, 'use_frame_select_uvs', text='Frame-Select UVs')
            _sub.prop(self, 'use_sync_select_uvs', text='Sync-Select UVs')
        '''

        header = layout.row()
        header.alignment = 'LEFT'
        header.prop(self, 'show_developer_options', emboss=False, icon = self.dropdown_icon(self.show_developer_options))
        if self.show_developer_options:
            box = layout.box()
            content = box.column()
            content.use_property_split=True
            content.use_property_decorate=False
            content.prop(self.uv_editor_debug, 'enabled')


# Register preferences but preserve the class typing.
Register.PREFS.GENERIC(UVFLOW_Preferences)
