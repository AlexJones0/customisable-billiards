""" events module
Functions:
  None.
Classes:
 - Event
 - ButtonEvent
 - MessageEvent
 - MultiEvent
Description:
  Manages the custom-implemented event system used within the program. This is
entirely seperate from pygame's 'event' system and instead contains events
that cause different things to be displayed on the screen to the user during
the course of the game. During the simulation, events will be added to and
removed from an event queue to display different messages and options to the
user. This allows the user to interact with necessary conditional UI elements
(e.g. choosing to keep or redo an illegal break) whilst still being able to
interact with the simulation if necessary; this allows additional UI management
without breaking user immersion in the simulation."""

# external imports
from time import time as current_time
import pygame  # relies on pygame.init() and pygame.font.init() already being called by the main program.


# internal imports
from vectors import Vector2D
from interface import Button 
from data import Queue


class Event:
    """ The general class representing an event stored in the event queue -
        inherited by other event classes."""

    def __init__(self, condition=None):
        """ The constructor for a general event, which sets the settings and
            controls for the events.
              Inputs:condition (either None, a function or a list of functions
            that return Boolean values - if any become True, the Event will be
            removed).
              Outputs: None."""
        self.condition = condition
        self.can_remove = False

    def resolve(self):
        """ This method processes the event and checks whether it can be removed
            and therefore the next event focused on.
              Inputs: None.
              Outputs: None."""
        if self.condition is not None:
            if isinstance(self.condition, (list, tuple)):
                for cond in self.condition:
                    if cond():
                        self.can_remove = True
            else:
                if self.condition():
                    self.can_remove = True


class ButtonEvent(Event):
    """ The class representing a button event stored in the event queue -
        displays an interactable button on the screen mid-game."""

    def __init__(self, controls, surface, text, target,
                 font=pygame.font.SysFont(None, 32), position=Vector2D(0,0),
                 padding_args={}, condition=None):
        """ Constructs a button event, which is an event where a button is
            displayed on the screen to the user. A defined subroutine (target)
            is called when the button is pressed and the button is only played
            whilst another subroutine or group of subroutines (a condition /
            conditions) remains false.
              Inputs: controls (a ControlsObject object that contains the
            current control state, which is updated by the  main loop), surface
            (a pygame.Surface object that the button will be drawn to), text (a
            string which will be the button's label), target (a function that is
            called when the button in the event is pressed), font (a
            pygame.font.SysFont object which the button text will be written in),
            position (a Vector2D object that defaults to (0, 0) representing the
            coordinates of the surface that the button will be drawn at),
            padding_args (a dictionary of arguments (strings and other objects)
            related to padding arguments that are used to construct the button)
            and condition (a function or a list of functions that return Boolean
            values - if any become True, the ButtonEvent will be removed).
              Outputs: None."""
        super().__init__(condition=condition)
        self.surface = surface
        self.button = Button(controls, text, position=Vector2D(position),
                             font=font, target=target, **padding_args)
        
    def is_pressed(self):
        """ This method checks if the button in the button event has been
            pressed. This is often used for event removal conditions e.g. when
            multiple button events are being used and only one can be chosen.
              Inputs: None.
              Outputs: a Boolean detailing whether the button is pressed."""
        return self.button.pressed

    def resolve(self):
        """ This method processes the event and checks whether it can be removed
            (a condition of removal is met or the button has been pressed), and
            therefore the next event can be focused on.
              Inputs: None.
              Outputs: None."""
        super().resolve()   # check for conditional removal
        self.button.draw(self.surface)
        self.button.do_controls()
        if self.is_pressed() and not self.can_remove:
            self.can_remove = True
            

class MessageEvent(Event):
    """ The class representing a message event stored in the event queue -
        displays a message on the screen mid-game."""

    def __init__(self, settings, surface, message,
                 font=pygame.font.SysFont(None, 32), message_length=5,
                 condition=None):
        """ Constructs a message event, which is an event where a message is
            displayed on the screen to the user for a given length of time -
            after the time is over, the event is finished and the message stops.
              Inputs: settings (a dictionary containg several settings used by
            the event), surface (a pygame.Surface object that the button will be
            drawn to), message (a string containing the message to be displayed
            to the user, with '\n' used to split lines), font (a
            pygame.font.SysFont object which the text will be written in),
            message_length (an optional positive integer or float describing the
            time in seconds that the message will be displayed to the screen),
            and condition (either None, a function or a list of functions that
            return Boolean values - if any become True, the MessageEvent will be
            removed ahead of its pre-defined removal time).
              Outputs: None."""
        super().__init__(condition=condition)
        self.settings = settings
        self.surface = surface
        self.message = message.split("\n")
        self.font = font
        self.line_sizes = [font.size(line) for line in self.message]  # we calculate line sizes in the constructor before displaying for efficiency
        self.__started_waiting = None
        self.__message_length = message_length

    def resolve(self):
        """ Attempts to resolve the message event, checking the conditions or
            whether the message can be removed based upon time passing.
              Inputs: None.
              Outputs: None."""
        time = current_time()
        if self.__started_waiting is None:
            self.__started_waiting = time
        elif time - self.__started_waiting > self.__message_length:
            self.can_remove = True
        super().resolve()  # check for conditional removal
        for index, line in enumerate(self.message):  # draw to the screen
            self.surface.blit(self.font.render(line, 1, self.settings["general_outline_colour"]), [(self.settings["window_width"] - self.line_sizes[index][0])//2, (self.settings["window_height"]//5) + self.line_sizes[index][1] * index])


class MultiEvent(Event):
    """ An event stored in the event_queue that holds multiple events allowing
        multiple events to be displayed at the same time e.g. several buttons
        and / or a message."""

    def __init__(self, *args, condition=None):
        """ Constructs a multi-event, which is an event where multiple different
            events are displayed to the screen and interacted with at once.
              Inputs: any variable number of Event or Event subclass objects
            that are to be displayed at the same  time (*args), and condition
            (either None, a function or a list of functions that return Boolean
            values - if any become True, the multi-event and all events it
            contains will be removed).
              Outputs: None."""
        super().__init__(condition=condition)
        self.events = []
        for event in args:
            self.events.append(event)

    def resolve(self):
        """ Attempts to resolve the multi-event event, checking the conditions
            or whether all the individual events have been resolved themselves.
              Inputs: None.
              Outputs: None."""
        super().resolve()   # check for conditional removal
        to_remove = []
        for event in self.events:
            event.resolve()
            if event.can_remove:
                to_remove.append(event)
        for event in to_remove:
            self.events.remove(event)
            del event
        if len(self.events) == 0:
            self.can_remove = True


# creates the event queue where events will be stored during runtime
event_queue = Queue()
