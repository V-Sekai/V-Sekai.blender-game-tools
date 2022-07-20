import logging
import os.path

import bpy
import bgl

import pillarsdk
from . import nodes

if bpy.app.version < (2, 80):
    from . import draw_27 as draw
else:
    from . import draw


library_icons_path = os.path.join(os.path.dirname(__file__), "icons")

ICON_WIDTH = 128
ICON_HEIGHT = 128


class MenuItem:
    """GUI menu item for the 3D View GUI."""

    icon_margin_x = 4
    icon_margin_y = 4
    text_margin_x = 6

    text_size = 12
    text_size_small = 10

    DEFAULT_ICONS = {
        "FOLDER": os.path.join(library_icons_path, "folder.png"),
        "SPINNER": os.path.join(library_icons_path, "spinner.png"),
        "ERROR": os.path.join(library_icons_path, "error.png"),
    }

    FOLDER_NODE_TYPES = {
        "group_texture",
        "group_hdri",
        nodes.UpNode.NODE_TYPE,
        nodes.ProjectNode.NODE_TYPE,
    }
    SUPPORTED_NODE_TYPES = {"texture", "hdri"}.union(FOLDER_NODE_TYPES)

    def __init__(self, node, file_desc, thumb_path: str, label_text):
        self.log = logging.getLogger("%s.MenuItem" % __name__)
        if node["node_type"] not in self.SUPPORTED_NODE_TYPES:
            self.log.info("Invalid node type in node: %s", node)
            raise TypeError(
                "Node of type %r not supported; supported are %r."
                % (node["node_type"], self.SUPPORTED_NODE_TYPES)
            )

        assert isinstance(node, pillarsdk.Node), "wrong type for node: %r" % type(node)
        assert isinstance(node["_id"], str), 'wrong type for node["_id"]: %r' % type(
            node["_id"]
        )
        self.node = node  # pillarsdk.Node, contains 'node_type' key to indicate type
        self.file_desc = file_desc  # pillarsdk.File object, or None if a 'folder' node.
        self.label_text = label_text
        self.small_text = self._small_text_from_node()
        self._thumb_path = ""
        self.icon = None
        self._is_folder = node["node_type"] in self.FOLDER_NODE_TYPES
        self._is_spinning = False

        # Determine sorting order.
        # by default, sort all the way at the end and folders first.
        self._order = 0 if self._is_folder else 10000
        if node and node.properties and node.properties.order is not None:
            self._order = node.properties.order

        self.thumb_path = thumb_path

        # Updated when drawing the image
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

    def _small_text_from_node(self) -> str:
        """Return the components of the texture (i.e. which map types are available)."""

        if not self.node:
            return ""

        try:
            node_files = self.node.properties.files
        except AttributeError:
            # Happens for nodes that don't have .properties.files.
            return ""
        if not node_files:
            return ""

        map_types = {f.map_type for f in node_files if f.map_type}
        map_types.discard("color")  # all textures have colour
        if not map_types:
            return ""
        return ", ".join(sorted(map_types))

    def sort_key(self):
        """Key for sorting lists of MenuItems."""
        return self._order, self.label_text

    @property
    def thumb_path(self) -> str:
        return self._thumb_path

    @thumb_path.setter
    def thumb_path(self, new_thumb_path: str):
        self._is_spinning = new_thumb_path == "SPINNER"

        self._thumb_path = self.DEFAULT_ICONS.get(new_thumb_path, new_thumb_path)
        if self._thumb_path:
            self.icon = bpy.data.images.load(filepath=self._thumb_path)
        else:
            self.icon = None

    @property
    def node_uuid(self) -> str:
        return self.node["_id"]

    def represents(self, node) -> bool:
        """Returns True iff this MenuItem represents the given node."""

        node_uuid = node["_id"]
        return self.node_uuid == node_uuid

    def update(self, node, file_desc, thumb_path: str, label_text=None):
        # We can get updated information about our Node, but a MenuItem should
        # always represent one node, and it shouldn't be shared between nodes.
        if self.node_uuid != node["_id"]:
            raise ValueError(
                "Don't change the node ID this MenuItem reflects, "
                "just create a new one."
            )
        self.node = node
        self.file_desc = file_desc  # pillarsdk.File object, or None if a 'folder' node.
        self.thumb_path = thumb_path

        if label_text is not None:
            self.label_text = label_text

        if thumb_path == "ERROR":
            self.small_text = "This open is broken"
        else:
            self.small_text = self._small_text_from_node()

    @property
    def is_folder(self) -> bool:
        return self._is_folder

    @property
    def is_spinning(self) -> bool:
        return self._is_spinning

    def update_placement(self, x, y, width, height):
        """Use OpenGL to draw this one menu item."""

        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self, highlighted: bool):
        bgl.glEnable(bgl.GL_BLEND)
        if highlighted:
            color = (0.555, 0.555, 0.555, 0.8)
        else:
            color = (0.447, 0.447, 0.447, 0.8)

        draw.aabox((self.x, self.y), (self.x + self.width, self.y + self.height), color)

        texture = self.icon
        if texture:
            err = draw.load_texture(texture)
            assert not err, "OpenGL error: %i" % err

        # ------ TEXTURE ---------#
        if texture:
            draw.bind_texture(texture)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        draw.aabox_with_texture(
            (self.x + self.icon_margin_x, self.y),
            (self.x + self.icon_margin_x + ICON_WIDTH, self.y + ICON_HEIGHT),
        )
        bgl.glDisable(bgl.GL_BLEND)

        if texture:
            texture.gl_free()

        # draw some text
        text_x = self.x + self.icon_margin_x + ICON_WIDTH + self.text_margin_x
        text_y = self.y + ICON_HEIGHT * 0.5 - 0.25 * self.text_size
        draw.text((text_x, text_y), self.label_text, fsize=self.text_size)
        draw.text(
            (text_x, self.y + 0.5 * self.text_size_small),
            self.small_text,
            fsize=self.text_size_small,
            rgba=(1.0, 1.0, 1.0, 0.5),
        )

    def hits(self, mouse_x: int, mouse_y: int) -> bool:
        return (
            self.x < mouse_x < self.x + self.width
            and self.y < mouse_y < self.y + self.height
        )
