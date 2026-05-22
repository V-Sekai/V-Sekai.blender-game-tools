# Optimized Tris to Quads Converter

## Overview

**Optimized Tris to Quads Converter** is a Blender add-on that converts triangles (tris) in a mesh to quadrilaterals (quads) using mathematical optimization. This approach ensures the most optimal conversion of tris to quads, resulting in cleaner and more efficient mesh topology.

## Compatibility

- Tested with **Blender 5.0**, should work with 4.2 and up.

## Prerequisite

This add-on requires the **PuLP** optimization library. The add-on provides a one-click installation option in the preferences panel.

## Comparison of Topology

The images below compare the topology produced by Blender's default tris-to-quads conversion tool and the topology produced by the **Optimized Tris to Quads Converter**.

### Original Mesh with Tris

![Original Mesh with Tris](img/og-tris.png)

### Default Blender Tris to Quads

![Default Blender Tris to Quads](img/defaultTTQ.png)

### Optimized Tris to Quads Converter

![Optimized Tris to Quads](img/OTQC.png)

As illustrated in the comparison images, the optimized converter maintains better edge flow and reduces the number of unnecessary vertices, resulting in a more aesthetically pleasing and functional mesh.

## Features

- Converts selected tris in a mesh to quads using the PuLP optimization library
- Ensures cleaner and more efficient mesh topology
- Simple and user-friendly interface with an easy-to-use operator

## Installation

1. Download or clone this repository
2. Open Blender and go to `Edit > Preferences > Get Extensions`
3. Click the dropdown arrow and select `Install from Disk...`
4. Navigate to and select the `Optimized-Tris-to-Quads-Converter.zip`
5. Enable the extension

## Usage

### Installing PuLP

The add-on requires the PuLP optimization library. Install it directly from the add-on preferences:

1. Go to `Edit > Preferences > Add-ons` (or `Get Extensions` in Blender 4.2+)
2. Find the **Optimized Tris to Quads Converter** in the list and expand it
3. If PuLP is not installed, click the `Install PuLP` button
4. Wait for the installation to complete (runs in background)
5. If the import still fails after installation, restart Blender once

Once installed, the preferences will show "PuLP is installed" with the version number.

### Converting Tris to Quads

1. Select a mesh object and enter `Edit Mode`
2. Select the triangular faces you want to convert
3. In the 3D Viewport menu, go to `Face > Optimized Tris to Quads`
4. The selected tris will be converted to quads using mathematical optimization

## Why Use This Add-on?

- **Optimization**: Uses Integer Linear Programming (ILP) to find the mathematically optimal edge dissolutions
- **Clean Topology**: Results in cleaner and more efficient mesh topology, beneficial for modeling, animation, and simulation
- **Ease of Use**: Simple interface integrated directly into Blender's Face menu
- **Modern Compatibility**: Updated for Blender 5.0 and the new Extensions system

## Troubleshooting

### PuLP won't import after installation
- Restart Blender after installing PuLP
- Check that your system has internet access during installation

### Installation button is grayed out
- An installation is already in progress; wait for it to complete

### "Select exactly one mesh object" error
- Make sure only one mesh object is selected before running the operator

## Files

- `__init__.py` - Main add-on code
- `blender_manifest.toml` - Extension manifest for Blender 4.2+ (optional for legacy installation)
- `README.md` - This file

## Credits

- **Original Author**: Tsutomu Saito (https://github.com/SaitoTsutomu/Tris-Quads-Ex)
- **Improved Version**: Rulesobeyer (https://github.com/Rulesobeyer/)

### Acknowledgement to the Original Author

This add-on is based on the original work of Tsutomu Saito. In his article on Qiita, Tsutomu Saito describes the development process and the motivation behind the "Tris to Quads Ex" add-on for Blender. The article explains how the add-on uses the PuLP optimization library to convert tris to quads, ensuring a more efficient and cleaner mesh topology.

Tsutomu Saito's work focused on addressing the limitations of Blender's default tris-to-quads conversion tool. By leveraging mathematical optimization, the "Tris to Quads Ex" add-on produces superior results, making it an invaluable tool for Blender users aiming for high-quality 3D models.

The original article provides a detailed explanation of the methodology and implementation, including:
- The motivation for creating the add-on
- The mathematical principles behind the optimization process
- Step-by-step instructions on how to use the add-on

Tsutomu Saito's innovative approach has significantly improved the tris-to-quads conversion process, and this improved version builds upon his foundation. We are grateful for his contributions to the Blender community.

[Read the original article on Qiita](https://qiita.com/SaitoTsutomu/items/b608c80d70a54718ec78)
