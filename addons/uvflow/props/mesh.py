from uvflow.addon_utils import Register, Property

from bpy.types import Context, MeshUVLoopLayer, Mesh, Object


@Register.PROP_GROUP.ROOT.MESH('uvflow')
class MeshProps:
    last_uv_layer_index: Property.INT(name="Last UV Layer Index", default=-1)
    last_uv_layer_count: Property.INT(name="Last UV Layer Count", default=0)
    last_uv_layer_name: Property.STRING(name="Last UV Layer Name", default="")

    @classmethod
    def ensure_last_uv_layer(cls, mesh: Mesh) -> None:
        if cls.get_last_uv_layer_count(mesh) == 0:
            cls.update_last_uv_layer_count(mesh)
        if cls.get_last_uv_layer_index(mesh) == -1:
            cls.update_last_uv_layer_index(mesh)
        if cls.get_last_uv_layer_name(mesh) == '':
            cls.update_last_uv_layer_name(mesh)

    @staticmethod
    def get_data(data: Object | Mesh | Context) -> 'MeshProps':
        if isinstance(data, Mesh):
            return data.uvflow
        if isinstance(data, Context):
            return data.object.data.uvflow
        if isinstance(data, Object):
            return data.data.uvflow
        raise TypeError("Invalid data type")

    @classmethod
    def update_last_uv_layer_index(cls, mesh: Mesh, get_indices: bool = False) -> tuple[bool, int, int] | bool:
        ''' Returns true if the name was indeed updated.
            - get_indices: will return the previous and the current active index. '''
        me_uvflow = cls.get_data(mesh)
        prev_index = me_uvflow.last_uv_layer_index
        curr_index = mesh.uv_layers.active_index if mesh.uv_layers.active is not None else -1

        if prev_index != curr_index:
            me_uvflow.last_uv_layer_index = curr_index

        if get_indices:
            return prev_index != curr_index, prev_index, curr_index
        return prev_index != curr_index

    @classmethod
    def update_last_uv_layer_count(cls, mesh: Mesh) -> int:
        ''' Returns 0 if nothing changed, 1 if added, -1 if removed. '''
        me_uvflow = cls.get_data(mesh)
        prev_count = me_uvflow.last_uv_layer_count
        curr_count = len(mesh.uv_layers)

        diff = curr_count - prev_count
        if diff != 0:
            me_uvflow.last_uv_layer_count = curr_count
        return diff

    @classmethod
    def update_last_uv_layer_name(cls, mesh: Mesh, get_names: bool = False) -> tuple[bool, str, str] | bool:
        ''' Returns true if the name was indeed updated.
            - get_names: will return the previous and the new name. '''
        me_uvflow = cls.get_data(mesh)
        prev_name = me_uvflow.last_uv_layer_name
        curr_name = mesh.uv_layers.active.name if mesh.uv_layers.active else ''

        diff = prev_name != curr_name
        if diff:
            me_uvflow.last_uv_layer_name = curr_name
        if get_names:
            return diff, prev_name, curr_name
        return diff

    @classmethod
    def get_last_uv_layer_index(cls, data: Object | Mesh | Context) -> int:
        return cls.get_data(data).last_uv_layer_index

    @classmethod
    def get_last_uv_layer_count(cls, data: Object | Mesh | Context) -> int:
        return cls.get_data(data).last_uv_layer_count
    
    @classmethod
    def get_last_uv_layer_name(cls, data: Object | Mesh | Context) -> str:
        return cls.get_data(data).last_uv_layer_name
