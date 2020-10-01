""" config module
Functions:
 - calculate_ppm
 - update_nonvisual_settings
Classes:
  None.
Description:
  A module containing basic information about default simulation / game settings
which is accessed by the client when the system is loaded. It also contains two
functions, which are used to process / change settings throughout the course
of the program."""

# external imports
from math import sqrt


# custom imports
from vectors import Vector2D


def calculate_ppm(table_length, table_width, window_width,
                  window_height, table_area_fraction):
    """ This functions calculates the scaled pixels per metre value of a given
        table and window size, so that any table dimensions can be scaled to
        the screen size appropriately.
          Inputs: table_length (an integer or float) and table_width (an integer
        or float) representing the length and width of the table being scaled in
        metres, window_width (an integer) and window_height (an integer),
        representing the dimensions of the window being scaled to in pixels, and
        table_area_fraction (a float between 0 and 0.8 (including 0.8) that
        represents the percentage of the window's area which the table should be
        scaled to cover.
          Outputs: a float detailing the number of pixels that should represent
        a metre so that the table can be correctly scaled to the window size."""
    if not isinstance(table_length, (int, float)) or \
       not isinstance(table_width, (int, float)):
        raise TypeError("Length and width should be numerical")
    elif not (isinstance(table_area_fraction, float)):
        raise TypeError("Area fraction should be numerical.")
    elif not (0 < table_area_fraction <= 0.8):
        raise ValueError("Area fraction should be 0 < fraction <= 0.8")
    elif table_length <= 0 or table_width <= 0:
        raise ValueError("Length and width must be positive")
    occupied_window_area = window_width * window_height * table_area_fraction
    table_area = table_width * table_length
    ppm = sqrt(occupied_window_area / table_area)
    return ppm


def update_nonvisual_settings(to_be_replaced, to_replace):
    """ A function that takes two settings dictionaries and updates the first's
        non-visual (i.e. important to game physics) settings to match that of
        the second dictionary.
          Inputs: to_be_replaced (a dictionary containing the settings of the
        game that are to be replaced) and to_replace (a dictionary containing
        the settings of the game that are to replace the other settings).
          Outputs: None (because the dictionary handed in is a pointer so
        changes are reflected outside)."""
    fields = ["fps", "table_length", "table_width", "hole_factor",
              "ball_radius", "gravity", "time_of_cue_impact", "max_cue_force",
              "table_coeff_of_rest", "coeff_of_static_friction",
              "coeff_of_rolling_friction", "ball_mass", "air_density",
              "ball_coeff_of_drag", "ball_coeff_of_rest", "limiting_vel"]
    for key in fields:  # updates every defined 'non-visual' setting
        to_be_replaced[key] = to_replace[key]


# a dictionary containing the default settings used by the program on startup.
settings = {
    "fps": 240,
    "screen_width": 1920,
    "screen_height": 1080,
    "scale_width": 0.9,  # the multiplier applied to screen dimensions to get to the window dimensions
    "scale_height": 0.9,  # same as above but for height
    "window_width": 1728,
    "window_height": 972,
    "side_ball_scale": 4,  # the amount the balls are scaled up by for display of balls remaining at the side 
    "display_mode": "windowed",
    "caption": "Customisable Billiards",  # caption of window
    "show_path_projection": True,
    "online_show_cue_position": True,
    "auto_focus": True,
    "show_numbers": True,  # whether to show numbers on the balls
    "save_replay": False,
    "back_time": 0.04,  # time inbetween backspaces in entry fields
    "table_length": 2.61,  
    "table_width": 1.31,
    "table_area_fraction": 0.5,
    "hole_factor": 1.92,  # the multiplier applied to the ball dimensions to find the pocket dimensions
    "ball_radius": 0.0286,
    "base_cue_offset": 0.0336,
    "max_cue_offset": 0.5336,
    "cue_length": 1.27,
    "cue_diameter": 0.011,
    "cue_angle_rate": 0.0104,
    "cue_offset_rate": 0.00208,
    "ppm": 100,  # value of pixels per metre, unit pixels
    "background_colour": (255, 255, 255),
    "general_outline_colour": (0, 0, 0),
    "general_background_colour": (255, 255, 255),
    "table_background_colour": (53, 143, 48),
    "table_outline_colour": (66, 36, 40),
    "table_hole_colour": (100, 100, 100),
    "ball_outline_colour": (0, 0, 0),
    "cue_colour": (204, 163, 117),
    "cue_outline_colour": (0, 0, 0),
    "ray_colour": (255, 255, 255),
    "message_font": "microsoftsansserif",
    "ball_font": "microsoftsansserif",
    "ui_font": "microsoftsansserif",
    "gravity": 9.80665,
    "time_of_cue_impact": 0.001,
    "max_cue_force": 1200,
    "table_coeff_of_rest": 0.6,
    "coeff_of_static_friction": 0.4,
    "coeff_of_rolling_friction": 0.04,
    "ball_mass": 0.17,
    "air_density": 1.225,
    "ball_coeff_of_drag": 0.45,
    "ball_coeff_of_rest": 0.96,
    "limiting_vel": 0.005
}
