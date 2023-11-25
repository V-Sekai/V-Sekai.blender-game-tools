from uvflow.addon_utils import Register, Property

from .draw_handler import UVEDITOR_DrawHandler

from bpy.types import Context


@Register.PROP_GROUP.CHILD
class UVEditorDebugOptions:
    def tag_redraw(self, context: Context) -> None:
        context.area.tag_redraw()


    enabled: Property.BOOL(
        name="Use UV Editor Debug",
        description="Enable debug visualization in the UV editor",
        default=False,
        update=lambda debug, ctx: UVEDITOR_DrawHandler.start(ctx, debug) and debug.tag_redraw(ctx) if debug.enabled else UVEDITOR_DrawHandler.stop()
    )

    show_island_border: Property.BOOL(
        name="Show island border",
        default=False,
        update=tag_redraw
    )
    
    show_sel_loop: Property.BOOL(
        name="Show Selected Loop",
        default=False,
        update=tag_redraw
    )

    show_linked_loops: Property.BOOL(
        name="Show Linked Loops",
        default=False,
        update=tag_redraw
    )

    show_link_loop_next: Property.BOOL(
        name="Show Link Loop Next",
        default=False,
        update=tag_redraw
    )

    show_link_loop_prev: Property.BOOL(
        name="Show Link Loop Prev",
        default=False,
        update=tag_redraw
    )

    show_link_loop_radial_next: Property.BOOL(
        name="Show Link Loop Radial Next",
        default=False,
        update=tag_redraw
    )

    show_link_loop_radial_prev: Property.BOOL(
        name="Show Link Loop Radial Prev",
        default=False,
        update=tag_redraw
    )

    show_seams: Property.BOOL(
        name="Show Seams",
        default=False,
        update=tag_redraw
    )

    show_indices: Property.ENUM(
        name="Show Indices",
        items=(
            ('VERT', 'Vert', "", 'UV_VERTEXSEL', 0),
            ('EDGE', 'Edge', "", 'UV_EDGESEL', 1),
            ('FACE', 'Face', "", 'UV_FACESEL', 2),
            # ('LOOP', 'Loop', "", 'MOD_EDGESPLIT', 3),
        ),
        default='VERT',
        # options={'ENUM_FLAG'},
        update=tag_redraw
    )
