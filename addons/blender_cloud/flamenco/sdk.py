import functools
import pathlib
import typing

from pillarsdk.resource import List, Find, Create


class Manager(List, Find):
    """Manager class wrapping the REST nodes endpoint"""

    path = "flamenco/managers"
    PurePlatformPath = pathlib.PurePath

    @functools.lru_cache(maxsize=1)
    def _path_replacements(self) -> list:
        """Defer to _path_replacements_vN() to get path replacement vars.

        Returns a list of tuples (variable name, variable value).
        """
        settings_version = self.settings_version or 1
        try:
            settings_func = getattr(self, "_path_replacements_v%d" % settings_version)
        except AttributeError:
            raise RuntimeError(
                "This manager has unsupported settings version %d; "
                "upgrade Blender Cloud add-on"
            )

        def longest_value_first(item):
            var_name, var_value = item
            return -len(var_value), var_value, var_name

        replacements = settings_func()
        replacements.sort(key=longest_value_first)
        return replacements

    def _path_replacements_v1(self) -> typing.List[typing.Tuple[str, str]]:
        import platform

        if self.path_replacement is None:
            return []

        items = self.path_replacement.to_dict().items()

        this_platform = platform.system().lower()
        return [
            (varname, platform_replacements[this_platform])
            for varname, platform_replacements in items
            if this_platform in platform_replacements
        ]

    def _path_replacements_v2(self) -> typing.List[typing.Tuple[str, str]]:
        import platform

        if not self.variables:
            return []

        this_platform = platform.system().lower()
        audiences = {"users", "all"}

        replacements = []
        for var_name, variable in self.variables.to_dict().items():
            # Path replacement requires bidirectional variables.
            if variable.get("direction") != "twoway":
                continue

            for var_value in variable.get("values", []):
                if var_value.get("audience") not in audiences:
                    continue
                if var_value.get("platform", "").lower() != this_platform:
                    continue

                replacements.append((var_name, var_value.get("value")))
        return replacements

    def replace_path(self, some_path: pathlib.PurePath) -> str:
        """Performs path variable replacement.

        Tries to find platform-specific path prefixes, and replaces them with
        variables.
        """
        assert isinstance(some_path, pathlib.PurePath), (
            "some_path should be a PurePath, not %r" % some_path
        )

        for varname, path in self._path_replacements():
            replacement = self.PurePlatformPath(path)
            try:
                relpath = some_path.relative_to(replacement)
            except ValueError:
                # Not relative to each other, so no replacement possible
                continue

            replacement_root = self.PurePlatformPath("{%s}" % varname)
            return (replacement_root / relpath).as_posix()

        return some_path.as_posix()


class Job(List, Find, Create):
    """Job class wrapping the REST nodes endpoint"""

    path = "flamenco/jobs"
    ensure_query_projections = {"project": 1}

    def patch(self, payload: dict, api=None):
        import pillarsdk.utils

        api = api or self.api

        url = pillarsdk.utils.join_url(self.path, str(self["_id"]))
        headers = pillarsdk.utils.merge_dict(
            self.http_headers(), {"Content-Type": "application/json"}
        )
        response = api.patch(url, payload, headers=headers)
        return response
