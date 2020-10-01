""" GUI module
Functions:
 - do_after_time
 - invert_greyscale
Classes:
 - Menu_System
Description:
  Manages the menu implementation of the system. Creates and stores all of
the UI elements and their relevant functionality required to create the menus
used in the system and controls user interaction with these menus."""

# external imports
import pygame
import glob
import os
import json
import re
import time
from threading import Thread
from datetime import timedelta
from math import floor


# internal imports
from interface import *
from vectors import Vector2D
from data import Stack, Validator
import encryption


def do_after_time(func, t=1, *args, **kwargs):
    """ This function creates a threads that calls the input function after an
        input amount of time. The thread sleeps until that amount has time has
        passed, at which point the function is called.
          Inputs: func (a function/method to be called after the set amount of
        time has passed), t (an integer/float describing the time in seconds to
        wait before the function is called) and *args and **kwargs which
        represent any arguments and keyword arguments that the function should
        be called with.
          Outputs: None (this function cannot return any results of called
        functions)."""
    def do_function(func, t):
        """ A general function that is threaded to perform the input function
            after a set amount of time.
              Inputs: func (a function/method to be called after the set amount
            of time has passed) and t (an integer/float describing the time in
            seconds to wait before the function is called).
              Outputs: None."""
        time.sleep(t)
        func(*args, **kwargs)
    Thread(target=do_function, args=(func, t)).start()


def invert_greyscale(colour):
    """ This method inverts the greyscale of a colour, calculating its new RGB-
        value by calculating '255 - value' for each colour component.
          Inputs: colour (a tuple containing 3 integers, representing the RGB-
        value of the colour).
          Outputs: a tuple containing 3 integers, representing the RGB-value of
        the new colour."""
    return (255-colour[0], 255-colour[1], 255-colour[2])


class Menu_System:
    """ The Menu_System class stores the main GUI of the program. It creates,
        displays and controls all of the different menus that the user can
        interact with and generally handles all non-simulation interaction
        between the user and program."""

    def __init__(self, surface, window_update_method, creation_method,
                 connection_method, settings, controls):
        """ The constructor for the Menu_System class, creating the Menu System
            object and all of the menus and attributes that will be used within
            the menu system of the program.
              Inputs: surface (a pygame.Surface object that all menus will be
            drawn onto), window_update_method (a function that can be called to
            update the pygame window based on values stored in settings. Used
            to apply changes in window settings), creation_method (a function
            that can be called to create a simulation e.g. offline game, online
            game, editor or replay so that menu interaction can be used to
            start a simulation), connection_method (a function that can be
            called to attempt to create a connection with the server, used when
            the menu system requires online communication), settings (a
            dictionary containing all of the settings that are used by the
            program) and controls (a ControlsObject object that contains all of
            the controls of the user in the current update, used for
            controlling the menus and menu objects).
              Outputs: None."""
        self.__controls = controls
        self.settings = settings
        self.surface = surface
        self.game_state = "offline"  # stores the current state of the menu system represented using specific strings.
        self.__has_quit = False
        self.logged_in = False
        self.active = True
        self.__connection = None
        self.temp_lobby_id = None  # stores the unique identifier of the server lobby the user is trying to join - needed if a password is requested
        self.window_update_method = window_update_method
        self.creation_method = creation_method
        self.connection_method = connection_method
        self.__create_gui()

    def __create_gui(self):
        """ This methos is a general method that creates all of the menus by
            calling all of the respective functions that create them. It acts
            as a manager for which menus should be created and used in the
            program. It also constructs other basic GUI properties including
            different font objects, padding sizes, and dictionaries of common
            attributes used by many UI elements such as checkbox sizes or label
            colours.
              Inputs: None.
              Outputs: None."""
        # first create different font and padding sizes used repeatedly by the
        # different UI elements.
        font_size = (0.02 * self.settings["window_height"] / 0.6876)
        screen_ratio = self.settings["screen_width"]/self.settings["screen_height"]
        self.window_vector = Vector2D(self.settings["window_width"], 
                                      self.settings["window_height"])
        self.max_dimension = max(self.settings["window_width"], 
                                 self.settings["window_height"])
        # change font size if below 16/9 screen ratio so UI all fits on screen.
        if screen_ratio < 16/9:
            font_size *= 0.75 
        self.ui_font = pygame.font.SysFont(self.settings["ui_font"],int(font_size))
        self.smaller_ui_font = pygame.font.SysFont(self.settings["ui_font"], int(font_size * 1.25))
        self.medium_ui_font = pygame.font.SysFont(self.settings["ui_font"], int(font_size * 1.75))
        self.larger_ui_font = pygame.font.SysFont(self.settings["ui_font"], int(font_size * 2.5))
        self.title_font = pygame.font.SysFont(self.settings["ui_font"], int(font_size * 5.25))
        self.padding_size = Vector2D(font_size/5, font_size/5)

        # Next create generic colour information and any commonly repeated
        # keyword arguments for elements to avoid repetitive code that is 
        # harder to read and comprehend.
        self.inverted_colour = invert_greyscale(self.settings["background_colour"])
        self.label_colour = {"background_colour": self.settings["background_colour"], "text_colour": self.inverted_colour}
        # we describe label colour as a dictionary so it can be easily passed
        # into label objects as arguments.
        self.checkbox_settings = [self.__controls, 
                                  self.max_dimension/40, 
                                  self.max_dimension/40]
        button_size = Vector2D(self.medium_ui_font.size("O" * 24)) + self.padding_size * 2
        self.selection_option_size = {"fixed_width": button_size.x,
                                      "fixed_height": button_size.y}

        # create attributes related to linked UI element management.
        self.slider_entry_links = []
        self.update_slider_entry_links = False  # boolean describing whether to
        # update links between sliders and entries or not.
        
        # create attributes for generic variable-length selection menus (e.g.
        # presets, lobbies, replays)
        self.current_selection_index = 0
        self.can_progress_selections = False
        self.can_regress_selections = False

        # method calls for menu creation
        self.__create_empty_menus()
        self.__create_generic_elements()
        self.__create_main_menu()
        self.__create_offline_menu()
        self.__create_lobby_creation_menu()
        self.__create_table_editor_menu()
        self.__create_settings_menu()
        self.__create_custom_sim_menu()
        self.__create_online_menu()
        self.__create_lobby_finalisation_menu()
        self.__create_lobby_select_menu()
        self.__create_lobby_password_menu()
        self.__create_password_change_menu()
        self.__create_preset_menu()
        self.__create_save_preset_menu()
        self.__create_login_menu()
        self.__create_signup_menu()
        self.__create_statistics_menu()
        self.__create_leaderboard_menu()
        self.__create_replay_select_menu()
        self.__create_replays_menu()
        
        # creation of the menu stack
        self.menu_stack = Stack()
        self.menu_stack.push(self.main_menu)

    def __create_empty_menus(self):
        """ This method creates the container objects that will become the
            menus and saves them to relevant attributes that can be accessed by
            other methods of the same class. Generally used so that all menus
            can be referred to by all UI elements, even if not yet populated.
              Inputs: None.
              Outputs: None."""
        generic_padding = {"edge_padding": self.padding_size,
                           "inner_padding": self.padding_size}
        self.main_menu = Container(2, 1, **generic_padding)
        self.offline_menu = Container(1, 2, **generic_padding)
        self.editor_menu = Container(1, 2, **generic_padding)
        self.settings_menu = Container(1, 2, **generic_padding)
        self.custom_sim_menu = Container(5, 14, **generic_padding)
        self.online_menu = Container(1, 4, **generic_padding)
        self.lobby_creation_menu = Container(1, 2, **generic_padding)
        self.lobby_finalise_menu = Container(3, 5, **generic_padding)
        self.lobby_select_menu = Container(1, 2, **generic_padding)
        self.lobby_password_entry_menu = Container(2, 2, **generic_padding)
        self.change_password_menu = Container(2, 4, **generic_padding)
        self.preset_menu = Container(3, 2, edge_padding=self.padding_size, 
                                     inner_padding=3*self.padding_size)
        self.save_preset_menu = Container(2, 2, **generic_padding)
        self.login_menu = Container(1, 2, **generic_padding)
        self.signup_menu = Container(1, 2, **generic_padding)
        self.statistics_menu = Container(1, 3, edge_padding=Vector2D(0,0), 
                                         inner_padding=self.padding_size)
        self.leaderboard_menu = Container(1, 2, **generic_padding)
        self.replays_menu = Container(1, 2, **generic_padding)
        self.replay_select_menu = Container(3, 2, **generic_padding)

    def __create_generic_elements(self):
        """ This method creates generic elements that are frequently reused by
            the GUI menus, such as the back button that returns to the previous
            menu, or validators that can be used to validate input data.
              Inputs: None.
              Outputs: None."""
        self.numeric_validator = Validator(spaces=False, upper_case=False, lower_case=False, numbers=True, symbols=False, quotation=False, currency=False, custom_chars={".": 1})  # validator for a numeric entry
        self.name_validator = Validator(upper_case=True, lower_case=True, parantheses=True, numbers=True, symbols=True, quotation=False, currency=False, max_length=24)
        self.password_validator = Validator(upper_case=True, lower_case=True, numbers=True, symbols=True, quotation=False, currency=True, max_length=1024)
        self.email_validator = Validator(spaces=False, parantheses=False, symbols=False, quotation=False, currency=False, custom_chars={"@": 1, ".": 4})
        self.final_username_validator = self.name_validator.copy()
        self.final_username_validator.min_length = 3
        self.final_username_validator.max_length = 24
        self.final_password_validator = self.password_validator.copy()
        self.final_password_validator.min_length = 8
        self.final_password_validator.max_length = 320
        self.final_email_validator = self.email_validator.copy()
        self.final_email_validator.regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
        self.final_email_validator.regex_used = True  # tell the validator to perform regex expression checks
        # create generic padding size dictionary for keywoard argument 
        # unpacking. Doesn't match every UI element but most UI elements use
        # these same padding settings
        self.generic_padding = {"outline_padding": self.padding_size,
                                "text_padding": self.padding_size}
        self.back_button = Button(self.__controls, "Return",
                                  font=self.medium_ui_font, 
                                  target=self.__menu_return,
                                  press_time=0, **self.generic_padding)

    def __create_main_menu(self):
        """ This method initialises all of the UI elements of the main menu
            container and positions all of the elements in the container to
            make a UI that can be displayed on screen. The main menu primarily
            features buttons that lead to other menus, a quit button and a
            large title card.
              Inputs: None.
              Outputs: None (adds to self.main_menu)."""
        # create buttons for the main menu
        offline_button = Button(self.__controls, "Offline", font=self.larger_ui_font, target=self.__load_offline, **self.generic_padding)
        online_button = Button(self.__controls, "Online", font=self.larger_ui_font, target=self.__load_online, **self.generic_padding)
        practice_button = Button(self.__controls, "Practice", font=self.larger_ui_font, target=self.__load_editor, **self.generic_padding)
        settings_button = Button(self.__controls, "Settings", font=self.larger_ui_font, target=self.load_menu, args=(self.settings_menu,), **self.generic_padding)
        statistics_button = Button(self.__controls, "Statistics", font=self.larger_ui_font, target=self.__load_statistics, **self.generic_padding)
        replay_button = Button(self.__controls, "Replays", font=self.larger_ui_font, target=self.load_menu, args=(self.replays_menu,), **self.generic_padding)
        quit_button = Button(self.__controls, "Quit", font=self.larger_ui_font,
                             target=self.__quit, outline_colour=(153, 0, 0), 
                             background_colour=(137, 81, 81), 
                             text_colour=(255, 0, 0), **self.generic_padding)

        # creates a smaller container to hold the main menu button elements
        button_container = Container(1, 7, edge_padding=self.padding_size, inner_padding=self.padding_size)
        buttons = [offline_button, online_button, practice_button, settings_button, statistics_button, replay_button, quit_button]
        button_data = [(button, Vector2D(1, 0.5), Vector2D(1, 0.5)) for button in buttons]  # add button positioning data
        button_container.add_elements(*button_data)

        # creates the title label for the main menu
        title_padding = self.window_vector / 30
        title_label_1 = Label("Customisable", font=self.title_font, 
                              background_colour=self.inverted_colour,
                              text_colour=self.settings["background_colour"],
                              outline_padding=Vector2D(0, 0), 
                              text_padding=title_padding)
        title_label_2 = Label("Billiards", font=self.title_font, 
                              background_colour=self.inverted_colour, 
                              fixed_width=title_label_1.size.x, 
                              fixed_height=title_label_1.size.y, centred=True,
                              text_colour=self.settings["background_colour"], 
                              outline_padding=Vector2D(0, 0), 
                              text_padding=title_padding)

        # create smaller container to hold title elements for the main menu
        title_container = Container(1, 3, edge_padding=Vector2D(0, 0), 
                                    inner_padding=Vector2D(0, -1))
        title_container.add_elements(title_label_1, title_label_2)

        # finishes constructing and positioning the main menu.
        self.main_menu.add_elements(button_container, title_container)
        self.main_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, object_size=self.main_menu.size, positioning=Vector2D(0.35, 0.5), scale_from=Vector2D(0.35, 0.5))

    def __create_offline_menu(self):
        """ This method initialises all of the UI elements of the offline
            selection menu container and positions all of the elements in the
            container to make a UI that can be displayed on screen. The offline
            menu features a title label and 3 buttons which lead to loading a
            preset, deleting a preset and creating a custom game.
              Inputs: None.
              Outputs: None (adds to self.offline_menu)."""
        # creates buttons for the offline menu
        presets_button = Button(self.__controls, "Load Preset", font=self.larger_ui_font, target=self.__load_presets_menu, args=(False,), **self.generic_padding)
        delete_presets_button = Button(self.__controls, "Delete Preset", font=self.larger_ui_font, target=self.__load_presets_menu, args=(True,), **self.generic_padding)
        custom_button = Button(self.__controls, "Custom Game", font=self.larger_ui_font, target=self.load_menu, args=(self.custom_sim_menu,), **self.generic_padding)
        self.delete_mode = False  # Boolean storing whether lobby menu is
        # opened in 'delete mode' or 'load mode'

        # creates a smaller container to hold the offline menu button elements
        self.sim_button_container = Container(3, 2, edge_padding=self.padding_size, inner_padding=self.padding_size)
        self.sim_button_container.add_elements(presets_button, delete_presets_button, custom_button)
        self.sim_button_container.add_element(self.back_button,x_index=2,y_index=1)

        # creates the title label for the offline menu
        title_label_1 = Label("OFFLINE", font=self.title_font, 
                              **self.label_colour)

        # finishes constructing and positioning the offline menu
        self.offline_menu.add_elements(title_label_1, self.sim_button_container)
        self.offline_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.offline_menu.size)

    def __create_lobby_creation_menu(self):
        """ This method initialises all of the UI elements for the lobby
            creation menu container and positions all of the elements in the
            container to make a UI that can be displayed on screen. It makes
            use of self.sim_button_menu created in self.__create_offline_menu
            as the lobby creation menu requires the same buttons.
              Inputs: None.
              Outputs: None (adds to self.lobby_creation_menu)."""
        # creates the title label for the online lobby creation options menu
        title_label_1 = Label("LOBBY CREATION", font=self.title_font, 
                              **self.label_colour)

        # creates the online lobby creation options menu using the same
        # elements as the offline menu
        self.lobby_creation_menu.add_elements(title_label_1, self.sim_button_container)
        self.lobby_creation_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.lobby_creation_menu.size)

    def __create_table_editor_menu(self):
        """ This method initialises all of the UI elements for the table editor
            menu container and positions all of the elements in the container
            to make a UI that can be displayed on screen. It makes use of
            self.sim_button_menu created in self.__create_offline_menu as the
            table editor menu requires the same buttons.
              Inputs: None.
              Outputs: None (adds to self.editor_menu)."""
        # creates the title label for the editor menu
        title_label_1 = Label("TABLE EDITOR", font=self.title_font, 
                              **self.label_colour)

        # creates the editor menu using the same elements as the offline menu
        self.editor_menu.add_elements(title_label_1, self.sim_button_container)
        self.editor_menu.pos = scale_position(Vector2D(0,0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.editor_menu.size)

    def __create_settings_menu(self):
        """ This method initialises all of the UI elements of the settings menu
            container and positions all of the elements in the container to
            make a UI that can be displayed on screen. The main menu primarily
            features sliders for window size and window display settings, as
            well as many checkbox options including auto-focusing, updating cue
            position online, showing a projection path for ball motion after
            hit and saving replays.
              Inputs: None.
              Outputs: None (adds to self.settings_menu)."""
        # creation of UI scaling for settings menu
        self.window_scales = [1/3, 1/2, 2/3, 5/6, 9/10, 1]
        window_sizes = []
        for scale in self.window_scales:
            # creates list of screen sizes based upon scales.
            width = int(self.settings["screen_width"] * scale)
            height = int(self.settings["screen_height"] * scale)
            window_sizes.append("{}x{}".format(width, height))
        self.ui_scale_slider = DiscreteSlider(
            self.__controls, 
            0,
            len(window_sizes) - 1, 
            window_sizes,
            length=self.settings["window_width"] / 5,
            height=self.settings["window_height"] / 30,
            line_colour=self.settings["general_outline_colour"],
            slider_colour=self.settings["general_outline_colour"]
        )
        current_width = int(self.settings["window_width"])
        current_height = int(self.settings["window_height"])
        self.ui_scale_slider.value = "{}x{}".format(current_width, 
                                                    current_height)
        longest_width, longest_height = self.medium_ui_font.size(window_sizes[-1])  # uses the maximum possible window size, stored at the end of the list.
        longest_size = Vector2D(longest_width, longest_height)+self.padding_size*2
        self.ui_scale_label = Label(window_sizes[-1], font=self.medium_ui_font,
                                    centred=True, fixed_width=longest_size.x,
                                    fixed_height=longest_size.y,
                                    outline_padding=self.padding_size/2)
        ui_description_label = Label("Screen resolution: ", font=self.medium_ui_font, background_colour=self.settings["background_colour"])

        # creation of display types for settings menu
        display_types = ["Windowed", "Windowed Borderless", "Fullscreen"]
        self.display_type_slider = DiscreteSlider(
            self.__controls, 
            0, 
            len(display_types) - 1, 
            display_types,
            length=self.settings["window_width"] / 5,
            height=self.settings["window_height"] / 30,
            line_colour=self.settings["general_outline_colour"],
            slider_colour=self.settings["general_outline_colour"]
        )
        self.display_type_slider.value = self.settings["display_mode"]
        ordered_types = sorted(display_types, key=lambda type: len(type))  # arrange in order of ascending string length
        longest_width, longest_height = self.medium_ui_font.size(ordered_types[-1])
        longest_size = Vector2D(longest_width, longest_height)+self.padding_size*2
        self.display_type_label = Label("Windowed Borderless", 
                                        font=self.medium_ui_font, centred=True,
                                        fixed_width=longest_size.x,
                                        fixed_height=longest_size.y,
                                        outline_padding=self.padding_size/2)
        display_type_description_label = Label("Display type: ", font=self.medium_ui_font, background_colour=self.settings["background_colour"])

        # creation of checkbox settings for settings menu
        label_settings = {"font": self.medium_ui_font, "background_colour": self.settings["background_colour"]}
        self.projection_checkbox = Checkbox(*self.checkbox_settings)
        if self.settings["show_path_projection"]:
            self.projection_checkbox.checked = True
        projection_label = Label("Enable ball projection: ", **label_settings)
        self.auto_focus_checkbox = Checkbox(*self.checkbox_settings)
        if self.settings["auto_focus"]:
            self.auto_focus_checkbox.checked = True
        auto_focus_label = Label("Enable auto focus: ", **label_settings)
        self.cue_pos_checkbox = Checkbox(*self.checkbox_settings)
        if self.settings["online_show_cue_position"]:
            self.cue_pos_checkbox.checked = True
        cue_pos_label = Label("Show cue movement online: ", **label_settings)
        self.save_replay_checkbox = Checkbox(*self.checkbox_settings)
        if self.settings["save_replay"]:
            self.save_replay_checkbox.checked = True
        save_replay_label = Label("Save replays: ", **label_settings)

        # creation of the saving options for the settings menu
        self.settings_save_button = Button(self.__controls, "Save", font=self.medium_ui_font, target=self.__save_settings, **self.generic_padding)
        self.saved_label = Label("Saved!", font=self.medium_ui_font, background_colour=self.settings["background_colour"], text_colour=(175, 175, 175))
        self.saved_label.active = False

        # placement of the settings element within the grid.
        inner_container = Container(3, 7, edge_padding=self.padding_size, 
                                    inner_padding=self.padding_size)
        d = [ui_description_label, self.ui_scale_slider, self.ui_scale_label, display_type_description_label, self.display_type_slider, self.display_type_label, projection_label, self.projection_checkbox]
        for i in range(len(d)):
            if isinstance(d[i], Label) and d[i] is not self.ui_scale_label:
                d[i] = (d[i], Vector2D(1, 0.5), Vector2D(1, 0.5))
        position_data = {"positioning": Vector2D(1, 0.5), 
                         "position_from": Vector2D(1, 0.5)}
        inner_container.add_elements(*d)
        inner_container.add_element(auto_focus_label, x_index=0, y_index=3, **position_data)
        inner_container.add_element(self.auto_focus_checkbox, x_index=1, y_index=3)
        inner_container.add_element(cue_pos_label, x_index=0, y_index=4, **position_data)
        inner_container.add_element(self.cue_pos_checkbox, x_index=1, y_index=4)
        inner_container.add_element(save_replay_label, x_index=0, y_index=5, **position_data)
        inner_container.add_element(self.save_replay_checkbox, x_index=1,y_index=5)
        inner_container.add_element(self.saved_label, x_index=0, y_index=6)
        inner_container.add_element(self.settings_save_button, x_index=1,y_index=6)
        inner_container.add_element(self.back_button, x_index=2, y_index=6)

        # creation of title for settings menu
        title_label_1 = Label("SETTINGS", font=self.title_font,
                              **self.label_colour)

        # final construction and positioning of the settings menu
        self.settings_menu.add_elements(title_label_1, inner_container)
        self.update_on_return = False
        self.settings_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.settings_menu.size)

    def __create_custom_sim_menu(self):
        """ This method initialises all of the UI elements of the custom
            simulation menu container and positions all of the elements in the
            container to make a UI that can be displayed on screen. The custom
            simulation menu primarily features several labels, sliders and
            entry boxes that can be used to customise different values used by
            the program. It also contains buttons for basic options.
              Inputs: None.
              Outputs: None (adds to self.custom_sim_menu)."""
        # construction of slider-entry links for custom simulation menu
        gravity_description, self.gravity_slider, self.gravity_entry = self.__slider_entry_link("Gravitational Field Strength: ", 0, 100, self.settings["gravity"], self.ui_font, decimal_places=6)
        self.__add_slider_entry_row(self.custom_sim_menu, 0, gravity_description, self.gravity_slider, self.gravity_entry)

        table_rest_description, self.table_rest_slider, self.table_rest_entry = self.__slider_entry_link("Table Coefficient of Restitution: ", 0, 1, self.settings["table_coeff_of_rest"], self.ui_font, decimal_places=4)
        self.__add_slider_entry_row(self.custom_sim_menu, 1, table_rest_description, self.table_rest_slider, self.table_rest_entry)
        
        ball_rest_description, self.ball_rest_slider, self.ball_rest_entry = self.__slider_entry_link("Ball Coefficient of Restitution: ", 0.5, 3, self.settings["ball_coeff_of_rest"], self.ui_font, decimal_places=4)
        self.__add_slider_entry_row(self.custom_sim_menu, 2, ball_rest_description, self.ball_rest_slider, self.ball_rest_entry)
        
        ball_drag_description, self.ball_drag_slider, self.ball_drag_entry = self.__slider_entry_link("Ball Coefficient of Drag: ", 0, 12.5, self.settings["ball_coeff_of_drag"], self.ui_font, decimal_places=4)
        self.__add_slider_entry_row(self.custom_sim_menu, 3, ball_drag_description, self.ball_drag_slider, self.ball_drag_entry)
        
        air_density_description, self.air_density_slider, self.air_density_entry = self.__slider_entry_link("Air Density: ", 0, 1000, self.settings["air_density"], self.ui_font, decimal_places=4)
        self.__add_slider_entry_row(self.custom_sim_menu, 4, air_density_description, self.air_density_slider, self.air_density_entry)
        
        ball_mass_description, self.ball_mass_slider, self.ball_mass_entry = self.__slider_entry_link("Ball Mass: ", 0.04, 2.5, self.settings["ball_mass"], self.ui_font, decimal_places=6)
        self.__add_slider_entry_row(self.custom_sim_menu, 5, ball_mass_description, self.ball_mass_slider, self.ball_mass_entry)
        
        static_friction_description, self.static_friction_slider, self.static_friction_entry = self.__slider_entry_link("Static Friction: ", 0, 25, self.settings["coeff_of_static_friction"], self.ui_font, decimal_places=3)
        self.__add_slider_entry_row(self.custom_sim_menu, 6, static_friction_description, self.static_friction_slider, self.static_friction_entry)
        
        roll_friction_description, self.roll_friction_slider, self.roll_friction_entry = self.__slider_entry_link("Rolling Friction: ", 0, 1, self.settings["coeff_of_rolling_friction"], self.ui_font, decimal_places=3)
        self.__add_slider_entry_row(self.custom_sim_menu, 7, roll_friction_description, self.roll_friction_slider, self.roll_friction_entry)
        
        impact_time_description, self.impact_time_slider, self.impact_time_entry = self.__slider_entry_link("Cue Impact Time (ms): ", 0.25, 2, self.settings["time_of_cue_impact"]*1000, self.ui_font, decimal_places=3)
        self.__add_slider_entry_row(self.custom_sim_menu, 8, impact_time_description, self.impact_time_slider, self.impact_time_entry)
        
        table_length_description, self.length_slider, self.length_entry = self.__slider_entry_link("Table Length: ", 0.95, 5, self.settings["table_length"], self.ui_font, decimal_places=2)
        self.__add_slider_entry_row(self.custom_sim_menu, 9, table_length_description, self.length_slider, self.length_entry)
        
        table_width_description, self.width_slider, self.width_entry = self.__slider_entry_link("Table Width: ", 0.95, 5, self.settings["table_width"], self.ui_font, decimal_places=2)
        self.__add_slider_entry_row(self.custom_sim_menu, 10, table_width_description, self.width_slider, self.width_entry)
        
        ball_radius_description, self.ball_radius_slider, self.ball_radius_entry = self.__slider_entry_link("Ball Radius (cm): ", 0.5, 5, self.settings["ball_radius"] * 100, self.ui_font, decimal_places=3)
        self.__add_slider_entry_row(self.custom_sim_menu, 11, ball_radius_description, self.ball_radius_slider, self.ball_radius_entry)
        
        hole_factor_description, self.hole_factor_slider, self.hole_factor_entry = self.__slider_entry_link("Pocket-to-Ball Radius Ratio: ", 1.5, 4, self.settings["hole_factor"], self.ui_font, decimal_places=2)
        self.__add_slider_entry_row(self.custom_sim_menu, 12, hole_factor_description, self.hole_factor_slider, self.hole_factor_entry)

        # initialisation of buttons for the custom simulation menu.
        save_preset_button = Button(self.__controls, "Save Preset",
                                    font=self.medium_ui_font, 
                                    target=self.load_menu, 
                                    args=(self.save_preset_menu,), 
                                    **self.generic_padding)
        start_button = Button(self.__controls, "Continue", 
                              font=self.medium_ui_font,
                              target=self.__start_simulation,
                              **self.generic_padding)

        # final construction and positioning of the custom simulation menu.
        self.__add_element_row(self.custom_sim_menu, 13, save_preset_button, start_button, self.back_button)
        self.custom_sim_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.custom_sim_menu.size)

    def __create_online_menu(self):
        """ This method initialises all of the UI elements of the online menu
            container and positions all of the elements in the container to
            make a UI that can be displayed on screen. The online menu features
            several different buttons which lead to different menus, in
            addition to a 'log out' button so that the user can log out.
              Inputs: None.
              Outputs: None (adds to self.online_menu)."""
        # online menu button initialisation 
        view_lobbies_button = Button(self.__controls, "View existing lobbies", font=self.medium_ui_font, target=self.__load_lobby_select, outline_padding=self.padding_size, text_padding=self.padding_size)
        button_size = {"fixed_width": view_lobbies_button.size.x, 
                       "fixed_height": view_lobbies_button.size.y, 
                       "centred": True}
        create_lobby_button = Button(self.__controls, "Create new lobby", font=self.medium_ui_font, target=self.load_menu, args=(self.lobby_creation_menu,), **button_size, **self.generic_padding)
        change_password_button = Button(self.__controls, "Change Password", font=self.medium_ui_font, target=self.load_menu, args=(self.change_password_menu,), **button_size, **self.generic_padding)
        button_size["fixed_width"] = view_lobbies_button.size.x / 2 - self.padding_size.x
        self.logout_button = Button(self.__controls, "Log out", font=self.medium_ui_font, target=self.__logout, **button_size, **self.generic_padding)
        # we create a seperate back button here because we want it to be of a specific size.
        back_button = Button(self.__controls, "Return", font=self.medium_ui_font, target=self.__menu_return, press_time=0, **button_size, **self.generic_padding)

        # final construction and positioning of the online menu
        bottom_container = Container(2, 1, edge_padding=Vector2D(0,0),
                                     inner_padding=self.padding_size)
        bottom_container.add_elements(self.logout_button, back_button)
        self.online_menu.add_elements(create_lobby_button, view_lobbies_button, change_password_button, bottom_container)
        self.online_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.online_menu.size)

    def __create_lobby_finalisation_menu(self):
        """ This method initialises all of the UI elements of the lobby
            finalisation menu container and positions all of the elements in
            the container to make a UI that can be displayed on screen. The
            lobby finalisation menu features two entries (for name & password),
            a checkbox, and buttons that lead to either lobby creation or
            returning to the previous menu.
              Inputs: None.
              Outputs: None (adds to self.lobby_finalise_menu)."""
        lobby_name_label = Label("Lobby Name", font=self.medium_ui_font,
                                 **self.label_colour)
        self.lobby_name_entry = Entry(self.__controls, back_time=self.settings["back_time"], initial_text="Lobby Name", font=self.ui_font, max_display_length=24, **self.generic_padding, validator=self.name_validator)
        protect_label = Label("Password Protected?", font=self.medium_ui_font, **self.label_colour)
        self.protected_checkbox = Checkbox(*self.checkbox_settings)
        self.password_label = Label("Password: ", font=self.medium_ui_font, **self.label_colour)
        self.password_label.active = False
        self.lobby_password_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, max_display_length=24, **self.generic_padding, hide_text=False, validator=self.password_validator)
        self.lobby_password_entry.active = False
        finalise_lobby_button = Button(self.__controls, "Create lobby", font=self.medium_ui_font, target=self.__create_new_lobby, **self.generic_padding)
        
        # final construction and positioning of the lobby finalisation menu
        self.lobby_finalise_menu.add_elements(lobby_name_label, 
                                              self.lobby_name_entry)
        self.__add_element_row(self.lobby_finalise_menu, 1, protect_label, self.protected_checkbox)
        self.__add_element_row(self.lobby_finalise_menu, 2, self.password_label, self.lobby_password_entry)
        self.__add_element_row(self.lobby_finalise_menu, 3, finalise_lobby_button, self.back_button)
        self.lobby_finalise_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.lobby_finalise_menu.size)

    def __create_lobby_select_menu(self):
        """ This method initialises all of the UI elements of the lobby
            selection menu container and positions all of the elements in the
            container to make a UI that can be displayed on screen. The lobby
            selection menu features several buttons and labels that descirbe
            and allow users to join different lobbies, as well as checkboxes to
            alter which lobbies should be shown and buttons to refresh or leave
            the menu.
              Inputs: None.
              Outputs: None (adds to self.lobby_select_menu)."""
        # initialisation of the UI elements for the lobby selection menu
        self.lobby_selection_rows = []  # contains rows of visual elements displayed on the screen
        self.lobby_data = []  # contains data about the lobbies being viewed
        for i in range(5):
            button = Button(self.__controls, "...", font=self.medium_ui_font,
                            target=self.__join_lobby, args=(i,),
                            **self.selection_option_size,
                            **self.generic_padding)
            players_label = Label("0/2", font=self.medium_ui_font, 
                                  **self.label_colour)
            private_label = Label("Private", font=self.medium_ui_font,
                                  **self.label_colour)
            button.active = False
            players_label.active = False
            private_label.active = False
            self.lobby_selection_rows.append([button, players_label,
                                              private_label])
        hide_full_label = Label("Hide full lobbies: ", font=self.medium_ui_font, **self.label_colour)
        self.hide_full_checkbox = Checkbox(*self.checkbox_settings)
        self.hide_full_checkbox.checked = True
        hide_private_label = Label("Hide private lobbies: ", font=self.medium_ui_font, **self.label_colour)
        self.hide_private_checkbox = Checkbox(*self.checkbox_settings)
        next_lobbies_button = Button(self.__controls, ">>>", font=self.larger_ui_font, target=self.__next_selections, args=(self.__process_lobby_data,), **self.generic_padding)
        prev_lobbies_button = Button(self.__controls, "<<<", font=self.larger_ui_font, target=self.__prev_selections, args=(self.__process_lobby_data,), **self.generic_padding)
        refresh_button = Button(self.__controls, "Refresh Lobbies", font=self.medium_ui_font, target=self.__refresh_lobby_data, press_time=1, **self.generic_padding)

        # final construction and positioning of the lobby selection menu
        lobby_selections_container = Container(3, 5, edge_padding=self.padding_size, inner_padding=self.padding_size, has_outline=True)
        for row in self.lobby_selection_rows:
            lobby_selections_container.add_elements(*row)
        upper_container = Container(3, 1, edge_padding=self.padding_size,
                                    inner_padding=3*self.padding_size)
        upper_container.add_elements(prev_lobbies_button, lobby_selections_container, next_lobbies_button)
        other_options = Container(2, 2, edge_padding=self.padding_size,
                                  inner_padding=self.padding_size)
        other_options.add_elements(hide_full_label, self.hide_full_checkbox, hide_private_label, self.hide_private_checkbox)
        bottom_container = Container(2, 2, edge_padding=self.padding_size,
                                     inner_padding=2*self.padding_size)
        bottom_container.add_elements(other_options, refresh_button)
        bottom_container.add_element(self.back_button, x_index=1, y_index=1)
        self.lobby_select_menu.add_elements(upper_container, bottom_container)
        self.lobby_select_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.lobby_select_menu.size)

    def __create_lobby_password_menu(self):
        """ This method initialises all of the UI elements of the lobby
            password entry menu container and positions all of the elements in
            the container to make a UI that can be displayed on screen. The
            lobby password entry menu features an entry in which users can
            enter the lobby password, as well as a label that describes the
            entry and buttons to either submit the password or quit the menu.
              Inputs: None.
              Outputs: None (adds to self.lobby_password_entry_menu)."""
        # initialisation of visual elements for the lobby password entry menu
        requested_password_label = Label("Enter password: ", font=self.medium_ui_font, **self.label_colour)
        self.requested_password_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, max_display_length=24, **self.generic_padding, hide_text=True, validator=self.password_validator)
        self.password_submit_button = Button(self.__controls, "Submit", font=self.medium_ui_font, target=self.__submit_password, **self.generic_padding)

        # final construction and positioning of the password entry menu
        self.lobby_password_entry_menu.add_elements(requested_password_label, self.requested_password_entry, self.password_submit_button, self.back_button)
        self.lobby_password_entry_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.lobby_password_entry_menu.size)

    def __create_password_change_menu(self):
        """ This method initialises all of the UI elements of the password
            change menu container and positions all of the elements in the
            container to make a UI that can be displayed on screen. The
            password change menu features entries in which users can enter
            their current password and their new password (twice, to confirm
            it), as well as submit and return buttons.
              Inputs: None.
              Outputs: None (adds to self.change_password_menu)."""
        # initialisation of the visual elements for the password change menu.
        current_pass_label = Label("Current Password: ", font=self.medium_ui_font, **self.label_colour)
        new_pass_label = Label("New Password: ", font=self.medium_ui_font, **self.label_colour)
        confirm_new_pass_label = Label("Confirm New Password: ", font=self.medium_ui_font, **self.label_colour)
        password_entry_args = {
            "back_time": self.settings["back_time"], 
            "font": self.ui_font,
            "max_display_length": 24, 
            "outline_padding": self.padding_size,
            "text_padding": self.padding_size, 
            "hide_text":False, 
            "validator": self.password_validator
        }  # defined here to avoid lots of repeated arguments in the code
        self.current_password_entry = Entry(self.__controls, 
                                            **password_entry_args)
        self.current_password_entry.hide_text = True
        self.new_password_entry = Entry(self.__controls, **password_entry_args)
        self.confirm_new_password_entry = Entry(self.__controls, 
                                                **password_entry_args)
        self.change_pass_button = Button(self.__controls, "Change Password", font=self.medium_ui_font, target=self.__submit_password_change, **self.generic_padding)

        # final construction and positioning of the password entry menu
        self.change_password_menu.add_elements(current_pass_label, self.current_password_entry, new_pass_label, self.new_password_entry, confirm_new_pass_label, self.confirm_new_password_entry, self.change_pass_button, self.back_button)
        self.change_password_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.change_password_menu.size)

    def __create_preset_menu(self):
        """ This method initialises all of the UI elements of the preset menu
            container and positions all of the elements in the container to
            make a UI that can be displayed on screen. The preset menu features
            several buttons that allow users to select presets, and a button to
            leave the menu.
              Inputs: None.
              Outputs: None (adds to self.preset_menu)."""
        # initialisation of the preset menu elements:
        self.preset_elements = []  # contains button elements used to select different presets in the preset menu.
        self.preset_data = []  # contains data of loaded presets
        for i in range(5):
            self.preset_elements.append(
                Button(self.__controls, "...", font=self.medium_ui_font,
                       target=self.__select_preset, args=(i,),
                       **self.selection_option_size, **self.generic_padding)
            )
        next_preset_button = Button(self.__controls, ">>>", font=self.larger_ui_font, target=self.__next_selections, args=(self.__process_preset_data,), **self.generic_padding)
        prev_preset_button = Button(self.__controls, "<<<", font=self.larger_ui_font, target=self.__prev_selections, args=(self.__process_preset_data,), **self.generic_padding)

        # final construction and positioning of the presets menu
        preset_selections_container = Container(1, 5, edge_padding=self.padding_size, inner_padding=self.padding_size, has_outline=True)
        for element in self.preset_elements:
            preset_selections_container.add_element(element)
        self.preset_menu.add_elements(prev_preset_button, preset_selections_container, next_preset_button)
        self.preset_menu.add_element(self.back_button, x_index=2, y_index=1)
        self.preset_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.preset_menu.size)

    def __create_save_preset_menu(self):
        """ This method initialises all of the UI elements of the save preset
            menu container and positions all of the elements in the container
            to make a UI that can be displayed on screen. The save preset menu
            features an entry to let users input a preset name and buttons to
            let them either save the preset or return.
              Inputs: None.
              Outputs: None (adds to self.save_preset_menu)."""
        # initialisation of the visual elements for the preset saving menu:
        new_preset_label = Label("Preset Name: ", font=self.medium_ui_font,
                                 **self.label_colour)
        preset_name_validator = self.name_validator.copy()
        preset_name_validator.max_length = 64
        self.preset_name_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, max_display_length=20, **self.generic_padding, validator=preset_name_validator)
        save_preset_button = Button(self.__controls, "Save", font=self.medium_ui_font, target=self.__save_preset, **self.generic_padding)

        # final construction and positioning of the new preset name entry menu
        bottom_container = Container(2, 1, edge_padding=self.padding_size,
                                     inner_padding=self.padding_size)
        bottom_container.add_elements(save_preset_button, self.back_button)
        self.save_preset_menu.add_elements(new_preset_label, self.preset_name_entry, self.saved_label, bottom_container)
        self.save_preset_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.save_preset_menu.size)

    def __create_login_menu(self):
        """ This method initialises all of the UI elements of the login menu
            container and positions  all of the elements in the container to
            make a UI that can be displayed on screen. The login menu features
            labels and entries to let users input their username and password,
            as well as buttons to let them log in, go to the account creation
            menu, or quit the menu.
              Inputs: None.
              Outputs: None (adds to self.login_menu)."""
        # initialisation of the visual elements for the login menu
        username_label = Label("Username: ", font=self.medium_ui_font,
                               **self.label_colour)
        self.username_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, max_display_length=24, **self.generic_padding, validator=self.name_validator)
        password_label = Label("Password: ", font=self.medium_ui_font, **self.label_colour)
        self.password_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, fixed_width=self.username_entry.size.x, fixed_height=self.username_entry.size.y, **self.generic_padding, hide_text=True, validator=self.password_validator)
        self.pass_visibility_button = Button(self.__controls, "Show", font=self.ui_font, target=self.__change_password_visibility, **self.generic_padding)
        login_button = Button(self.__controls, "Login", font=self.medium_ui_font, target=self.__attempt_login, **self.generic_padding)
        goto_signup_button = Button(self.__controls, "Sign up", font=self.medium_ui_font, target=self.__load_signup_menu, **self.generic_padding)
        back_button = Button(self.__controls, "Return", font=self.medium_ui_font, target=self.__return_from_login_menu, press_time=0, **self.generic_padding)
        # we use a custom back_button to call __return_from_login_menu instead
        # of __menu_return to clear the sensitive entries' text.

        # final construction and positioning of the login menu
        entry_container = Container(3, 3, edge_padding=self.padding_size,
                                    inner_padding=self.padding_size)
        entry_container.add_elements((username_label, Vector2D(1, 0.5), Vector2D(1, 0.5)), self.username_entry)
        self.__add_element_row(entry_container, 1, (password_label, Vector2D(1, 0.5), Vector2D(1, 0.5)), self.password_entry, self.pass_visibility_button)
        button_container = Container(3, 1, edge_padding=self.padding_size, inner_padding=3*self.padding_size)
        button_container.add_elements(login_button, goto_signup_button,
                                      back_button)
        self.login_menu.add_elements(entry_container, button_container)
        self.login_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.login_menu.size)

    def __create_signup_menu(self):
        """ This method initialises all of the UI elements of the signup menu
            container and positions all of the elements in the container to
            make a UI that can be displayed on screen. The signup menu features
            labels and entries to let users input their new username, email and
            password (with an extra entry to confirm their password) as well as
            buttons to either complete the sign up or return to the login menu.
              Inputs: None.
              Outputs: None (adds to self.signup_menu)."""
        # initialisation of the visual elements for the signup menu
        username_label = Label("Username: ", font=self.medium_ui_font, 
                               **self.label_colour)
        password_label = Label("Password: ", font=self.medium_ui_font, 
                               **self.label_colour)
        confirm_label = Label("Confirm Password: ", font=self.medium_ui_font,
                              **self.label_colour)
        email_label = Label("Email: ", font=self.medium_ui_font, 
                            **self.label_colour)
        self.email_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, fixed_width=self.username_entry.size.x, fixed_height=self.username_entry.size.y, **self.generic_padding, validator=self.email_validator)
        self.confirm_pass_entry = Entry(self.__controls, back_time=self.settings["back_time"], font=self.ui_font, fixed_width=self.username_entry.size.x, fixed_height=self.username_entry.size.y, **self.generic_padding, hide_text=False, validator=self.password_validator)
        signup_button = Button(self.__controls, "Create Account", font=self.medium_ui_font, target=self.__create_new_account, **self.generic_padding)
        goto_login_button = Button(self.__controls, "Return to Login", font=self.medium_ui_font, target=self.__return_to_login_menu, **self.generic_padding)

        # final construction and positioning of the signup menu
        entry_container = Container(2, 4, edge_padding=self.padding_size,
                                    inner_padding=self.padding_size)
        signup_elements = [username_label, self.username_entry, password_label, self.password_entry, confirm_label, self.confirm_pass_entry, email_label, self.email_entry]
        # Add required padding (positioning) to each label element
        for i in range(0, len(signup_elements), 2):
            signup_elements[i] = (signup_elements[i], Vector2D(1, 0.5), 
                                  Vector2D(1, 0.5))
        entry_container.add_elements(*signup_elements)
        button_container = Container(2, 1, edge_padding=self.padding_size,
                                     inner_padding=3*self.padding_size)
        button_container.add_elements(signup_button, goto_login_button)
        self.signup_menu.add_elements(entry_container, button_container)
        self.signup_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.signup_menu.size)

    def __create_statistics_menu(self):
        """ This method initialises all of the UI elements of the statistics
            menu container and positions all of the elements in the container
            to make a UI that can be displayed on screen. The statistics menu
            features a 'loading' label by default along with a logout and
            return button. It should also feature an inactive (hidden)
            leaderboard button to appear when the statistics have fully loaded.
              Inputs: None.
              Outputs: None (adds to self.statistics_menu)."""
        # initialisation of UI elements for the statistics menu
        loading_stats_label = Label("Loading your statistics...", font=self.larger_ui_font, **self.label_colour)
        title_label_1 = Label("STATISTICS", font=self.title_font,
                              **self.label_colour)
        self.leaderboards_button = Button(self.__controls, "Leaderboards", font=self.medium_ui_font, target=self.__load_leaderboards, **self.generic_padding)
        self.leaderboards_button.active = False

        # final construction and positioning of the statistics menu
        button_container = Container(3, 1, edge_padding=Vector2D(0,0),
                                     inner_padding=self.padding_size)
        button_container.add_elements(self.logout_button, self.leaderboards_button, self.back_button)
        self.statistics_menu.add_elements(title_label_1, loading_stats_label, button_container)
        self.statistics_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.statistics_menu.size)

    def __create_leaderboard_menu(self):
        """ This method initialises all of the UI elements of the leaderboard
            menu container and positions all of the elements in the container
            to make a UI that can be displayed on screen. The leaderboard menu
            features labels showing the top 5 users within different
            categories, as well as buttons to request different categories and
            display these leaderboards, as well as quit the menu.
              Inputs: None.
              Outputs: None (adds to self.leaderboard_menu)."""
        # initialisation of UI elements for the leaderboards menu:
        ranking_label = Label("Rank", font=self.medium_ui_font, 
                              **self.label_colour)
        username_size = Vector2D(self.smaller_ui_font.size("O" * 24)) + self.padding_size * 2
        user_label = Label("User ", font=self.medium_ui_font, 
                           **self.label_colour)
        category_size = Vector2D(self.medium_ui_font.size("Top Competitive Games Played")) + self.padding_size * 2  # based on largest category name available; hard-coded.
        self.category_label = Label("Top Games Played", font=self.medium_ui_font, fixed_width=category_size.x, fixed_height=category_size.y, **self.label_colour)
        self.leaderboard_elements = []
        for i in range(5):
            rank_label = Label(str(i+1), font=self.medium_ui_font, 
                               text_padding=self.padding_size, 
                               **self.label_colour)
            username_label = Label("...", font=self.smaller_ui_font,
                                   fixed_width=username_size.x, 
                                   fixed_height=username_size.y, 
                                   text_padding=self.padding_size, 
                                   **self.label_colour)
            data_label = Label("...", font=self.smaller_ui_font, 
                               fixed_width=category_size.x,
                               fixed_height=category_size.y, 
                               text_padding=self.padding_size, 
                               **self.label_colour)
            self.leaderboard_elements.append(rank_label)
            self.leaderboard_elements.append(username_label)
            self.leaderboard_elements.append(data_label)
        categories = ["Games Played", "Victories", "Win Rate", 
                      "Competitive Played"]
        category_buttons = []
        for category in categories:
            category_button = Button(self.__controls, category, 
                                     font=self.medium_ui_font,
                                     target=self.__request_category,
                                     args=(category,),
                                     outline_padding=self.padding_size, 
                                     text_padding=2*self.padding_size)
            category_buttons.append((category_button, Vector2D(0, 0.5), 
                                     Vector2D(0, 0.5)))

        # final construction and positioning of the leaderboards menu
        data_container = Container(3, 6, edge_padding=self.padding_size,
                                   inner_padding=self.padding_size)
        data_container.add_elements(ranking_label, (user_label, Vector2D(0, 0.5), Vector2D(0, 0.5)), self.category_label, *self.leaderboard_elements)
        category_container = Container(4, 1, edge_padding=self.padding_size,
                                       inner_padding=self.padding_size)
        category_container.add_elements(*category_buttons)
        button_container = Container(1, 2, edge_padding=self.padding_size,
                                     inner_padding=self.padding_size)
        button_container.add_elements(category_container, (self.back_button, Vector2D(1, 0.5), Vector2D(1, 0.5)))
        self.leaderboard_menu.add_elements(data_container, button_container)
        self.leaderboard_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.leaderboard_menu.size)

    def __create_replay_select_menu(self):
        """ This method initialises all of the UI elements of the replay select
            menu container and positions all of the elements in the container
            to make a UI that can be displayed on screen. The replay select
            menu features several buttons that allow users to select presets,
            and a button to leave the menu.
              Inputs: None.
              Outputs: None (adds to self.replay_select_menu)."""
        # initialisation of the replay select menu elements:
        self.replay_elements = []
        self.replay_data = []
        for i in range(5):
            replay_button = Button(self.__controls, "...", 
                                   font=self.medium_ui_font, 
                                   target=self.__select_replay, args=(i,),
                                   **self.selection_option_size,
                                   **self.generic_padding)
            self.replay_elements.append(replay_button)
        next_replays_button = Button(self.__controls, ">>>", font=self.larger_ui_font, target=self.__next_selections, args=(self.__process_replay_data,), **self.generic_padding)
        prev_replays_button = Button(self.__controls, "<<<", font=self.larger_ui_font, target=self.__prev_selections, args=(self.__process_replay_data,), **self.generic_padding)

        # final construction and positioning of the replay select menu
        replay_selections_container = Container(1, 5, edge_padding=self.padding_size, inner_padding=self.padding_size, has_outline=True)
        for element in self.replay_elements:
            replay_selections_container.add_element(element)
        self.replay_select_menu.add_elements(prev_replays_button, replay_selections_container, next_replays_button)
        self.replay_select_menu.add_element(self.back_button, 
                                            x_index=2, y_index=1)
        self.replay_select_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.replay_select_menu.size)

    def __create_replays_menu(self):
        """ This method initialises all of the UI elements of the replays menu
            container and positions  all of the elements in the container to
            make a UI that can be displayed on screen. The replays menu
            features three buttons that either load the replay select menu to
            play a replay, load the replay select menu to delete a replay, or
            quit the menu.
              Inputs: None.
              Outputs: None (adds to self.replays_menu)."""
        # initialisation of the UI elements for the replay menu
        play_replay_button = Button(self.__controls, "Play Replay", font=self.larger_ui_font, target=self.__load_replay_selection, args=(False,), outline_padding=self.padding_size, text_padding=2*self.padding_size)
        delete_replay_button = Button(self.__controls, "Delete Replay", font=self.larger_ui_font, target=self.__load_replay_selection, args=(True,), outline_padding=self.padding_size, text_padding=2*self.padding_size)
        # the replay selection menu uses the same self.delete_mode attribute
        # that the preset selection menu uses for efficiency, and there is no
        # issue with overlap, as both menus cannot be active at once.
        title_label_1 = Label("REPLAYS", font=self.title_font,
                              **self.label_colour)

        # final construction and positioning of the replay menu
        inner_container = Container(2, 2, edge_padding=Vector2D(0,0),
                                    inner_padding=self.padding_size)
        inner_container.add_elements(play_replay_button, delete_replay_button)
        inner_container.add_element(self.back_button, x_index=1, y_index=1)
        self.replays_menu.add_elements(title_label_1, inner_container)
        self.replays_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), object_size=self.replays_menu.size)
        
    def __load_online(self):
        """ This method loads the online menu. It calls the load_menu function
            with the online menu if the client is logged in (using the
            self.logged_in attribute), or the login menu if the client is not.
            If the client has not yet attempted a connection with the server,
            it also calls for the creation of a connection 
            (self.conection_method()). It finally changes the game_state
            attribute to be "online" so that other parts of the menu system
            know that the user is online.
              Inputs: None.
              Outputs: None."""
        if self.__connection is None or not self.__connection.in_use:
            self.connection_method()
        elif self.logged_in:
            self.load_menu(self.online_menu)
        else:
            self.load_menu(self.login_menu)
        self.game_state = "online"

    def __load_offline(self):
        """ This method loads the offline menu. It calls the load_menu function
            with the offline menu and changes the game_state attribute to be
            "offline" so that other parts of the menu system know that the user
            is offline.
              Inputs: None.
              Outputs: None."""
        self.load_menu(self.offline_menu)
        self.game_state = "offline"

    def __load_statistics(self):
        """ This method loads the statistics menu. If the client is not already
            connected, this calls the function stored in the connection_method
            attribute to create a connection with the server. If the user is
            already logged in (stored in the self.logged_in attribute), this
            sends a command to the server to retrive user statistics through
            the connection and calls the load_menu function with the statistics
            menu. Otherwise, it calls the load_menu function with the login
            menu. Finally, it updates the game_state attribute to 'statistics'
            to reflect that the statistics section of the UI is being accessed.
              Inputs: None.
              Outputs: None."""
        if self.__connection is None or not self.__connection.in_use:
            self.connection_method()
        elif self.logged_in:
            self.__connection.send_queue.enqueue({"command": "retrieve_user_statistics", "args": ("connection",)})  # retrieve user statistics
            self.load_menu(self.statistics_menu)
        else:
            self.load_menu(self.login_menu)
        self.game_state = "statistics"

    def load_lobby_password_menu(self):  
        """ This method loads the lobby password menu. It simply calls the
            load_menu method with the lobby password entry menu. This is its
            own unique method so that it can be easily called and accessed by
            online communication without having to supply arguments, which is 
            needed as the server may request a lobby password.
              Inputs: None.
              Outputs: None."""
        self.load_menu(self.lobby_password_entry_menu)

    def __load_editor(self):
        """ This method loads the editor menu. It calls the load_menu function
            with the editor menu, and also changes the game_state variable to
            'editor' so that the rest of the menu system knows that the client
            is currently accessing the editor section of the program.
              Inputs: None.
              Outputs: None."""
        self.load_menu(self.editor_menu)
        self.game_state = "editor"
    
    def __load_signup_menu(self):
        """ This method loads the signup menu. It calls the load_menu function
            with the signup menu, and also changes the password entry to no
            longer hide text.
              Inputs: None.
              Outputs: None."""
        self.load_menu(self.signup_menu)
        self.password_entry.hide_text = False
        self.password_entry.update_text()
    
    def __return_to_login_menu(self):
        """ This method returns to the login menu from the signup menu. It does
            this by calling the __menu_return method and then modifies the
            password entry to begin hiding its text again. It also clears the
            text in the password confirmation and email entries. It then hides
            the text within the password entry and updates the login menu's UI
            elements (namely the pass_visibility_button) to reflect this.
              Inputs: None.
              Outputs: None."""
        self.__menu_return()
        self.password_entry.hide_text = True
        self.password_entry.update_text()
        self.confirm_pass_entry.text = ""
        self.confirm_pass_entry.update_text()
        self.email_entry.text = ""
        self.email_entry.update_text()
        self.pass_visibility_button.text = "Show"
    
    def __return_from_login_menu(self):
        """ This method quits the login menu. It calls the __menu_return 
            method, but also clears the username and password entries 
            in case another user comes to use the program.
              Inputs: None.
              Outputs: None."""
        self.__menu_return()
        self.username_entry.text = ""
        self.username_entry.update_text()
        self.password_entry.text = ""
        self.password_entry.update_text()
    
    def __change_password_visibility(self):
        """ This method changes the visibility of the password stored in
            self.password_entry. It applies a NOT operation to the
            password_entry's hide_text attribute, and then updates this entry.
            It also updates the pass_visbility_button's text to either "Show"
            or "Hide" depending on the password's visibility.
              Inputs: None.
              Outputs: None."""
        is_hidden = not self.password_entry.hide_text
        self.password_entry.hide_text = is_hidden
        self.password_entry.update_text()
        self.pass_visibility_button.text = "Show" if is_hidden else "Hide"

    def __load_leaderboards(self):
        """ This method loads the leaderboard menu. It calls the load_menu
            method with the leaderboard menu, and calls the __request_category
            method with the default 'Games Played' category to be displayed.
              Inputs: None.
              Outputs: None."""
        self.load_menu(self.leaderboard_menu)
        self.__request_category("Games Played")

    def __request_category(self, category):
        """ This method requests the information for the top 5 players of an
            input leaderboard category from the server. This sends the request,
            and also alters the category label's text (self.category_label) to
            reflect this change in category.
              Inputs: category (a string describing the category requested).
              Outputs: None."""
        self.category_label.text = "Top {}:".format(category)
        self.__connection.send_queue.enqueue({"command": "request_leaderboard", "args": ("connection", category.replace(" ", ""))})

    def load_leaderboard_category(self, leaderboard_data):
        """ This method loads the information received from requesting a
            leaderboard category. It formats the received information about the
            top 5 players, seperating the players and inserting the data into
            the leaderboard UI elements (self.leaderboard_elements). If the
            leaderboard is not filled, it also adds a '...' to any empty
            elements. It also handles cases of overlapping scores by assigning
            identical ranks e.g. "1 -> 1 -> 1 -> 4 -> 5".
              Inputs: leaderboard_data (a list/tuple of two-item tuples where
            the first item is a string containing the user's username and the
            second is a string containing the data related to those users and
            the current category).
              Outputs: None."""
        for i in range(5):
            if i >= len(leaderboard_data):
                # we multiply by 3 to change every 3rd element (as there are 3
                # UI elements per user)
                self.leaderboard_elements[i*3].text = "..."
                self.leaderboard_elements[i*3+1].text = "..."
                self.leaderboard_elements[i*3+2].text = "..."
            else:
                if i>0 and leaderboard_data[i][1] == leaderboard_data[i-1][1]:
                    # if data identical for two consecutive users, assign the
                    # same rank to both of them.
                    ranking = self.leaderboard_elements[(i-1)*3].text
                else:
                    ranking = str(i + 1)
                self.leaderboard_elements[i*3].text = ranking
                self.leaderboard_elements[i*3+1].text = leaderboard_data[i][0]
                self.leaderboard_elements[i*3+2].text = str(leaderboard_data[i][1])

    def receive_statistics(self, user_stats):
        """ This method receives requested user statistic data from the server
            and formats them into different UI Label elements to be displayed
            on the screen by adding them to the statistics_menu container. It
            applies formatting to any relevant elements e.g. by formatting time
            into different formats, formatting percentages, and putting the
            last game information into a seperate, boxed container.
              Inputs: user_stats (a dictionary containing several different
            user statistics. Each key in the dictionary is a string containing
            the name of the statistic and each key is the value associated with
            the user and that statistic. The first 3 items in the dictionary
            should be general user statistics, whilst the 4th through 10th
            items should be last game statistics. The items from the 11th index
            onwards are general overall user statistical information).
              Outputs: None."""
        self.leaderboards_button.active = True  # allows access to leaderboards
        upper_stat_container = Container(1, 3, edge_padding=self.padding_size,
                                         inner_padding=Vector2D(0,0),
                                         has_outline=True)
        larger_padding = Vector2D(self.padding_size.x * 5, self.padding_size.y)
        massive_padding = self.window_vector * 0.2  # 1/5th of the window size
        last_game_stats_container = Container(4, 4, 
                                              edge_padding=self.padding_size,
                                              inner_padding=larger_padding)
        lower_stat_container = Container(6, 7, edge_padding=self.padding_size,
                                         inner_padding=larger_padding)
        # we format account age to be time in days; this is more understandable
        account_age = timedelta(seconds=floor(user_stats["Account Age"])).days
        user_stats["Account Age"] = "{} days".format(account_age)
        for stat in ["Overall Win Rate", "Competitive Win Rate"]:
            if user_stats[stat] is None:
                user_stats[stat] = "N/A"
            else:
                # format percentage-based statistics
                user_stats[stat] = '{:.2f}%'.format(user_stats[stat] * 100)
        # format time into a H:MM:SS format
        for stat in ["Length", "Total Time Played", "Mean Time Played"]:
            if user_stats[stat] is None:
                user_stats[stat] = 0
            user_stats[stat] = str(timedelta(seconds=floor(user_stats[stat])))

        ui_elements = []
        for stat in user_stats:
            # convert all stats in the dictionary to UI elements (one Label for
            # the key, one for the value)
            ui_elements.append(Label("{}: ".format(stat), font=self.ui_font, 
                                     **self.label_colour))
            ui_elements.append(Label(str(user_stats[stat]), font=self.ui_font,
                                     **self.label_colour))
        # we next make every UI element after the first 6 (which contain
        # general account info) left alligned.
        ui_elements = ui_elements[:6] + [(element, Vector2D(0, 0.5), Vector2D(0, 0.5)) for element in ui_elements[6:]]
        
        # we then create a container for each set of two elements (the
        # describing label and value pair) in the first 6 elements.
        for i in range(0, 5, 2):
            smaller_container = Container(1, 2, edge_padding=Vector2D(0,0),
                                          inner_padding=Vector2D(0,0))
            smaller_container.add_elements(*ui_elements[i:i+2])
            upper_stat_container.add_element(smaller_container)
        # we then add the UI elements to the different containers
        last_game_stats_container.add_elements(*ui_elements[6:20])
        lower_stat_container.add_elements(*ui_elements[20:])
        last_game_container = Container(1, 2, edge_padding=Vector2D(self.padding_size), inner_padding=self.padding_size, has_outline=True)
        last_game_title = Label("Your Last Game: ", font=self.medium_ui_font,
                                **self.label_colour)
        last_game_container.add_elements(last_game_title, 
                                         last_game_stats_container)
        # combine all the different containers in the stats menu together
        full_upper_container = Container(2, 1, edge_padding=Vector2D(0,0),
                                         inner_padding=massive_padding)
        full_upper_container.add_elements(upper_stat_container, 
                                          last_game_container)
        full_container = Container(1, 2, edge_padding=Vector2D(0,0),
                                   inner_padding=self.padding_size)
        full_container.add_elements(full_upper_container, lower_stat_container)
        self.statistics_menu.add_element(full_container, x_index=0, y_index=1)
        # re-calculate the position of the statistics menu so that it remains
        # centred with the new added UI elements.
        self.statistics_menu.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), scale_from=Vector2D(0.5, 0.5), object_size=self.statistics_menu.size)

    def update_server_connection_status(self, connected_state):
        """ This method updates GUI with connection status information,
            allowing the menu system to be manipulated based upon whether the
            client is connected or not. If it is, it calls the load_menu
            function with the login menu so the user can login now that they
            are connected. If not, then it clears the menu stack and reloads
            the main menu, and then displays a message to the user informing
            them that the connection failed (by calling self.display_message).
              Inputs: connected_state (a Boolean describing whether the client
            is connected or not).
              Outputs: None."""
        if connected_state:
            self.load_menu(self.login_menu)
        else:
            self.menu_stack.clear()
            self.load_menu(self.main_menu)
            self.display_message("Connection to server failed. Please try again later.", t=2)

    def __submit_password(self):
        """ This method submits a password to the server to attempt to join the
            lobby. It references the lobby ID stored in the self.temp_lobby_id
            attribute (saved when first attempting to join the lobby) and the
            text attribute of self.requested_password_entry. It first validates
            the password (and displays a message if invalid), and then if valid
            sends this information to the server in a lobby join request.
              Inputs: None.
              Outputs: None."""
        password = self.requested_password_entry.text
        valid_info = self.final_password_validator.validate(password)
        if valid_info[0] is False:
            message = valid_info[1].replace("Input", "Entered Password")
            self.display_message(message)
            return
        self.__connection.send_queue.enqueue({"command": "join_lobby", "args": ("connection", self.temp_lobby_id, password)})

    def __submit_password_change(self):
        """ This method submits a user account password change to the server.
            It first validates the entered password inputs to ensure they meet
            strict password formats (using self.password_validator with a
            length between 8 and 320), and checks that the entered new password
            matches in both entries. It then encrypts the current password and
            new password, and sends them off to the server in a password change
            request. Finally, it empties the password entries of any text.
              Inputs: None.
              Outputs: None."""
        current_pass = self.current_password_entry.text
        new_pass = self.new_password_entry.text
        confirmation_pass = self.confirm_new_password_entry.text
        valid_info = self.final_password_validator.validate(current_pass)
        if valid_info[0] is False:
            message = valid_info[1].replace("Input", "Current Password")
            self.display_message(message)
            return
        valid_info = self.final_password_validator.validate(new_pass)
        valid_info2 = self.final_password_validator.validate(confirmation_pass)
        if valid_info[0] is False or valid_info2[0] is False:
            if valid_info[0] is False:
                message = valid_info[1]
            else:
                message = valid_info2[1]
            self.display_message(message.replace("Input", "New Password"))
            return
        if new_pass != confirmation_pass:
            self.display_message("Your input new passwords do not match. Please ensure that you have entered your password correctly in both boxes.")
            return
        current_pass = encryption.encrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                          current_pass)
        new_pass = encryption.encrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                      new_pass)
        self.__connection.send_queue.enqueue({"command": "change_password", "args": ("connection", current_pass, new_pass)})
        for entry in [self.current_password_entry, 
                      self.new_password_entry, 
                      self.confirm_new_password_entry]:
            entry.text = ""
            entry.update_text()  # empty entries for next use of this method.

    def __create_new_account(self):
        """ This method attempts to request a new user account creation from
            the server. It first validates the entered username
            (self.username_entry), password (self.password_entry and
            self.confirm_pass_entry) and email (self.email_entry) using the
            respective validators (self.final_name_validator,
            self.final_password_validator, self.final_email_validator). It
            displays any errors in entered information validity to the user,
            and if successful then proceeds to seperately encrypt the username,
            password and email. It finally sends an account creation request to
            the server.
              Inputs: None.
              Outputs: None."""
        username = self.username_entry.text
        password = self.password_entry.text
        email = self.email_entry.text
        valid_info = self.final_username_validator.validate(username)
        if valid_info[0] is False:
            self.display_message(valid_info[1].replace("Input", "Username"))
            return
        valid_info = self.final_password_validator.validate(password)
        if valid_info[0] is False:
            self.display_message(valid_info[1].replace("Input", "Password"))
            return
        valid_info = self.final_email_validator.validate(email)
        if valid_info[0] is False:
            self.display_message(valid_info[1].replace("Input", "Email"))
            return
        if self.password_entry.text != self.confirm_pass_entry.text:
            self.display_message("Your input passwords do not match. Please ensure that you have entered your password correctly in both boxes.")
            return
        username = encryption.encrypt(r"CP-]m@f)qN]¬xDLv74}{:Ba¬9gGhpfO7{8-2^-i1t?_DG*hk%jon6+4/_?1CGaSLzsW[vIR^9_>,U8SuN?=p0ry&-$+>nkN\f|VPPr0=p|$t<N£<^g{^%pB3)0~[^~*Y9qU$[[[K,SFpw,ffRdRW7jtQ,pw^KRA<£Jj0/=M}2W^UEA-|rm*AmCOM¬{*/@LFReOixVqHdY64*3DTJT:0sv%$F<({J*1CU^C00-LOKOWaiIF2nK[$9GQOZGdfbZ&{hel1/C<|NPdXt!£EpkNL&-NCgFy¬$JGflSh!%N$~K,|+3!c?GI)£TX{\$uVB]jrBJ!AL^L3a<}RM]v*80_Ox]1f%5r4d+}G@=Oj<(n?|mi(CiXv{9YSpKb^gKr5Q|A0|<:ICPNpD??gV++(/.r7V=X>DL]K[~d`TN.%Y)£1w_|_n?2oyA(?gQ`(Fa`Ha]tx,=;=yj]ZT|£o;&(E:_+tK6)[$dK5xW6=>T`l\xS@R$YL.{P£=?dRmJqR,c6E_,h,)A",
                                      username)
        password = encryption.encrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                      password)
        email = encryption.encrypt(r"4_yx7JN|qxHN<8W*lr2)R|l{g¬AO!3<~\NZh7tB(W[,sYJzvT?4[{JT{o$oShLw4ALFx~|s!BrCpfva|o!JMx7vHnIZ<NZ%£Wk.?3aaC¬};wwbE£}F`Z{j1{wSk£C£uHw&z,|6u~%=*!*2gxG[iSl&^u3F]5GAJ2/1N2/|V&d%/G2MN`U)[mmb1£^~[N+`iy:AmHy+<R_IVGG@H*d(<ZQ[B`7tI¬[s<Tpis!prd?T8pOz6c£A£<jV)tc)WsJ¬:z%I/WjAan?N{V|?:YdMP¬(40qiOby¬Y)4v}`t[>HGl3I;@YVO4^<-Wnbx<p1]@e{Q4rhl|xCD77k=iYq!Kdt;]h>^[{{W4GOfMN1Qj(M>v*rl-}vErJSJt$£o4PgamKLOwIpF/fr7/A<4Qp¬M&eI%mUvfc;~$\l£Nsr=Z8lZMg(WB7g/i>Q3y£!9c9]C46$DTe&d{eaOIp[x]P,+8)]_TYmTo(p)2}P5N1U,PhHFeRf}(Py&&_h6<iX@zk;1v&Xh>3",
                                   email)
        self.__connection.send_queue.enqueue({"command": "create_new_account", "args": ("connection", username, password, email)})
        
    def account_creation_success(self):
        """ This method updates the UI to reflect that the user has
            successfully created an account. It removes the signup_menu from
            the menu stack, hides the password entry's text, and clears the
            password confirmation and email entries. It finally displays a
            message to the user telling them of their account creation success
            (using the self.display_message method).
              Inputs: None.
              Outputs: None."""
        self.menu_stack.remove()
        self.password_entry.hide_text = True
        self.password_entry.update_text()
        self.pass_visibility_button.text = "Show"
        self.confirm_pass_entry.text = ""
        self.confirm_pass_entry.update_text()
        self.email_entry.text = ""
        self.email_entry.update_text()
        self.display_message("Your account has been created. Please log in to use your account.", t=2.5)

    def __attempt_login(self):
        """ This method attempts to log the user in based upon their currently
            entered username and password. It seperately encrypts the username
            and password and then sends them to the server in a login request.
              Inputs: None.
              Outputs: None."""
        username = self.username_entry.text
        password = self.password_entry.text
        username = encryption.encrypt(r"CP-]m@f)qN]¬xDLv74}{:Ba¬9gGhpfO7{8-2^-i1t?_DG*hk%jon6+4/_?1CGaSLzsW[vIR^9_>,U8SuN?=p0ry&-$+>nkN\f|VPPr0=p|$t<N£<^g{^%pB3)0~[^~*Y9qU$[[[K,SFpw,ffRdRW7jtQ,pw^KRA<£Jj0/=M}2W^UEA-|rm*AmCOM¬{*/@LFReOixVqHdY64*3DTJT:0sv%$F<({J*1CU^C00-LOKOWaiIF2nK[$9GQOZGdfbZ&{hel1/C<|NPdXt!£EpkNL&-NCgFy¬$JGflSh!%N$~K,|+3!c?GI)£TX{\$uVB]jrBJ!AL^L3a<}RM]v*80_Ox]1f%5r4d+}G@=Oj<(n?|mi(CiXv{9YSpKb^gKr5Q|A0|<:ICPNpD??gV++(/.r7V=X>DL]K[~d`TN.%Y)£1w_|_n?2oyA(?gQ`(Fa`Ha]tx,=;=yj]ZT|£o;&(E:_+tK6)[$dK5xW6=>T`l\xS@R$YL.{P£=?dRmJqR,c6E_,h,)A",
                                      username)
        password = encryption.encrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                      password)
        self.__connection.send_queue.enqueue({"command": "login", "args": ("connection", username, password)})

    def login_success(self):
        """ This method updates the UI to reflect that the user has
            successfully logged in. It changes the logged_in attribute to True,
            removes the login menu from the menu stack, and then depending on
            whether the game_state attribute says the user is in the 'online'
            menu or the 'statistics' menu, calls either the __load_online or
            __load_statistics method respectively. Finally, it calls
            display_message to tell the user that the login was successful.
              Inputs: None.
              Outputs: None."""
        self.password_entry.text = ""
        self.password_entry.update_text()
        self.username_entry.text = ""
        self.username_entry.update_text()
        self.logged_in = True
        self.menu_stack.remove()
        if self.game_state == "online":
            self.__load_online()
        elif self.game_state == "statistics":
            self.__load_statistics()
        self.display_message("Login successful.", t=1)

    def clear(self):
        """ This method entirely clears the menu system from use, removing all
            menus in the menu stack and changing self's active attribute to
            false. Generally used when a game has been started.
              Inputs: None.
              Outputs: None."""
        self.menu_stack.clear()
        self.active = False

    def __logout(self):
        """ This method sends a logout request to the server and updates the UI
            to reflect that the user has logged out. It does this by changing
            the logged_in attribute to False, and clearing the menu stack to
            load the main menu. It also calls the display_message method to
            tell the user that they have been logged out.
              Inputs: None.
              Outputs: None."""
        self.__connection.send_queue.enqueue({"command": "logout"})
        self.logged_in = False
        self.menu_stack.clear()
        self.load_menu(self.main_menu)
        self.display_message("You have been logged out.", t=1)

    def __create_new_lobby(self):
        """ This method creates a new lobby based on inputs. It first calls the
            clear() method to de-activate the UI (self), before collecting
            basic information about the name (from self.lobby_name_entry), and
            the lobby's password (or sets it to None if no password has been
            entered). It finally calls its creation_method attribute with the
            online argument along with the collected lobby information.
              Inputs: None.
              Outputs: None."""
        self.clear()
        lobby_password = None if self.lobby_password_entry.text == "" else self.lobby_password_entry.text
        self.creation_method("online",
                             (self.lobby_name_entry.text, 
                              lobby_password))

    def display_message(self, message, t=3.5):
        """ This method displays a message to the user for a given amount of
            time. It first formats the message and creates UI Label elements
            that can be dispalyed on the screen. It formats this into its own
            message container, and pushes this to the top of the menu stack.
            Finally, it calls the do_after_time function to create a short
            thread that will wait to call the menu_stack's remove method (and
            hence stop displaying the message).
              Inputs: message (a string that contains the message to be
            directly displayed to the user), and t (an integer / float
            describing the amount of time in seconds that the message should be
            displayed for).
              Outputs: None."""
        line_width = self.settings["window_width"] / 10 * 9  # the maximum
        # width of a line is 90% of the window width
        message_width = self.medium_ui_font.size(message)[0]
        number_of_lines = int(message_width // line_width + 1)  # we add 1 because integer division effectively rounds down
        message_container = Container(1, number_of_lines, 
                                      inner_padding=self.padding_size)
        words = message.split(" ")  # split by words to make text cleanly fit 
        # across multiple lines
        word_index = 0  # current word index of the message
        letter_index = 0  # current letter index of a word. Used when a word is
        # too long to fit on one line (an extreme case)
        for i in range(number_of_lines):
            text = ""
            # first keep adding words until the line is full
            while word_index < len(words):
                new_text = text + words[word_index] + " "
                if self.medium_ui_font.size(new_text)[0] >= line_width:
                    break
                else:
                    word_index += 1
                    text = new_text
            # if message featured a word too long to display on a single line,
            # add the word letter-by-letter.
            if len(text) == 0:
                # keep adding letters of that word until the line is full
                while letter_index < len(words[word_index]):
                    new_text = text + words[word_index][letter_index]
                    letter_index += 1  # remove the letters added from the word
                    if self.medium_ui_font.size(new_text)[0] >= line_width:
                        break
                    else:
                        letter_index += 1
                        text = new_text
                if letter_index == len(words):  
                    # if used up all letters, onto the next word like normal
                    word_index += 1
            # finally we create a Label UI element to draw for each line.
            if len(text) != 0:  # check text length so we don't add any empty final lines labels if no text is left.
                message_label = Label(text, font=self.medium_ui_font)
                message_container.add_element(message_label)
        message_container.pos = scale_position(Vector2D(0, 0), self.window_vector, Vector2D(0.5, 0.5), scale_from=Vector2D(0.5, 0.5), object_size=message_container.size)
        self.menu_stack.push(message_container)
        do_after_time(self.menu_stack.remove, t=t)
    
    def __join_lobby(self, button_index):
        """ This method is called to select a specific lobby that is currently
            displayed in the Menu_System. It is intended to be called by
            buttons, which provide their position (index) in the list of
            displayed buttons. This is then used with the index of the current
            lobby data (self.current_selection_index) to determine the lobby
            currently accessed by the user. This is saved in self.temp_lobby_id
            in case the server requests a password and we need to resend this
            information. It finally sends a lobby join request to the server
            with the located lobby ID.
              Inputs: button_index (an integer containing the index of the
            selected lobby's button in the list of currently displayed lobby
            buttons).
              Outputs: None."""
        lobby_index = button_index + self.current_selection_index
        self.temp_lobby_id = self.lobby_data[lobby_index][0]
        self.__connection.send_queue.enqueue({"command": "join_lobby", "args": ("connection", self.temp_lobby_id)})

    def __next_selections(self, processing_func):
        """ This method attempts to loads the next 5 selection items (or
            however many are left) into the relevant selection menu (e.g.
            lobbies, presets, replays). It does this only if the 
            self.can_progress_selections attribute is True, and if it is then
            it will add 5 to the current selection index
            (self.current_selection_index) and call the provided processing
            method to update the selection menu's visual elements with the
            newly loaded data based on the updated index.
              Inputs: processing_func (a method/function that will update the
            item selections container using the new index, loading the items to
            the relevant menus and displaying them actively on the screen).
              Outputs: None."""
        if self.can_progress_selections:
            self.current_selection_index += 5
            processing_func()
    
    def __prev_selections(self, processing_func):
        """ This method attempts to loads the previous 5 selection items (or
            however many are left) into the relevant selection menu (e.g.
            lobbies, presets, replays). It does this only if the 
            self.can_regress_selections attribute is True, and if it is then it
            will minus 5 from the current selection index
            (self.current_selection_index) and call the provided processing
            method to update the selection menu's visual elements with the
            newly loaded data based on the updated index.
              Inputs: processing_func (a method / function that will update the
            item selections container using the new index, loading the items to
            the relevant menus and displaying them actively on the screen).
              Outputs: None."""
        if self.can_regress_selections:
            self.current_selection_index -= 5
            if self.current_selection_index < 0:
                self.current_selection_index = 0
            processing_func()

    def __process_replay_data(self):
        """ This method processes the replay data, updating the UI based upon
            the currently viewed replays. It first updates the
            can_progress_selections and can_regress_selections attributes
            (based on whether there are more than five replays above the
            current index (i.e. there is at least one to display) and whether
            the replay index is greater than 0 respectively). It then retrieves
            the names of the 5 accessed replays from self.replay_data using the
            current replay index, and formats this data into the replay UI
            elements (self.replay_elements). If there are not 5 replays to
            display, then it also hides extra UI elements that are not needed.
              Inputs: None.
              Outputs: None."""
        self.can_progress_selections = len(self.replay_data[self.current_selection_index:]) > 5
        self.can_regress_selections = self.current_selection_index > 0
        replays = self.replay_data[self.current_selection_index:self.current_selection_index + 5]
        length = len(replays)
        if length != 5:
            for i in range(5):
                self.replay_elements[i].active = i < length
        else:
            for element in self.replay_elements:
                element.active = True
        for i, replay in enumerate(replays):
            try:
                name_parts = replay.replace(".json", "").split("_")
                self.replay_elements[i].text = "{} {} - {}".format(name_parts[0], name_parts[1].replace("-", ":"), name_parts[2])
            except:
                self.replay_elements[i].text = replay.replace(".json", "")

    def __load_replay(self, index):
        """ This method loads the replay that is selected in the Menu_System.
            The input button index is added to the current replay index
            (self.current_selection_index) to determine the replay to be
            loaded. The matching file name from that index in self.replay_data
            is then read and the data in the file is loaded. Any errors in the
            file handling process are caught and relevant messages are
            displayed to the user. Finally, if no errors occured, the clear()
            method is called to clear the Menu_System and the function stored
            in the creation_method attribute is called with the "replay"
            argument and the loaded replay data.
              Inputs: index (an integer containing the index of the selected
            replay's button in the list of currently displayed replay buttons).
              Outputs: None."""
        new_index = self.current_selection_index + index
        file_name = "replays\\" + self.replay_data[new_index]
        try:
            with open(file_name, "r") as replay_file:
                data = json.loads(replay_file.read())
                replay_file.close()
        except FileNotFoundError:
            self.display_message("Unable to load the replay because the file cannot be found.", t=2)
            return
        except json.decoder.JSONDecodeError:
            self.display_message("Unable to load the replay because the file has been corrupted.", t=2)
            return
        except OSError:
            self.display_message("Unable to load the replay because the file could not be accessed by the program.", t=2)
            return
        self.clear()
        self.creation_method("replay", data)

    def __delete_replay(self, index):
        """ This method deletes the replay that is selected in the Menu_System.
            The input button index is added to the current replay index
            (self.current_selection_index) to determine the replay to be
            deleted. The matching file name from that index in self.replay_data
            is then searched for and removed (using os.remove). Any errors in
            the file handling process are caught and relevant messages are
            displayed to the user. Finally, if no errors occured, the
            replay_data attribute is updated to remove this replay, and the 
            __process_replay_data() method is called to update the list of
            displayed replays.
              Inputs: index (an integer containing the index of the selected
            replay's button in the list of currently displayed replay buttons).
              Outputs: None."""
        new_index = self.current_selection_index + index
        file_name = "replays\\" + self.replay_data[new_index]
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
            except OSError:
                self.display_message("Unable to delete replay file because the program does not have permission to delete this file. Please change the file or program permissions and try again later.", t=4)
                return
        self.replay_data = self.replay_data[:new_index] + self.replay_data[new_index+1:]
        self.__process_replay_data()

    def __select_replay(self, index):
        """ This method is called to interact with a replay selected in the
            replay select menu. It either calls the __delete_replay method or
            the __load_replay method depending on which menu is currently open,
            which is determined using the delete_mode attribute (True = delete
            replay, False = load replay).
              Inputs: index (an integer containing the index of the selected
            replay's button in the list of currently displayed replay buttons).
              Outputs: None."""
        if self.delete_mode:
            self.__delete_replay(index)
        else:
            self.__load_replay(index)

    def __load_replays(self):
        """ This method loads a list of replays currently found within the
            relative replays file directory. It first checks if the directory
            exists (and makes it if it does not). Then, it finds all files that
            end with .json and adds their names to the self.replay_data list.
            Finally, it reverses the replay_data list so that the replays are
            sorted with the most current replay first.
              Inputs: None.
              Outputs: None."""
        cwd = os.getcwd()
        if not os.path.isdir("replays"):
            os.mkdir("replays")
            return
        os.chdir("replays")
        self.replay_data = []
        for file in glob.glob("*.json"):
            self.replay_data.append(file)
        os.chdir(cwd)
        self.replay_data = self.replay_data[::-1]

    def __load_replay_selection(self, delete_mode):
        """ This method loads the replay selection menu. It first updates the
            delete_mode attribute to reflect whether selected replays should be
            loaded or deleted (based on input), and then calls the
            __load_replays and __process_replay_data methods to load initial
            replay data. It then resets the current_selection_index attribute
            to zero. Finally, it calls the load_menu method with the replay
            select menu.
              Inputs: delete_mode (a Boolean describing whether the replay
            selection menu is being loaded to select replays to delete (True)
            or to load (False)).
              Outputs: None."""
        self.delete_mode = delete_mode
        self.current_selection_index = 0
        self.__load_replays()
        self.__process_replay_data()
        self.load_menu(self.replay_select_menu)

    def __process_preset_data(self):
        """ This method processes the preset data, updating the UI based upon
            the currently viewed presets. It first updates the
            can_progress_selections and can_regress_selections attributes
            (based on whether there are more than five presets above the
            current index (i.e. there is at least one to display) and whether
            the preset index is greater than 0 respectively). It then retrieves
            the names of the 5 accessed presets from self.preset_data using the
            current preset index, and formats this data into the preset UI
            elements (self.preset_elements). If there are not 5 presets to
            display, then it also hides extra UI elements that are not needed.
              Inputs: None.
              Outputs: None."""
        self.can_progress_selections = len(self.preset_data[self.current_selection_index:]) > 5
        self.can_regress_selections = self.current_selection_index > 0
        presets = self.preset_data[self.current_selection_index:self.current_selection_index+5]
        num_of_presets = len(presets)
        if num_of_presets != 5:  # no need to consider > 5 as preset selection selects a maximum of 5 presets.
            for i in range(5):
                self.preset_elements[i].active = i < num_of_presets
        else:
            for element in self.preset_elements:
                element.active = True
        for i, preset in enumerate(presets):
            self.preset_elements[i].text = preset["name"]

    def __load_preset_settings(self, index):
        """ This method loads the settings stored in a set preset file into the
            program, updating the UI elements in the custom simulation menu
            (self.custom_sim_menu) to reflect these new values. The input
            button index is added to the current preset index
            (self.current_selection_index) to determine the preset who is being
            accessed and whose data should be loaded. It also loads the custom
            simulation menu (self.custom_sim_menu) if it is not already loaded
            by calling the load_menu method.
              Inputs: index (an integer containing the index of the button
            selected in the list of buttons in preset selection menu).
              Outputs: None."""
        self.update_slider_entry_links = True  # We flag to update the slider
        # entry links in the next update call because we need to update the
        # entries as well as the sliders with the newly added values.
        self.__menu_return()  # unload the preset selection menu
        if self.menu_stack.peek() != self.custom_sim_menu:
            self.load_menu(self.custom_sim_menu)
        settings = self.preset_data[self.current_selection_index+index]["settings"]
        required_keys = ["gravity", "table_coeff_of_rest",
                         "ball_coeff_of_rest", "ball_coeff_of_drag", 
                         "air_density", "ball_mass", 
                         "coeff_of_static_friction", 
                         "coeff_of_rolling_friction", "time_of_cue_impact",
                         "table_length", "table_width", "ball_radius",
                         "hole_factor"]
        preset_keys = settings.keys()
        for key in required_keys:  
            # presence check all of the required preset settings.
            if key not in preset_keys:
                self.display_message("Unable to load preset because the preset file is corrupted.")
                return
        # we only update the sliders because the slider_entry_control method
        # will update the entries for us.
        self.gravity_slider.value = settings["gravity"]
        self.table_rest_slider.value = settings["table_coeff_of_rest"]
        self.ball_rest_slider.value = settings["ball_coeff_of_rest"]
        self.ball_drag_slider.value = settings["ball_coeff_of_drag"]
        self.air_density_slider.value = settings["air_density"]
        self.ball_mass_slider.value = settings["ball_mass"]
        self.static_friction_slider.value = settings["coeff_of_static_friction"]
        self.roll_friction_slider.value = settings["coeff_of_rolling_friction"]
        self.impact_time_slider.value = settings["time_of_cue_impact"] * 1000
        self.length_slider.value = settings["table_length"]
        self.width_slider.value = settings["table_width"]
        self.ball_radius_slider.value = settings["ball_radius"] * 100
        self.hole_factor_slider.value = settings["hole_factor"]

    def __delete_preset(self, index):
        """ This method deletes the preset that is selected in the Menu_System.
            The input button index is added to the current preset index
            (self.current_selection_index) to determine the preset to be
            deleted. The matching file name from that index in self.preset_data
            is then searched for and removed (using os.remove). Any errors in
            the file handling process are caught and relevant messages are
            displayed to the user. Finally, if no errors occured, the
            preset_data attribute is updated to remove this preset, and the
            __process_preset_data method is called to update the list of
            displayed presets.
              Inputs: index (an integer containing the index of the selected
            preset's button in the list of currently displayed preset buttons).
              Outputs: None."""
        new_index = self.current_selection_index + index
        name = self.preset_data[new_index]["name"]
        file_name = "presets\\" + name + ".json"
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
            except OSError:
                self.display_message("Unable to delete preset file because the program does not have permission to delete this file. Please change the file or program permissions and try again later.", t=4)
                return
        self.preset_data = self.preset_data[:new_index] + self.preset_data[new_index+1:]
        self.__process_preset_data()

    def __select_preset(self, index):
        """ This method is called to interact with a preset selected in the
            preset select menu. It either calls the __delete_preset method or
            the __load_preset_settings method depending on which menu is
            currently open, which is determined using the delete_mode attribute
            (True = delete preset, False = load preset).
              Inputs: index (an integer containing the index of the selected
            preset's button in the list of currently displayed preset buttons).
              Outputs: None."""
        if self.delete_mode:
            self.__delete_preset(index)
        else:
            self.__load_preset_settings(index)

    def __load_presets(self):
        """ This method loads the presets currently found within the relative
            presets file directory. It first checks if the directory exists
            (and makes it if it does not). Then, it finds all files that end
            with .json and adds their contained information to the
            self.preset_data list. Any errors in opening the files and loading
            data is handled and relevant messages are printed to the console.
            Finally, it orders the preset data based on their time created so
            that the oldest presets are shown first.
              Inputs: None.
              Outputs: None."""
        cwd = os.getcwd()
        if not os.path.isdir("presets"):
            os.mkdir("presets")
            return
        os.chdir("presets")
        files = []
        for file in glob.glob("*.json"):
            files.append(file)
        self.preset_data = []
        for file in files:
            try:
                with open(file) as preset_file:
                    data = json.load(preset_file)
                    self.preset_data.append(data)
            except FileNotFoundError:
                print("Unable to load file {} because the file cannot be found.".format(file))
            except json.decoder.JSONDecodeError:
                print("Unable to load file {} because the file has been corrupted.".format(file))
            except OSError:
                print("Unable to access file {}. This may be because the file is protected by system privileges\n".format(file) +
                      "or because the file is hosted online and cannot be accessed currently.")
        self.preset_data = sorted(self.preset_data, key=lambda preset: preset["time_created"])  # sort in ascending order of time created
        os.chdir(cwd)
        
    def __load_presets_menu(self, delete_mode):
        """ This method loads the preset menu. It first updates the delete_mode
            attribute to reflect whether  selected presets should be loaded or
            deleted (based on input), and then calls the __load_presets
            and __process_preset_data methods to load initial preset data. It
            then resets the current_selection_index attribute to zero. Finally,
            it calls the load_menu method with the preset menu.
              Inputs: delete_mode (a Boolean describing whether the preset menu
            is being loaded to select presets to delete (True) or to load 
            (False)).
              Outputs: None."""
        self.delete_mode = delete_mode
        self.current_selection_index = 0
        self.__load_presets()
        self.__process_preset_data()
        self.load_menu(self.preset_menu)

    def __save_preset(self):
        """ This method saves the currently selected custom simulation values
            (of the sliders in the custom simulation menu) as a new json preset
            file, using the specified file name in the preset_name_entry's text
            attribute. It first checks if the presets file exists and makes it
            if it does not. It then checks whether a preset of the same name
            already exists and adds an extra number in brackets to the end to
            make the name unique if not. Finally, it calls the
            __load_simulation_values method with an empty dictionary to
            retrieve the loaded settings, and stores them as a key in another
            dictionary that also contains information about the preset's name
            and time created. The json file is then created and the json data
            is dumped to the file. Finally, self.saved_label is made active to
            notify the user that the preset successfuly saved.
              Inputs: None.
              Outputs: None."""
        cwd = os.getcwd()
        if not os.path.isdir("presets"):
            os.mkdir("presets")
        os.chdir("presets")
        presets = []
        for file in glob.glob("*.json"):  # find all existing preset names
            presets.append(file)
        os.chdir(cwd)
        preset_name = self.preset_name_entry.text
        if preset_name + ".json" in presets:
            extra = 2
            while "{} ({}).json".format(preset_name, extra) in presets:
                extra += 1  # keep adding to number until file name is unique.
            preset_name = "{} ({})".format(preset_name, extra)
        current_settings = {}
        self.__load_simulation_values(current_settings)
        data = {}
        data["name"] = preset_name
        data["time_created"] = time.time()
        data["settings"] = current_settings
        filename = "presets\\" + str(preset_name) + ".json"
        with open(filename, "w+") as preset_file:
            json.dump(data, preset_file)
            preset_file.close()
        self.saved_label.active = True

    def __refresh_lobby_data(self):
        """ This method refreshes the currently stored lobby data by sending a
            command to the server to retrive information on current lobbies.
              Inputs: None.
              Outputs: None."""
        self.__connection.send_queue.enqueue({"command": "retrieve_lobbies",
                                              "args": ("connection", 0)})

    def __process_lobby_data(self):
        """ This method processes the lobby data, updating the UI based upon
            the currently viewed lobbies. It first updates the
            can_progress_selections and can_regress_selections attributes
            (based on whether there are more than five lobbies above the
            current index (i.e. there is at least one to display) and whether
            the lobby index is greater than 0 respectively). It then retrieves
            the names and information of the 5 accessed lobbies from
            self.lobby_data using the current lobby index, and formats this
            data into the lobby UI elements (self.lobby_selection_rows). If
            there are not 5 lobbies to display, then it also hides any extra UI
            elements that are not needed.
              Inputs: None.
              Outputs: None."""
        self.can_progress_selections = len(self.lobby_data[self.current_selection_index:]) > 5
        self.can_regress_selections = self.current_selection_index > 0
        lobbies = self.lobby_data[self.current_selection_index:self.current_selection_index+5]
        num_of_lobbies = len(lobbies)
        if num_of_lobbies != 5:
            for i in range(5):
                if i < num_of_lobbies: 
                    for ui_element in self.lobby_selection_rows[i]:
                        ui_element.active = True
                else:
                    for ui_element in self.lobby_selection_rows[i]:
                        ui_element.active = False
        else:
            for row in self.lobby_selection_rows:
                for ui_element in row:
                    ui_element.active = True
        for i, lobby_info in enumerate(lobbies):
            elements = self.lobby_selection_rows[i]
            elements[0].text = lobby_info[1]
            elements[1].text = "{}/2".format(lobby_info[2])
            elements[2].text = "Private" if lobby_info[3] else "Public"

    def load_lobby_data(self, data):
        """ This method lodas current lobby information received from the
            server. It first resets the current lobby index
            (self.current_selection_index) to 0, and then clears any existing
            lobby data. It then filters through the received lobbies based upon
            whether they are full or password protected (based upon the current
            state of the hide_full_checkbox and the hide_private_checkbox). It
            then calls the __process_lobby_data method to update the lobby UI
            elements with the newly received lobbies.
              Inputs: None.
              Outputs: None."""
        self.current_selection_index = 0
        self.lobby_data = []  # clear any existing lobby data that may exist
        for lobby in data:
            # filter based on user settings
            if not ((lobby[2] == 2 and self.hide_full_checkbox.checked) or \
                    (lobby[3] == True and self.hide_private_checkbox.checked)):
                self.lobby_data.append(lobby)
        self.__process_lobby_data()

    def __load_lobby_select(self):
        """ This method loads the lobby selection menu. First it calls the
            __refresh_lobby_data method to retrieve lobby information from the
            server, and then resets the current lobby index
            (self.current_selection_index) to 0. Finally, it calls the
            load_menu method with the lobby select menu.
              Inputs: None.
              Outputs: None."""
        self.__refresh_lobby_data()
        self.current_selection_index = 0
        self.load_menu(self.lobby_select_menu)

    def __load_simulation_values(self, settings):
        """ This method loads the simulation values stored within the different
            sliders of the custom simulation menu (self.custom_sim_menu) into a
            given settings dictionary for use to create new simulations.
              Inputs: settings (a dictionary to be updated with the
            new simulation settings).
              Outputs: None (the settings dictionary is directly updated)."""
        settings["gravity"] = self.gravity_slider.value
        settings["table_coeff_of_rest"] = self.table_rest_slider.value
        settings["ball_coeff_of_rest"] = self.ball_rest_slider.value
        settings["ball_coeff_of_drag"] = self.ball_drag_slider.value
        settings["air_density"] = self.air_density_slider.value
        settings["ball_mass"] = self.ball_mass_slider.value
        settings["coeff_of_static_friction"] = self.static_friction_slider.value
        settings["coeff_of_rolling_friction"] = self.roll_friction_slider.value
        settings["time_of_cue_impact"] = self.impact_time_slider.value / 1000
        settings["table_length"] = self.length_slider.value
        settings["table_width"] = self.width_slider.value
        ball_radius = self.ball_radius_slider.value / 100
        settings["ball_radius"] = ball_radius
        settings["base_cue_offset"] = ball_radius + 0.01
        settings["max_cue_offset"] = ball_radius + 0.51
        settings["hole_factor"] = self.hole_factor_slider.value

    def __start_simulation(self):
        """ This method starts a simulation. It first loads the simulation
            values (using the __load_simulation_values with the self.settings
            dictionary), and it then uses the current value of the game_state
            attribute to determine which methods it should call. If the game
            state is either 'offline' or 'editor' this will call the clear
            method (clear the GUI) and call the function stored in the
            creation_method attribute with the current game_state so that the
            simulation can be started. If the game state if 'online', then this
            will instead call the load_menu method with the lobby_finalise_menu
            to finalise lobby information such as its name and password.
              Inputs: None.
              Outputs: None."""
        self.__load_simulation_values(self.settings)
        if self.game_state == "online":
            self.load_menu(self.lobby_finalise_menu)
        elif self.game_state == "offline" or self.game_state == "editor":
            self.clear()
            self.creation_method(self.game_state)

    def __add_slider_entry_row(self, menu, y_index, description, slider, entry,
                               start_x_index=0):
        """ This method will quickly position and add a row containing a label,
            slider and entry from left to right to a given Container. This is a
            very useful and quick method for adding a simple user-customisable
            value to a menu. It exists due to large amount of repeated code
            when creating the simulation customisation menu.
              Inputs: menu (a Container object which the label, slider and
            entry should be added to), y_index (an integer containing the
            y index (i.e. row) of the container that the elements should be
            added to), description (a Label describing what the slider and
            entry change), slider (a ContinuousSlider or DiscreteSlider object
            which is the slider object to be added to the row), entry (an
            Entry object to be added to the row), and start_x_index (an
            optional integer that defaults to 0, containing the x index (i.e.
            column) of the container which the row of elements should be added
            from).
              Outputs: None."""
        self.__add_element_row(
            menu, 
            y_index, 
            (description, Vector2D(1, 0.5), Vector2D(1, 0.5)),
            slider, 
            (entry, Vector2D(0, 0.5), Vector2D(0, 0.5)), 
            start_x_index=start_x_index
        )

    def __add_element_row(self, menu, y_index, *args, start_x_index=0):
        """ This method will add several UI elements to a given menu Container
            to form a row. They will be added at a given y_index of the
            container and can optionally start at a given x_index.
              Inputs: menu (a Container object to which the elements will be
            added), y_index (an integer containing the y index (i.e. row) of
            the container that the elements should be added to), *args (a
            variable number of UI elements (e.g. Entry, ContinuousSlider,
            Checkbox etc.) to be added as a row), and start_x_index (an integer
            containing the x index (i.e. column) of the container which the row
            of elements should be added from).
              Outputs: None."""
        for item in args:
            if isinstance(item, (tuple, list)):
                menu.add_element(item[0], start_x_index, y_index,
                                 positioning=item[1], position_from=item[2])
            else:
                menu.add_element(item, start_x_index, y_index)
            start_x_index += 1

    def __slider_entry_link(self, description, lower_bound, upper_bound,
                            default_value, font, decimal_places=None,
                            discrete=False, steps=None):
        """ This method creates a slider and entry based upon input values that
            are linked to each other. It allows easy creation of linked sliders
            and entries for user-customisable value manipulation, adding the
            created slider, entry and number of decimal places to the
            self.slider_entry_links list.
              Inputs: description (a string containing the description of the
            value being changed in the slider and entry, to be added to a
            Label), lower_bound (an integer / float containing the lower
            boundary of the slider), upper_bound (an integer / float containing
            the upper boundary of the slider), default_values (an integer /
            float / other object containing the default value of the slider and
            entry), font (a pygame.font.SysFont object that the label and entry
            text will be rendered in), decimal_places (an integer > 0
            containing the number of decimal places which the entry should be
            rounded to), discrete (an optional Boolean value describing whether
            the created slider should be a DiscreteSlider (True) or a
            ContinuousSlider (False)), and steps (None if the slider is not
            discrete, or an integer representing the number of steps or a list
            / tuple containing all the values (steps) that can be assumed by
            the slider if it is discrete).
              Outputs: description_label (a Label that contains the slider /
            entry description), slider (a ContinuousSlider or DiscreteSlider
            object constructed based upon input values), and entry (an Entry
            object constructed based upon input values)."""
        description_label = Label(description, font=font)
        slider_length = self.settings["window_width"] / 3
        slider_height = self.settings["window_width"] / 60
        if discrete:
            slider = DiscreteSlider(self.__controls, lower_bound, upper_bound,
                                    steps, length=slider_length,
                                    height=slider_height)
        else:
            slider = ContinuousSlider(self.__controls, lower_bound,
                                      upper_bound, length=slider_length,
                                      height=slider_height)
        slider.value = default_value
        # we size the entry based upon the largest value that can be assumed
        # (including the number of decimal places).
        if decimal_places != None:
            # size of upper bound formatted to full number of decimal places
            entry_size = Vector2D(font.size(("{:." + str(decimal_places) + "f}").format(upper_bound)))
        else:
            entry_size = Vector2D(font.size(str(upper_bound)))
        entry_size += 4 * self.padding_size
        entry = Entry(self.__controls, back_time=self.settings["back_time"],
                      initial_text=str(default_value), font=font,
                      fixed_width=entry_size.x, fixed_height=entry_size.y,
                      validator=self.numeric_validator, **self.generic_padding)
        self.slider_entry_links.append((slider, entry, decimal_places))
        return description_label, slider, entry
        
    def __menu_return(self):
        """ This method returns from the current menu. It checks the
            update_on_return attribute to determine whether to recreate the GUI
            menu (by calling the function stored in the window_update_method
            attribute and the __create_gui method). It might need to do this
            because of changes in display settings, e.g. when leaving the
            settings menu having made changes. If not updating, then it simply
            calls menu_stack.remove to remove the top menu from the stack.
            Finally, if the saved label (self.saved_label) is active because it
            has been used in the menu, then it resets it to being inactive.
              Inputs: None.
              Outputs: None."""
        if self.update_on_return:
            self.window_update_method()
            self.__create_gui()
            self.update_on_return = False
        else:
            self.menu_stack.remove()
        if self.saved_label.active:  # any saved label notices are hidden again.
            self.saved_label.active = False

    def load_menu(self, menu):
        """ This method loads a given menu into the displayed UI. It first
            checks whether the menu is not active and currently contains no
            menus - if it does, then it makes the GUI active again so that it
            can be seen. Next, regardless of if the menu is active or not, it
            pushes the given menu to the menu_stack.
              Inputs: menu (a Container object to be loaded).
              Outputs: None."""
        if not self.active and len(self.menu_stack) == 0:
            self.active = True
        self.menu_stack.push(menu)

    def add_connection(self, connection):
        """ This methods adds a created connection to the GUI object so that it
            is able to communicate with the server to send and retrieve
            different information.
              Inputs: connection (a Connection object which is connected to the
            server).
              Outputs: None."""
        self.__connection = connection

    def __save_settings(self):
        """ This method saves the settings stored in the settings menu to the
            self.settings dictionary. It also sets the update_on_return
            attribute to True (so that the Menu_System is updated to use the
            new settings when the settings menu is quit) and makes the
            saved_label active so that the user knows the save was successful.
              Inputs: None.
              Outputs: None."""
        self.settings["scale_width"] = self.window_scales[self.ui_scale_slider.current_step]
        self.settings["scale_height"] = self.window_scales[self.ui_scale_slider.current_step]
        self.settings["display_mode"] = self.display_type_slider.value.lower()
        self.settings["show_path_projection"] = self.projection_checkbox.checked
        self.settings["auto_focus"] = self.auto_focus_checkbox.checked
        self.settings["online_show_cue_position"] = self.cue_pos_checkbox.checked
        self.settings["save_replay"] = self.save_replay_checkbox.checked
        self.update_on_return = True
        self.saved_label.active = True

    def __quit(self):
        """ This method quits the Menu_System, changing the __has_quit variable
            so that the update method knows to return that the user has clicked
            the quit button to exit the program.
              Inputs: None.
              Outputs: None."""
        self.__has_quit = True
        if self.__connection is not None and self.__connection.in_use:
            self.__connection.send_queue.enqueue({"command": "disconnect"})
            time.sleep(0.5)

    def slider_entry_control(self, slider, entry, decimal_places):
        """ This method controls the link between a linked slider and entry. If
            the slider has been updated or the update_slider_entry_links flag
            is True then this will update the entry's text to match the
            slider's value (to the given number of decimal places).
            Alternatively, if the entry is active, then this will check that
            the entry's text is not empty and does not end with a decimal point
            (i.e. check that it contains a value that the slider can assume),
            and if it does then it will update the slider's value to match the
            entry value.
              Inputs: slider (the ContinuousSlider or DiscreteSlider object
            that is linked), entry (the Entry object that is linked) and
            decimal_places (an integer describing the number of decimal places
            that the entry text should be formatted to when assuming the
            slider's value).
              Outputs: None."""
        if slider.do_update or self.update_slider_entry_links:
            entry.update_text(text=("{:." + str(decimal_places) + "f}").format(slider.value))
        elif entry.is_focused and \
          entry.text != "" and not entry.text.endswith("."):
            slider.value = float(entry.text)

    def update(self):
        """ This method updates the Menu_System object, drawing the menu to the
            screen and checking controls for any controllable elements. As long
            as self is active, then this peeks at the menu at the top of the
            menu stack. It updates any Label or Entry text that need to be
            updated based upon the current top menu or any stored slider-entry
            links (in self.slider_entry_links). It also locks any sliders if
            needed. It finally calls the menus draw and do_controls methods
            before returning the self.__has_quit attribute to inform the main
            loop of whether the user has quit the program through the GUI.
              Inputs: None.
              Outputs: a Boolean describing whether the user has chosen to quit
            the program or not."""
        if not self.active:
            return False

        menu = self.menu_stack.peek()
        if menu == self.settings_menu:
            self.ui_scale_label.text = self.ui_scale_slider.value
            self.display_type_label.text = self.display_type_slider.value
            if self.display_type_slider.value != "Windowed":
                if not self.ui_scale_slider.locked:
                    # while not in windowed display mode, the window size
                    # is locked to its maximum and cannot be changed.
                    self.ui_scale_slider.locked = True
                    self.ui_scale_slider.do_update = False
                    self.ui_scale_slider.current_step = self.ui_scale_slider.upper_bound
            elif self.ui_scale_slider.locked:
                # unlock the window scale slider when windowed is selected.
                self.ui_scale_slider.locked = False
        elif menu == self.lobby_finalise_menu:
            self.password_label.active = self.protected_checkbox.checked
            self.lobby_password_entry.active = self.protected_checkbox.checked
        for link in self.slider_entry_links:
            self.slider_entry_control(*link) # don't need to check activity for
            # this as checks are performed by the slider_entry_control method
        if self.update_slider_entry_links:  
            # we reset the update slider entry links flag once updated
            self.update_slider_entry_links = False

        menu.draw(self.surface)
        menu.do_controls()

        return self.__has_quit
