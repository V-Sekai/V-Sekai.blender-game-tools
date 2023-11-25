from uvflow.gpu.handler import DrawHandler
from uvflow.utils.editor_uv import get_uv_editor
from uvflow.gpu import idraw

from collections import defaultdict

from bpy.types import SpaceImageEditor, Context, SpaceUVEditor
import bmesh
from bmesh.types import BMesh, BMVert, BMEdge, BMFace, BMLoop, BMLoopUV
from bpy_extras import bmesh_utils
from mathutils import Vector


_bm_instance = None


class UVEDITOR_DrawHandler:
    @classmethod
    def start(cls, *args):
        DrawHandler.start_2d_no_op('UVEDITOR_DEBUG', SpaceImageEditor, cls.draw_debug, *args)

    @classmethod
    def stop(cls):
        DrawHandler.stop_no_op('UVEDITOR_DEBUG', SpaceImageEditor)

    @staticmethod
    def draw_debug(context: Context, debug_options):
        if context.mode != 'EDIT_MESH':
            return
        if context.area.ui_type != 'UV':
            return

        uv_editor = get_uv_editor(context.window)
        if uv_editor is None:
            # NOTE: Should be disabled automatically?
            # and re-enabled when the UVEditor is available again?
            # OR probably would make our timer more dirty with debug stuff...
            # which would require another inifite timer just for debug stuff
            # which is not ideal at all (probably a global toggle to control that timer???).
            return

        for reg in uv_editor.regions:
            if reg.type == 'WINDOW':
                break

        view2d = reg.view2d

        global _bm_instance
        if _bm_instance is not None and isinstance(_bm_instance, BMesh) and _bm_instance.is_valid:
            bm = _bm_instance
        else:
            bm = bmesh.from_edit_mesh(context.active_object.data)
            _bm_instance = bm

        bm_faces: list[BMFace] = bm.faces
        uv_layer = bm.loops.layers.uv.active
        bm_loops: list[BMLoop] = [l for f in bm_faces for l in f.loops]
        bm_loop_uvs: list[tuple[BMLoop, BMLoopUV]] = [(l, l[uv_layer]) for l in bm_loops]

        selected_loop_uvs: list[tuple[BMLoop, BMLoopUV]] = [(loop, loop_uv) for (loop, loop_uv) in bm_loop_uvs if loop_uv.select]

        ## print(type(debug_options), dir(debug_options))

        ''' SHOW ISLAND BORDER. '''
        if debug_options.show_island_border:
            # Find a target island and it's loops
            uv_islands: tuple[tuple[BMFace]] = bmesh_utils.bmesh_linked_uv_islands(bm, uv_layer)
            for island_faces in uv_islands:
                # act_face = bm.faces.active
                # if bm.faces.active in island_faces:
                #     break

                for face in island_faces:
                    for loop in face.loops:
                        loop_uv: BMLoopUV = loop[uv_layer]
                        if loop_uv.select:
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

            island_loops: list[BMLoop] = [loop for face in island_faces for loop in face.loops]

            # Get border loops on the island
            border_loops = []
            for loop in island_loops:
                loops = (loop, loop.link_loop_radial_next)

                if (loops[0] == loops[1]
                    or loops[1].face not in island_faces
                    or loops[0][uv_layer].uv != loops[1].link_loop_next[uv_layer].uv
                    or loops[1][uv_layer].uv != loops[0].link_loop_next[uv_layer].uv):

                    border_loops.append(loop)

            # Get border UV coordinates and select UV edges.
            border_uv_coords: list[Vector] = [0]*len(border_loops)
            for i, loop in enumerate(border_loops):
                border_uv_coords[i] = loop[uv_layer].uv

            # print(border_uv_coords)

            # Transpose UV coordinates to region coordinates.
            reg_uv_coords = [0]*len(border_loops)
            for i, uv in enumerate(border_uv_coords):
                reg_uv_coords[i] = view2d.view_to_region(*uv, clip=False)
                # reg_uv_coords[i] = (
                #     proj_size.x * uv.x + A.x,
                #     proj_size.y * uv.y + A.y
                # )

            # print(reg_size, proj_size, A, B)
            # print(reg_uv_coords)

            # Draw line border.
            idraw.line_2d(reg_uv_coords, loop=True, line_thickness=1.0, color=(1, 1, 0, .64))


        ''' SHOW LINKED LOOPS. (from selected loops) '''
        if debug_options.show_linked_loops:
            for (loop, loop_uv) in selected_loop_uvs:
                for lk_loop in loop.link_loops:
                    lk_loop_uv: BMLoopUV = lk_loop[uv_layer]
                    idraw.line_2d(
                        (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                        line_thickness=2.0, color=(1, 0, 1, .64))

        '''
        if debug_options.show_link_loop_next:
            for (loop, loop_uv) in selected_loop_uvs:
                lk_loop_uv: BMLoopUV = loop.link_loop_next[uv_layer]
                idraw.line_2d(
                    (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                    line_thickness=2.0, color=(.5, .2, .8, .5))

        if debug_options.show_link_loop_prev:
            for (loop, loop_uv) in selected_loop_uvs:
                lk_loop_uv: BMLoopUV = loop.link_loop_prev[uv_layer]
                idraw.line_2d(
                    (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                    line_thickness=2.0, color=(.5, .2, .2, .5))

        if debug_options.show_link_loop_radial_next:
            for (loop, loop_uv) in selected_loop_uvs:
                lk_loop_uv: BMLoopUV = loop.link_loop_radial_next[uv_layer]
                idraw.line_2d(
                    (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                    line_thickness=2.0, color=(.8, .2, .5, .5))

        if debug_options.show_link_loop_radial_prev:
            for (loop, loop_uv) in selected_loop_uvs:
                lk_loop_uv: BMLoopUV = loop.link_loop_radial_prev[uv_layer]
                idraw.line_2d(
                    (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                    line_thickness=2.0, color=(.2, .2, .5, .5))
        '''

        ''' SHOW SEAMS. '''
        if debug_options.show_seams:
            for loop in bm_loops:
                if loop.edge.seam:
                    loop_uv = loop[uv_layer]
                    lk_loop_uv = loop.link_loop_next[uv_layer]
                    idraw.line_2d(
                        (view2d.view_to_region(*loop_uv.uv, clip=False), view2d.view_to_region(*lk_loop_uv.uv, clip=False)),
                        line_thickness=2.0, color=(0, 1, 1, .5))

        draw_prim: dict[int, int] = defaultdict(int)
        if debug_options.show_indices:
            show_vert_indices = 'VERT' == debug_options.show_indices
            show_edge_indices = 'EDGE' == debug_options.show_indices
            show_face_indices = 'FACE' == debug_options.show_indices

            # show_loop_indices = 'LOOP' in debug_options.show_indices
            for loop in bm_loops:
                text = 'Loop: %i' % loop.index

                if show_vert_indices:
                    if not loop.vert.select:
                       continue 
                    text += (', Vert: %i' % loop.vert.index)
                    q = draw_prim[loop.vert.index]
                    draw_prim[loop.vert.index] += 1
                    
                if show_edge_indices:
                    if not loop.edge.select:
                       continue 
                    text += (', Edge: %i' % loop.edge.index)
                    q = draw_prim[loop.edge.index]
                    draw_prim[loop.edge.index] += 1
                    
                if show_face_indices:
                    if not loop.face.select:
                       continue 
                    text += (', Face: %i' % loop.face.index)
                    q = draw_prim[loop.face.index]
                    draw_prim[loop.face.index] += 1
                    

                loop_uv = loop[uv_layer]
                idraw.text(
                    Vector(view2d.view_to_region(*loop_uv.uv, clip=False)) + Vector((0, q * 12)),
                    text,
                    12,
                    (1, 1, 1, 1)
                )

        if debug_options.show_sel_loop and selected_loop_uvs != []:
            sel_count = len(selected_loop_uvs)
            f = 1 / sel_count * 0.5
            for i, (loop, loop_uv) in enumerate(selected_loop_uvs):
                edge = loop.edge
                vert = loop.vert
                other_vert = edge.other_vert(vert)
                if loop.link_loop_next.vert == other_vert:
                    other_loop = loop.link_loop_next
                else:
                    other_loop = loop.link_loop_prev
                other_loop_uv = other_loop[uv_layer]
                idraw.arrow_2d(
                    Vector(view2d.view_to_region(*other_loop_uv.uv, clip=False)),
                    Vector(view2d.view_to_region(*loop_uv.uv, clip=False)),
                    8, 8, 1.5,
                    (1, f * i + .2, .68, 1.0))
