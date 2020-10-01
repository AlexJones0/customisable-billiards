""" controls module
Functions:
  None.
Classes:
 - ControlsObject
Description:
  A simple module that will only contain one class, which is the ControlsObject.
This will be an extension of a dictionary which will allow controls to be easily
accessed by all parts of the program. It will simply be used to store the
current state of user-input controls and add small additional functionality
which will make different control inputs easier to access (e.g. a mouse_clicked
property)."""

# external modules
import pygame


class ControlsObject(dict):
    """ A subclass of a dictionary, used to store the current state of the
        user-input controls."""

    def __init__(self, *args, **kwargs):
        """ A constructor for the dictionary. Requires the same inputs as a
            dictionary object.
              Inputs: Any inputs.
              Outputs: None."""
        super().__init__(*args, **kwargs)

    @property
    def mouse_clicked(self):
        """ A property that returns a Boolean value describing whether the mouse
            was clicked (not pressed down, specifically clicked) in the last
            control update or not. No inputs, and it outputs a Boolean value."""
        for event in self["events"]:
            if event.type == pygame.MOUSEBUTTONDOWN:
                return True
        return False
