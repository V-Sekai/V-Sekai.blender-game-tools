from ..utils import log

active_tool = None

MODULES = {  # tool_name -> modules
    "select": ["select", "transform_trigger", "clone"],  # 'select' should get enabled before 'transform'
    "erase": "erase",
    "draw.stroke": "draw_stroke",
    "draw.shape": "draw_shape",
    "draw.hull": "draw_hull",
    "edit_mesh.loop_cut": "edit_mesh.loop_cut",
}


def _get_modules(tool_name):
    import importlib
    from ..settings_manager import settings

    if tool_name not in MODULES:
        return

    module_names = MODULES[tool_name]
    module_names = [module_names] if not isinstance(module_names, list) else module_names

    if settings["transform.grab_button"] == "squeeze" and tool_name == "select":  # temp hack for testing
        module_names = ["select"]

    modules = [importlib.import_module("." + module_name, __name__) for module_name in module_names]
    return modules


def enable_tool(tool_name):
    global active_tool

    if active_tool == tool_name:
        return

    if active_tool:
        disable_tool(active_tool)

    log.info(f"Enabling tool: {tool_name}")

    enabled = False
    modules = _get_modules(tool_name)
    if modules:
        for module in modules:
            is_tool_allowed = getattr(module, "is_tool_allowed", lambda: True)
            if is_tool_allowed():
                enabled |= True
            else:
                continue

            module.enable_tool()

    active_tool = tool_name if enabled else None

    if tool_name == "select":
        from ..gizmos import enable_gizmo

        enable_gizmo("transform_handles")


def disable_tool(tool_name):
    global active_tool

    if active_tool != tool_name:
        return

    log.debug(f"Disabling tool: {tool_name}")

    modules = _get_modules(tool_name)
    if modules:
        for module in modules:
            module.disable_tool()

    active_tool = None

    if tool_name == "select":
        from ..gizmos import disable_gizmo

        disable_gizmo("transform_handles")
