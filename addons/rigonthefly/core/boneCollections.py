#########################################
#######       Rig On The Fly      #######
####### Copyright © 2023 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

RotFOnlyColName = 'Rig On The Fly Only'
RotFAnimationColName = 'RotF Animation Controls'
#RotFSecondaryColName = 'RotF Secondary Controls'
RotFUnusedColName = 'RotF Hidden'
RotFUnoritentedColName = 'RotF Hidden Unoriented Bones'

RotFSecondaryFKColName = 'RotF Secondary FK Controls'
RotFHiddenFKColName = 'RotF Hidden FK'

RotFHiddenRotDistColName = 'RotF Hidden Rotation Distribution'
RotFSecondaryRotDistColName = 'RotF Secondary Rotation Distribution'


AllRotFBoneCollectionNameList = [
    RotFOnlyColName, 
    RotFAnimationColName, 
    #RotFSecondaryColName, 
    RotFUnusedColName, 
    RotFUnoritentedColName,
    RotFHiddenFKColName,
    RotFSecondaryFKColName,
    RotFHiddenRotDistColName,
    RotFSecondaryRotDistColName
    ]

RotFBaseBoneCollectionNameList = [
    RotFOnlyColName, 
    RotFAnimationColName, 
    #RotFSecondaryColName, 
    RotFUnusedColName
    ]

CollectionsHiddenByDefault = [
    RotFOnlyColName, 
    #RotFAnimationColName, 
    #RotFSecondaryColName, 
    RotFUnusedColName, 
    RotFUnoritentedColName,
    RotFHiddenFKColName,
    RotFSecondaryFKColName,
    RotFHiddenRotDistColName]

def AddBaseBoneCollections(armature):
    noRotFBoneCollections = True
    #print("No RotF bone collections in armature = "+ str(noRotFBoneCollections))
    for RotFCollectionName in RotFBaseBoneCollectionNameList:
        #create collection if they are missing
        collection = armature.collections.get(RotFCollectionName)
        if collection:
            noRotFBoneCollections = False
        else:
            collectionRotF = armature.collections.new(RotFCollectionName)
            
            #hide collection if collection got created and should be hidden by default 
            if RotFCollectionName in CollectionsHiddenByDefault:
                collectionRotF.is_visible = False
            
    #print("No RotF bone collections in armature = "+ str(noRotFBoneCollections))

    #if no RotF collection existed on the armature at the begining of the process, 
    #take all bones in the non-RotF bone collections and move them to the animation bone collection
    """
    if noRotFBoneCollections:
        print("No RotF Bone Collections")
        for boneCollection in armature.collections:
            print(boneCollection.name) 
            if boneCollection.name not in AllRotFBoneCollectionNameList:
                print("Not a RotF Collection")
                boneCollection.is_visible = False

                #add non-RotF bones to the animation bone collection
                for bone in boneCollection.bones:
                    armature.collections[RotFAnimationColName].assign(bone)
    """
def AddBoneToCollections(bone, collectionNameList):
    armature = bone.id_data

    #make sure default collections exist
    AddBaseBoneCollections(armature)

    for collectionName in collectionNameList:
        #create the collection if it is missing
        if collectionName not in armature.collections:
            collectionRotF = armature.collections.new(collectionName)
            
            #hide collection if collection got created and should be hidden by default 
            if collectionName in CollectionsHiddenByDefault:
                collectionRotF.is_visible = False
        
        collection = bone.id_data.collections[collectionName]
        collection.assign(bone)

def UnassignBoneFromCollections(bone, collectionNameList):
    armature = bone.id_data
    for collectionName in collectionNameList:
        armature.collections[collectionName].unassign(bone)

def RemoveEmptyBoneCollection(armature):
    for boneCollectionName in AllRotFBoneCollectionNameList:
        boneCollection = armature.collections.get(boneCollectionName)
        if boneCollection:
            #remove bone collection if it is empty
            if len(boneCollection.bones) == 0:
                armature.collections.remove(boneCollection)

def RemoveRotFBoneCollections(armature):
    for collectionName in AllRotFBoneCollectionNameList:
        if collectionName in armature.collections:
            armature.collections.remove(armature.collections[collectionName])
    
    for collection in armature.collections:
        collection.is_visible = True