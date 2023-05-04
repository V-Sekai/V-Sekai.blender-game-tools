import bpy

def setBM(self,context):
    BM_Count = len(context.scene.QOL_BM_DataSets)
    my_item = context.scene.QOL_BM_DataSets.add()
    my_item.name = ("Camera Bookmark_"+str(BM_Count+1))
    my_item.location = context.scene.camera.location
    my_item.rotation_euler = context.scene.camera.rotation_euler
    my_item.scale = context.scene.camera.scale
    my_item.passepartout_alpha = context.scene.camera.data.passepartout_alpha
    my_item.angle_x = context.scene.camera.data.angle_x
    my_item.angle_y = context.scene.camera.data.angle_y
    my_item.clip_start = context.scene.camera.data.clip_start
    my_item.clip_end = context.scene.camera.data.clip_end
    my_item.lens = context.scene.camera.data.lens
    my_item.sensor_width = context.scene.camera.data.sensor_width
    my_item.sensor_height = context.scene.camera.data.sensor_height
    my_item.ortho_scale = context.scene.camera.data.ortho_scale
    my_item.shift_x = context.scene.camera.data.shift_x
    my_item.shift_y = context.scene.camera.data.shift_y


def setVP(self,context):
    BM_Count = len(context.scene.QOL_VP_DataSets)
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D': vp= area.spaces[0].region_3d
    my_item = context.scene.QOL_VP_DataSets.add()
    my_item.name = ("Perspective Bookmark_"+str(BM_Count+1))
    my_item.view_perspective = vp.view_perspective
    my_item.view_camera_zoom = vp.view_camera_zoom
    my_item.view_location = vp.view_location
    my_item.view_rotation = vp.view_rotation
    my_item.view_distance = vp.view_distance
    context.area.tag_redraw()
    vp.update()

def updateBM(self,context,index):
    my_item = context.scene.QOL_BM_DataSets[index]
    my_item.location = context.scene.camera.location
    my_item.rotation_euler = context.scene.camera.rotation_euler
    my_item.scale = context.scene.camera.scale        
    my_item.passepartout_alpha = context.scene.camera.data.passepartout_alpha   
    my_item.angle_x = context.scene.camera.data.angle_x   
    my_item.angle_y = context.scene.camera.data.angle_y   
    my_item.clip_start = context.scene.camera.data.clip_start   
    my_item.clip_end = context.scene.camera.data.clip_end   
    my_item.lens = context.scene.camera.data.lens   
    my_item.sensor_width = context.scene.camera.data.sensor_width   
    my_item.sensor_height = context.scene.camera.data.sensor_height   
    my_item.ortho_scale = context.scene.camera.data.ortho_scale   
    my_item.shift_x = context.scene.camera.data.shift_x   
    my_item.shift_y = context.scene.camera.data.shift_y

def updateVP(self,context,index):
    my_item = context.scene.QOL_VP_DataSets[index]
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D': vp= area.spaces[0].region_3d
    my_item.view_perspective = vp.view_perspective
    my_item.view_camera_zoom = vp.view_camera_zoom
    my_item.view_location = vp.view_location
    my_item.view_rotation = vp.view_rotation
    my_item.view_distance = vp.view_distance   

def ApplyBM(self,context,BMIndex):
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D': vp= area.spaces[0].region_3d
    if vp.view_perspective == "PERSP":
        vp.view_perspective = 'CAMERA'
    BM = bpy.context.scene.QOL_BM_DataSets
    targetBM = BM[BMIndex]
    context.scene.camera.location = targetBM.location
    context.scene.camera.rotation_euler = targetBM.rotation_euler
    context.scene.camera.scale = targetBM.scale 
    context.scene.camera.data.passepartout_alpha = targetBM.passepartout_alpha 
    context.scene.camera.data.angle_x = targetBM.angle_x 
    context.scene.camera.data.angle_y = targetBM.angle_y 
    context.scene.camera.data.clip_start = targetBM.clip_start 
    context.scene.camera.data.clip_end = targetBM.clip_end 
    context.scene.camera.data.lens = targetBM.lens 
    context.scene.camera.data.sensor_width = targetBM.sensor_width 
    context.scene.camera.data.sensor_height = targetBM.sensor_height 
    context.scene.camera.data.ortho_scale = targetBM.ortho_scale 
    context.scene.camera.data.shift_x = targetBM.shift_x 
    context.scene.camera.data.shift_y = targetBM.shift_y
    self.report({'INFO'}, ('Bookmark: ' + targetBM.name))

def ApplyVP(self,context,BMIndex):
    BM = context.scene.QOL_VP_DataSets
    try:
        targetBM = BM[BMIndex]
        for area in bpy.context.screen.areas:   
            if area.type == 'VIEW_3D': vp= area.spaces[0].region_3d

        vp.view_distance = targetBM.view_distance
        vp.view_perspective = targetBM.view_perspective
        vp.view_camera_zoom = targetBM.view_camera_zoom   
        vp.view_location = targetBM.view_location   
        vp.view_rotation = targetBM.view_rotation
        self.report({'INFO'}, ('Bookmark: ' + targetBM.name))
    except:
        pass    
