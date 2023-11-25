from ctypes import POINTER, Structure, c_bool, c_char, c_char_p, c_double, c_float, c_int, c_longlong, c_short, c_byte, c_void_p
from enum import Enum


##############################################################
# TYPES
##############################################################

c_float_p = POINTER(c_float)
c_int_p = POINTER(c_int)
c_byte_p = POINTER(c_byte)
c_bool_p = POINTER(c_bool)


##############################################################
# STRUCT DEFINITIONS.
##############################################################

class CY_ListBase(Structure):
    _fields_ = [
        ('first', c_void_p), # POINTER(ListBase)),
        ('last', c_void_p), # POINTER(ListBase)),
    ]

class CY_rect:
    @property
    def position(self):
        return self.xmin, self.ymin

    @property
    def size_x(self):
        return self.xmax - self.xmin

    @property
    def size_y(self):
        return self.ymax - self.ymin

    @property
    def size(self) -> tuple:
        return self.size_x, self.size_y


class CY_recti(CY_rect, Structure):
    _fields_ = [
        ('xmin', c_int),
        ('xmax', c_int),
        ('ymin', c_int),
        ('ymax', c_int)
    ]


class CY_rectf(CY_rect, Structure):
    _fields_ = [
        ('xmin', c_float),
        ('xmax', c_float),
        ('ymin', c_float),
        ('ymax', c_float)
    ]


######################################
# SPACE IMAGE

class CY_Histogram(Structure):
    _fields_ = [
        ('channels', c_int),
        ('x_resolution', c_int),
        ('data_luma', c_float * 256),
        ('data_r', c_float * 256),
        ('data_g', c_float * 256),
        ('data_b', c_float * 256),
        ('data_a', c_float * 256),
        ('xmax', c_float),
        ('ymax', c_float),
        ('mode', c_short),
        ('flag', c_short),
        ('height', c_int),
        ('co', c_float * 2 * 2),
    ]

class CY_Scopes(Structure):
    _fields_ = [
        ('ok', c_int),
        ('sample_full', c_int),
        ('sample_lines', c_int),
        ('accuracy', c_float),
        ('wavefrm_mode', c_int),
        ('wavefrm_alpha', c_float),
        ('wavefrm_yfac', c_float),
        ('wavefrm_height', c_int),
        ('vecscope_alpha', c_float),
        ('vecscope_height', c_int),
        ('minmax', c_float * 3 * 2),
        ('hist', CY_Histogram),
        ('waveform_1', c_float_p),
        ('waveform_2', c_float_p),
        ('waveform_3', c_float_p),
        ('vecscope', c_float_p),
        ('waveform_tot', c_int),
        ('_pad', c_char* 4),
    ]


class CY_ImageUser(Structure):
    _fields_ = [
        ('scene', c_void_p),
        ('framenr', c_int),
        ('frames', c_int),
        ('offset', c_int),
        ('sfra', c_int),
        ('cycl', c_char),
        ('multiview_eye', c_char),
        ('pass', c_short),
        ('tile', c_int),
        ('multi_index', c_short),
        ('view', c_short),
        ('layer', c_short),
        ('flag', c_short),
    ]


class CY_SpaceImage(Structure):
    _fields_ = [
        ('next', c_void_p),
        ('prev', c_void_p),
        # Storage of regions for inactive spaces.
        ('regionbase', CY_ListBase),
        ('spacetype', c_char),
        ('link_flag', c_char),
        # Mem Spacing.
        ('_pad0', c_char * 6),

        ('image', c_void_p),
        ('image_user', CY_ImageUser),

        ('scopes', CY_Scopes),
        ('sample_line_hist', CY_Histogram),

        ('gpd', c_void_p),

        ('cursor', c_float * 2),
        ('xof', c_float),
        ('yof', c_float),
        ('zoom', c_float),
        ('centx', c_float),
        ('centy', c_float),

        # NOTE! INCOMPLETE AS WE DON'T NEED THE FULL SCOPE.
    ]


######################################
# AREGION

class CY_SmoothView2DStore(Structure):
    _fields_ = [
        ('orig_cur', CY_rectf),
        ('new_rect', CY_rectf),
        ('time_allowed', c_double)
    ]


class CY_View2D(Structure):
    _fields_ = [
        # Tot - area that data can be drawn in; cur - region of tot that is visible in viewport.
        ('tot', CY_rectf),
        ('cur', CY_rectf),
        # Vert - vertical scroll-bar region; hor - horizontal scroll-bar region.
        ('vert', CY_recti),
        ('hor', CY_recti),
        # Mask - region (in screen-space) within which 'cur' can be viewed.
        ('mask', CY_recti),
        # Min/max sizes of 'cur' rect (only when keepzoom not set).
        ('min', c_float * 2),
        ('max', c_float * 2),
        # Allowable zoom factor range (only when (keepzoom & V2D_LIMITZOOM)) is set.
        ('minzoom', c_float),
        ('maxzoom', c_float),
        # Scroll - scroll-bars to display (bit-flag).
        ('scroll', c_short),
        # Scroll_ui - temp settings used for UI drawing of scrollers.
        ('scroll_ui', c_short),
        # Keeptot - 'cur' rect cannot move outside the 'tot' rect?
        ('keeptot', c_short),
        # Keepzoom - axes that zooming cannot occur on, and also clamp within zoom-limits.
        ('keepzoom', c_short),
        # Keepofs - axes that translation is not allowed to occur on.
        ('keepofs', c_short),
        # Settings.
        ('flag', c_short),
        # Alignment of content in totrect.
        ('align', c_short),
        # Storage of current winx/winy values, set in UI_view2d_size_update.
        ('winx', c_short),
        ('winy', c_short),
        # Storage of previous winx/winy values encountered by #UI_view2d_curRect_validate(),
        # for keep-aspect.
        ('oldwinx', c_short),
        ('oldwiny', c_short),
        # Pivot point for transforms (rotate and scale).
        ('around', c_short),
        # Usually set externally (as in, not in view2d files).
        # Alpha of vertical and horizontal scroll-bars (range is [0, 255]).
        ('alpha_vert', c_char),
        ('alpha_hor', c_char),
        # Mem Spacing.
        ('_pad', c_char * 2),
        # When set (not 0), determines how many pixels to scroll when scrolling an entire page.
        # Otherwise the height of #View2D.mask is used.
        ('page_size_y', c_float),
        # Animated smooth view.
        ('sms', POINTER(CY_SmoothView2DStore)),
        ('smooth_timer', c_longlong) # POINTER(wmTimer)
    ]


class CY_ARegion_Runtime(Structure):
    _fields_ = [
        ('category', c_char_p),
        ('visible_rect', CY_recti),
        ('offset_x', c_int),
        ('offset_y', c_int),
        ('block_name_map', c_longlong) # POINTER(GHash)
    ]


class CY_ARegion(Structure):
    @property
    def size(self) -> tuple[int, int]:
        return self.sizex, self.sizey

    def resize_x(self, width) -> None:
        self.sizex = width

    def resize_y(self, height) -> None:
        self.sizey = height

    @property
    def size_win(self) -> tuple[int, int]:
        return self.winx, self.winy

    @property
    def size_view2d(self) -> tuple[int, int]:
        return self.v2d.cur.size

    @property
    def view2d_scroll(self) -> int:
        return self.v2d.scroll

    _fields_ = [
        ('next', c_longlong), # ARegion
        ('prev', c_longlong), # ARegion
        ('v2d', CY_View2D),
        ('winrct', CY_recti),
        ('drawrct', CY_recti),
        ('winx', c_short),
        ('winy', c_short),
        # This is a Y offset on the panel tabs that represents pixels,
        # where zero represents no scroll - the first category always shows first at the top.
        ('category_scroll', c_int), # 3.6
        ('_pad0', c_char * 4), # 3.6
        ('visible', c_short),
        ('regiontype', c_short),
        ('alignment', c_short),
        ('flag', c_short),
        # Current split size in unscaled pixels (if zero it uses regiontype).
        #    To convert to pixels use: `UI_DPI_FAC * region->sizex + 0.5f`.
        #    However to get the current region size, you should usually use winx/winy from above, not this! '''
        ('sizex', c_short),
        ('sizey', c_short),
        ('do_draw', c_short),
        ('do_draw_paintcursor', c_short),
        ('overlap', c_short),
        ('flagfullscreen', c_short),
        ('type', c_longlong), # POINTER(ARegionType)
        ('uiblocks', CY_ListBase),
        ('panels', CY_ListBase),
        ('panels_category_active', CY_ListBase),
        ('ui_lists', CY_ListBase),
        ('ui_previews', CY_ListBase),
        ('handlers', CY_ListBase),
        ('panels_category', CY_ListBase),
        ('gizmo_map', c_longlong), # POINTER(wmGizmoMap)
        ('regiontimer', c_longlong), # POINTER(wmTimer)
        ('draw_buffer', c_longlong), # POINTER(wmDrawBuffer)
        ('headerstr', POINTER(c_char)),
        ('regiondata', c_void_p), # 3.6?
        ('runtime', CY_ARegion_Runtime) # ARegion_Runtime
    ]



######################################

class CyBlStruct(Enum):
    _UI_REGION = CY_ARegion
    _UI_VIEW2D = CY_View2D
    _UI_SPACE_IMAGE = CY_SpaceImage

    @classmethod
    def UI_REGION(cls, region) -> CY_ARegion:
        return cls._UI_REGION(region)

    @classmethod
    def UI_VIEW2D(cls, view2d) -> CY_View2D:
        return cls._UI_VIEW2D(view2d)

    @classmethod
    def UI_SPACE_IMAGE(cls, space_image) -> CY_SpaceImage:
        return cls._UI_SPACE_IMAGE(space_image)

    def __call__(self, bl_struct):
        return self.value.from_address(bl_struct.as_pointer())
