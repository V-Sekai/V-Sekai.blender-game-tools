import bpy
from bpy.app.handlers import persistent
from .osc_receiver import osc_queue
from .osc_operators import live_animator, receiver

update_queries = 60
queries_per_second = 200


def process_osc_queue():
    '''runs persistent and processes all incoming messages.'''
    global osc_queue
    if osc_queue and receiver.enabled:
        anim_list = osc_queue[:-update_queries:-1]
        for _ in range(update_queries):
            if not anim_list:
                break
            else:
                data = anim_list.pop()
                live_animator.process_data(data)
        return 1 / queries_per_second
    return .01


@persistent
def close_osc_on_scene_save(self, context):
    # abort live connection, don't write data.
    bpy.ops.faceit.receiver_cancel()


def register():
    bpy.app.handlers.save_pre.append(close_osc_on_scene_save)
    bpy.app.handlers.load_pre.append(close_osc_on_scene_save)
    bpy.app.timers.register(process_osc_queue, persistent=True)


def uregister():
    bpy.app.timers.unregister(process_osc_queue)
    bpy.app.handlers.save_pre.remove(close_osc_on_scene_save)
    bpy.app.handlers.load_pre.remove(close_osc_on_scene_save)
