import pillarsdk


class SpecialFolderNode(pillarsdk.Node):
    NODE_TYPE = "SPECIAL"


class UpNode(SpecialFolderNode):
    NODE_TYPE = "UP"

    def __init__(self):
        super().__init__()
        self["_id"] = "UP"
        self["node_type"] = self.NODE_TYPE


class ProjectNode(SpecialFolderNode):
    NODE_TYPE = "PROJECT"

    def __init__(self, project):
        super().__init__()

        assert isinstance(
            project, pillarsdk.Project
        ), "wrong type for project: %r" % type(project)

        self.merge(project.to_dict())
        self["node_type"] = self.NODE_TYPE
