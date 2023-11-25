import bpy

edit_modes = [
  'EDIT_MESH',
  'EDIT_CURVE',
  'EDIT_SURFACE'
]

switch = {
  'EDIT_MESH': bpy.ops.object.editmode_toggle,
  'SCULPT': bpy.ops.sculpt.sculptmode_toggle,
  'PAINT_VERTEX': bpy.ops.paint.vertex_paint_toggle,
  'PAINT_WEIGHT': bpy.ops.paint.weight_paint_toggle,
  'PAINT_TEXTURE': bpy.ops.paint.texture_paint_toggle
}


def mode_toggle(context: bpy.types.Context | str, switch_to_mode: str):
  curr_mode = context if isinstance(context, str) else context.mode
  if curr_mode == switch_to_mode:
    return curr_mode
  bpy.ops.object.mode_set(False, mode=switch_to_mode)
  return curr_mode


class CM_ModeToggle:
  def __init__(self, context: bpy.types.Context | str, mode: str) -> None:
    self.prev_mode = context.mode if isinstance(context, bpy.types.Context) else context
    if self.prev_mode == 'EDIT_MESH':
      self.prev_mode = 'EDIT'
    self.mode = mode
    self._skip = self.prev_mode == self.mode

  def __enter__(self):
    if self._skip: return
    mode_toggle(self.prev_mode, self.mode)
  
  def __exit__(self, exc_type, exc_value, trace):
    if self._skip: return
    mode_toggle(self.mode, self.prev_mode)
