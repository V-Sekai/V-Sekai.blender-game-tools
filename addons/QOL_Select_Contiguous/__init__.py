bl_info = {
    "name": "QOL Select Contiguous",
    "author": "Rico Holmes",
    "version": (1, 0, 8),
    "blender": (3, 20, 0),
    "location": "View3D > Edge menu or Context menu",
    "description": "Select Contiguous",
    "warning": "",
    "wiki_url": "",
    "category": "Select",
    }
import bpy,bmesh,os
from math import degrees
from bpy.props import (IntProperty)

# select contiguous edges
class QOL_SelContiguousEdges(bpy.types.Operator):
    """Select Contiguous Edges"""
    bl_idname = "mesh.qol_contiguous_edges"
    bl_label = "QOL Select Contiguous Edges"
    bl_options = {'REGISTER', 'UNDO'}



    angle: IntProperty(
        name="Angle",
        description="Angle",
        default=30,
        min=0,
        max=360,
        )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        os.system('cls')
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        edges = [e for e in bm.edges if e.select]
        
        if edges:
            for edgex in edges:
                vert_A = origvert_A = edgex.verts[0]
                vert_B = origvert_B = edgex.verts[1]
                if edgex.is_boundary:
                    while True:
                        edges_A = [e for e in vert_A.link_edges if e.select == False and e.is_boundary == True]
                        if edges_A:
                            edges_A[0].select = True
                            vert_B = vert_A
                            vert_A = edges_A[0].other_vert(vert_A)
                        else:
                            break
                    bmesh.update_edit_mesh(obj.data)

                    vert_A = origvert_A
                    vert_B = origvert_B

                    while True:
                        edges_B = [e for e in vert_B.link_edges if e.select == False and e.is_boundary == True]
                        if edges_B:
                            edges_B[0].select = True
                            vert_A = vert_B
                            vert_B = edges_B[0].other_vert(vert_B)
                        else:
                            break
                    bmesh.update_edit_mesh(obj.data)
   


                else:
                    while True:
                        edges_A = [e for e in vert_A.link_edges if e.select == False]
                        if edges_A:
                            angles = []
                            for edge in edges_A:
                                vert_C = edge.other_vert(vert_A)
                                vec_A_C = vert_C.co - vert_A.co
                                vec_B_A = vert_A.co - vert_B.co
                                angle = degrees(vec_B_A.angle(vec_A_C))
                                angles.append(angle)
                            index = angles.index(min(angles))
                            if angles[index] < self.angle:
                                edges_A[index].select = True
                                vert_B = vert_A
                                vert_A = edges_A[index].other_vert(vert_A)
                            else:
                                break
                        else:
                            break
                    bmesh.update_edit_mesh(obj.data)

                    vert_A = origvert_A
                    vert_B = origvert_B
                    while True:
                        edges_B = [e for e in vert_B.link_edges if e.select == False]
                        if edges_B:
                            angles = []
                            for edge in edges_B:
                                vert_C = edge.other_vert(vert_B)
                                vec_B_C = vert_C.co - vert_B.co
                                vec_A_B = vert_B.co - vert_A.co
                                angle = degrees(vec_A_B.angle(vec_B_C))
                                angles.append(angle)
                            index = angles.index(min(angles))
                            if angles[index] < self.angle:
                                edges_B[index].select = True
                                vert_A = vert_B
                                vert_B = edges_B[index].other_vert(vert_B)
                            else:
                                break
                        else:
                            break
                bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}





def menu_func(self, context):
    self.layout.operator(QOL_SelContiguousEdges.bl_idname, text=QOL_SelContiguousEdges.bl_label)

classes = [
        QOL_SelContiguousEdges
        ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()
