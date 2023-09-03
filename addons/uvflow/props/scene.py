from uvflow.addon_utils import Register, Property


@Register.PROP_GROUP.ROOT.SCENE('uvflow')
class SceneProps:
    uv_editor_enabled: Property.BOOL(name="Toggle UV Editor")
