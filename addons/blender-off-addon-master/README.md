# Blender OFF Addon

This addon will add the ability to import and export ascii OFF mesh files in Blender 2.91+ (tested in 2.93.8 LTS and 3.4.1).

# Quickstart

1. Download the latest version off the addon from Github: https://github.com/richard-sim/blender-off-addon/archive/refs/heads/master.zip
2. Open Blender.
3. Go to Edit > Preferences... > Add-ons tab.
4. On the top right, click Install... button.
5. Select the downloaded zip file `blender-off-addon-master.zip`.
6. Check the checkbox by the `Import-Export: OFF format` addon to enable it.
7. Now you should have new import/export menu items to work with OFF files.

# Older Blender versions

This fork has only been tested with Blender 2.93.8 (LTS) and 3.4.1 (stable). It should work for 2.91+ (including 3.0+), but probably not for 2.8x.

# Other Authors

This is fork of the original Blender OFF Addon, and takes changes by various other forks in order to create The One Fork To Rule Them All. It includes changes from:

- https://github.com/brothermechanic/blender-off-addon
- https://github.com/A-Metaphysical-Drama/blender-off-addon

Notably, it does not include changes in the fork by keckj that adds support for vertex normals.

# License + Contributing

This addon is licensed under Apache 2.0.

    http://www.apache.org/licenses/LICENSE-2.0

Please feel free to open an issue/pull request about any problems you have or
features you'd want to have. I'll do my best to be responsive, but if not,
feel free to ping me an email or tweet at me.

# Changelog

## 0.5.0 / 2023-01-17

- Fixed errors that occur with Blender 2.91+
- Fixed exporting and importing of vertex colors
- Merged changes from various other forks of the original project to get the best of everything
- Improved the installation instructions in the readme (this file)

## 0.4.0 / 2020-05-10

- Support breaking API changes in Blender 2.8x release.

## 0.3.1 / 2017-11-03

- Allow blank line after the first line of the header (a common occurrence)
- Allow blank lines between the header and the data

## 0.3.0 / 2015-06-01

- Handle loading edges and faces with more than 3 sides properly

## 0.2.0 / 2014-05-17

- Handle Blender transformations

## 0.1.0 / 2014-01-21

- Initial implementation

# Developer notes

http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Guidelines/Addons

To have your script show up in the Add-Ons panel, it needs to:

    be in the addons/ directory
    contain a dictionary called "bl_info"
    define register() / unregister() functions.
