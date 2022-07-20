# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import asyncio
import logging
import os
import threading
import typing

import bpy
import bgl

import pillarsdk
from .. import async_loop, pillar, cache, blender, utils
from . import (
    menu_item as menu_item_mod,
)  # so that we can have menu items called 'menu_item'
from . import draw, nodes

REQUIRED_ROLES_FOR_TEXTURE_BROWSER = {"subscriber", "demo"}
MOUSE_SCROLL_PIXELS_PER_TICK = 50

TARGET_ITEM_WIDTH = 400
TARGET_ITEM_HEIGHT = 128
ITEM_MARGIN_X = 5
ITEM_MARGIN_Y = 5
ITEM_PADDING_X = 5

log = logging.getLogger(__name__)


class BlenderCloudBrowser(
    pillar.PillarOperatorMixin, async_loop.AsyncModalOperatorMixin, bpy.types.Operator
):
    bl_idname = "pillar.browser"
    bl_label = "Blender Cloud Texture Browser"

    _draw_handle = None

    current_path = pillar.CloudPath("/")
    project_name = ""

    # This contains a stack of Node objects that lead up to the currently browsed node.
    path_stack = []  # type: typing.List[pillarsdk.Node]

    # This contains a stack of MenuItem objects that lead up to the currently browsed node.
    menu_item_stack = []  # type: typing.List[menu_item_mod.MenuItem]

    timer = None
    log = logging.getLogger("%s.BlenderCloudBrowser" % __name__)

    _menu_item_lock = threading.Lock()
    current_display_content = []  # type: typing.List[menu_item_mod.MenuItem]
    loaded_images = set()  # type: typing.Set[str]
    thumbnails_cache = ""
    maximized_area = False

    mouse_x = 0
    mouse_y = 0
    scroll_offset = 0
    scroll_offset_target = 0
    scroll_offset_max = 0
    scroll_offset_space_left = 0

    def invoke(self, context, event):
        # Refuse to start if the file hasn't been saved. It's okay if
        # it's dirty, we just need to know where '//' points to.
        if not os.path.exists(context.blend_data.filepath):
            self.report(
                {"ERROR"},
                "Please save your Blend file before using " "the Blender Cloud addon.",
            )
            return {"CANCELLED"}

        wm = context.window_manager

        self.current_path = pillar.CloudPath(wm.last_blender_cloud_location)
        self.path_stack = []  # list of nodes that make up the current path.

        self.thumbnails_cache = cache.cache_directory("thumbnails")
        self.mouse_x = event.mouse_x
        self.mouse_y = event.mouse_y

        # See if we have to maximize the current area
        if not context.screen.show_fullscreen:
            self.maximized_area = True
            bpy.ops.screen.screen_full_area(use_hide_panels=True)

        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        self._draw_handle = context.space_data.draw_handler_add(
            self.draw_menu, (context,), "WINDOW", "POST_PIXEL"
        )

        self.current_display_content = []
        self.loaded_images = set()
        self._scroll_reset()

        context.window.cursor_modal_set("DEFAULT")
        return async_loop.AsyncModalOperatorMixin.invoke(self, context, event)

    def modal(self, context, event):
        result = async_loop.AsyncModalOperatorMixin.modal(self, context, event)
        if not {"PASS_THROUGH", "RUNNING_MODAL"}.intersection(result):
            return result

        if event.type == "TAB" and event.value == "RELEASE":
            self.log.info("Ensuring async loop is running")
            async_loop.ensure_async_loop()

        if event.type == "TIMER":
            self._scroll_smooth()
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if "MOUSE" in event.type:
            context.area.tag_redraw()
            self.mouse_x = event.mouse_x
            self.mouse_y = event.mouse_y

        left_mouse_release = event.type == "LEFTMOUSE" and event.value == "RELEASE"
        if left_mouse_release and self._state in {"PLEASE_SUBSCRIBE", "PLEASE_RENEW"}:
            self.open_browser_subscribe(renew=self._state == "PLEASE_RENEW")
            self._finish(context)
            return {"FINISHED"}

        if self._state == "BROWSING":
            selected = self.get_clicked()

            if selected:
                if selected.is_spinning:
                    context.window.cursor_set("WAIT")
                else:
                    context.window.cursor_set("HAND")
            else:
                context.window.cursor_set("DEFAULT")

            # Scrolling
            if event.type == "WHEELUPMOUSE":
                self._scroll_by(MOUSE_SCROLL_PIXELS_PER_TICK)
                context.area.tag_redraw()
            elif event.type == "WHEELDOWNMOUSE":
                self._scroll_by(-MOUSE_SCROLL_PIXELS_PER_TICK)
                context.area.tag_redraw()
            elif event.type == "TRACKPADPAN":
                self._scroll_by(event.mouse_prev_y - event.mouse_y, smooth=False)
                context.area.tag_redraw()

            if left_mouse_release:
                if selected is None:
                    # No item clicked, ignore it.
                    return {"RUNNING_MODAL"}

                if selected.is_spinning:
                    # This can happen when the thumbnail information isn't loaded yet.
                    return {"RUNNING_MODAL"}

                if selected.is_folder:
                    self.descend_node(selected)
                else:
                    self.handle_item_selection(context, selected)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._finish(context)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    async def async_execute(self, context):
        self._state = "CHECKING_CREDENTIALS"
        self.log.debug("Checking credentials")

        try:
            db_user = await self.check_credentials(
                context, REQUIRED_ROLES_FOR_TEXTURE_BROWSER
            )
        except pillar.NotSubscribedToCloudError as ex:
            self._log_subscription_needed(can_renew=ex.can_renew, level="INFO")
            self._show_subscribe_screen(can_renew=ex.can_renew)
            return None

        if db_user is None:
            raise pillar.UserNotLoggedInError()

        await self.async_download_previews()

    def _show_subscribe_screen(self, *, can_renew: bool):
        """Shows the "You need to subscribe" screen."""

        if can_renew:
            self._state = "PLEASE_RENEW"
        else:
            self._state = "PLEASE_SUBSCRIBE"

        bpy.context.window.cursor_set("HAND")

    def descend_node(self, menu_item: menu_item_mod.MenuItem):
        """Descends the node hierarchy by visiting this menu item's node.

        Also keeps track of the current node, so that we know where the "up" button should go.
        """

        node = menu_item.node
        assert isinstance(node, pillarsdk.Node), "Wrong type %s" % node

        if isinstance(node, nodes.UpNode):
            # Going up.
            self.log.debug("Going up to %r", self.current_path)
            self.current_path = self.current_path.parent
            if self.path_stack:
                self.path_stack.pop()
            if self.menu_item_stack:
                self.menu_item_stack.pop()
            if not self.path_stack:
                self.project_name = ""
        else:
            # Going down, keep track of where we were
            if isinstance(node, nodes.ProjectNode):
                self.project_name = node["name"]

            self.current_path /= node["_id"]
            self.log.debug("Going down to %r", self.current_path)
            self.path_stack.append(node)
            self.menu_item_stack.append(menu_item)

        self.browse_assets()

    @property
    def node(self):
        if not self.path_stack:
            return None
        return self.path_stack[-1]

    def _finish(self, context):
        self.log.debug("Finishing the modal operator")
        async_loop.AsyncModalOperatorMixin._finish(self, context)
        self.clear_images()

        context.space_data.draw_handler_remove(self._draw_handle, "WINDOW")
        context.window.cursor_modal_restore()

        if self.maximized_area:
            bpy.ops.screen.screen_full_area(use_hide_panels=True)

        context.area.tag_redraw()
        self.log.debug("Modal operator finished")

    def clear_images(self):
        """Removes all images we loaded from Blender's memory."""

        for image in bpy.data.images:
            if image.filepath_raw not in self.loaded_images:
                continue

            image.user_clear()
            bpy.data.images.remove(image)

        self.loaded_images.clear()
        self.current_display_content.clear()

    def add_menu_item(self, *args) -> menu_item_mod.MenuItem:
        menu_item = menu_item_mod.MenuItem(*args)

        # Just make this thread-safe to be on the safe side.
        with self._menu_item_lock:
            self.current_display_content.append(menu_item)
            if menu_item.icon is not None:
                self.loaded_images.add(menu_item.icon.filepath_raw)

        self.sort_menu()

        return menu_item

    def update_menu_item(self, node, *args):
        node_uuid = node["_id"]

        # Just make this thread-safe to be on the safe side.
        with self._menu_item_lock:
            for menu_item in self.current_display_content:
                if menu_item.represents(node):
                    menu_item.update(node, *args)
                    self.loaded_images.add(menu_item.icon.filepath_raw)
                    break
            else:
                raise ValueError("Unable to find MenuItem(node_uuid=%r)" % node_uuid)

        self.sort_menu()

    def sort_menu(self):
        """Sorts the self.current_display_content list."""

        if not self.current_display_content:
            return

        with self._menu_item_lock:
            self.current_display_content.sort(key=menu_item_mod.MenuItem.sort_key)

    async def async_download_previews(self):
        self._state = "BROWSING"

        thumbnails_directory = self.thumbnails_cache
        self.log.info("Asynchronously downloading previews to %r", thumbnails_directory)
        self.log.info("Current BCloud path is %r", self.current_path)
        self.clear_images()
        self._scroll_reset()

        project_uuid = self.current_path.project_uuid
        node_uuid = self.current_path.node_uuid

        if node_uuid:
            # Query for sub-nodes of this node.
            self.log.debug("Getting subnodes for parent node %r", node_uuid)
            children = await pillar.get_nodes(
                parent_node_uuid=node_uuid, node_type={"group_texture", "group_hdri"}
            )
        elif project_uuid:
            # Query for top-level nodes.
            self.log.debug("Getting subnodes for project node %r", project_uuid)
            children = await pillar.get_nodes(
                project_uuid=project_uuid,
                parent_node_uuid="",
                node_type={"group_texture", "group_hdri"},
            )
        else:
            # Query for projects
            self.log.debug(
                "No node UUID and no project UUID, listing available projects"
            )
            children = await pillar.get_texture_projects()
            for proj_dict in children:
                self.add_menu_item(
                    nodes.ProjectNode(proj_dict), None, "FOLDER", proj_dict["name"]
                )
            return

        # Make sure we can go up again.
        self.add_menu_item(nodes.UpNode(), None, "FOLDER", ".. up ..")

        # Download all child nodes
        self.log.debug("Iterating over child nodes of %r", self.current_path)
        for child in children:
            # print('  - %(_id)s = %(name)s' % child)
            if child["node_type"] not in menu_item_mod.MenuItem.SUPPORTED_NODE_TYPES:
                self.log.debug("Skipping node of type %r", child["node_type"])
                continue
            self.add_menu_item(child, None, "FOLDER", child["name"])

        # There are only sub-nodes at the project level, no texture nodes,
        # so we won't have to bother looking for textures.
        if not node_uuid:
            return

        directory = os.path.join(thumbnails_directory, project_uuid, node_uuid)
        os.makedirs(directory, exist_ok=True)

        self.log.debug("Fetching texture thumbnails for node %r", node_uuid)

        def thumbnail_loading(node, texture_node):
            self.add_menu_item(node, None, "SPINNER", texture_node["name"])

        def thumbnail_loaded(node, file_desc, thumb_path):
            self.log.debug("Node %s thumbnail loaded", node["_id"])
            self.update_menu_item(node, file_desc, thumb_path)

        await pillar.fetch_texture_thumbs(
            node_uuid,
            "s",
            directory,
            thumbnail_loading=thumbnail_loading,
            thumbnail_loaded=thumbnail_loaded,
            future=self.signalling_future,
        )

    def browse_assets(self):
        self.log.debug("Browsing assets at %r", self.current_path)
        bpy.context.window_manager.last_blender_cloud_location = str(self.current_path)
        self._new_async_task(self.async_download_previews())

    def draw_menu(self, context):
        """Draws the GUI with OpenGL."""

        drawers = {
            "INITIALIZING": self._draw_initializing,
            "CHECKING_CREDENTIALS": self._draw_checking_credentials,
            "BROWSING": self._draw_browser,
            "DOWNLOADING_TEXTURE": self._draw_downloading,
            "EXCEPTION": self._draw_exception,
            "PLEASE_SUBSCRIBE": self._draw_subscribe,
            "PLEASE_RENEW": self._draw_renew,
        }

        if self._state in drawers:
            drawer = drawers[self._state]
            drawer(context)

        # For debugging: draw the state
        draw.text(
            (5, 5),
            "%s %s" % (self._state, self.project_name),
            rgba=(1.0, 1.0, 1.0, 1.0),
            fsize=12,
        )

    @staticmethod
    def _window_region(context):
        window_regions = [
            region for region in context.area.regions if region.type == "WINDOW"
        ]
        return window_regions[0]

    def _draw_browser(self, context):
        """OpenGL drawing code for the BROWSING state."""
        from . import draw

        if not self.current_display_content:
            self._draw_text_on_colour(
                context, "Communicating with Blender Cloud", (0.0, 0.0, 0.0, 0.6)
            )
            return

        window_region = self._window_region(context)
        content_width = window_region.width - ITEM_MARGIN_X * 2
        content_height = window_region.height - ITEM_MARGIN_Y * 2

        content_x = ITEM_MARGIN_X
        content_y = context.area.height - ITEM_MARGIN_Y - TARGET_ITEM_HEIGHT

        col_count = content_width // TARGET_ITEM_WIDTH

        item_width = (content_width - (col_count * ITEM_PADDING_X)) / col_count
        item_height = TARGET_ITEM_HEIGHT

        block_width = item_width + ITEM_PADDING_X
        block_height = item_height + ITEM_MARGIN_Y

        bgl.glEnable(bgl.GL_BLEND)
        draw.aabox(
            (0, 0), (window_region.width, window_region.height), (0.0, 0.0, 0.0, 0.6)
        )

        bottom_y = float("inf")

        # The -1 / +2 are for extra rows that are drawn only half at the top/bottom.
        first_item_idx = max(
            0, int(-self.scroll_offset // block_height - 1) * col_count
        )
        items_per_page = int(content_height // item_height + 2) * col_count
        last_item_idx = first_item_idx + items_per_page

        for item_idx, item in enumerate(self.current_display_content):
            x = content_x + (item_idx % col_count) * block_width
            y = content_y - (item_idx // col_count) * block_height - self.scroll_offset

            item.update_placement(x, y, item_width, item_height)

            if first_item_idx <= item_idx < last_item_idx:
                # Only draw if the item is actually on screen.
                item.draw(highlighted=item.hits(self.mouse_x, self.mouse_y))

            bottom_y = min(y, bottom_y)
        self.scroll_offset_space_left = window_region.height - bottom_y
        self.scroll_offset_max = (
            self.scroll_offset - self.scroll_offset_space_left + 0.25 * block_height
        )

        bgl.glDisable(bgl.GL_BLEND)

    def _draw_downloading(self, context):
        """OpenGL drawing code for the DOWNLOADING_TEXTURE state."""

        self._draw_text_on_colour(
            context, "Downloading texture from Blender Cloud", (0.0, 0.0, 0.2, 0.6)
        )

    def _draw_checking_credentials(self, context):
        """OpenGL drawing code for the CHECKING_CREDENTIALS state."""

        self._draw_text_on_colour(
            context, "Checking login credentials", (0.0, 0.0, 0.2, 0.6)
        )

    def _draw_initializing(self, context):
        """OpenGL drawing code for the INITIALIZING state."""

        self._draw_text_on_colour(context, "Initializing", (0.0, 0.0, 0.2, 0.6))

    def _draw_text_on_colour(self, context, text: str, bgcolour):
        content_height, content_width = self._window_size(context)

        bgl.glEnable(bgl.GL_BLEND)

        draw.aabox((0, 0), (content_width, content_height), bgcolour)
        draw.text(
            (content_width * 0.5, content_height * 0.7), text, fsize=20, align="C"
        )

        bgl.glDisable(bgl.GL_BLEND)

    def _window_size(self, context):
        window_region = self._window_region(context)
        content_width = window_region.width
        content_height = window_region.height
        return content_height, content_width

    def _draw_exception(self, context):
        """OpenGL drawing code for the EXCEPTION state."""

        import textwrap

        content_height, content_width = self._window_size(context)

        bgl.glEnable(bgl.GL_BLEND)
        draw.aabox((0, 0), (content_width, content_height), (0.2, 0.0, 0.0, 0.6))

        ex = self.async_task.exception()
        if isinstance(ex, pillar.UserNotLoggedInError):
            ex_msg = (
                "You are not logged in on Blender ID. Please log in at User Preferences, "
                "Add-ons, Blender ID Authentication."
            )
        else:
            ex_msg = str(ex)
            if not ex_msg:
                ex_msg = str(type(ex))
        text = "An error occurred:\n%s" % ex_msg
        lines = textwrap.wrap(text, width=100)

        draw.text((content_width * 0.1, content_height * 0.9), lines, fsize=16)

        bgl.glDisable(bgl.GL_BLEND)

    def _draw_subscribe(self, context):
        self._draw_text_on_colour(
            context, "Click to subscribe to the Blender Cloud", (0.0, 0.0, 0.2, 0.6)
        )

    def _draw_renew(self, context):
        self._draw_text_on_colour(
            context,
            "Click to renew your Blender Cloud subscription",
            (0.0, 0.0, 0.2, 0.6),
        )

    def get_clicked(self) -> typing.Optional[menu_item_mod.MenuItem]:

        for item in self.current_display_content:
            if item.hits(self.mouse_x, self.mouse_y):
                return item

        return None

    def handle_item_selection(self, context, item: menu_item_mod.MenuItem):
        """Called when the user clicks on a menu item that doesn't represent a folder."""

        from pillarsdk.utils import sanitize_filename

        self.clear_images()
        self._state = "DOWNLOADING_TEXTURE"

        node_path_components = (
            node["name"] for node in self.path_stack if node is not None
        )
        local_path_components = [
            sanitize_filename(comp) for comp in node_path_components
        ]

        top_texture_directory = bpy.path.abspath(context.scene.local_texture_dir)
        local_path = os.path.join(top_texture_directory, *local_path_components)
        meta_path = os.path.join(top_texture_directory, ".blender_cloud")

        self.log.info("Downloading texture %r to %s", item.node_uuid, local_path)
        self.log.debug("Metadata will be stored at %s", meta_path)

        file_paths = []
        select_dblock = None
        node = item.node

        def texture_downloading(file_path, *_):
            self.log.info("Texture downloading to %s", file_path)

        def texture_downloaded(file_path, file_desc, map_type):
            nonlocal select_dblock

            self.log.info("Texture downloaded to %r.", file_path)

            if context.scene.local_texture_dir.startswith("//"):
                file_path = bpy.path.relpath(file_path)

            image_dblock = bpy.data.images.load(filepath=file_path)
            image_dblock["bcloud_file_uuid"] = file_desc["_id"]
            image_dblock["bcloud_node_uuid"] = node["_id"]
            image_dblock["bcloud_node_type"] = node["node_type"]
            image_dblock["bcloud_node"] = pillar.node_to_id(node)

            if node["node_type"] == "hdri":
                # All HDRi variations should use the same image datablock, hence once name.
                image_dblock.name = node["name"]
            else:
                # All texture variations are loaded at once, and thus need the map type in the name.
                image_dblock.name = "%s-%s" % (node["name"], map_type)

            # Select the image in the image editor (if the context is right).
            # Just set the first image we download,
            if context.area.type == "IMAGE_EDITOR":
                if select_dblock is None or file_desc.map_type == "color":
                    select_dblock = image_dblock
                    context.space_data.image = select_dblock

            file_paths.append(file_path)

        def texture_download_completed(_):
            self.log.info(
                "Texture download complete, inspect:\n%s", "\n".join(file_paths)
            )
            self._state = "QUIT"

        # For HDRi nodes: only download the first file.
        download_node = pillarsdk.Node.new(node)
        if node["node_type"] == "hdri":
            download_node.properties.files = [download_node.properties.files[0]]

        signalling_future = asyncio.Future()
        self._new_async_task(
            pillar.download_texture(
                download_node,
                local_path,
                metadata_directory=meta_path,
                texture_loading=texture_downloading,
                texture_loaded=texture_downloaded,
                future=signalling_future,
            )
        )
        self.async_task.add_done_callback(texture_download_completed)

    def open_browser_subscribe(self, *, renew: bool):
        import webbrowser

        url = "renew" if renew else "join"
        webbrowser.open_new_tab("https://cloud.blender.org/%s" % url)
        self.report({"INFO"}, "We just started a browser for you.")

    def _scroll_smooth(self):
        diff = self.scroll_offset_target - self.scroll_offset
        if diff == 0:
            return

        if abs(round(diff)) < 1:
            self.scroll_offset = self.scroll_offset_target
            return

        self.scroll_offset += diff * 0.5

    def _scroll_by(self, amount, *, smooth=True):
        # Slow down scrolling up
        if smooth and amount < 0 and -amount > self.scroll_offset_space_left / 4:
            amount = -self.scroll_offset_space_left / 4

        self.scroll_offset_target = min(
            0, max(self.scroll_offset_max, self.scroll_offset_target + amount)
        )

        if not smooth:
            self._scroll_offset = self.scroll_offset_target

    def _scroll_reset(self):
        self.scroll_offset_target = self.scroll_offset = 0


class PILLAR_OT_switch_hdri(
    pillar.PillarOperatorMixin, async_loop.AsyncModalOperatorMixin, bpy.types.Operator
):
    bl_idname = "pillar.switch_hdri"
    bl_label = "Switch with another variation"
    bl_description = (
        "Downloads the selected variation of an HDRi, " "replacing the current image"
    )

    log = logging.getLogger("bpy.ops.%s" % bl_idname)

    image_name: bpy.props.StringProperty(
        name="image_name", description="Name of the image block to replace"
    )

    file_uuid: bpy.props.StringProperty(
        name="file_uuid", description="File ID to download"
    )

    async def async_execute(self, context):
        """Entry point of the asynchronous operator."""

        self.report({"INFO"}, "Communicating with Blender Cloud")

        try:
            try:
                db_user = await self.check_credentials(
                    context, REQUIRED_ROLES_FOR_TEXTURE_BROWSER
                )
                user_id = db_user["_id"]
            except pillar.NotSubscribedToCloudError as ex:
                self._log_subscription_needed(can_renew=ex.can_renew)
                self._state = "QUIT"
                return
            except pillar.UserNotLoggedInError:
                self.log.exception("Error checking/refreshing credentials.")
                self.report({"ERROR"}, "Please log in on Blender ID first.")
                self._state = "QUIT"
                return

            if not user_id:
                raise pillar.UserNotLoggedInError()

            await self.download_and_replace(context)
        except Exception as ex:
            self.log.exception("Unexpected exception caught.")
            self.report({"ERROR"}, "Unexpected error %s: %s" % (type(ex), ex))

        self._state = "QUIT"

    async def download_and_replace(self, context):
        self._state = "DOWNLOADING_TEXTURE"

        current_image = bpy.data.images[self.image_name]
        node = current_image["bcloud_node"]
        filename = "%s.taken_from_file" % pillar.sanitize_filename(node["name"])

        local_path = os.path.dirname(bpy.path.abspath(current_image.filepath))
        top_texture_directory = bpy.path.abspath(context.scene.local_texture_dir)
        meta_path = os.path.join(top_texture_directory, ".blender_cloud")

        file_uuid = self.file_uuid
        resolution = next(
            file_ref["resolution"]
            for file_ref in node["properties"]["files"]
            if file_ref["file"] == file_uuid
        )

        my_log = self.log
        my_log.info("Downloading file %r-%s to %s", file_uuid, resolution, local_path)
        my_log.debug("Metadata will be stored at %s", meta_path)

        def file_loading(file_path, file_desc, map_type):
            my_log.info(
                "Texture downloading to %s (%s)",
                file_path,
                utils.sizeof_fmt(file_desc["length"]),
            )

        async def file_loaded(file_path, file_desc, map_type):
            if context.scene.local_texture_dir.startswith("//"):
                file_path = bpy.path.relpath(file_path)

            my_log.info("Texture downloaded to %s", file_path)
            current_image["bcloud_file_uuid"] = file_uuid
            current_image.filepath = (
                file_path  # This automatically reloads the image from disk.
            )

            # This forces users of the image to update.
            for datablocks in bpy.data.user_map({current_image}).values():
                for datablock in datablocks:
                    datablock.update_tag()

        await pillar.download_file_by_uuid(
            file_uuid,
            local_path,
            meta_path,
            filename=filename,
            map_type=resolution,
            file_loading=file_loading,
            file_loaded_sync=file_loaded,
            future=self.signalling_future,
        )

        self.report({"INFO"}, "Image download complete")


# store keymaps here to access after registration
addon_keymaps = []


def image_editor_menu(self, context):
    self.layout.operator(
        BlenderCloudBrowser.bl_idname,
        text="Get image from Blender Cloud",
        icon_value=blender.icon("CLOUD"),
    )


def hdri_download_panel__image_editor(self, context):
    _hdri_download_panel(self, context.edit_image)


def hdri_download_panel__node_editor(self, context):
    if context.active_node.type not in {"TEX_ENVIRONMENT", "TEX_IMAGE"}:
        return

    _hdri_download_panel(self, context.active_node.image)


def _hdri_download_panel(self, current_image):
    if not current_image:
        return
    if "bcloud_node_type" not in current_image:
        return
    if current_image["bcloud_node_type"] != "hdri":
        return
    try:
        current_variation = current_image["bcloud_file_uuid"]
    except KeyError:
        log.warning(
            "Image %r has a bcloud_node_type but no bcloud_file_uuid property.",
            current_image.name,
        )
        return

    row = self.layout.row(align=True).split(factor=0.3)
    row.label(text="HDRi", icon_value=blender.icon("CLOUD"))
    row.prop(current_image, "hdri_variation", text="")

    if current_image.hdri_variation != current_variation:
        props = row.operator(
            PILLAR_OT_switch_hdri.bl_idname, text="Replace", icon="FILE_REFRESH"
        )
        props.image_name = current_image.name
        props.file_uuid = current_image.hdri_variation


# Storage for variation labels, as the strings in EnumProperty items
# MUST be kept in Python memory.
variation_label_storage = {}


def hdri_variation_choices(self, context):
    if context.area.type == "IMAGE_EDITOR":
        image = context.edit_image
    elif context.area.type == "NODE_EDITOR":
        image = context.active_node.image
    else:
        return []

    if "bcloud_node" not in image:
        return []

    choices = []
    for file_doc in image["bcloud_node"]["properties"]["files"]:
        label = file_doc["resolution"]
        variation_label_storage[label] = label
        choices.append((file_doc["file"], label, ""))

    return choices


def register():
    bpy.utils.register_class(BlenderCloudBrowser)
    bpy.utils.register_class(PILLAR_OT_switch_hdri)
    bpy.types.IMAGE_MT_image.prepend(image_editor_menu)
    bpy.types.IMAGE_PT_image_properties.append(hdri_download_panel__image_editor)
    bpy.types.NODE_PT_active_node_properties.append(hdri_download_panel__node_editor)

    # HDRi resolution switcher/chooser.
    # TODO: when an image is selected, switch this property to its current resolution.
    bpy.types.Image.hdri_variation = bpy.props.EnumProperty(
        name="HDRi variations",
        items=hdri_variation_choices,
        description="Select a variation with which to replace this image",
    )

    # handle the keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        print("No addon key configuration space found, so no custom hotkeys added.")
        return

    km = kc.keymaps.new(name="Screen")
    kmi = km.keymap_items.new(
        "pillar.browser", "A", "PRESS", ctrl=True, shift=True, alt=True
    )
    addon_keymaps.append((km, kmi))


def unregister():
    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    if hasattr(bpy.types.Image, "hdri_variation"):
        del bpy.types.Image.hdri_variation

    bpy.types.IMAGE_MT_image.remove(image_editor_menu)
    bpy.types.IMAGE_PT_image_properties.remove(hdri_download_panel__image_editor)
    bpy.types.NODE_PT_active_node_properties.remove(hdri_download_panel__node_editor)
    bpy.utils.unregister_class(BlenderCloudBrowser)
    bpy.utils.unregister_class(PILLAR_OT_switch_hdri)
