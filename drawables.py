""" drawables module
Functions:
 - draw_dashed_line
Classes:
 - Cue
 - DrawableTable
 - DrawableBall
Description:
  Contains classes that inherit from the classes in the simulation module, which
handles the physics simulation of 8-ball pool. This module extends the Table and
Ball objects in order to make it so that they can be drawn to the pygame screen
so that users can see the simulation. This is kept seperate from the
non-drawable versions as those are used by the server, which does not need to be
able to draw the simulation. It also contains a Cue class that users can use to
actually interact with the simulation, hitting balls on the table."""

# python/downloaded modules
import pygame  # relies on pygame.init() and pygame.font.init() already having been called externally.
from random import randint
import math


# custom-made modules
from vectors import Vector2D
from simulation import Table, Ball, LineSegment


def draw_dashed_line(surface, colour, coord1, coord2, thickness, dash_length):
    """ A method to draw a dashed line to a surface, made by splitting up a
        given line into multiple smaller line objects.
          Inputs: surface (a pygame.Surface object which the dashed line is
        drawn to), colour (a tuple containing 3 integers that represents the RGB
        colour of the line, coord1 (a Vector2D object) and coord2 (a Vector2D
        object) representing the start and end points of the dashed line,
        thickness (an integer representing the thickness / width in pixels of
        the dashed lines, and dash_length (an integer or float representing the
        length of each dash within the line that the line will be split into).
          Outputs: None (changes will be made to the pygame.Surface object)."""
    if isinstance(coord1, (tuple, list)):
        coord1 = Vector2D(coord1)
    if isinstance(coord2, (tuple, list)):
        coord2 = Vector2D(coord2)
    distance_vector = coord2 - coord1
    dash_vector = distance_vector.normalise_result() * dash_length
    x_change = dash_vector.x
    y_change = dash_vector.y
    dash_num = int(distance_vector.magnitude / dash_length)
    for i in range(0, dash_num, 2):  # steps of 2 means other dash is not drawn.
        pygame.draw.line(surface, colour,
                         [coord1.x + i * x_change, coord1.y + i * y_change],
                         [coord1.x + (i+1) * x_change, coord1.y + (i+1) * y_change],
                         thickness)


class Cue:
    """ This class holds the information about the cue that currently occupies
        the table, including whether it is in use / can be used, the angle and
        position it is at, the ball it is focusing and its maximum and minimum
        displacements."""

    def __init__(self, settings):
        """ The constructor for the cue class, creating the cue based upon
            predefined settings.
              Inputs: settings (a dictionary containing several predefined
            settings about the cue, including "cue_length" (integer/float),
            "cue_diameter" (integer/float), "base_cue_offset" (integer/float),
            "max_cue_offset" (integer/float), "table_length" (integer/float),
            "table_width" (integer/float), "ppm" (integer/float),
            "max_cue_force" (integer/float), "cue_colour" (3-integer tuple),
            "cue_outline_colour" ( 3-integer tuple/list),
            "ray_colour" (3-integer tuple/list) and "show_path_projection"
            (a Boolean detailing whether a pathing ray should be shown).
              Outputs: None."""
        self.settings = settings
        self.can_focus = self.settings["auto_focus"]
        self.active = False
        self.focus = None
        self.ray = None
        self.angle = math.pi
        self.base_offset = self.settings["base_cue_offset"]
        self.max_offset = self.settings["max_cue_offset"]
        self.current_offset = self.base_offset
        self.positions = []  # an array that stores the 4 corners of the cue as coordinates for easy drawing (no repeated calculations every update).
        self.update_ray()

    def reset_positioning(self):
        """ This method resets the position and angle of the cue whenever it is
            focused / de-focused or reset.
              Inputs: None.
              Outputs: None."""
        self.angle = math.pi
        self.current_offset = self.base_offset

    def has_shot(self):
        """ This method simply returns whether the cue has been shot (i.e. the
            cue is inactive). Outputs a Boolean value."""
        return not self.active

    def update_ray(self):
        """ This method updates the cue's projection ray object (a LineSegment
            object) based upon a change its new angle and positioning after a
            change has occured.
              Inputs: None (only attributes within the cue are accessed).
              Outputs: None."""
        if self.settings["show_path_projection"] and self.focus is not None:
            largest_dimension = max(self.settings["table_length"],
                                    self.settings["table_width"])
            angle_vector = Vector2D(math.cos(self.angle + math.pi),
                                    math.sin(self.angle + math.pi))
            radius_vector = angle_vector * self.focus.representation.radius
            outer_coord = self.focus.centre + angle_vector * largest_dimension
            self.ray = LineSegment(self.focus.centre+radius_vector, outer_coord)
        else:
            self.ray = None

    def set_focus(self, ball):
        """ This method focuses the cue on a ball, making the cue active and
            appear by / control around the ball.
              Inputs: ball (a Ball object currently on the table that the Cue
            should focus on and control around).
              Outputs: None."""
        self.active = True
        self.focus = ball
        self.reset_positioning()
        self.update_positions()

    def remove_focus(self):
        """ This method removes focus from the currently focused ball, making
            the cue inactive and resetting the cue's position and angle.
              Inputs: None.
              Outputs: None."""
        self.active = False
        self.focus = None
        self.reset_positioning()

    def change_offset(self, amount):
        """ This method changes the offset of the cue (relative to the ball that
            it is focusing on) by a given input amount provided that it does not
            decrease past its base offset amount or increase past the maximum
            offset amount, moving the cue towards/away from the ball.
              Inputs: amount (an integer or float, the length in metres that
            offset is to be changed by).
              Outputs: None."""
        self.current_offset += amount
        if self.current_offset > self.max_offset:
            self.current_offset = self.max_offset
        elif self.current_offset < self.base_offset:
            self.current_offset = self.base_offset

    def update_positions(self):
        """ This method works out the new coordinates of the corners of the cue
            after a change in position/angle so that the cue can be correctly
            displayed on a surface.
              Inputs: None.
              Outputs: None (changes self.positions)."""
        angle_vector = Vector2D(math.cos(self.angle), math.sin(self.angle))
        angle_vector.normalise()
        start_vector = self.focus.centre + angle_vector * self.current_offset
        perpendicular_vector = angle_vector.perpendicular() * (self.settings["cue_diameter"] / 2)
        end_vector = start_vector + angle_vector * self.settings["cue_length"]
        self.positions = [start_vector + perpendicular_vector,
                          start_vector - perpendicular_vector,
                          end_vector - perpendicular_vector,
                          end_vector + perpendicular_vector]

    @property
    def force(self):
        """ This property calculates the current force applied by the cue by
            using the ratio of its current offset to its maximum possible cue
            offset as well as the maximum cue force stored in settings.
              Outputs: an integer/float representing the current force that
            would be applied by the Cue."""
        ratio = (self.current_offset - self.focus.radius) / (self.max_offset - self.focus.radius)
        return float(ratio * self.settings["max_cue_force"])

    @force.setter
    def force(self, new_force):
        """ A setter for the force, making it so that you can directly set a
            custom cue_force, and the cue's position will automatically be
            scaled so that this force can be achieved.
              Inputs: new_force (an integer/float that will be the new force
            applied by the cue).
              Outputs: None."""
        ratio = new_force / self.settings["max_cue_force"]
        ratio *= (self.max_offset - self.focus.radius)
        self.current_offset = ratio + self.focus.radius

    def use(self):
        """ This method is called when the cue is actually used (i.e. a shot is
            made and the cue hits the ball). It applies a force based upon its
            set maximum force applied and its current offset relative to the
            ball, and removes the ball from its focus.
              Inputs: None.
              Outputs: None."""
        if self.active:  # can't use the cue if it is not active
            self.focus.apply_force(self.settings["time_of_cue_impact"],
                                   self.force, self.angle - math.pi)
            print("Hitting the ball with a force of {} N at an angle of {} from a position of {}".format(self.force, self.angle, self.focus.pos))
            self.remove_focus()

    def draw(self, surface, shift=Vector2D(0, 0), scale=1):
        """ This method is responsible for drawing the cue on a surface,
            assuming that it is active. It also draws the projected ray that
            comes from the cue if that option is in use.
              Inputs: surface (a pygame.Surface object that the cue will be
            drawn to), shift (an optional Vector2D object that defaults to
            (0, 0), representing the amount that the cue's drawn position should
            be shifted/padded by when it is drawn to the surface), and scale (an
            integer or float describing the scale factor at which the cue should
            be drawn, allowing change of size).
              Outputs: None (the cue is drawn on the surface object)."""
        if len(self.positions) == 0 or not self.active:
            return
        scaling_factor = self.settings["ppm"] * scale
        positions = [tuple((i+shift)*scaling_factor) for i in self.positions]
        pygame.draw.polygon(surface, self.settings["cue_colour"], positions, 0)
        # in pygame, 0 thickness = filled
        pygame.draw.polygon(surface, self.settings["cue_outline_colour"], positions, 1)  # adds an outline to the cue.
        if self.ray is not None:  # draws the path projection ray if applicable.
            dash_length = self.settings["window_width"] // 50
            draw_dashed_line(surface, self.settings["ray_colour"],
                             tuple((self.ray.coord1 + shift) * scaling_factor),
                             tuple((self.ray.coord2 + shift) * scaling_factor),
                             2, dash_length)


class DrawableTable(Table):
    """ This class is a subclass of the simulation module's Table class, and is
        modified so that the Table can also be drawn to a screen."""
    
    def __init__(self, coords, settings):
        """ The constructor for a DrawableTable. Like constructing a normal
            Table, except that an image is created as well.
              Inputs: coords (a tuple, list or Vector2D object describing the
            position of the top left corner of the table (the centre of the top
            left pocket)), and settings (a dictionary containing many pre-
            determined values to be used in the simulation, such as the table's
            length, width and pocket sizes).
              Outputs: None."""
        super().__init__(coords, settings)
        self.cue = Cue(settings)
        self.image = None
        self.create_image()

    def create_image(self):
        """ This method creates the image representation of the table that will
            be displayed on the screen, based upon the attributes currently
            stored within the table and settings objects. It constructs the
            background, rails and pockets.
              Inputs: None.
              Outputs: None (because the new image is stored within the
            DrawableTable object)."""
        ppm = self.settings["ppm"]
        image_size = Vector2D(self.length, self.width)
        image_size += Vector2D(self.pocket_radius, self.pocket_radius) * 2
        image_size *= ppm
        image_size.round()
        self.image = pygame.Surface(tuple(image_size), pygame.SRCALPHA, 32)
        self.image.convert_alpha()  # Gives the table a transparent background.
        self.image.fill(self.settings["background_colour"])
        main_surface_size = Vector2D(self.length, self.width) * ppm
        main_surface_size.round()
        main_surface = pygame.Surface(tuple(main_surface_size))
        main_surface.fill(self.settings["table_background_colour"])
        corner_offset = self.pocket_radius * ppm
        corner_pos = Vector2D(corner_offset, corner_offset)
        self.image.blit(main_surface, tuple(corner_pos))
        for rail in self.rails:
            pygame.draw.line(self.image, self.settings["table_outline_colour"],
                             tuple((rail.coord1 - self.pos) * ppm + corner_pos),
                             tuple((rail.coord2 - self.pos) * ppm + corner_pos),
                             3)
        for pocket in self.pockets:
            centre_coord = ((pocket.centre - self.pos) * ppm + corner_pos)
            centre_coord.round()
            pocket_radius = int(round(pocket.radius * ppm, 0))
            pygame.draw.circle(self.image, self.settings["table_outline_colour"],
                               tuple(centre_coord), pocket_radius, 0)
            pygame.draw.circle(self.image, self.settings["table_hole_colour"],
                               tuple(centre_coord),
                               pocket_radius-2 if pocket_radius >= 2 else 0, 0)

    def resolve_pockets(self):
        """ A method which will check for and resolve all incidences of pockets
            on the table, removing them from the table if they are a normal ball
            or putting the ball in hand if it is the cue ball (and a foul has
            been incurred).
              Inputs: None.
              Outputs: None."""
        super().resolve_pockets()
        for ball in self.pocketed:
            if ball.can_show:
                ball.can_show = False

    def attempt_focus(self):
        """ This methods applies the auto focusing setting property after each
            turn, such that when the table is no longer in motion and the next
            turn has started, it will try and find a ball that can be focused
            (the cue ball) and focus it.
              Inputs: None.
              Outputs: None."""
        # applies many relevant checks to see if the cue can auto focus.
        if not self.cue.active and not self.in_motion and \
           not self.previously_in_motion and self.cue.can_focus and \
           self.holding is None:
            for ball in self.balls:
                if ball.can_focus:
                    self.cue.set_focus(ball)
                    break

    def update(self, time):
        """ A method that will update the physics of a table over a given period
            of time, managing the movement and collisions of different balls and
            also checking whether the table is in motion or not.
              Inputs: time (a float or integer that describes the amount of time
            in seconds over which to update the physics of the table).
              Outputs: None."""
        super().update(time)
        if self.settings["auto_focus"]:
            self.attempt_focus()

    def draw(self, surface, draw_balls=True, draw_cue=True, shift=Vector2D(0,0)):
        """ This method is used to draw a table and all of the objects it
            contains (the cue and balls) to the given surface i.e. the screen.
            The values are scaled up to the size of the screen and then drawn.
              Inputs: surface (a pygame.Surface object on which the table should
            be drawn), draw_balls (an optional Boolean detailing whether the table
            should also draw any balls that are on it or not), draw_cue (an
            optional Boolean detailing whether the table should also draw the
            cue on it or not), and shift (an optional Vector2D object that
            defaults to (0, 0) describing any padding applied to move the
            table's position).
              Outputs: None (changes the given surface object)."""
        # the coordinates of the background surface + 1 because of the border
        position = self.pos + shift - Vector2D(self.pocket_radius,
                                               self.pocket_radius)
        position *= self.settings["ppm"]
        surface.blit(self.image, tuple(position))
        if draw_balls:
            for ball in self.balls:
                if ball.can_show:
                    ball.draw(surface, shift=shift)
        if draw_cue and self.cue.active:
            self.cue.draw(surface, shift=shift)


class DrawableBall(Ball):
    """ This class is a subclass of the simulation module's Ball class, and is
        modified so that the Ball can also be easily drawn to the screen for
        user interaction at a variety of different sizes."""
    
    def __init__(self, coords, settings, colour, striped=False, number=None,
                 can_focus=False):
        """ The constructor for a DrawableBall. Like constructing a normal Ball,
            except that an image scaling dictionary is created as well.
              Inputs: coords (a tuple, list or Vector2D object that describes
            the centre coordinates of the ball), settings (a dictionary with
            many predetermined values used to construct the ball such as
            physical constants, ball size and ball mass), colour (a tuple or
            list containing 3 integers that represent the RGB value of the
            colour of the ball), striped (an optional Boolean detailing whether
            the ball should have be considered a striped ball or not), number
            (an optional Integer value that is None by default; the ball's
            number), and can_focus (a Boolean value describing whether the ball
            can be focused and hit by the cue).
              Outputs: None."""
        super().__init__(coords, settings, striped=striped, number=number)
        self.can_show = True
        self.can_focus = can_focus
        self.colour = colour
        self.font_type = self.settings["ball_font"]
        self.font_size = int(0.8726 * self.settings["ball_radius"] * self.settings["ppm"])
        self.scales = {}  # dictionary that stores differently scaled versions of the ball image to avoid repeat creation
        self.create_image(1)

    def create_image(self, scale):
        """ This function creates the image representation of the ball at a
            certain scale that will be drawn to the screen for the user to view.
              Inputs: scale (an integer or float detailing the enlargement scale
            factor applied to the ball when creating the image, so that it can
            late be drawn at this scale).
              Outputs: None."""
        unrounded_radius = self.radius * self.settings["ppm"] * scale
        image_radius = int(round(unrounded_radius, 0))
        # has to be rounded as pygame only accepts integers
        image_size = int(round(unrounded_radius * 2, 0))
        # we calculate using unrounded for accuracy
        image = pygame.Surface((image_size, image_size), pygame.SRCALPHA, 32)
        image.convert_alpha()  # creates a transparent background
        pygame.draw.circle(image, self.settings["ball_outline_colour"],
                           (image_radius, image_radius), image_radius, 0)
        if not self.striped:
            pygame.draw.circle(image, self.colour, (image_radius, image_radius),
                               image_radius - 1 if image_radius >= 1 else 0, 0)
        else:
            pygame.draw.circle(image, (255, 255, 255),  # draws outline
                               (image_radius, image_radius),
                               image_radius - 1 if image_radius >= 1 else 0, 0)
            # now we create a smaller rectangle surface to draw a cut off circle
            # in order to make the striped pattern.
            smaller_surface = pygame.Surface((int(image_radius * 2), image_radius), pygame.SRCALPHA, 32)
            smaller_surface.convert_alpha()
            half_radius = int(round(unrounded_radius / 2, 0))
            pygame.draw.circle(smaller_surface, self.colour,
                               (image_radius, half_radius),
                               image_radius - 1 if image_radius >= 1 else 0, 0)
            image.blit(smaller_surface, (0, half_radius))
        if self.settings["show_numbers"] and self.number is not None:
            font = pygame.font.SysFont(self.font_type, int(self.font_size*scale))
            number_label = font.render(str(self.number), 1, (0, 0, 0))
            number_size = font.size(str(self.number))
            pygame.draw.circle(image, (255, 255, 255),
                               (image_radius, image_radius),
                               int(round(image_radius / 2.15)), 0)
            image_position = (int(round(image_radius - number_size[0] / 2)),
                              int(round(image_radius - number_size[1] / 2)))
            image.blit(number_label, image_position)
        self.scales[scale] = image

    def draw(self, surface, scale=1, alternate_pos=None, shift=Vector2D(0,0)):
        """ This method draws the image of the ball to the screen at different
            required scales so that the user can see and interact with the ball.
              Inputs: surface (a pygame.Surface object on which the table should
            be drawn), scale (an optional positive integer or float detailing
            what scale the ball should be drawn at - if an image has not yet
            been created at this scale, the image will be created and stored to
            be drawn at this scale easily in the future), alternate_pos (an
            optional Vector2D object or None that describes an alternate centre
            position that you wish the ball to be drawn at instead of its
            current centre position) and shift (an optional Vector2D object that
            defaults to (0,0) and describes any padding applied to move the
            ball's position.
              Outputs: None (changes the given surface object)."""
        if scale not in self.scales:
            self.create_image(scale)
        if alternate_pos is not None:
            if isinstance(alternate_pos, Vector2D):
                alternate_pos = tuple(alternate_pos)
            surface.blit(self.scales[scale], alternate_pos)
        else:
            blit_pos = self.representation.centre + shift - self._radius_vector
            blit_pos *= self.settings["ppm"]
            blit_pos.round()  # must round as pygame only accepts integers.
            surface.blit(self.scales[scale], tuple(blit_pos))
