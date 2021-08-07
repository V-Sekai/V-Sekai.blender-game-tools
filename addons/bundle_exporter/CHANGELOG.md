# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.3](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_2_3)
### Added
- new "UVs to 0-1 space" modifier. Moves all uv shells to the same "square" keeping their local positions

### Fixed
- error when exporting with an object in edit mode

## [2.2.2](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_2_2)
### Added
- new "Set origin to pivot" modifier
- new unity preset with the bake transforms experimental option enabled

### Fixed
- "Unity Rotation Fix" modifier increased float precission
- "Merge" modifier now takes into account the pivot of the bundle

## [2.2.1](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_2_1)
### Added
- "Unity Rotation Fix" Modifier that fixes rotations missmatch between blender and unity

### Changed
- The default unity FBX preset now has the bake transforms experimental option disabled

## [2.2.0](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_2_0)
### Added
- Option for merge meshes to merge UVs by index instead of by name
- New Pivot option "From Collection" it will get the pivot from the collection instance_offset parameter (Properties->Object->Collection->X,Y,Z)
- New modifiers:
    - Triangulate
    - Export Animations
        - export each action as a separate file
        - disable renaming the actions when exported
    - Purge Bones (lets the user delete or keep specific bones)
    - Collision modifier rework:
        - it will search possible colliders inside the bundle and set them up correctly for unreal engine
        - Option to create colliders:
            - Box: it will create a box collider with the shape of the bounding box for each object in the bundle
            - Decimate: it will create collider the old way (applying decimation modifiers etc)
        - operators:
            - Create box collider from selected object:
                - in object mode, it will cover the entire object
                - in edit mode it will create a collision based on the vertex selection

### Changed
- Modifiers are now displayed in the order they are applied
- Minor UI changes and typos fixed
- default fbx presets don't export animations (it is enabled when adding an export actions modifier)

### Fixed
- Fixed error using the "Export Textures" modifier (it would cause error when finding a texture node without an image applied to it)
- UI stopped working when adding the Master Collection as a bundle (Master Collection bundles are deliberately not supported)
- Exporting to a path that doesnt exists now works (it gets created)

### Removed
- "actions as separate files" modifier (merged into export animations)
- "keep action names" modifier (merged into export animations)

## [2.1.2](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_1_2)
### Fixed
- Unity export preset fixed

## [2.1.1](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_1_1) - 2020-06-03
### Fixed
- Children of objects are now correctly exported (the bundle pivot was being applied to both parents and children)
- Error when drawing fences when "Export actions as files" is active
- Objects hidden in the view layer are now correclty exported

### Changed
- Some UI changes

## [2.1.0](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_1_0) - 2020-05-31
### Added
- New modifiers:
    - "Export actions as files" (only FBX) creates separate fbx files with an armature and an animation each (for game development)
- "Merge Armatures" modifier now deletes the created actions after exporting
- Added auto updater

### Fixed
- Drivers from sub collections are now kept when using "Instanced collections to objects" modifier
- Fixed error when trying to select a bundle with one of its objects hidden by an excluded collection

## [2.0.1](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_0_1) - 2020-05-30
### Added
- New modifiers:
    - "Keep action names". For exporting actions in FBX, it avoids adding the object name before the action name.
    - "Export textures". It will export all textures being used by the materials of the exported objects to the export path (useful when they are embeded).
- Option to remove duplicate numbering (".001", ".002", ".003"...) for the "Rename" modifier
- "Copy modifiers" modifier now shows the modifiers in a list
- "Merge Meshes" modifier searches for exportable armatures if a mesh being exported has an invalid "Armature" modifier and tries to fix it
- Easy access to scene unit system and scale in the main panel
- New button that shows the modifier tooltip (It can be disabled in the addon preferences)
- Changelog

### Fixed
- Fixed issues when baking actions with the "Merge armatures" modifier
- Drawing fences now takes into account modifiers (for pivots and names for example)
- Drivers are now kept when using the "Instanced collections to objects" modifier
- Error when using the "Exclude from export" modifier
- Actions are no longer duplicated when exporting an object with an active action

### Changed
- More UI changes for the bundles (more compact and easier to read)

## [2.0.0](https://gitlab.com/AquaticNightmare/bundle_exporter/-/releases/2_0_0) - 2020-05-16
### Added
- Support for exporting **empties**
- Support for exporting **armatures**
- Defaults for modifiers can now be saved in the addon preferences
- Each bundle has its own **Override modifiers**. These have preference over the modifiers added to the scene
- New modifiers:
    - "Custom pivot": uses the origin of the provided source object as the new pivot for the bundle
    - "Transform empties": lets you apply a scale to all the empties (useful for exporting into unreal)
    - "Instance collections to objects" (support for **instanced collections**)
    - "Merge armatures" (and actions)
    - "Exclude from export": lets you choose if non-selectable/invisible objects or collections should be exported
- Modifiers now show a description when hovering over them inside the dropdown
- Modifiers now show an icon to better identify them
- Each bundle has its own "Bundle by" and "Pivot from" options
- Option to merge by collection or by parent for the "Merge Meshes" modifier
- Option to keep armature for the "Merge Meshes" modifier
- Export format OBJ

### Changed
- Bundles are now stored in the blend file and are not based on current selection
- Modifiers are now added from a dropdown
- Bundles are now selected from a list
- Export platform was changed to "Export format" and "Export preset"

### Fixed
- Hidden and unselectable objects and collections are now correctly exported

### Removed
- The apply modifiers operator
- The unity script
- "Move pivots to ground" operator