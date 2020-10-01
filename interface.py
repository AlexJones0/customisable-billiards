""" interface module
Functions:
 - scale_position
Classes:
 - ContinuousSlider
 - DiscreteSlider
 - Button
 - Label
 - Entry
 - Checkbox
 - Element
 - Container
Description:
  Contains code pertaining to the different visual UI elements that users can
interact with in the system. Examples include sliders, checkboxes, buttons,
entries and simple labels. This also contains the Container class, which is
a tree-like data structure in which it is a UI element that can contain other
UI elements in a grid-like structure (including other Containers). This can
be utilised to easily make complex menus for UI systems without the hassle
of having to figure out exact positioning etc."""

#external imports
from time import time as current_time
import pygame  # relies on pygame.init() and pygame.font.init() already being called by the main program.


# internal imports
from vectors import Vector2D


def scale_position(lower_pos, upper_pos, positioning,
                   object_size=None, scale_from=Vector2D(0.5,0.5)):
    """ A function that positions a certain point or object within another space
        based on input scaling factors.
          Inputs: lower_pos (a Vector2D object) and upper_pos (a Vector2D object)
        that detail the top left and bottom right coordinates of the space the
        coordinate/object is being scaled in, positioning (a Vector2D object
        that details where in the space the point/object should be located, with
        x- and y- components ranging from 0 to 1), object_size (an optional
        Vector2D object that details the size of the object being scaled in the
        space for use with input scale_from), and scale_from (an optional
        Vector2D object that defaults to (0.5, 0.5), detailing which point on
        the object should be scaled in the space).
          Outputs: A Vector2D object containing the new coordinate (or the new
        top-left corner coordinate if using an object with real size) that
        matches the input scaling requirements."""
    new_x = (upper_pos.x - lower_pos.x) * positioning.x + lower_pos.x
    new_y = (upper_pos.y - lower_pos.y) * positioning.y + lower_pos.y
    if object_size is not None:
        new_x -= scale_from.x * object_size.x
        new_y -= scale_from.y * object_size.y
    return Vector2D(new_x, new_y)


class ContinuousSlider:
    """ A class representing a continuous slider, which is a slider that does
        not increase in steps."""

    def __init__(self, controls, lower_bound, upper_bound, position=Vector2D(0,0),
                 length=100, height=10, slider_thickness=3,
                 line_colour=(55, 55, 55), slider_colour=(0, 0, 0)):
        """ Constructs the continuous slider based upon provided values + sizes.
              Inputs: controls (a ControlsObject object containing the control
            input state, which is updated by the main loop),
            lower_bound (an integer or float) and upper_bound (an integer or
            float) which represent the lower and upper boundaries of the slider,
            position (an optional Vector2D object containing the positional
            padding applied to the slider image, defaults to (0, 0)), length
            (an optional integer representing the length of the slider image in
            pixels, defaults to 100px), height (an optional integer representing
            the height of the slider image in pixels, defaults to 10 px),
            slider_thickness (an optional integer representing the thickness of
            the slider bar in pixels, defaults to 3 px), line_colour (a 3-item
            tuple or list representing the RGB colour value of the line,
            defaults to dark grey) and slider_colour (a 3-item tuple or list
            representing the RGB colour of the slider that is dragged on the
            line, defaults to black).
              Outputs: None."""
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.current_ratio = 0.50
        self.length = length
        self.height = height
        self.line_colour = line_colour
        self.slider_colour = slider_colour
        self.slider_thickness = slider_thickness
        self.line_image = None
        self.slider_image = None
        self.create_image()
        self.do_update = False  # boolean variable storing whether to update slider
        self.initial_offset = 0  # a variable to store the initial mouse offset from slider.
        self.pos = position
        self.controls = controls
        self.active = True
        self.locked = False

    def create_image(self):
        """ A method that creates the image of the slider based upon the current
            values of its attributes.
              Inputs: None.
              Outputs: None."""
        self.line_image = pygame.Surface((self.length + self.height, self.height),
                                         pygame.SRCALPHA, 32)
        self.line_image.convert_alpha()  # makes background transparent
        half_height = self.height // 2  # calculated beforehand for efficiency
        pygame.draw.line(self.line_image, self.line_colour,
                         (half_height, half_height),
                         (self.length + half_height, half_height),
                         self.slider_thickness)
        self.slider_image = pygame.Surface((self.height, self.height))
        self.slider_image.fill(self.slider_colour)

    @property
    def current_ratio(self):
        return self.__current_ratio

    @current_ratio.setter
    def current_ratio(self, value):
        """ Sets the current position/ratio of the slider as a decimal ranging
            from 0 to 1, representing the left and right ends of the slider.
              Inputs: New ratio value (an integer of 0 or 1 or a float between
            0 and 1).
              Outputs: None."""
        value = float(value)
        if value < 0:
            self.__current_ratio = 0
        elif value > 1:
            self.__current_ratio = 1
        else:
            self.__current_ratio = value

    @property
    def value(self):
        """ A property to return the current value of the slider based upon the
            slider ratio and its boundaries. No inputs, and outputs a
            float/integer value."""
        return self.current_ratio * (self.upper_bound - self.lower_bound) + self.lower_bound

    @value.setter
    def value(self, new_value):
        """ A setter for the value. Takes an input value (integer/foat) and
            calculates the corresponding slider ratio to that value."""
        self.current_ratio = (new_value - self.lower_bound) / (self.upper_bound - self.lower_bound)

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method for checking all input controls (stored in the self.controls
            ControlsObject object) and moving the slider if certain conditions
            are met, moving it along its stepped values.
              Inputs: padding (an optional Vector2D object that describes any
            padding that may be applied to the slider by outside elements that
            contain the slider, meaning that the mouse position controls will be
            shifted by this amount before the control checks and math are applied,
            defaults to (0, 0)).
              Outputs: None."""
        if not self.active or self.locked:
            return
        mouse_position = tuple(self.controls["mouse_position"] - padding)
        if self.do_update:
            # here we update the step of the slider based upon the mouse's
            # position relative to its position when first clicked.
            x_difference = mouse_position[0] - self.pos.x - self.initial_offset
            self.current_ratio = x_difference / self.length
            if not self.controls["mouse_pressed"][0]:
                self.do_update = False
                self.initial_offset = 0
        # here we check whether the user is clicking (focusing) on the slider.
        if not self.do_update:
            if not self.controls.mouse_clicked:
                self.do_update = False
                self.initial_offset = 0
                return
            slider_vector = Vector2D(self.length * self.current_ratio, 0)
            slider_pos = self.pos + slider_vector
            upper_pos = slider_pos + Vector2D(self.height, self.height)
            if slider_pos.x < mouse_position[0] < upper_pos.x and \
               slider_pos.y < mouse_position[1] < upper_pos.y:
                self.do_update = True
                self.initial_offset = mouse_position[0] - slider_pos.x

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method for drawing the slider onto a given surface.
              Inputs: surface (a pygame.Surface object that the slider image
            will be drawn onto) and padding (an optional Vector2D object that
            describes any padding that may be applied to the slider by outside
            elements that contain the slider, shifting the image placement on
            the screen, defaults to (0, 0)).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.line_image, tuple(self.pos+padding))
        slider_vector = Vector2D(self.length * self.current_ratio, 0)
        surface.blit(self.slider_image, tuple(self.pos+slider_vector+padding))

    @property
    def size(self):
        return Vector2D(self.length + self.height, self.height)


class DiscreteSlider(ContinuousSlider):
    """ A class representing a discrete slider, which is a slider that
        increases in steps."""

    def __init__(self, controls, lower_bound, upper_bound, steps, length=100,
                 height=10, position=Vector2D(0, 0), slider_thickness=3,
                 line_colour=(55, 55, 55), slider_colour=(0, 0, 0)):
        """ Constructs the discrete slider based upon provided values and sizes.
            If steps is a number, then the slider will increase in that number
            of equally sized steps from the lower to upper bound. If steps is a
            list of items, then the slider will change between these values,
            increasing in the index of the list, where lower bound and upper
            bound are the starting and ending indexes of the list.
              Inputs: controls (a ControlsObject object containing the control
            input state, which is updated by the main loop), lower_bound (an
            integer or float) and upper_bound (an integer or float) which
            represent the lower and upper boundaries of the slider, steps (an
            integer representing the number of steps or a list/tuple containing
            all the values/steps that can be assumed), position (an optional
            Vector2D object containing the positional padding applied to the
            slider image, defaults to (0, 0)), length (an optional integer
            representing the length of the slider image in pixels, defaults to
            100px), height (an optional integer representing the height of the
            slider image in pixels, defaults to 10 px), slider_thickness (an
            optional integer representing the thickness of the slider bar in
            pixels, defaults to 3 px), line_colour (a 3-item tuple or list
            representing the RGB colour value of the line, defaults to dark grey)
            and slider_colour (a 3-item tuple or list representing the RGB
            colour value of the slider that is dragged along the line, defaults
            to black).
              Outputs: None."""
        super().__init__(controls, lower_bound, upper_bound, position,
                         length, height, slider_thickness, line_colour,
                         slider_colour)
        if isinstance(steps, (list, tuple)):
            self.step_amount = 1
            self.step_values = steps
            self.set_values = True  # a Boolean storing whether values are set or are auto-generated.
            self.steps = len(self.step_values)
        else:
            self.steps = steps
            self.step_amount = (upper_bound - lower_bound) / (self.steps - 1)
            self.step_values = None
            self.set_values = False
        self.step_length = length / (self.steps - 1)
        self.current_step = self.steps // 2
        self.initial_step = self.current_step

    @property
    def current_step(self):
        return self.__current_step

    @current_step.setter
    def current_step(self, value):
        """ A setter for setting the current step of the discrete slider that
            ensures that the slider stays within its boundaries. 
              Inputs: value (an integer representing the step of the slider that
            the slider should be at).
              Outputs: None."""
        value = int(value)
        if value <= 0:
            self.__current_step = 0
        elif value >= self.steps:
            self.__current_step = self.steps - 1
        else:
            self.__current_step = value

    @property
    def value(self):
        """ A property of the slider equal to its current value based upon the
            values within its attributes and its current step."""
        if self.set_values:
            return self.step_values[self.current_step]
        else:
            return self.current_step * self.step_amount + self.lower_bound

    @value.setter
    def value(self, new_value):
        """ A setter for setting the changing the value of the discrete slider
            by setting its current step to the the respective (or if that's not
            possible, the closest) value.
              Inputs: new_value (an integer/float or any other object
            representing the value that the slider should assume.
              Outputs: None."""
        if self.set_values:  # if using set vales, finds the index of that value and sets the current_step to be its index
            for i in range(self.steps):
                if self.step_values[self.lower_bound + i] == new_value:
                    self.current_step = i
                elif isinstance(self.step_values[self.lower_bound + i], str) and isinstance(new_value, str):
                    if self.step_values[self.lower_bound + i].lower() == new_value.lower():
                        self.current_step = i
        else:  # if not using set values, finds the current step that would equal to or be closest to that value.
            values = []
            for i in range(self.steps):
                values.append((i, self.lower_bound + i * self.step_amount))
            below = None
            above = None
            for value in values:
                if value[1] == new_value:
                    self.current_step = value[0]
                    return
                elif (value[1] < new_value and self.lower_bound <= self.upper_bound) or (value[1] > new_value and self.lower_bound > self.upper_bound):
                    below = value
                else:
                    above = value
                    break  # only loop until a step above the input is found
            if above is not None:
                # determines whether the next or previous value is closest to
                # the input value and sets the step accordingly.
                if (above[1] - new_value) > (new_value - below[1]):
                    self.current_step = above[0]
                else:
                    self.current_step = below[0]
            elif below is not None:
                self.current_step = below[0]

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method for checking all input controls (stored in the self.controls
            ControlsObject object) and controlling the slider if certain
            conditions are met, moving it along its stepped values.
              Inputs: padding (an optional Vector2D object that describes any
            padding that may be applied to the slider by outside elements that
            contain the slider, meaning that the mouse position controls will be
            shifted by this amount before the control checks and math are
            applied, defaults to (0, 0)).
              Outputs: None."""
        if not self.active or self.locked:
            return
        mouse_position = tuple(self.controls["mouse_position"] - padding)
        if self.do_update:
            # here we update the step of the slider based upon the mouse's
            # position relative to its initial position when clicked.
            x_difference = mouse_position[0] - self.initial_offset
            if x_difference < 0:
                # add 1 if negative so integer division continues working like
                # floor function. Otherwise steps will not work properly.
                new_step = self.initial_step + x_difference//self.step_length + 1
            else:
                new_step = self.initial_step + x_difference // self.step_length
            if new_step != self.current_step:
                self.initial_offset += (new_step - self.current_step) * self.step_length
                self.current_step = new_step
                self.initial_step = new_step
            if not self.controls["mouse_pressed"][0]:
                # stop updating if not holding the left mouse button down
                self.do_update = False
                self.initial_offset = 0
        if not self.do_update:
            if not self.controls.mouse_clicked:
                self.do_update = False
                self.initial_offset = 0
                return
            slider_vector = Vector2D(self.step_length * self.current_step, 0)
            slider_pos = self.pos + slider_vector
            upper_pos = slider_pos + Vector2D(self.height, self.height)
            # checks if mouse is on the slider
            if slider_pos.x < mouse_position[0] < upper_pos.x and \
               slider_pos.y < mouse_position[1] < upper_pos.y:
                self.do_update = True
                self.initial_offset = mouse_position[0]
                self.initial_step = self.current_step

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method for drawing the slider onto a given surface.
              Inputs: surface (a pygame.Surface object that the slider image
            will be drawn onto) and  padding (an optional Vector2D object that
            describes any padding that may be applied to the slider by outside
            elements that contain the slider, shifting the image placement on
            the screen, defaults to (0, 0)).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.line_image, tuple(self.pos+padding))
        slider_vector = Vector2D(self.step_length * self.current_step, 0)
        surface.blit(self.slider_image, tuple(self.pos+slider_vector+padding))


class Button:
    """ A class representing a button, which can be pressed down by a user and
        call a function."""

    def __init__(self, controls, text, position=Vector2D(0, 0),
                 target=None, args=None, fixed_width=None, fixed_height=None,
                 centred=False, outline_padding=Vector2D(3, 3),
                 text_padding=Vector2D(17,7), text_colour=(0,0,0),
                 background_colour=(200, 200, 200), outline_colour=(0, 0, 0),
                 pressed_colour=None, press_time=0.3,
                 font=pygame.font.SysFont(None, 32)):
        """ Constructs a button using input values. If you input a fixed_width
            and fixed_height then this will be the button size otherwise the
            button will automatically size itself.
              Inputs: controls (a ControlsObject object containing the control
            input state, which is updated by the main loop), text (a string
            containing the text label of the button), position (an optional
            Vector2D object containing the positional padding applied to the
            button image, defaults to (0, 0)), target (an optional function/
            method that is called when the button is pressed or None), args
            (either None or a tuple of arguments to be passed into the called
            target function), fixed_width (an optional integer or None) and
            fixed_height (an optional integer or None) used to give the button a
            fixed size instead of it automatically scaling, centred (an optional
            Boolean that details whether the text should be centred in the
            button, which is only relevant when applying a certain fixed_width
            and fixed_height. Defaults to False), outline_padding (an optional
            Vector2D object) and text_padding (an optional Vector2D object)
            which represents respectively the padding size of the outline of the
            button from its edge and the padding offset of the text label from
            the outline, text_colour (an optional 3-item list/tuple, defaults to
            black) and background_colour (an optional 3-item list/tuple that
            defaults to light grey) and outline_colour (a 3-item list/tuple that
            defaults to black) that represent the colour of the button's text,
            background and outline respectively, pressed_colour (an optional
            3-item list/tuple that defaults to the RGB background colour with
            each component subtracted by 50, press_time (an optional float or
            integer detailing the amount of time in seconds the button should be
            pressed down for) and font (an optional pygame.font.SysFont object
            that describes the font the display text is written in).
              Outputs: None."""
        self.centred = centred
        if fixed_width is not None and fixed_height is not None:
            self.fixed_size = True
            self.width = fixed_width
            self.height = fixed_height
        else:  # size is not fixed - auto scaled based on text and padding
            self.fixed_size = False
            font_size = Vector2D(font.size(text))
            image_size = font_size + 2 * (outline_padding + text_padding)
            self.width = image_size.x
            self.height = image_size.y
        self.target = target
        self.args = args
        self.font = font
        self.background_colour = background_colour
        if pressed_colour is not None:
            self.pressed_colour = pressed_colour
        else:
            rgb_value = [0 if (value - 50 < 0) else value - 50 for value in background_colour]
            self.pressed_colour = tuple(rgb_value)
        self.outline_colour = outline_colour
        self.text_colour = text_colour
        self.outline_padding = outline_padding
        self.text_padding = text_padding
        self.pressed_time = press_time
        self.unpressed_image = None
        self.pressed_image = None
        self.image = None
        self.text = text  # setting self.text calls the create_image function, so we do not have to do that here.
        self.time_of_press = 0.0
        self.pressed = False
        self.pos = position
        self.controls = controls
        self.active = True

    def create_image(self):
        """ A method that creates the image and smaller image counterparts of
            the button, based upon the current values of attributes.
              Inputs: None.
              Outputs: None."""
        self.unpressed_image = pygame.Surface((self.width, self.height))
        self.pressed_image = pygame.Surface((self.width, self.height))
        self.unpressed_image.fill(self.outline_colour)
        self.pressed_image.fill(self.outline_colour)
        size_without_outline = (self.width - 2 * self.outline_padding.x,
                                self.height - 2 * self.outline_padding.y)
        smaller_unpressed_image = pygame.Surface(size_without_outline)
        smaller_unpressed_image.fill(self.background_colour)
        smaller_pressed_image = pygame.Surface(size_without_outline)
        smaller_pressed_image.fill(self.pressed_colour)
        text_label = self.font.render(self.text, 1, self.text_colour)
        if self.centred:
            label_width, label_height = self.font.size(self.text)
            button_dimensions = Vector2D(self.width, self.height) - self.outline_padding  # do not factor in outline padding when calculating centre
            blit_position = tuple((button_dimensions - Vector2D(label_width, label_height)) / 2)
        else:
            blit_position = tuple(self.text_padding)  # no outline_padding
            # because that has already been removed from these smaller images
        smaller_unpressed_image.blit(text_label, blit_position)
        smaller_pressed_image.blit(text_label, blit_position)
        self.unpressed_image.blit(smaller_unpressed_image,
                                  tuple(self.outline_padding))
        self.pressed_image.blit(smaller_pressed_image,
                                tuple(self.outline_padding))
        self.image = self.unpressed_image

    @property
    def pos(self):
        """ A getter for the pos attribute."""
        return self.__pos

    @pos.setter
    def pos(self, new_pos):
        """ A setter for pos that ensures the upper position (self.upper_pos) is
            also changed whenever the position is changed/set so that mouse
            position detection doesn't fail when changing positions. Takes a new
            Vector2D object (representing position) as input."""
        self.__pos = new_pos
        self.upper_pos = self.pos + Vector2D(self.width, self.height)

    @property
    def text(self):
        """ A getter for the text attribute."""
        return self.__text

    @text.setter
    def text(self, new_text):
        """ A setter for text so that the image of the button is updated any
            time you change the text on a button. Takes a string object
            representing the new button text as input."""
        self.__text = new_text
        if not self.fixed_size:
            w, h = self.font.size(new_text)
            self.width = w + (self.text_padding.x + self.outline_padding.x) * 2
            self.height = h + (self.text_padding.y + self.outline_padding.y) * 2
        self.create_image()

    def __press(self):
        """ A method that presses the button down, updating attributes inside
            the image to store information about the press and updating the
            buttons image to reflect that it has been pressed. Called directly
            when you want to press the button but not call its function.
              Inputs: None.
              Outputs: None."""
        self.pressed = True
        self.time_of_press = current_time()
        self.image = self.pressed_image

    def __press_with_functionality(self):
        """ This function presses the button down with its given functionality,
            not just displaying the updated graphic but also calling the target
            function with any relevant arguments.
              Inputs: None.
              Outputs: None."""
        self.__press()
        if self.target is not None:
            if self.args != None:
                self.target(*self.args)
            else:
                self.target()

    def __unpress(self):
        """ This method removes the pressed button graphic created when the
            press() method is called, resetting the button from its pressed
            state and updating variables to reflect that the button is no longer
            pressed.
              Inputs: None.
              Outputs: None."""
        self.pressed = False
        self.image = self.unpressed_image

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method for drawing the button onto a given surface.
              Inputs: surface (a pygame.Surface object that the button image
            will be drawn onto) and padding (an optional Vector2D object that
            describes any padding that may be applied to the button by outside
            elements that contain the button, shifting the image placement on
            the screen, defaults to (0, 0)).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.image, tuple(self.pos + padding))

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method for checking all input controls (stored in the self.controls
            ControlsObject object) and controlling the button if
            certain conditions are met, pressing it. Set up so that it cannot be
            pressed again whilst it is already pressed.
              Inputs: padding (an optional Vector2D object that describes any
            padding that may be applied to the slider by outside elements that
            contain the slider, meaning that the mouse position controls will be
            shifted by this amount before the control checks and math are
            applied, defaults to (0, 0)).
              Outputs: None."""
        if not self.active:
            return
        mouse_position = tuple(self.controls["mouse_position"] - padding)
        if self.pressed:
            if (current_time() - self.time_of_press) >= self.pressed_time:
                self.__unpress()
        # Cannot press whilst button is already pressed. Also only checks if the
        # mouse was clicked on the button, not dragged over it.
        if not self.pressed and self.controls.mouse_clicked and \
          self.pos.x < mouse_position[0] < self.upper_pos.x and \
          self.pos.y < mouse_position[1] < self.upper_pos.y:
            self.__press_with_functionality()

    @property
    def size(self):
        return Vector2D(self.width, self.height)


class Label:
    """ A class representing a label, which has no control functionality and is
        just some text (potentially with a background or outline, which can be
        drawn to the screen as a visual element)."""

    def __init__(self, text, position=Vector2D(0,0),
                 font=pygame.font.SysFont(None, 32), fixed_width=None,
                 fixed_height=None, centred=False, text_colour=(0,0,0),
                 outline_colour=(0,0,0), background_colour=(230,230,230),
                 outline_padding=Vector2D(0,0), text_padding=Vector2D(2,2)):
        """ Constructs a label (text) using input values. If you input a
            fixed_width and fixed_height then this will be the label size
            otherwise the label will automatically size itself.
              Inputs: text (a string containing the text of the label),
            has_outline (a Boolean detailing whether the label should have an
            outline or not), position (an optional Vector2D object containing
            the positional padding applied to the label, defaults to (0, 0)),
            font (an optional pygame.font.SysFont object that describes the font
            the display text is written in), fixed_width (an optional integer or
            None) and fixed_height (an optional integer or None) used to give
            the label a fixed size instead of it automatically scaling, centred
            (an optional Boolean that details whether the text should be centred
            in the label, which is only relevant when applying a certain
            fixed_width and fixed_height. Defaults to False), text_colour (an
            optional 3-item list/tuple, defaults to black) and background_colour
            (an optional 3-item list/tuple that defaults to light grey) and
            outline_colour (a 3-item list/tuple that defaults to black) that
            represent the colour of the label's text, background and outline (if
            the label has one) respectively, outline_padding (an optional
            Vector2D object) and text_padding (an optional Vector2D object)
            which represents respectively the padding size of the outline of the
            label from its edge and the padding offset of the text label from
            the outline (if the label has one).
              Outputs: None."""
        self.centred = centred
        self.text_padding = text_padding
        self.outline_padding = outline_padding
        self.outline_colour = outline_colour
        self.background_colour = background_colour
        self.text_colour = text_colour
        self.font = font
        if fixed_width is not None and fixed_height is not None:
            self.width = fixed_width
            self.height = fixed_height
            self.fixed_size = True
        else:
            font_size = Vector2D(self.font.size(text))
            image_size = font_size + 2*(self.outline_padding+self.text_padding)
            self.width = image_size.x
            self.height = image_size.y
            self.fixed_size = False
        self.image = None
        self.text = text  # we don't need to call create_image() as text.setter does that for us.
        self.pos = position
        self.active = True

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, new_text):
        """ A setter for the label's text that updates its image when the text
            is updated as well. Input is new_text, a string."""
        self.__text = new_text
        if not self.fixed_size:
            image_size = Vector2D(self.font.size(new_text)) + 2 * (self.outline_padding + self.text_padding)
            self.width = image_size.x
            self.height = image_size.y
        self.create_image()

    def create_image(self):
        """ A method that creates the image of the label to be drawn to a
            surface, based upon the current values of attributes.
              Inputs: None.
              Outputs: None."""
        smaller_surface = pygame.Surface((self.width - 2 * self.outline_padding.x, self.height - 2 * self.outline_padding.y))
        smaller_surface.fill(self.background_colour)
        label = self.font.render(self.text, 1, self.text_colour)
        if self.centred:
            label_width, label_height = self.font.size(self.text)
            blit_position = ((self.width - label_width - self.outline_padding.x) / 2, (self.height - label_height - self.outline_padding.y) / 2)
        else:
            blit_position = tuple(self.text_padding)
        smaller_surface.blit(label, blit_position)
        if self.outline_padding != Vector2D(0, 0):
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(self.outline_colour)
            self.image.blit(smaller_surface, tuple(self.outline_padding))
        else:
            self.image = smaller_surface

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method for drawing the label onto a given surface.
              Inputs: surface (a pygame.Surface object that the button image
            will be drawn onto) and padding (an optional Vector2D object that
            describes any padding that may be applied to the label by outside
            elements, shifting the image on the screen, defaults to (0, 0)).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.image, tuple(self.pos + padding))

    @property
    def size(self):
        return Vector2D(self.width, self.height)


class Entry:
    """ A class representing an entry, which is a box that users can type and
        input text into, changing its value."""

    def __init__(self, controls, back_time=0.04, max_display_length=None,
                 fixed_width=None, fixed_height=None, position=Vector2D(0,0),
                 initial_text="", font=pygame.font.SysFont(None, 32),
                 text_colour=(0,0,0), background_colour=(230,230,230),
                 outline_colour=(0,0,0), outline_padding=Vector2D(2,2),
                 text_padding=Vector2D(2,2), hide_text=False, validator=None):
        """ Constructs an entry (text input) using input values. If you input a
            fixed_width and fixed_height then this will be the entry size
            otherwise the entry will automatically size itself.
              Inputs: controls (a ControlsObject object containing the control
            input state, which is updated by the main loop), back_time (an
            integer or float detailing how quickly the use can backspace to
            delete the text in the entry), max_display_length (an integer or
            None that describes the limit of the entry's size in terms of the
            letter spacing), fixed_width (an optional integer or None) and
            fixed_height (an optional integer or None) used to give the label a
            fixed size instead of it automatically scaling, position (an
            optional Vector2D object containing the positional padding applied
            to the label, defaults to (0, 0)), initial_text (an optional string
            detailing any text the entry should start with), font (an optional
            pygame.font.SysFont object that describes the font the entry text is
            written in), text_colour (an optional 3-item list/tuple, defaults to
            black) and background_colour (an optional 3-item list/tuple that
            defaults to light grey) and outline_colour (a 3-item list/tuple that
            defaults to black) that represent the colour of the label's text,
            background and outline respectively, outline_padding (an optional
            Vector2D object) and text_padding (an optional Vector2D object)
            which represents respectively the padding size of the outline of the
            entry from its edge and the padding offset of the text from the
                outline, hide_text (a Boolean describing whether the text in the
            entry should be censored and replaced with asteriks), and validator
            (an optional Validator object or None that validates any text typed
            into the entry to check it meets given conditions).
              Outputs: None."""
        self.max_display_length = max_display_length
        self.text = initial_text
        self.font = font
        if fixed_width is not None and fixed_height is not None:
            self.width = fixed_width
            self.height = fixed_height
            self.max_text_width = self.width - 2*(outline_padding.x+text_padding.x)
        else:
            if self.max_display_length is not None:
                width, height = self.font.size("O" * self.max_display_length)
            else:
                # default entry size is 10 letters long.
                width, height = self.font.size("O" * 10)
            self.max_text_width = width
            dimensions = Vector2D(width, height) + 2*(outline_padding+text_padding)
            self.width = dimensions.x
            self.height = dimensions.y
        self.hide_text = hide_text
        self.update_text()
        self.font = font
        self.background_colour = background_colour
        self.outline_colour = outline_colour
        self.text_colour = text_colour
        self.outline_padding = outline_padding
        self.text_padding = text_padding
        self.image = None
        self.create_image()
        self.is_focused = False
        self.back_time = current_time()  # variable to store timestamp of the last backspace press.
        self.initial_back_time = 0.4  # variable to store the time until the second back is functional.
        self.faster_back_time = back_time
        self.backspace_count = 0  # integer that varies between 0 and 2 depending
        # on the amount of existing backspaces. The count does not need to count
        # past 2 because the speed does not change past this point so this would
        # just be inefficient.
        self.pos = position
        self.controls = controls
        self.active = True
        self.validator = validator

    @property
    def pos(self):
        """ A getter for the pos attribute."""
        return self.__pos

    @pos.setter
    def pos(self, new_pos):
        """ A setter for pos that ensures the upper position (self.upper_pos) is
            also changed whenever the position is changed/set so that mouse
            position detection doesn't fail when changing positions. Takes a new
            Vector2D position as input."""
        self.__pos = new_pos
        self.upper_pos = self.pos + Vector2D(self.width, self.height)

    def update_text(self, text=None):
        """ A method to update the text of an entry, either using its current
            attributes or new given text.
              Inputs: text (an optional string or None that contains the new
            text the entry should contain, if it should contain any).
              Outputs: None."""
        if text is not None:  # if given text, update to include this text.
            self.text = text
        self.display_text = self.text
        if self.hide_text:
            self.display_text = "*" * len(self.display_text)
        while self.font.size(self.display_text)[0] > self.max_text_width:
            self.display_text = self.display_text[1:]

    def create_image(self):
        """ A method used to create (or update) the image of the entry that can
            be drawn to surfaces.
              Inputs: None.
              Outputs: None."""
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.outline_colour)
        smaller_surface = pygame.Surface((self.width - 2 * self.outline_padding.x, self.height - 2 * self.outline_padding.y))
        smaller_surface.fill(self.background_colour)
        self.image.blit(smaller_surface, tuple(self.outline_padding))

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method that draws the entry element to a given surface.
              Inputs: surface (a pygame.Surface object that the image should be
            drawn onto for display to the user) and padding (an optional
            Vector2D object that describes the amount the UI element should be
            shifted by as a result of other outside elements).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.image, tuple(self.pos + padding))
        label = self.font.render(self.display_text, 1, self.text_colour)
        label_padding = self.outline_padding + self.text_padding + padding
        surface.blit(label, tuple(self.pos + label_padding))

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method that performs all the controllable functionality of the
            entry, including typing into the entry box, removing text from the
            entry, and focusing or removing focus from the entry UI element.
              Inputs: padding (a Vector2D object that describes the amount the
            UI element is shifted by and hence how much should be removed from
            the mouse's position when considering mouse position detection
            controls).
              Outputs: None."""
        if not self.active:
            return
        backspace_pressed = self.controls["keys_pressed"][8]
        mouse_position = tuple(self.controls["mouse_position"] - padding)
        if self.controls["mouse_pressed"][0]:
            # updates whether the entry box is being focused on or not
            self.is_focused = self.pos.x < mouse_position[0] < self.upper_pos.x and self.pos.y < mouse_position[1] < self.upper_pos.y
        if self.is_focused:
            back_time = self.initial_back_time if self.backspace_count == 1 else self.faster_back_time
            time_since_last_back = current_time() - self.back_time
            if backspace_pressed and len(self.text) >= 1 and \
               time_since_last_back >= back_time:
                self.text = self.text[:-1]
                self.back_time = current_time()
                if self.backspace_count < 2:
                    self.backspace_count += 1
            elif not backspace_pressed:
                self.backspace_count = 0
            for event in self.controls["events"]:
                if event.type == pygame.KEYDOWN:
                    keypress = pygame.key.name(event.key)
                    if keypress == "escape":
                        self.is_focused = False
                    elif keypress not in ["backspace", "enter", "return"]:  # no need for max length check; that is done by validator
                        self.text += event.unicode
                        if self.validator is not None:
                            validity = self.validator.validate(self.text)
                            if not validity[0]:
                                error = validity[1]
                                print(error)
                                self.text = self.text[:-1]
            self.update_text()

    @property
    def size(self):
        return Vector2D(self.width, self.height)


class Checkbox:
    """ A class representing a checkbox, which users can check and uncheck."""

    def __init__(self, controls, width, height, position=Vector2D(0,0),
                 outline_colour=(0,0,0), background_colour=(220,220,220),
                 check_colour=(0,0,0), outline_padding=Vector2D(2,2),
                 check_padding=None, use_cross=False, thickness=3):
        """ Constructs a checkbox using input values for use in a user interface.
              Inputs: controls (a ControlsObject object containing the control
            input state, which is updated by the main loop), width (an integer
            or float) and height (an integer or float) which represent the
            dimensions of the checkbox, position (an optional Vector2D object
            containing the positional padding applied to the label, defaults to
            (0, 0)), outline_colour (a 3-item list/tuple that defaults to black)
            and background_colour (an optional 3-item list/tuple that defaults
            to light grey) and check_colour (a 3-item list/tuple that defaults
            to black) that represent the colour of the checkbox's outline,
            background and check mark respectively, outline_padding (an optional
            Vector2D object) and check_padding (an optional Vector2D object)
            which represents respectively the padding size of the outline of the
            check mark from its edge and the padding offset of the check mark
            from the outline, use_cross (a Boolean describing whether the
            checkbox marker should be a cross (True) or a tick (False), and
            thickness (an integer that represents the thickness in pixels of the
            checkbox marker).
              Outputs: None."""
        self.width = width
        self.height = height
        self.use_cross = use_cross
        self.background_colour = background_colour
        self.check_colour = check_colour
        self.outline_colour = outline_colour
        self.outline_padding = outline_padding
        if check_padding is None:
            check_size = Vector2D(self.width,self.height)-2*self.outline_padding
            self.check_padding = check_size / 6  # if no check padding is specified, it is by default 1/6 of the checkbox's background size
        else:
            self.check_padding = check_padding
        self.thickness = thickness
        self.image = None
        self.check_image = None
        self.create_image()
        
        self.checked = False
        self.pos = position
        self.controls = controls
        self.active = True

    def create_image(self):
        """ A method that creates the image of the checkbox and the check that
            will appear in it for drawing to a surface.
              Inputs: None.
              Outputs: None."""
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.outline_colour)
        background_size = Vector2D(self.width, self.height) - 2 * self.outline_padding
        smaller_surface = pygame.Surface(tuple(background_size))
        smaller_surface.fill(self.background_colour)
        self.image.blit(smaller_surface, tuple(self.outline_padding))
        self.check_image = pygame.Surface(tuple(background_size))
        self.check_image.fill(self.background_colour)
        check_size = background_size - 2 * self.check_padding
        if self.use_cross:  # constructs the cross symbol
            pygame.draw.line(self.check_image, self.check_colour,
                             tuple(self.check_padding),
                             tuple(check_size + self.check_padding),
                             self.thickness)
            pygame.draw.line(self.check_image, self.check_colour,
                             (check_size.x + self.check_padding.x, self.check_padding.y),
                             (self.check_padding.x, check_size.y + self.check_padding.y),
                             self.thickness)
        else:  # constructs the tick (check) symbol
            common_coord = (int(check_size.x/3) + self.check_padding.x,
                            check_size.y + self.check_padding.y)
            pygame.draw.line(self.check_image, self.check_colour,
                             (self.check_padding.x, int(3 * check_size.y / 5) + self.check_padding.y),
                             common_coord, self.thickness)
            pygame.draw.line(self.check_image, self.check_colour, common_coord,
                             (check_size.x + self.check_padding.x, self.check_padding.y),
                             self.thickness)

    @property
    def pos(self):
        """ A getter for the pos attribute."""
        return self.__pos

    @pos.setter
    def pos(self, new_pos):
        """ A setter for pos that ensures the upper position (self.upper_pos)
            is also changed whenever the position is changed/set so that mouse
            position detection doesn't fail when changing positions. Takes a
            new Vector2D position as input."""
        self.__pos = new_pos
        self.upper_pos = self.pos + Vector2D(self.width, self.height)

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method that draws the checkbox to a given surface based upon its
            current status.
              Inputs: surface (a pygame.Surface object that the checkbox should
            be drawn onto so that the user can see it), and padding (a Vector2D
            object that details the amount the checkbox's position should be
            shifted by as a result of outside element positioning).
              Outputs: None."""
        if not self.active:
            return
        surface.blit(self.image, tuple(self.pos + padding))
        if self.checked:
            extra_padding = self.outline_padding + padding
            surface.blit(self.check_image, tuple(self.pos + extra_padding))

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method that performs the control functionality of the checkbox,
            toggling its checked state when the user clicks on it.
              Inputs: padding (a Vector2D object that describes the amount the
            UI element is shifted by and hence how much should be removed from
            the mouse's position when considering mouse position detection
            controls).
              Outputs: None."""
        if not self.active:
            return
        mouse_position = tuple(self.controls["mouse_position"] - padding)
        if self.controls.mouse_clicked and \
           self.pos.x < mouse_position[0] < self.upper_pos.x and \
           self.pos.y < mouse_position[1] < self.upper_pos.y:
            self.checked = not self.checked

    @property
    def size(self):
        return Vector2D(self.width, self.height)


class Element:
    """ A class to hold information about the visual UI elements held by
        containers so that the UI objects' positioning and controls are properly
        handled. Should never be interfaced directly by the code outside of the
        container - only the UI elements themselves or the containers should be
        interfaced, and only containers can communicate with Elements."""

    def __init__(self, visual_object, positioning,
                 position_from=Vector2D(0.5, 0.5)):
        """ The constructor for the Element objects.
              Inputs: visual_object (any UI element, e.g. ContinuousSlider,
            DiscreteSlider, Button, Label, Entry, Checkbox objects), positioning
            (a Vector2D object with x- and y- components ranging from 0 to 1
            detailing the positioning of the UI element within its container
            space, with (0, 0) being the top left corner and (1, 1) being the
            bottom right corner), position_from (an optional Vector2D object
            with x- and y- components ranging from 0 to 1 detailing from which
            part of the UI element's body the positioning factor should be
            applied, with (0, 0) being the top left corner of the object and
            (1, 1) being the bottom right corner of the object)."""
        self.visual_object = visual_object
        self.box_location = Vector2D(0, 0)
        self.positioning = positioning
        self.position_from = position_from
        self.padding = Vector2D(0, 0)
        self.container_size = Vector2D(0, 0)
        self.needs_controls = isinstance(self.visual_object, (DiscreteSlider, ContinuousSlider, Button, Entry, Checkbox, Container))

    def __str__(self):
        return str(self.visual_object)

    @property
    def active(self):
        return self.visual_object.active

    @active.setter
    def active(self, is_active):
        self.visual_object.active = is_active

    def update_padding(self):
        """ A method to update the padding of the UI element based on its
            positioning, position_from and container_size attributes, ensuring
            that the elements are correctly positioned within the container.
              Inputs: None.
              Outputs: None."""
        self.padding = scale_position(Vector2D(0,0), self.container_size,
                                      self.positioning, object_size=self.size,
                                      scale_from=self.position_from)

    def draw(self, surface, padding=Vector2D(0,0)):
        """ A method to draw the contained UI element to a given surface,
            applying the padding due to its positioning in the container.
              Inputs: surface (a pygame.Surface object that the containing UI
            element is drawn onto for the user to interact with), and padding (a
            Vector2D object that details the amount that the UI object's
            position should be shifted by as a result of outside element
            positioning).
              Outputs: None."""
        padding = padding + self.box_location + self.padding
        self.visual_object.draw(surface, padding=padding)

    def do_controls(self, padding=Vector2D(0,0)):
        """ A method to perform the control functionality of the contained UI
            elements, changing them with the user's control inputs.
              Inputs: padding, which is an optional Vector2D object that details
            the amount the UI object is shifted by by outside elements, so that
            controls involving mouse position can remove this padding for
            correct mouse position checks.
              Outputs: None."""
        if not self.needs_controls:
            return
        padding = padding + self.box_location + self.padding
        self.visual_object.do_controls(padding=padding)

    @property
    def size(self):
        return self.visual_object.size


class Container:
    """ A class that can hold groups of elements in a grid-like structure, used
        to easily display, control and position multiple elements, and to align
        negative space in GUI menu designs."""

    def __init__(self, width, height, edge_padding=Vector2D(0,0),
                 inner_padding=Vector2D(15,15), position=Vector2D(0,0),
                 has_outline=False):
        """ The constructor for the container class.
              Inputs: width (an integer or float) and height (an integer or
            float) which describe the size of the container in elements, e.g. a
            width of 2 and a height of 3 means you get a container of 6 elements
            in a 2x3 format, edge_padding (a Vector2D object) and inner_padding
            (a Vector2D object) which respectively represent the spacing between
            the UI elements from the edges of the container and between each
            other, position (a Vector2D object that represents the position of
            the container on the surfaces which it will be drawn on), and
            has_outline (an optional Boolean that details whether the container
            should be drawn with a surrounding black rectangle that outlines
            it)."""
        self.elements = []
        for i in range(height):
            row = []
            for j in range(width):
                row.append(Element(None, Vector2D(0,0)))
            self.elements.append(row)
        self.width = width
        self.height = height
        self.has_outline = has_outline
        self.active = True
        self.edge_padding = edge_padding
        self.inner_padding = inner_padding
        self.pos = position

    def check_index_validity(self, x_index, y_index):
        """ This method takes given input x- and y-index positions of the
            container and checks whether they are valid, i.e the position
            specified by the index exists given the size (width and height) of
            the container.
              Inputs: x_index (an Integer containing the x-index) and y_index
            (an integer containing the y-index)
              Output: a Boolean describing whether the indexes are valid (True
            if valid, False if not)."""
        if not(isinstance(x_index, int) and isinstance(y_index, int)):
            return False
        return 0 <= x_index < self.width and 0 <= y_index < self.height

    def display_in_text(self):
        """ A method that prints the contents of the container out into the
            standard input/output console. Used more for developing purposes
            than any practical purposes in the program.
              Inputs: None.
              Outputs: None."""
        for row in self.elements:
            print(" ".join([str(element) for element in row]))

    def create_image(self):
        """ A method which creates the image of the container, by creating /
            updating the images of all the UI elements that it contains, hence
            updating the container's image.
              Inputs: None.
              Outputs: None."""
        for row in self.elements:
            for element in row:
                if element.visual_object is not None:
                    element.visual_object.create_image()

    def update_element_locations(self):
        """ This method updates the locations of all of the UI elements within
            the container based upon the container's edge and inner padding and
            their positioning within the container.
              Inputs: None.
              Outputs: None."""
        cumulative_h = self.edge_padding.y
        for i in range(0, self.height):
            cumulative_w = self.edge_padding.x
            for j in range(self.width):
                element = self.elements[i][j]
                element.box_location = Vector2D(cumulative_w, cumulative_h)
                cumulative_w += element.container_size.x + self.inner_padding.x
            cumulative_h += element.container_size.y + self.inner_padding.y

    def update_paddings(self):
        """ This method updates the padding positions of each of the container's
            UI elements based on the positioning information that is stored
            within each element.
              Inputs: None.
              Outputs: None."""
        for row in self.elements:
            for element in row:
                if element.visual_object is not None:
                    element.update_padding()

    def update_element_boxes(self):
        """ This method updates the box sizes of all of the UI elements that the
            container holds. Each box's width becomes the maximum element width
            within that column and each box's height becomes the maximum element
            height within that column.
              Inputs: None.
              Outputs: None."""
        container_sizes = []
        for i in range(self.height):
            row = []
            for j in range(self.width):
                row.append(Vector2D(0,0))
            container_sizes.append(row)
        for index, row in enumerate(self.elements):  # set element height to max in row.
            element_sizes = [0 if element.visual_object is None else element.size.y for element in row]
            max_height_in_row = max(element_sizes)
            for size in container_sizes[index]:
                size.y = max_height_in_row
        for i in range(0, self.width):  # set element width to max in column.
            element_sizes = []
            for j in range(0, self.height):
                element_sizes.append(0 if self.elements[j][i].visual_object is None else self.elements[j][i].size.x)
            max_width_in_column = max(element_sizes)
            for j in range(0, self.height):
                container_sizes[j][i].x = max_width_in_column
        for i in range(0, self.height):
            for j in range(self.width):
                self.elements[i][j].container_size = container_sizes[i][j]
        self.update_element_locations()   

    def add_element(self, item, x_index=None, y_index=None,
                    positioning=Vector2D(0.5, 0.5), position_from=Vector2D(0.5,0.5)):
        """ This method adds a new UI object to the container as an element at a
            certain position in the grid. You can either specify a given index
            or the Container will automatically insert the object in the next
            available slot.
              Inputs: item (any UI element, e.g. ContinuousSlider,
            DiscreteSlider, Button, Label, Entry, Checkbox objects), x_index (an
            integer or None) and y_index (an integer or None) which represent
            the positon in the container to add the element to based upon zero-
            based indexing, positioning (a Vector2D object with x- and y-
            components ranging from 0 to 1 detailing the positioning of the UI
            element within its container space, with (0, 0) being the top left
            corner and (1, 1) being the bottom right corner), position_from (an
            optional Vector2D object with x- and y- components ranging from 0 to
            1 detailing from which part of the UI element's body the positioning
            factor should be applied, with (0, 0) being the top left corner of
            the object and (1, 1) being the bottom right corner of the object).
              Outputs: None."""
        element = Element(item, positioning, position_from=position_from)
        if x_index is not None and y_index is not None:
            if not self.check_index_validity(x_index, y_index):
                print("That is not a valid position. The element cannot be " + \
                      "added to the container.")
                return
            removed_item = self.elements[y_index][x_index]
            self.elements[y_index][x_index] = None
            del removed_item  # deletes current element at that index.
            self.elements[y_index][x_index] = element
        else:
            changed = False
            for i in range(0, self.height):
                for j in range(0, self.width):
                    if self.elements[i][j].visual_object is None:
                        self.elements[i][j] = element
                        changed = True
                        break
                if changed:
                    break
            if not changed:
                print("Container is full. Unable to add UI element.")
        # update the box sizes and padding with the new element added.
        self.update_element_boxes()
        self.update_paddings()

    def add_elements(self, *args):
        """ This method adds multiple elements to the container at once based
            upon provided information at the first possible spaces that can be
            found within the container.
              Inputs: You can either input several elements to be added in a row
            as arguments with default centredd positioning within the container,
            or you can input each element as a 3-item tuple argument. The 3-item
            tuple's first item should be the actual visual object itself (e.g. a
            ContinuousSlider, DiscreteSlider, Button, Label, Entry or Checkbox
            object), the second item should be the position Vector2D object from
            (0, 0) to (1, 1) and the third item should be the position_from
            Vector2D object again from (0, 0) to (1, 1)).
              Outputs: None."""
        for arg in args:
            if isinstance(arg, (list, tuple)):
                positioning = arg[1]
                position_from = arg[2]
                element = arg[0]
                self.add_element(element, positioning=positioning,
                                 position_from=position_from)
            else:
                element = arg
                self.add_element(element)

    def remove_element(self, item=None, x_index=None, y_index=None):
        """ This method removes an element from the container (but does not
            delete it from memory so it can still be used.
              Inputs: item (an optional UI object e.g. a ContinuousSlider,
            DiscreteSlider, Button, Label, Entry or Checkbox object) or x_index
            (an integer or None) and y_index (an integer or None) which
            represent the position in the container to delete an element from
            based upon zero-based indexing.
              Outputs: None."""
        if item is not None:
            for i in range(0, self.height):
                for j in range(0, self.width):
                    if self.elements[i][j].visual_object is item:
                        self.elements[i][j] = Element(None, Vector2D(0,0))
                        return
            print("UI element not found in container. Cannot remove element.")
        else:
            if x_index is None or y_index is None:
                print("No valid information was input to use to remove an element. You must either input a y-index value\n"
                      + "and an x-index value or the visual object to delete.")
                return
            if not self.check_index_validity(x_index, y_index):
                print("That is not a valid position. There is no element to remove from the container.")
                return
            self.elements[y_index][x_index] = Element(None, Vector2D(0,0))
        # does not update element box sizes, positions or padding unless
        # specifically told to as this is not necessary

    def draw(self, surface, padding=Vector2D(0,0)):
        """ This method draws the container and all of its elements to a given
            surface.
              Inputs: surface (a pygame.Surface object which the container will
            be drawn to so that the user can interact with it) and padding (an
            optional Vector2D object describing any positional shift to the
            container and all of its elements as a result of outside elements
            changing its position).
              Outputs: None."""
        if not self.active:
            return
        for row in self.elements:
            for element in row:
                if element.visual_object is not None:
                    element.draw(surface, padding=(padding + self.pos))
        if self.has_outline:
            pos = self.pos + padding
            positions = [tuple(pos), (pos.x + self.size.x, pos.y),
                         tuple(pos + self.size), (pos.x, pos.y + self.size.y)]
            pygame.draw.polygon(surface, (0, 0, 0), positions, 1)

    def do_controls(self, padding=Vector2D(0,0)):
        """ This method performs the control functionalities of the container
            (i.e. the controls of all of the elements within the container).
              Inputs: padding (an optional Vector2D object that details any
            padding applied to the container from outside, by which this padding
            needs to be transmitted to all other elements for mouse position
            shifting.
              Outputs: None."""
        if not self.active:
            return
        element_padding = padding + self.pos
        for row in self.elements:
            for element in row:
                if element.needs_controls:
                    element.do_controls(padding=element_padding)

    @property
    def size(self):
        """ A property equivalent to the size of the container for use in
            positioning and use in other containers and menus.
              Outputs: the size of the object as a Vector2D object in the format
            (width, height)."""
        total_width = 0
        total_height = 0
        for i in range(0, self.width):
            widths = []
            for j in range(0, self.height): 
                element = self.elements[j][i]
                widths.append(element.container_size.x if element.visual_object is not None else 0)
            total_width += max(widths)  # finds and adds up the maximum width for each column of visual elements
        for row in self.elements:
            total_height += max([(element.container_size.y if element.visual_object is not None else 0) for element in row])
            # finds and adds up the maximum height for each row
        size = Vector2D(total_width, total_height)
        # add any inner and edge padding size values.
        size += self.edge_padding * 2
        size.x += self.inner_padding.x * (self.width - 1)
        size.y += self.inner_padding.y * (self.height - 1)
        return size
