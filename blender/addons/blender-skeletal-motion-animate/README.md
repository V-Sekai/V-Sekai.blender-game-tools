# Skeletal Motion Animate Plugin for Blender

This plugin lets you retarget animations.

This project is derived from https://github.com/Rokoko/rokoko-studio-live-blender.

## Requirements
- Blender **2.83** or higher

## Features
- Easily retarget motion capture animations
- VRM Bone renaming
 
## Getting Started for Streaming

### Make sure the model is ready for Studio Live
The character in Blender has to be in T-pose:

  <img src="https://i.imgur.com/p4uVZBx.png" height="450"/>

**For SmartGloves:** Make sure that the character's hands and fingers are posed as close as possible to the following pose to get the best 
possible retargeting of finger animation. All fingers should be straight and the thumb should be rotated 45 degrees away from the other fingers.

  <img src="https://i.imgur.com/9I13bHI.png"/>

## Retargeting

In order to retarget an animation in Blender you will need to do the following:

- Open the Retargeting panel

  <img src="https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/47029758599/original/gt30hHJ2JCfKDmmALDxjffiHbYjqFMQFmg.png"/>

- Select an armature with an animation as the source armature, select an armature that should receive the animation as the target armature and then press "Build Bone List"

  <img src="https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/47029758649/original/AuSYaHVCMTAQmTYRX8JHohflx4B6tu7EVQ.png"/>

- Check if the bones got filled in correctly and fix any incorrect or missing bones

  <img src="https://s3.amazonaws.com/cdn.freshdesk.com/data/helpdesk/attachments/production/47029758669/original/O_kTjk6qEKnNr_jOmvMXa2OI5d561ttBqA.png"/>

- Select "Auto Scale" if the armatures differ in size or resize them manually
- In "Use Pose:" select the pose that should be used for retargeting
- Important: Make sure that both armature are in the same pose for correct retargeting
- Press "Retarget Animation"
