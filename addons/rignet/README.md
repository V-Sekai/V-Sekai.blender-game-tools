# bRigNet

Neural Rigging for [blender](https://www.blender.org/ "Blender Home Page") using [RigNet](https://zhan-xu.github.io/rig-net/ "RigNet Home Page")

## Table of Contents

1. [Introduction](#introduction)
2. [Setup](#setup)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Training](#training)
6. [License](#license)

## Introduction

Blender is an open-source 3D application from the Blender Foundation. RigNet is the Machine Learning prediction
for articulated characters.

## Setup

bRigNet requires SciPy, PyTorch, and torch-geometric, along with torch-scatter and torch-sparse.

## Installation

Download the Neural Rigging add-on as a .zip file and install it from the blender add-ons window,
or copy the code to the blender scripts path

    nvcc: NVIDIA (R) Cuda compiler driver
    Copyright (c) 2005-2019 NVIDIA Corporation
    Built on Wed_Oct_23_19:32:27_Pacific_Daylight_Time_2019
    Cuda compilation tools, release 10.2, V10.2.89

### Install dependencies via "Install" button

At present, the CUDA toolkit from nVidia is required, it can be found at the
[manufacturer website](https://developer.nvidia.com)

A dependency installer is available in the preferences.

- Install CUDA. At present prebuilt packages support versions 10.1, 10.2
- In the addon preferences, make sure that the Cuda version is detected correctly.
- Hit the "Install" button. It can take time!

## Usage

Enable _bRigNet_ in the blender addons, the preferences will show up.
Set the Modules path properties to the RigNet environment from the previous step

RigNet requires a trained model. They have made theirs available at [this address](https://umass-my.sharepoint.com/:u:/g/personal/zhanxu_umass_edu/EYKLCvYTWFJArehlo3-H2SgBABnY08B4k5Q14K7H1Hh0VA)
The checkpoint folder can be copied to the RigNet subfolder.
A different location can be set in the addon preferences.

#### Rig Generation

the **bRigNet** tab will show up in the Viewport tools. Select a character mesh as target.
Please make sure it doesn't exceed the 5K triangles. You can use the _Decimator_ modifier
to reduce the polycount on a copy of the mesh, and select a _Collection_ of high res model
on which to transfer the final weights

#### Load generated rigs

Rigs generated using RigNet from the command line can be loaded via the **Load Skeleton** panel.
Please select the _.obj and _.txt file and press the button **Load Rignet character**

## Training

The blender addon doesn't cover training yet. If you want to train your own model, please follow the instructions
from the [RigNet project](https://github.com/zhan-xu/RigNet#training).

## License

This addon is released under the GNU General Public License version 3 (GPLv3).
The RigNet subfolder is licensed under the General Public License Version 3 (GPLv3), or under a Commercial License.
