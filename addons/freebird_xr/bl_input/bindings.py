# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
from typing import Union


@dataclass
class Binding:
    component_path: Union[str, list] = None
    num_components: int = 1
    threshold: float = 0.0
    suffix: str = ""
    axis_region: str = "ANY"
    type: str = "BASIC"  # or "AXIS" or "POSE"


class AxisBinding(Binding):
    def __init__(self, component_path, **kwargs):
        super().__init__(component_path, **kwargs)

        self.type = "AXIS"


PROFILES = {
    "index": "/interaction_profiles/valve/index_controller",
    "oculus": "/interaction_profiles/oculus/touch_controller",
    "reverb_g2": "/interaction_profiles/hp/mixed_reality_controller",
    "vive": "/interaction_profiles/htc/vive_controller",
    "vive_cosmos": "/interaction_profiles/htc/vive_cosmos_controller",
    "vive_focus": "/interaction_profiles/htc/vive_focus3_controller",
    "wmr": "/interaction_profiles/microsoft/motion_controller",
}
DISABLED_PROFILES = ["reverb_g2", "vive_cosmos", "vive_focus"]

GRIP_COMPONENT_PATH = "/input/grip/pose"
AIM_COMPONENT_PATH = "/input/aim/pose"
TRIGGER_COMPONENT_PATH = "/input/trigger/value"
HAPTIC_COMPONENT_PATH = "/output/haptic"
SQUEEZE_COMPONENT_PATHS = {
    "index": "/input/squeeze/force",
    "oculus": "/input/squeeze/value",
    "reverb_g2": "/input/squeeze/value",
    "vive": "/input/squeeze/click",
    "vive_cosmos": "/input/squeeze/click",
    "vive_focus": "/input/squeeze/click",
    "wmr": "/input/squeeze/click",
}
JOYSTICK_COMPONENT_PATHS = {
    "index": "/input/thumbstick",
    "oculus": "/input/thumbstick",
    "reverb_g2": "/input/thumbstick",
    "vive": "/input/trackpad",
    "vive_cosmos": "/input/thumbstick",
    "vive_focus": "/input/thumbstick",
    "wmr": "/input/thumbstick",
}
BUTTON_A_LEFTHAND_COMPONENT_PATHS = {
    "index": "/input/a/click",
    "oculus": "/input/x/click",
    "reverb_g2": "/input/x/click",
    "vive_cosmos": "/input/x/click",
    "vive_focus": "/input/x/click",
}
BUTTON_B_LEFTHAND_COMPONENT_PATHS = {
    "index": "/input/b/click",
    "oculus": "/input/y/click",
    "reverb_g2": "/input/y/click",
    "vive_cosmos": "/input/y/click",
    "vive_focus": "/input/y/click",
}
BUTTON_A_RIGHTHAND_COMPONENT_PATHS = {
    "index": "/input/a/click",
    "oculus": "/input/a/click",
    "reverb_g2": "/input/a/click",
    "vive_cosmos": "/input/a/click",
    "vive_focus": "/input/a/click",
}
BUTTON_B_RIGHTHAND_COMPONENT_PATHS = {
    "index": "/input/b/click",
    "oculus": "/input/b/click",
    "reverb_g2": "/input/b/click",
    "vive_cosmos": "/input/b/click",
    "vive_focus": "/input/b/click",
}
BUTTON_A_LEFTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/a/touch",
    "oculus": "/input/x/touch",
}
BUTTON_B_LEFTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/b/touch",
    "oculus": "/input/y/touch",
}
BUTTON_A_RIGHTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/a/touch",
    "oculus": "/input/a/touch",
}
BUTTON_B_RIGHTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/b/touch",
    "oculus": "/input/b/touch",
}

THRESHOLD = {
    "trigger": 0.05,
    "squeeze": 0.3,
    "joystick": 0.3,
    "button": 0.01,
}


bindings: dict[str, Binding] = {
    "GRIP_POSE": Binding(GRIP_COMPONENT_PATH, num_components=2, type="POSE"),
    "AIM_POSE": Binding(AIM_COMPONENT_PATH, num_components=2, type="POSE"),
    "TRIGGER": Binding(TRIGGER_COMPONENT_PATH, num_components=2, threshold=THRESHOLD["trigger"]),
    "SQUEEZE": Binding(SQUEEZE_COMPONENT_PATHS, num_components=2, threshold=THRESHOLD["squeeze"]),
    "HAPTIC": Binding(HAPTIC_COMPONENT_PATH, num_components=2),
    # "JOYSTICK": Binding(JOYSTICK_COMPONENT_PATHS, threshold=JOYSTICK_DIR_THRESHOLD),
    "JOYSTICK_X": AxisBinding(JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x"),
    "JOYSTICK_Y": AxisBinding(JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y"),
    "JOYSTICK_LEFT": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x", axis_region="NEGATIVE"
    ),
    "JOYSTICK_RIGHT": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x", axis_region="POSITIVE"
    ),
    "JOYSTICK_DOWN": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y", axis_region="NEGATIVE"
    ),
    "JOYSTICK_UP": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y", axis_region="POSITIVE"
    ),
    "BUTTON_A_LEFTHAND": AxisBinding(BUTTON_A_LEFTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_LEFTHAND": AxisBinding(BUTTON_B_LEFTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_RIGHTHAND": AxisBinding(BUTTON_A_RIGHTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_RIGHTHAND": AxisBinding(BUTTON_B_RIGHTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_TOUCH_LEFTHAND": AxisBinding(BUTTON_A_LEFTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_TOUCH_LEFTHAND": AxisBinding(BUTTON_B_LEFTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_TOUCH_RIGHTHAND": AxisBinding(BUTTON_A_RIGHTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_TOUCH_RIGHTHAND": AxisBinding(BUTTON_B_RIGHTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
}


def make_bindings(action, binding_name: str):
    b = bindings[binding_name]

    for platform_name in PROFILES.keys():
        if isinstance(b.component_path, dict) and platform_name not in b.component_path:
            continue

        binding = action.bindings.new(platform_name, True)
        binding.profile = PROFILES[platform_name]

        path = b.component_path[platform_name] if isinstance(b.component_path, dict) else b.component_path
        path += b.suffix
        paths = [path] * b.num_components

        if hasattr(binding, "component_paths"):  # introduced in Blender 3.2
            for path in paths:
                binding.component_paths.new(path)
        else:
            binding.component_path0 = paths[0]
            if len(paths) > 1:
                binding.component_path1 = paths[1]

        if b.type != "POSE":
            binding.threshold = b.threshold

        if b.type == "AXIS":
            binding.axis0_region = b.axis_region
        elif b.type == "POSE":
            binding.pose_location = [0.0, 0.0, 0.0]
            binding.pose_rotation = [0.0, 0.0, 0.0]
