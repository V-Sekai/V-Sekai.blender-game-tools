"""Handle saving and loading project-specific settings."""

import contextlib
import logging
import typing

# Names of BlenderCloudPreferences properties that are both project-specific
# and simple enough to store directly in a dict.
PROJECT_SPECIFIC_SIMPLE_PROPS = ("cloud_project_local_path",)

# Names of BlenderCloudPreferences properties that are project-specific and
# Flamenco Manager-specific, and simple enough to store in a dict.
FLAMENCO_PER_PROJECT_PER_MANAGER = (
    "flamenco_exclude_filter",
    "flamenco_job_file_path",
    "flamenco_job_output_path",
    "flamenco_job_output_strip_components",
    "flamenco_relative_only",
)

log = logging.getLogger(__name__)
project_settings_loading = 0  # counter, if > 0 then we're loading stuff.


@contextlib.contextmanager
def mark_as_loading():
    """Sets project_settings_loading > 0 while the context is active.

    A counter is used to allow for nested mark_as_loading() contexts.
    """
    global project_settings_loading
    project_settings_loading += 1
    try:
        yield
    finally:
        project_settings_loading -= 1


def update_preferences(
    prefs,
    names_to_update: typing.Iterable[str],
    new_values: typing.Mapping[str, typing.Any],
):
    for name in names_to_update:
        if not hasattr(prefs, name):
            log.debug("not setting %r, property cannot be found", name)
            continue

        if name in new_values:
            log.debug("setting %r = %r", name, new_values[name])
            setattr(prefs, name, new_values[name])
        else:
            # The property wasn't stored, so set the default value instead.
            bl_type, args = getattr(prefs.bl_rna, name)
            log.debug("finding default value for %r", name)
            if "default" not in args:
                log.debug("no default value for %r, not touching", name)
                continue
            log.debug("found default value for %r = %r", name, args["default"])
            setattr(prefs, name, args["default"])


def handle_project_update(_=None, _2=None):
    """Handles changing projects, which may cause extensions to be disabled/enabled.

    Ignores arguments so that it can be used as property update callback.
    """

    from .blender import preferences, project_extensions

    with mark_as_loading():
        prefs = preferences()
        project_id = prefs.project.project
        log.debug(
            "Updating internal state to reflect extensions enabled on current project %s.",
            project_id,
        )

        project_extensions.cache_clear()

        from blender_cloud import attract, flamenco

        attract.deactivate()
        flamenco.deactivate()

        enabled_for = project_extensions(project_id)
        log.info("Project extensions: %s", enabled_for)
        if "attract" in enabled_for:
            attract.activate()
        if "flamenco" in enabled_for:
            flamenco.activate()

        # Load project-specific settings from the last time we visited this project.
        ps = prefs.get("project_settings", {}).get(project_id, {})
        if not ps:
            log.debug(
                "no project-specific settings are available, "
                "only resetting available Flamenco Managers"
            )
            # The Flamenco Manager should really be chosen explicitly out of the available
            # Managers.
            prefs.flamenco_manager.available_managers = []
            return

        if log.isEnabledFor(logging.DEBUG):
            from pprint import pformat

            log.debug("loading project-specific settings:\n%s", pformat(ps.to_dict()))

        # Restore simple properties.
        update_preferences(prefs, PROJECT_SPECIFIC_SIMPLE_PROPS, ps)

        # Restore Flamenco settings.
        prefs.flamenco_manager.available_managers = ps.get(
            "flamenco_available_managers", []
        )
        flamenco_manager_id = ps.get("flamenco_manager_id")
        if flamenco_manager_id:
            log.debug("setting flamenco manager to %s", flamenco_manager_id)
            try:
                # This will trigger a load of Project+Manager-specfic settings.
                prefs.flamenco_manager.manager = flamenco_manager_id
            except TypeError:
                log.warning(
                    "manager %s for this project could not be found",
                    flamenco_manager_id,
                )
        elif prefs.flamenco_manager.available_managers:
            prefs.flamenco_manager.manager = prefs.flamenco_manager.available_managers[
                0
            ]["_id"]


def store(_=None, _2=None):
    """Remember project-specific settings as soon as one of them changes.

    Ignores arguments so that it can be used as property update callback.

    No-op when project_settings_loading=True, to prevent saving project-
    specific settings while they are actually being loaded.
    """
    from .blender import preferences

    global project_settings_loading
    if project_settings_loading:
        return

    prefs = preferences()
    project_id = prefs.project.project
    all_settings = prefs.get("project_settings", {})
    ps = all_settings.get(project_id, {})  # either a dict or bpy.types.IDPropertyGroup

    for name in PROJECT_SPECIFIC_SIMPLE_PROPS:
        ps[name] = getattr(prefs, name)

    # Store project-specific Flamenco settings
    ps["flamenco_manager_id"] = prefs.flamenco_manager.manager
    ps["flamenco_available_managers"] = prefs.flamenco_manager.available_managers

    # Store per-project, per-manager settings for the current Manager.
    pppm = ps.get("flamenco_managers_settings", {})
    pppm[prefs.flamenco_manager.manager] = {
        name: getattr(prefs, name) for name in FLAMENCO_PER_PROJECT_PER_MANAGER
    }
    ps[
        "flamenco_managers_settings"
    ] = pppm  # IDPropertyGroup has no setdefault() method.

    # Store this project's settings in the preferences.
    all_settings[project_id] = ps
    prefs["project_settings"] = all_settings

    if log.isEnabledFor(logging.DEBUG):
        from pprint import pformat

        if hasattr(all_settings, "to_dict"):
            to_log = all_settings.to_dict()
        else:
            to_log = all_settings
        log.debug("Saving project-specific settings:\n%s", pformat(to_log))
