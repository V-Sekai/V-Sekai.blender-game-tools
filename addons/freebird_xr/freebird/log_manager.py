# IMPORTANT: Don't import anything other than stdlib or blender. Don't want any other code to run before logging is setup.

import logging
import sys

LOG_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s"
LOG_FILE = "freebird.log.txt"
PREV_LOG_FILE = "freebird.log.previous.txt"


def init_logging():
    import bpy
    import logging as logging
    import tempfile
    import traceback
    from shutil import copy
    from os import path

    # set this very early to DEBUG, to ensure that we don't lose any log entries
    # while the saved log level is fetched and applied eventually in settings.py
    logging.getLogger("freebird").setLevel("DEBUG")
    logging.getLogger("bl_xr").setLevel("DEBUG")

    log_file = path.join(tempfile.gettempdir(), LOG_FILE)

    # backup the previous log file, to avoid overwriting a crashed session's logs
    try:
        if path.exists(log_file):
            prev_path = path.join(tempfile.gettempdir(), PREV_LOG_FILE)
            copy(log_file, prev_path)
    except:
        traceback.print_exc()

    # setup the logger
    if not bpy.app.background:
        logging.basicConfig(
            filename=log_file, filemode="w", level=logging.ERROR, format=LOG_FORMAT, encoding="utf-8", datefmt="%X"
        )

    # log unhandled exceptions, don't crash the process
    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        traceback.print_exc()

    sys.excepthook = handle_unhandled_exception


class DeveloperLogFilter(logging.Filter):
    def __init__(self, name: str = "") -> None:
        super().__init__(name)

        self.move_events = True
        self.drag_events = True
        self.pointer_events = True

    def filter(self, record):
        msg = record.getMessage()

        if record.filename == "bind_and_dispatch.py":
            if not self.move_events and "ControllerEvent(" in msg:
                return False
            if not self.move_events and "MouseEvent(" in msg:
                return False
            if not self.drag_events and "DragEvent(" in msg:
                return False
            if not self.pointer_events and "UIEvent(" in msg:
                return False
        if record.filename == "types.py":
            if not self.move_events and "dispatching: controller_main_move" in msg:
                return False
            if not self.move_events and "dispatching: controller_alt_move" in msg:
                return False
            if not self.move_events and "dispatching: mouse_move" in msg:
                return False
            if not self.drag_events and "dispatching: drag" in msg:
                return False
            if not self.pointer_events and "dispatching: pointer_" in msg:
                return False
            if not self.move_events and "Calling LISTENER for mouse_move" in msg:
                return False
            if not self.drag_events and "Calling LISTENER for drag" in msg:
                return False
            if not self.pointer_events and "Calling LISTENER for pointer_" in msg:
                return False
        if record.filename == "click_drag.py":
            if not self.drag_events and msg.startswith(("NOW: ", "PREV: ", "DELTA: ")):
                return False

        return True


_dev_log_filter = DeveloperLogFilter()


def enable_log_filter(state: bool):
    log = logging.getLogger("bl_xr")
    if state:
        log.addFilter(_dev_log_filter)
    else:
        log.removeFilter(_dev_log_filter)
