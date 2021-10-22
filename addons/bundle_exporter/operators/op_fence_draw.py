import bpy
from mathutils import Vector
import operator

from .. import gp_draw
from .. import bundles


class BGE_OT_fence_draw(bpy.types.Operator):
    """Draws "fences" to visualize bundles"""
    bl_idname = "bge.fence_draw"
    bl_label = "Draw Fences"
    bl_description = "Draw fences around selected bundles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(bpy.context.scene.BGE_Settings.bundles) > 0

    def execute(self, context):

        gp_draw.clear()

        bundle_list = bundles.get_bundles()
        for bundle in bundle_list:
            objects = bundle.objects
            if len(objects) > 0:
                draw_bounds(bundle)

        return {'FINISHED'}


def draw_bounds(bundle):
    bounds = bundle.get_bounds()
    objects = bundle.objects

    padding = bpy.context.scene.BGE_Settings.padding

    pos = bounds.center

    _min = bounds.min
    _max = bounds.max
    _min -= Vector((padding, padding, 0))
    _max += Vector((padding, padding, 0))
    size = _max - _min

    # Bounds
    draw = gp_draw.get_draw()
    draw.add_line(
        [_min + Vector((0, 0, 0)),
         _min + Vector((size.x, 0, 0)),
         _min + Vector((size.x, size.y, 0)),
         _min + Vector((0, size.y, 0)),
         _min + Vector((0, 0, 0))]
    )
    draw.add_line([_min + Vector((0, 0, 0)), _min + Vector((0, 0, padding))])
    draw.add_line([_min + Vector((size.x, 0, 0)), _min + Vector((size.x, 0, padding))])
    draw.add_line([_min + Vector((size.x, size.y, 0)), _min + Vector((size.x, size.y, padding))])
    draw.add_line([_min + Vector((0, size.y, 0)), _min + Vector((0, size.y, padding))])

    bundle_info = bundle.create_bundle_info()
    for x in bundle.modifiers:
        x.process(bundle_info)

    # Draw Text
    label = bundle_info['name']
    if len(objects) > 1:
        label = "{} {}x".format(label, len(objects))
    draw.add_text(label.upper(), _min, padding * 0.5)

    # Draw pole + Flag
    pivot = bundle_info['pivot']

    height = max(padding, size.z) * 2.0
    draw.add_line([Vector((pivot.x, pivot.y, _min.z)), Vector((pivot.x, pivot.y, _min.z + height))], dash=padding * 0.25)
    # Flag
    draw.add_line([
        Vector((pivot.x, pivot.y, _min.z + height - padding)),
        Vector((pivot.x - padding, pivot.y - padding, _min.z + height - padding / 2)),
        Vector((pivot.x, pivot.y, _min.z + height)),
        Vector((pivot.x, pivot.y, _min.z + height - padding))
    ])

    draw.add_circle(pivot, padding, sides=8, alpha=0.4)
    draw.add_line([pivot + Vector((-padding / 2, 0, 0)), pivot + Vector((padding / 2, 0, 0))])
    draw.add_line([pivot + Vector((0, -padding / 2, 0)), pivot + Vector((0, padding / 2, 0))])


class SortedGridAxis:
    groups = []
    bounds = []

    def __init__(self, objects, bounds, axis_var='x'):
        self.groups = [[o] for o in objects]
        self.bounds = [[getattr(bounds[o].min, axis_var), getattr(bounds[o].max, axis_var)] for o in objects]
        # self.setup_gp()

        # Calculate clusters

        for i in range(len(self.groups)):
            # print("i {}. / {}".format(i, len(self.groups)))

            j = 0
            for x in range(len(self.groups)):
                # print("  j {}. / {}".format(j, len(self.groups)))

                if i != j and i < len(self.groups) and j < len(self.groups):
                    g0 = self.groups[i]
                    g1 = self.groups[j]
                    b0 = self.bounds[i]
                    b1 = self.bounds[j]
                    # if g0 not in processed:
                    if self.is_collide(b0[0], b0[1], b1[0], b1[1]):
                        for o in g1:
                            g0.append(o)
                        b0[0] = min(b0[0], b1[0])
                        b0[1] = max(b0[1], b1[1])
                        self.groups.remove(g1)
                        self.bounds.remove(b1)
                        j -= 1
                        # print("    Grp @ {} {} = {}x".format(i, j, len(self.groups)))
                        # break
                        # j-=1
                        # i-=1
                        # processed.append(g0)
                j += 1
            # 	j+=1
            # i+=1

        # print("Final {} x {}".format(len(self.groups), len(self.bounds)))

        # Sort
        values = {(self.bounds.index(b)): (b[0]) for b in self.bounds}
        ordered = sorted(values.items(), key=operator.itemgetter(1))
        if len(self.groups) > 1:
            copy_groups = self.groups.copy()
            copy_bounds = self.bounds.copy()

            index = 0
            for s in ordered:
                # print(".. Sorted {} = {}".format(s[0], s[1]))
                self.groups[index] = copy_groups[s[0]]
                self.bounds[index] = copy_bounds[s[0]]
                index += 1

    def is_collide(self, A_min, A_max, B_min, B_max):
        # One line is inside the other
        length_A = A_max - A_min
        length_B = B_max - B_min
        center_A = A_min + length_A / 2
        center_B = B_min + length_B / 2
        return abs(center_A - center_B) <= (length_A + length_B) / 2
