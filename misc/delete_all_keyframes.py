# https://blenderartists.org/t/delete-all-animation-data-how-to/622600/5
import bpy

scene = bpy.context.scene
for ob in bpy.context.scene.objects:      
    if ob:    
        ad = ob.animation_data        
        if ad:
            ob.animation_data_clear()
