# RigOnTheFly
Version : 2.0.8-beta

Rig on the Fly is a Blender 3.6 and 4.0 dynamic rigging tool used to simplify and speed up animation workflow.  
Inspired by Richard Lico's GDC 2018 talk: [Animating Quill: Creating an Emotional Experience](https://www.youtube.com/watch?v=u3CzLVpuE4k&t=2011s) and his Animation Sherpa Space Switching course.  
  
The main goal of Rig on the Fly is to facilitates animators job by automating repetitive tasks such as rigging. It does so by modularizing the rig allowing changes to how it functions on the fly without losing motion. Letting animators focus on performance rather than find ways to circumvent rig limitations.

Rig on the Fly is the result of my brother's and my free time, used to improve my personal animation workflow. We are sharing this tool in case it helps others animate in Blender 3D.  
If you have any questions or suggestions you can contact us on dypsloom's [discord](https://discord.gg/guN9QXn) and through twitter @dypsloom and @Wardl_ .
You can also check other cool things that we do on [dypsloom.com](https://dypsloom.com/).

### Compatibility
Blender 3.6 and 4.2

### Known Issues   
If an animation uses exaggerated non-uniform scale transforms, baking or exporting the animation can look different.

### Features to Fix/Improve  

### Future Features

### Installation
Go to the following address [https://gitlab.com/dypsloom/rigonthefly/-/tree/v2-beta](https://gitlab.com/dypsloom/rigonthefly/-/tree/v2-beta) and download the addon to a chosen folder on your computer.   

Then in Blender, go to "Add-ons" tab on the preference window. There click on the "Install" button and navigate to the folder where you downloaded the addon. Choose the RigOnTheFly file and it will be installed.

Make sure the addon check-mark is active.

Once installed you can find the RigOnTheFly panel on the right side of your 3d view in Sidebar. Press N to Toggle Sidebar visibility or click on the small arrow pointing left on the top right part of your 3d view.

At the moment RigOnTheFly has the following features. 

## Bake Settings
### Smart Frame

With the **Smart Frames** setting turned **off**, any changes to the rig using **Rig On The Fly** will result in keeping the pre-existing motion using Blender's regular bake operation.

 

When **Smart Frames** is turned **on**, any changes to the rig using **Rig On The Fly** will result in **keeping only the relevant keyed poses from the pre-existing motion.**
This setting is ideal for the early stages of an animation preventing too many keys from clogging the timeline.

### No Bake On Remove
When **No Bake On Remove** is turned **on** whenever a constraint created by **Rig on the Fly** gets removed, motion will not be baked down onto the constrained bones. This options exist for the case where you have modified your rig using **Rig on the Fly** and made changes to your animation but are not satisfied with the result and want to go back to the initial animation.

## Controller Shapes Settings
### Controller Size
**[+] Increases** the selected bones' **custom shapes scale** uniformly.

**[-] Decreases** the selected bones' **custom shapes scale** uniformly.

When **Mirror** is turned **on** changing the size of a bone ending in a side suffix eg. **_L** or **_R** it will check if there is an opposite bone and force it to have the same **custom shapes scale**. 

## Bone Layers/Collections
**Blender 3.6** uses bone layers, **Blender 4.0+** and use bone collections. The addon will automatically detect which Blender version you are using and give you the appropriate options.

### Bone Layers (Blender 3.6)
The following properties are per object. Meaning different armatures can have different values for their bone layer settings.

When using **Rig on the Fly** a lot of bones get added or removed. To keep armature clear and readable bones get sent to different bone layers to avoid clutter in the 3D viewport. This panel sets the guidelines that **Rig on the Fly** will follow when it comes to moving bones from bone layer to bone layer.

#### Base Bones

The armature’s bone layer where bones that are directly driven by rig bones are sent to.

#### Unused Controllers

The armature’s bone layer where temporarily unused rig bones are sent to.

#### Unoriented Bones

The armature’s bone layer where not-oriented bones are sent to.

### Bone Collections (Blender 4.0+)

(Documentation coming at a later time)

## Armature Tools

### Basic Setup (Blender 3.6)

Adds a **controller shape** to all **bones not using a controller shape** in the **visible bone layers** and assigns them to the **left, middle or right RigOnTheFly bone group.**

### Basic Setup (Blender 4.0+)

(Documentation coming at a later time)

### Bake Rig

**Bakes** down the all the motion onto the rig and removes all **bones** and **constraints **created by **Rig on the Fly.**

### Proxy

**Rig on the Fly** requires access to an armature’s **Edit Mode** to add and remove bones. This is not possible when using **proxy** armatures (**library override**). To get around this limitation **[Proxy]** recreates the selected armatures and uses them to drive the selected ones with the use of **transform constraints**. Transferring any animation to the newly created armatures.

### Orient visible

Specifically for armatures where the **Y axis** of the bones **do not** point towards their children. Duplicates the hierarchy and re-orients the newly created bones correctly by having their **Y axis** point towards their children and make them compatible with Blender’s **mirror-X** (symmetry posing). This is needed because some of Blender’s **constraints** (eg. IK) do not behave as required if the **Y axis** of the bones **do not** point towards their children.

### Add Bone

Adds an extra bone to the armature with it’s axis aligned to the world scene.

### Root Motion/Remove RM

**Adds a bone** at the **base of the hierarchy** and transfer the **object's motion** onto it. 
Removing it re-transfers the motion back to the **armature object**.

## Baking Process

When **Rig on the Fly** bakes any kind of motion it gets fed a dictionary containing the bones whose motion has to be keyframed.

Each item in the dictionary uses the **pose bones** that need to be baked as keys. Under this key will be a list of the bones that need to be checked for keyframes. This list of bones is only used when **Smart Frames** is turned on in the **Bakes Settings**.

It then goes through the following process.

### ROTF Bake

#### Find Actions

Goes through the armature’s **current action** and **nla** (nonlinear animation) and comes up with a **lists of all actions** (animation clips) that it is using. **Muted NLA tracks will be ignored from the baking process.** If no animation clips are found the process stops there as the armature is not using any animation.

#### Save Animation State

Sets aside the state the armature’s **current action**, it’s **blend mode** and if it was in the **nla’s tweak mode** so that it can be restored back once the baking process is finished.

#### Rest Pose

Checks if a **RotF Rest Pose track** exist in the armature’s nla and adds one if needed. A **RotF Rest Pose track** consists of a single action placed at the very bottom of the nla where the armature is in it’s rest pose. Usually A or T pose. It is important to bake actions that use **blend modes** other than **replace** on top of a “clean” pose.

#### Find Frames to Bake

For each **action** in the **actions list**, comes up with the list of the **frames** that will be keyed by going through the list of bones under each key from the dictionary and finds the frames in the action where the have keyframes.

#### Bake

For each **action** in the **actions list**, goes through each frame from the **frame list** and adds keys to the bones that need to be baked.

#### Restore the Animation State

Takes the armature’s animation state saved from earlier and applies it now that the baking process is done.

### Clear Channels

Regularly some animations channels become irrelevant either by the **bones not existing any more** or **driven by constraints**. This step goes through **all actions** relevant to the armature and **removes those animation channels.**

## Center of Mass

(Documentation coming at a later time)

### Center of Mass/Remove CoM (Center of Mass)
Creates a bone with it's location driven between the position of the selected bones. The influence values can be edited under the Item → Properties. Ideal to get a sense of where the centre of mass of a character is.

### Add to CoM/Remove from CoM 

Adds or removes the **selected bones**' influence to the **active** CoM bone.

## Rotation & Scale Tools

### Rotation Mode

Changes selected bones' **rotation mode**.

### Inherit Rotation - On/Off

Changes selected bones' **rotation inheritance**

### Inherit Scale - On/Off

Changes selected bones' **scale inheritance**

### Distribute/Apply

Distributes **rotation** from the selected bone **up the hierarchy** depending on the chosen **chain length**.

**[Apply]** bakes down the distributions.

## IK FK Switch

### Bend IK

Bend IK will have a chain of bones bend to have it's tip reach the IK target controller. Ideal for limbs.

#### IK Chain Length

The number of bones up the hierarchy of the selected bones that will be made part of the IK chain. Selecting a hand bone with a chain length of 2 will result in your typical arm IK.

#### IK Stretch Type

**None** - The chain will not stretch to reach the IK target.

**Location** - The bones in the chain will shift their location to reach the IK target.

**Scale** - The bones in the chain will scale in their Y axis to reach the IK target.

#### If Straight

Blender’s IK cannot bend a completely straight chain. So if the chain of bones result in a straight RotF will rotate the bones  of the chain away from the chosen axis. It does so in pose mode so it will not modify the rig.

#### IK

Turns the selected bones into Bend IK chains following the chosen settings.

#### FK

Removes the Bend IK behaviour

### Stretch IK

Stretch IK will have a chain of bones stretch to have it's tip reach the IK target controller. Ideal for a cartoony spine.

#### IK Chain Length

The number of bones up the hierarchy of the selected bones that will be made part of the IK chain.

#### IK Stretch Type

**Location** - The bones in the chain will shift their location to reach the IK target.

**Scale** - The bones in the chain will scale in their Y axis to reach the IK target.

**Keep Volume** - The bones of the chain will keep their volum as they stretch or squash.

#### Stretch IK

Turns the selected bones into Stretch IK chains following the chosen settings.

#### Remove

Removes the Stretch IK behaviour

## Space Switch

### Make World
Turns the selected controllers into World space.

### Remove World
Returns the selected World space controllers to their previous space.

### Make Aim
Turns the selected controllers into Aim space. Adds an aim target to the selected controllers in the direction of their respective specified **Axis** and **Distance**.

#### Axis
Axis that the selected controllers will be pointing with.

#### Distance
Distance in meters between the selected controller and their aim targets.

### Aim Offset
Similar to **Make Aim** but the aim target get’s placed at the position of the **3D cursor** instead.

### Remove Aim
Returns the selected Aim space controllers back to their previous space.

### Parent
Parents the selected controllers to the active controller (usually the one selected last).

### Parent Copy
Parents the selected controllers to a copy of the active controller (usually the one selected last). Ideal when wanting to parent a controller to one of it’s children.

### Parent Offset
Parents the selected controllers to a controller placed at the 3D cursor’s position.

### Restore Child
Restore the selected child controllers in Parent space back to their previous space.

### Restore Siblings
Restore the selected child controllers and all their “siblings” in Parent space back to their previous space. In this case, "siblings" refer to other Parent space controllers that have the same parent as the selected controller.

### Reverse
Reverses the hierarchy from the selected controller. If a parent of the selected controller is using RotF’s **IK** or **World** space it will go up the hierarchy of those controllers instead of continuing it's usual hierarchy.

### Restore
Restores a reverse hierarchy back to it’s original hierarchy.

## Simple Constraints
Simple constraints do not keep the existing motion intact. It is no different to adding a constraint by hand but in a way that gets registers into a Rig’s **Rig State**.

### Copy Transforms
Adds a **Location**, **Rotation** and or **Scale** constraint to the selected controllers using the active controller as target. If all types of transforms are selected it will simply use a **Copy Transforms** constraint instead.

### Aim
Adds a **Damped Track** constraint to controllers down the selection order controllers. 

### Influence
Defines the influence of the constraints created by **Copy Transforms** and **Aim**.

### Remove
Removes RotF’s **Simple Constraints** on the selected controllers without preserving their influence on the motion.

### Bake
Bakes down RotF’s **Simple Constraints** on the selected controllers before removing them.

## Keyframe Tools
The following tools **do not** affect the rig's sturcture or the bake settings in anyway. They only affect the active **action**.

### Key Range
Adds keys to the selected controllers between the specified range between **Start** and **End**.

#### Step
Defines the number of frames between each keys.

### Key as Active
Adds keys to the selected controllers on the same frames as the keys on the **Active** controller (usually the last to be selected).

#### Use Selection
If turned **on**, only key on the on the frames of the **selected keys** of the **Active** controller.

### Offset Keys
Offsets the selected keyframes from the selected controllers along the timeline in the order of selection.

## Dynamic on Transforms
Tool to create procedural motion. Dirrectly adapted from https://www.youtube.com/watch?v=KPoeNZZ6H4s

#### Start Blend Frame
The specific frame when the effect of applying dynamics starts to blend in.

#### Frequency
Reaction speed to change in motion.

#### Damp
How much the motion settles

#### Response
Initial response to change in motion. High Response results in sudden change in direction whereas negative Response results in anticipation of the motion.

### Loc, Rot, Scale, Selected Transforms
Add keys to the specified transform of the selected controller following the dynamics settings.

## Rig State
**Rig States** are a property on each armature that records the changes made from using **Rig on the Fly**.

### Save
Saves a .json file containing the **active** rig's **Rig State, Bone Groups, Bone Shapes** and **Bone Relations**.

### Folder Path
Let's you look for the folder from where you want to load your saved **Rig States**.

#### Bake on load
Bakes down the rig’s motion and removing all **Rig on the Fly** controllers before loading a **Rig State**. Makes the loading process take longer but provides a clean slate that prevents potential errors in loading.

### Bake Rig
Exactly the same as the one found in the **Armature Tools* tab. For each **action** in the **actions list**, goes through each frame from the **frame list** and adds keys to the bones that need to be baked.

## Single Frame Pose

### Set up
Single Frame Pose isolate the current pose into a new 1 frame action. Once **Set Up** all changes to the rig made by **Rig on the Fly** will only apply to the active action letting you change the rig's structure without having to wait for all actions to bake.

Especially useful when working on long animations or on **Additive** NLA strips. It is compatible with rig states. 

## Apply
Reverts the **Rig State** back to it’s previous state on **Set Up**. Copies the pose and applies it to the active action from before **Set Up**.

