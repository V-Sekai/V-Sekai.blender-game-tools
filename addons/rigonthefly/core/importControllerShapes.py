import bpy
import os
import pathlib

def ImportControllerShapes(shapesNameList=list()):
    #print("Importing Controller Shapes")

    for obj in bpy.data.objects:
        if obj.name in shapesNameList :
            shapesNameList.remove(obj.name)

    # Path to the icons folder
    # The path is calculated relative to this py file inside the addon folder
    main_dir = pathlib.Path(os.path.dirname(__file__)).parent.resolve()
    resources_dir = os.path.join(str(main_dir), "resources","controllerShapes")
    controllerShapes_dir = os.path.join(resources_dir, "RotF_ControllerShapes.blend")

    # link all objects starting with 'RotF'
    with bpy.data.libraries.load(controllerShapes_dir, link=False) as data_to:
        data_to[1].objects = [name for name in shapesNameList]
    
    controllerShapesCollection = bpy.data.collections.get("RotF_ControllerShapes")
    if controllerShapesCollection == None:
        controllerShapesCollection = bpy.data.collections.new("RotF_ControllerShapes")
        controllerShapesCollection.hide_render = True

        bpy.context.scene.collection.children.link(controllerShapesCollection) #add controllerShapesCollection to the scene collection to be visible in the outliner

    ImportControllerShapesThicknessGeoNode()

    #link object to current scene
    for obj in data_to[1].objects:
        if obj is not None:
            controllerShapesCollection.objects.link(obj)
            obj.hide_set(True)
            obj.hide_render = True
            #bpy.context.collection.objects.link(obj)
            modifier = obj.modifiers.new(name="RotF_Wireframe_Thickness", type='NODES')
            #modifier.name = "RotF "+ modifier.name
            modifier.node_group = bpy.data.node_groups["RotF_Wireframe_Thickness"]

    #for shapeName in shapesNameList:
    #    collectionList = bpy.data.objects[shapeName].users_collection
    #    for collection in collectionList:
    #        collection.objects.unlink(bpy.data.objects[shapeName])

def ImportControllerShapesThicknessGeoNode():
    # Path to the icons folder
    # The path is calculated relative to this py file inside the addon folder
    main_dir = pathlib.Path(os.path.dirname(__file__)).parent.resolve()
    resources_dir = os.path.join(str(main_dir), "resources","controllerShapes")
    controllerShapes_dir = os.path.join(resources_dir, "RotF_ControllerShapes.blend")

    with bpy.data.libraries.load(controllerShapes_dir, link=False) as (data_from, data_to):
        data_to.node_groups = [name for name in data_from.node_groups if name.startswith("RotF_Wireframe_Thickness")]