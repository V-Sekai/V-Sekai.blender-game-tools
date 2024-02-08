# blender-xatlas
This is a simple add-on for Blender allowing you to use Xatlas to unwrap and pack your uvs  
It currently works on Windows/Linux (Tested on Windows 10, Windows 8, Ubuntu)  
Code in /xatlas_src is modified from [xatlas](https://github.com/jpcy/xatlas/)  

<p float="left">
<img src="./readme_images/comparisons/sponza-xatlas.png" alt="Tool Location" width="400" height="333">
<img src="./readme_images/comparisons/sponza-xatlas-uv.png" alt="Tool Location" width="400" height="333">
</p>

## Usage

### Install
Don't know what a GitHub is? Here's some simple instructions!
1. [Download the repository.](https://codeload.github.com/s-ilent/blender-xatlas/zip/refs/heads/master)
2. From the downloaded ZIP file, extract the contents of the `addons` folder into your Blender addons folder.
   You should have a `blender-xatlas` folder in your Blender `addons` folder afterwards.
3. Enable the addon from Blender Preferences
4. You should see the Xatlas menu appear as an option in the 3D View sidebar (opened with 'n' by default)


### Use
Warning! The tool will make a single user copy and triangulate your mesh! (Unless using 'Pack Only')
<img src="./readme_images/tool-location.png" alt="Tool Location" width="569" height="408">
1. Make sure your file is saved
2. Change your settings under Xatlas Tools
3. Select the objects you wish to unwrap and unpack
4. Click ```Run Xatlas```
5. Wait for an undetermined period of time
6. Your unwrapped UVs should pop out of the oven

## Rebuilding Xatlas
If you just want to install the addon, this section is not for you.
### Build (Windows vs2017)
1. Run ```./bin/premake.bat```
2. Open ```./build/vs2017/xatlas.sln```
3. Build
4. The Output file should be copied to ```./addons/blender-xatlas/xatlas``` automatically

### Edit Addon
```xatlas-blender.cpp```

## Status
![Works On My Machine](works_on_my_machine.png)
