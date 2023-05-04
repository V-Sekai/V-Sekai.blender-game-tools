import os,bpy.utils.previews
# icons_dict = bpy.utils.previews.new()
# icons_dir = os.path.join(os.path.dirname(__file__), "icons")
# icons_dict.load("Contiguous", os.path.join(icons_dir, "Contiguous.png"), 'IMAGE')
# icons_dict.load("FillHole", os.path.join(icons_dir, "FillHole.png"), 'IMAGE')
# icons_dict.load("Flip", os.path.join(icons_dir, "Flip.png"), 'IMAGE')
# icons_dict.load("GridCut", os.path.join(icons_dir, "GridCut.png"), 'IMAGE')
# icons_dict.load("QuickBool", os.path.join(icons_dir, "QuickBool.png"), 'IMAGE')
# icons_dict.load("RingArray", os.path.join(icons_dir, "RingArray.png"), 'IMAGE')
# icons_dict.load("SameSize", os.path.join(icons_dir, "SameSize.png"), 'IMAGE')
# icons_dict.load("SameVtxCount", os.path.join(icons_dir, "SameVtxCount.png"), 'IMAGE')
# icons_dict.load("SnapOffCopy", os.path.join(icons_dir, "SnapOffCopy.png"), 'IMAGE')
# icons_dict.load("GroundObjects", os.path.join(icons_dir, "GroundObjects.png"), 'IMAGE')
# icons_dict.load("OriginToBase", os.path.join(icons_dir, "OriginToBase.png"), 'IMAGE')
# icons_dict.load("MatchOrigins", os.path.join(icons_dir, "MatchOrigins.png"), 'IMAGE')
# icons_dict.load("Primitives", os.path.join(icons_dir, "Primitives.png"), 'IMAGE')
# icons_dict.load("ExportSelected", os.path.join(icons_dir, "ExportSelected.png"), 'IMAGE')
# icons_dict.load("MaterialsPanel", os.path.join(icons_dir, "MaterialsPanel.png"), 'IMAGE')

ICONS = {
    "QOL_Contiguous": "Contiguous.png",
    "QOL_FillHole": "FillHole.png",
    "QOL_Flip": "Flip.png",
    "QOL_GridCut": "GridCut.png",
    "QOL_QuickBool": "QuickBool.png",
    "QOL_RingArray": "RingArray.png",
    "QOL_SameSize": "SameSize.png",
    "QOL_SameVtxCount": "SameVtxCount.png",
    "QOL_SnapOffCopy": "SnapOffCopy.png",
    "QOL_GroundObjects": "GroundObjects.png",
    "QOL_OriginToBase": "OriginToBase.png",
    "QOL_MatchOrigins": "MatchOrigins.png",
    "QOL_Primitives": "Primitives.png",
    "QOL_ExportSelected": "ExportSelected.png",
    "QOL_MaterialsPanel": "MaterialsPanel.png",
    "QOL_NewPen": "NewPen.png",
    "QOL_Subdivide": "Subdivide.png",
    "QOL_HandlesVector": "HandlesVector.png",
    "QOL_HandlesFree": "HandlesFree.png",
    "QOL_HandlesAligned": "HandlesAligned.png",
    "QOL_HandlesAuto": "HandlesAuto.png",
    "QOL_Fillet": "Fillet.png",
    "QOL_Chamfer": "Chamfer.png",
    "QOL_UnFillet": "UnFillet.png",}
icons_dict = bpy.utils.previews.new()
icons_dir = os.path.join(os.path.dirname(__file__), "icons")
for icon_id, icon_file in ICONS.items():
    icons_dict.load(icon_id, os.path.join(icons_dir, icon_file), 'IMAGE')