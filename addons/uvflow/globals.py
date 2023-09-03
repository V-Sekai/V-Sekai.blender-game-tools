_skip_mesh_updates = False
_USE_DEBUG = True


class GLOBALS:
    
    @property
    def use_debug(self) -> bool:
        return _USE_DEBUG

    @property
    def skip_mesh_updates(self) -> bool:
        global _skip_mesh_updates
        return _skip_mesh_updates
    
    @skip_mesh_updates.setter
    def skip_mesh_updates(self, state: bool) -> None:
        print("* GLOBALS.skip_mesh_updates set to ", state)
        global _skip_mesh_updates
        _skip_mesh_updates = state



class CM_SkipMeshUpdates:
    def __init__(self) -> None:
        self._skip = GLOBALS.skip_mesh_updates # Controlled by an outer scope.
    
    def __enter__(self):
        if self._skip: return
        GLOBALS.skip_mesh_updates = True
    
    def __exit__(self, exc_type, exc_value, trace):
        if self._skip: return
        GLOBALS.skip_mesh_updates = False



def print_debug(*args) -> None:
    if GLOBALS.use_debug:
        print(*args)
