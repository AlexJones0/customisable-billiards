""" simulation module
Functions:
 - circle_line_collision_check
 - circle_circle_collision_check
Classes:
 - LineSegment
 - Circle
 - Table
 - Ball
Description:
  Contains code pertaining to the physics simulation of 8-ball pool.
Uses mathematical models to represent the table and balls and the circles and
lines that make up these objects. Dictates the physics behind the objects and
how they are interfaced with by the rest of the system. Examples include
collision detection and collision resolving, updating motion, etc."""

# python/downloaded modules
import time
import math
from random import randint
import pygame


# custom-made modules
from vectors import Vector2D


def circle_line_collision_check(circle, line):
    """ A function that checks whether a given circle and line are colliding.
        Does not find time or point of collision.
          Inputs: circle (a Circle object) and line (a LineSegment object),
        which you are checking for collision.
          Output: A Boolean value describing whether the input circle and line
        are colliding or not."""
    if not (isinstance(circle, Circle) and isinstance(line, LineSegment)):
        raise TypeError("Must input a Circle and Line object.")
    # Uses vector maths to determine the point on the line through which a
    # perpendicular bisecting line would cross through the circle's centre.
    distance_vector = circle.centre - line.coord1
    normalised_line_vector = line.vector.normalise_result()
    projected_magnitude = distance_vector.dot_product(normalised_line_vector)
    projected_vector = normalised_line_vector * projected_magnitude
    new_position = line.coord1 + projected_vector
    # checks if the new point is actually on the line segment or outside it,
    # as if it is outside the objects are not colliding.
    if line.coord_within_bounds(new_position):
        # check with magnitude squared as square rooting is CPU expensive.
        distance_vector = circle.centre - new_position
        return distance_vector.magnitude_squared <= circle.radius**2
    else:
        # A check in case the circle is touching the end point of the line
        # segment and so would not be seen by checking the centre coordinate
        # boundaries - we instead check whether the closest end of the line is
        # colliding with the ball.
        coord_one_distance = (line.coord1 - circle.centre).magnitude_squared
        coord_two_distance = (line.coord2 - circle.centre).magnitude_squared
        closest_distance = min(coord_one_distance, coord_two_distance)
        return closest_distance <= circle.radius**2


def circle_circle_collision_check(circle1, circle2):
    """ A function that checks whether two given circles are colliding with each
        other.
          Inputs: two Circle objects, of any dimensions or positions, which you
        are checking for collision.
          Output: A Boolean value describing whether the two input circles are
        colliding or not."""
    separation_vector = circle2.centre - circle1.centre
    distance_between_squared = separation_vector.magnitude_squared
    # comparison with squares as it is less expensive
    if distance_between_squared > (circle1.radius + circle2.radius)**2:
        return False
    elif distance_between_squared < (circle1.radius - circle2.radius)**2:
        # checks if one circle is contained inside another
        return False
    else:
        return True


class LineSegment:
    """ A class to store a line segment represented with two coordinate vectors,
        or a distance vector between these two coordinates."""

    def __init__(self, coord1, coord2):
        """ Constructs the line segment based upon provided end coordinates.
              Inputs: coord1 (a Vector2D, tuple or list), coord2 (a Vector2D,
            tuple or list), both representing end coordinatesof the line segment
            in 2D space.
              Outputs: None, raises exceptions depending on the inputs."""
        if isinstance(coord1, (tuple, list)) and \
           isinstance(coord2, (tuple, list)):
            if len(coord1) == 2 and len(coord2) == 2:
                self.coord1 = Vector2D(coord1[0], coord1[1])
                self.coord2 = Vector2D(coord2[0], coord2[1])
                # Creates a vector displacement value from coord 1 to 2.
                self.vector = self.coord2 - self.coord1
            else:
                raise ValueError("Coordinates must contain 2 items, x- and y-positions.")
        elif isinstance(coord1, Vector2D) and isinstance(coord2, Vector2D):
            self.coord1, self.coord2 = coord1, coord2
            self.vector = self.coord2 - self.coord1
        else:
            raise TypeError("Coordinates must be tuples, lists or a 2D vector.")

    def coord_within_bounds(self, coord, extra=0):
        """ This function checks whether a given coordinate is within the
            bounding box of the line, i.e. whether the specified coordinate
            lies within the boundary of the line.
              Inputs: coord (a Vector2D, tuple or list which is the input
            coordinate you are checking) and extra (an optional integer or float
            which is any extra distance to check from both ends of the line).
              Outputs: A Boolean value that describes whether the input coord is
            within the boundaries of the line."""
        if isinstance(coord, Vector2D):
            x = coord.x
            y = coord.y
        elif isinstance(coord, (tuple, list)):
            if len(coord) == 2:
                x = coord[0]
                y = coord[1]
            else:
                raise ValueError("Coordinates must contain 2 items, x- and y-positions.")
        else:
            raise TypeError("Coordinate must be a tuple, list or 2D Vector.")
        # check whether x- or y- components of the input coordinate is between
        # the respective components of the line segment's coordinates.
        return self.coord1.x - extra < x < self.coord2.x + extra or \
               self.coord2.x - extra < x < self.coord1.x + extra or \
               self.coord1.y - extra < y < self.coord2.y + extra or \
               self.coord2.y - extra < y < self.coord1.y + extra

    def check_collision(self, collision_obj):
        """ This function is a general function to check whether the line
            segment is colliding with a given object. It calls a different
            collision function depending upon the type of input object.
              Inputs: collision_obj (a Circle object, the object for collision).
              Outputs: None."""
        if isinstance(collision_obj, Circle):
            return circle_line_collision_check(collision_obj, self)


class Circle:
    """ A class to store a circle shape represented with a coordinate centre
        vector and a set radius."""

    def __init__(self, centre, radius):
        """ Constructs the circle based upon provided centre coordinates and a
            radius.
              Input: centre (a tuple, list or Vector2D object detailing the
            coordinates of the circle's centre) and radius (an integer or float
            that describes the radius of the circle).
              Outputs: None, raises exceptions if input is of the wrong type."""
        self.centre = centre
        self.radius = radius

    @property
    def centre(self):
        return self.__centre

    @centre.setter
    def centre(self, centre):
        """ A setter for the circle's centre positions. Also updates the
            centre_to_draw attribute value.
              Input: centre (a tuple, list or Vector2D object detailing the
            coordinates of the circle's centre).
              Outputs: None, raises an error if input is of the wrong type."""
        if isinstance(centre, Vector2D):
            self.__centre = centre
        elif isinstance(centre, (tuple, list)) and len(centre) == 2:
            self.__centre = Vector2D(centre[0], centre[1])
        else:
            raise TypeError("Centre coordinate must be a 2D Vector or a 2-item tuple / array.")
        # centre_to_draw and radius_to_draw are rounded values of centre and
        # radius, used because the pygame coordinate system only works with
        # integers. They are calculated here for efficiency, to avoid having to
        # round them every time you want to update and draw to the screen, when
        # in actuality these values will rarely be changed during the runtime of
        # the program.
        self.centre_to_draw = centre.round_result()

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, radius):
        """ A setter for the circle's radius value. Also updates the
            centre_to_draw value.
              Input: radius (an integer or float that describes the radius of
            the circle).
              Outputs: None, raises an error if input is of the wrong type."""
        if not isinstance(radius, (int, float)):
            raise TypeError("Radius must be either an integer or a float.")
        self.__radius = radius
        # radius_to_draw calculated here for efficiency.
        self.radius_to_draw = int(round(self.radius, 0))

    def contains(self, coordinate, extra=0):
        """ Checks whether an input coordinate is contained within the circle.
              Inputs: coordinate (a tuple, list or Vector2D object that
            describes the coordinate being checked), and extra (an integer or
            float value which is added onto the circle's own radius when doing
            this check).
              Outputs: A Boolean value describing whether the circle contains
            the input coordinate or not."""
        if isinstance(coordinate, Vector2D):
            distance = coordinate - self.centre
        elif isinstance(coordinate, (tuple, list)) and len(coordinate) == 2:
            distance = Vector2D(self.centre.x - coordinate[0],
                                self.centre.y - coordinate[1])
        else:
            raise TypeError("Input coordinate must be a 2D Vector or a 2-item list / tuple")
        return distance.magnitude_squared <= (self.radius + extra)**2

    def check_collision(self, collision_obj):
        if isinstance(collision_obj, LineSegment):
            return circle_line_collision_check(self, collision_obj)
        elif isinstance(collision_obj, Circle):
            return circle_circle_collision_check(self, collision_obj)


class Table:
    """ This class holds all the information about the pool table currently in
        play, as well as the objects that occupy that table such as the cue and
        the balls."""

    def __init__(self, coords, settings):
        """ Constructs the table based upon input coordinates and settings.
              Inputs: coords (a tuple, list or Vector2D object describing the
            position of the top left corner of the table (the centre of the top
            left pocket)), and settings (a dictionary containing many pre-
            determined values to be used in the simulation, such as the
            table's length, width and pocket sizes).
              Outputs: None."""
        self.settings = settings
        self.pos = Vector2D(coords)
        self.length = self.settings["table_length"]
        self.width = self.settings["table_width"]
        self.pocket_radius = self.settings["ball_radius"] * self.settings["hole_factor"]
        # calculate bottom right corner pos of table for later boundary checks
        self.upper_pos = self.pos + Vector2D(self.length, self.width)
        self.balls = []
        # using shorthand to refer to variables so that code is more readable
        r = self.pocket_radius
        L = self.length
        w = self.width
        line_coords = [((r, 0), (L / 2 - r, 0)),
                       ((r + L / 2, 0), (0 - r + L, 0)),
                       ((r, w), (0 - r + L / 2, w)),
                       ((r + L / 2, w), (0 - r + L, w)), ((0, r), (0, w - r)),
                       ((L, r), (0 + L, w - r))]
        circle_coords = [(0, 0), (L / 2, 0), (L, 0), (0, w), (L / 2, w), (L, w)]
        self.rails = [LineSegment(Vector2D(coord[0]) + self.pos,
                                  Vector2D(coord[1]) + self.pos)
                      for coord in line_coords]
        self.pockets = [Circle(Vector2D(coords) + self.pos, r)
                        for coords in circle_coords]
        self.in_motion = False
        self.previously_in_motion = False
        self.holding = None
        self.eight_ball = None
        self.cue_ball = None
        self.hit = []
        self.pocketed = []
        self.rail_contacts = []

    def reset_counts(self):
        """ A method that resets the hit, pocketed and rail_contact arrays that
            store information about the table during a player's turn to
            determine which game rules to apply.
              Inputs: None
              Outputs: None"""
        self.hit = []
        self.pocketed = []
        self.rail_contacts = []

    def add_ball(self, ball):
        """ A method which adds an input ball to the table, meaning it will be
            part of the game and can be interacted with by a user.
              Inputs: ball (a Ball object, the ball to be added to the table).
              Outputs: None."""
        if ball.number == 8:
            self.eight_ball = ball
        else:
            if ball.number is None and self.cue_ball is None:
                self.cue_ball = ball
        self.balls.append(ball)

    def remove_ball(self, ball, delete_ball=False):
        """ A method which removes an input ball from the table, meaning it will
            no longer be a part of the simulation and can no longer be
            interacted with by the user.
              Inputs: ball (either a Ball object or one of its subclasses e.g.
            DrawableBall, the ball that is to be removed from the table) and
            delete_ball (an optional Boolean value that details whether the ball
            should be deleted after removal for efficiency or not).
              Outputs: None, prints to the output console if it was unable to
            find the input ball."""
        try:
            self.balls.remove(ball)
            if delete_ball:
                del ball
        except ValueError:
            print("Could not remove ball; ball was not found")

    def resolve_pockets(self):
        """ A method which will check for and resolve all incidences of pockets
            on the table, removing them from the table if they are a normal ball
            or putting the ball in hand if it is the cue ball (and a foul has
            been incurred).
              Inputs: None.
              Outputs: None."""
        change_factor = 0  # an incremented value used to stop skipping indexes when deleting items from ball list
        for index, ball in enumerate(self.balls):
            if ball.vel.x != 0 or ball.vel.y != 0:  # first checks if moving for efficiency - balls that have not moved cannot have been pocketed.
                for pocket in self.pockets:
                    if pocket.contains(ball.centre):
                        self.pocketed.append(ball)
                        if ball is not self.cue_ball:
                            del self.balls[index - change_factor]
                            change_factor += 1
                        else:
                            self.holding = ball
                            ball.vel.set((0, 0))
                            ball.can_collide = False
                        break

    def resolve_collisions(self):
        """ A method that will manage resolving collisions between balls
            occupying the table and recording the different statistics about
            these collisions used for applying game rules.
              Inputs: None.
              Outputs: None."""
        for ball in self.balls:
            # Don't check collisions if the ball is not in motion - if another
            # ball is colliding with it, that ball will be checked (because it
            # is in motion).
            if not ball.colliding and ball.can_collide and \
               (ball.vel.x != 0 or ball.vel.y != 0):
                collided_with = ball.get_collisions(self.balls, self.rails,
                                                    self.pos, self.upper_pos)
                if ball.colliding:
                    if ball not in self.hit and ball is not self.cue_ball:
                        self.hit.append(ball)
                    for collided_ball in collided_with:
                        if collided_ball not in self.hit and \
                           collided_ball is not self.cue_ball:
                            self.hit.append(collided_ball)
                if ball.hit_rail and ball not in self.rail_contacts and \
                   ball != self.cue_ball:
                    self.rail_contacts.append(ball)

    def update(self, time):
        """ A method that will update the physics of a table over a given period
            of time, managing the movement and collisions of different balls and
            also checking whether the table is in motion or not.
              Inputs: time (a float or integer that describes the amount of time
            in seconds over which to update the physics of the table).
              Outputs: None."""
        self.previously_in_motion = self.in_motion
        self.in_motion = False
        for ball in self.balls:
            if ball.vel.x != 0 or ball.vel.y != 0 or \
               ball.applied_force is not None: # only update balls in motion
                ball.update_physics(time)
                self.in_motion = True
            elif ball.attempted_force_application:  # catch case that considers
                # the table in motion if a force was applied to the ball but it
                # was not greater than the static friction, as otherwise the shot
                # made by the cue would not be detected and checked.
                ball.attempted_force_application = False
                self.in_motion = True
        self.resolve_collisions()
        for ball in self.balls:
            ball.update_position()
        self.resolve_pockets()


class Ball:
    """ The Ball class holds all the information and methods of the balls that
        occupy the table and move around and collide with each other. They
        represent any standard billiard balls, but are modelled in many ways
        (except friction) as perfect spheres."""

    def __init__(self, coords, settings, striped=False, number=None):
        """ Constructs the ball object based upon input parameters.
              Inputs: coords (a tuple, list or Vector2D object that describes
            the centre coordinates of the ball), settings (a dictionary with
            many predetermined values used to construct the ball such as physical
            constants, ball size and ball mass), striped (an optional Boolean
            detailing whether the ball should have be considered a striped ball
            or not) and number (an optional Integer value that is None by
            default; the ball's number).
              Outputs: None."""
        self.pos = Vector2D(coords)
        self.settings = settings
        self.striped = striped
        self.number = number
        self.new_pos = self.pos.copy()
        self.old_pos = self.pos.copy()
        self.radius = self.settings["ball_radius"]
        # also sets _radius_vector and representation through the setter.
        self.mass = self.settings["ball_mass"]
        self.normal_contact = -self.mass * self.settings["gravity"]
        self.vel = Vector2D(0, 0)
        self.applied_force = None
        area = 2 * math.pi * (self.radius**2)
        self.air_res_coeff = (-self.settings["air_density"] * self.settings["ball_coeff_of_drag"] * area) / 2
        self.colliding = False
        self.hit_rail = False
        self.can_collide = True
        self.attempted_force_application = False

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, radius):
        """ A setter for the radius which updates the radius and _radius_vector
            attributes, which is used when drawing the ball.
              Inputs: radius, an integer/float that describes the ball's radius.
              Outputs: None."""
        self.__radius = radius
        self._radius_vector = Vector2D(radius, radius) # created here for a more
        # efficient repeated use in self.draw() method (avoiding repetition).
        self.representation = Circle(self.pos, radius)

    @property
    def centre(self):
        return self.representation.centre

    @centre.setter
    def centre(self, new_centre):
        self.representation.centre = new_centre

    def apply_force(self, time_of_application, force, angle):
        """ A method used to apply a force to a ball for a time so that its
            physics will change.
              Inputs: time_of_application (a float or integer describing the
            time in seconds for which the given force is applied), force (an
            integer or float describing the average amount of Newtons of force
            that are applied to the ball over this time) and angle (an integer
            or float describing the angle in radians on a 2D cartesian axis at
            which the force is applied).
              Outputs: None. """
        self.attempted_force_application = True
        if self.vel.magnitude_squared == 0 and force <= self.settings["coeff_of_static_friction"] * self.normal_contact * -1:
            return # only apply force if great enough to overcome static friction
            # and move the ball.
        self.applied_force = (Vector2D(math.cos(angle) * force,
                                       math.sin(angle) * force),
                              time_of_application)

    def update_physics(self, time):
        """ A method used to update the physics (motion/kinematics, not
            collisions) of the ball based upon the attributes it contains over
            a given amount of time.
              Inputs: time (a float or integer used to represent the time in
            seconds that the update should be calculated for).
              Outputs: None. """
        self.colliding = False
        self.hit_rail = False
        if self.applied_force is not None:
            time_remaining = self.applied_force[1]
            if time_remaining < time:
                # splits the update into smaller times if the applied force is
                # applied for less time than the time of the update
                self.update_physics(time_remaining)
                self.applied_force = None
                time -= time_remaining
            else:  # subtracts time of update from remaining of force application
                self.applied_force = (self.applied_force[0],
                                      self.applied_force[1] - time)
        friction = self.settings["coeff_of_rolling_friction"] * self.normal_contact * self.vel.normalise_result()
        air_res = self.air_res_coeff * self.vel * self.vel.magnitude
        if self.applied_force is not None:
            resultant = self.applied_force[0] + friction + air_res
            if self.applied_force[1] <= 0:
                self.applied_force = None
        else:
            resultant = friction + air_res
        acceleration = resultant / self.mass
        previous_vel = self.vel.copy()
        self.vel += acceleration * time
        self.new_pos += self.vel * time
        zero_vector = Vector2D(0, 0)
        # A check whether the ball is in motion in a direction opposite to before
        # the update, which stops friction from changing your direction if its
        # value is too large.
        if self.vel != zero_vector and previous_vel != zero_vector and previous_vel.dot_product(self.vel) < 0:
            self.vel = zero_vector
        if abs(self.vel.x) < self.settings["limiting_vel"]:
            self.vel.x = 0
        if abs(self.vel.y) < self.settings["limiting_vel"]:
            self.vel.y = 0
        self.centre.set(self.new_pos)

    def check_collision(self, collision_object):
        """ A general method that takes an input object and checks whether the
            ball is colliding with it.
             Input: collision_object (a Ball, Circle or LineSegment to check
            collision with).
             Output: A Boolean value detailing whether the ball and other
            collision object are colliding or not."""
        if isinstance(collision_object, Ball):
            collision_object = collision_object.representation
        return self.representation.check_collision(collision_object)

    def update_position(self):
        """ A method used to update the position attributes of the ball after
            their collisions have been resolved so that they can be properly
            drawn to the screen and are ready for the next update.
              Inputs: None.
              Outputs: None."""
        self.old_pos = self.pos
        self.pos = self.new_pos.copy()
        self.centre = self.pos

    def collide_with_line(self, line):
        """ A method that collides the ball with a given line, resolving the
            collision and calculating the new position and velocity of the ball.
              Inputs: line (a LineSegment that the ball is colliding with).
              Outputs: None."""
        line_vector = line.vector.normalise_result()
        perpendicular_line = line_vector.perpendicular()
        dot_product = perpendicular_line.dot_product(self.vel)
        # resolving any overlap as a result of collisions being calculated over
        # set time updates of the physics engine
        upper_point = self.new_pos + (perpendicular_line * self.representation.radius)
        distance_vector = upper_point - line.coord1
        upper_position = line.coord1 + line_vector * distance_vector.dot_product(line_vector)
        overlap = upper_position - upper_point
        if overlap.dot_product(self.vel) >= 0:
            # determines which overlap to use (from above or below line) based
            # on the direction of ball's velocity
            lower_point = self.new_pos - (perpendicular_line * self.representation.radius)
            distance_vector = lower_point - line.coord1
            lower_position = line.coord1 + line_vector * distance_vector.dot_product(line_vector)
            overlap = lower_position - lower_point
        self.new_pos += 2 * overlap
        self.centre.set(self.new_pos)
        # to collide, reverse the component of the velocity in the direction of
        # the line and applying the coefficient of restitution.
        change_in_velocity = perpendicular_line * (dot_product * (1 + self.settings["table_coeff_of_rest"]))
        self.vel -= change_in_velocity

    def collide_with_ball(self, ball):
        """ A method that collides the ball with another given ball, resolving
            the collision between the two, calculating and setting both balls'
            new positions and velocities.
              Inputs: ball (a Ball object that the ball is colliding with).
              Outputs: None."""
        old_ball_vel = ball.vel.copy()
        old_self_vel = self.vel.copy()
        normal_vector = self.new_pos - ball.new_pos
        old_movement = self.old_pos - ball.old_pos
        angle_between = normal_vector.dot_product(old_movement)
        factor = 1 if angle_between > 0 else -1
        # account for whether balls have passed through each other and are
        # moving away from each other - cos(theta) will be negative if the angle
        # is between pi/2 and 3pi/2 radians and hence if cos theta is negative
        # athey are moving away from each other (they passed through each other).
        overlap = (self.radius + ball.radius) - factor * normal_vector.magnitude
        self_vel_mag = self.vel.magnitude
        ball_vel_mag = ball.vel.magnitude
        total_vel_mag = self_vel_mag + ball_vel_mag
        if total_vel_mag != 0:
            # resolves the overlap of balls that are colliding, proportionally
            # such that the distance travelled backwards is equal to the ratio
            # of the ball's velocity to total velocity in collision
            self.new_pos -= self.vel.normalise_result() * overlap * (self_vel_mag / total_vel_mag) * 2
            ball.new_pos -= ball.vel.normalise_result() * overlap * (ball_vel_mag / total_vel_mag) * 2
        else:  #  should never occur, but exception handling is applied just in case to avoid division by 0.
            self.new_pos -= (self.new_pos - self.old_pos).normalise_result() * overlap * 0.5
            ball.new_pos -= (ball.new_pos - ball.old_pos).normalise_result() * overlap * 0.5
        self.centre.set(self.new_pos)
        ball.centre.set(ball.new_pos)
        
        normal_vector.normalise()  # obtain direction of the vector of collision
        self_normal_vel = self.vel.dot_product(normal_vector)
        ball_normal_vel = ball.vel.dot_product(normal_vector)
        perpendicular = normal_vector.perpendicular()
        self_perpendicular_vel = self.vel.dot_product(perpendicular)*perpendicular
        ball_perpendicular_vel = ball.vel.dot_product(perpendicular)*perpendicular
        coeff = self.settings["ball_coeff_of_rest"]
        # applies relevant equations to determine final velocities
        self.vel = 0.5 * ((1 - coeff) * self_normal_vel + (1 + coeff) * ball_normal_vel) * normal_vector
        ball.vel = (self_normal_vel + ball_normal_vel) * normal_vector - self.vel + ball_perpendicular_vel
        self.vel += self_perpendicular_vel
        # catch for resolving extreme cases where the balls are still overlapping.
        zero_vector = Vector2D(0, 0)
        while circle_circle_collision_check(self.representation,
                                            ball.representation):
            if self.vel == zero_vector or ball.vel == zero_vector:
                self.new_pos += old_self_vel * 0.0001
                self.update_position()
                ball.new_pos += old_ball_vel * 0.0001
                ball.update_position()
            else:
                self.update_physics(0.0001)
                self.centre.set(self.new_pos)
                ball.update_physics(0.0001)
                ball.centre.set(ball.new_pos)

    def collide(self, collision_object):
        """ A general method to collide the ball with another given object. This
            does not check for the collisions.
              Inputs: collision_object (a Ball or LineSegment object, the object
            to be collided with).
              Outputs: None."""
        if isinstance(collision_object, Ball):
            self.collide_with_ball(collision_object)
        elif isinstance(collision_object, LineSegment):
            self.collide_with_line(collision_object)

    def resolve_bounding_box_collision(self, lower_pos, upper_pos):
        """ A method to check whether a ball is otuside a bounding box
            constructing from two given coordinates, and, if it is, to resolve a
            theoretical collision between the ball and the edges of the
            bounding box so that the ball is in the correct place. A function
            that should only be required if the table edge line collision
            doesn't work because the ball is going too fast.
              Inputs: lower_pos (a Vector2D object) and upper_pos (a Vector2D
            object), representing two corners of the bounding box that the ball
            is checked with.
              Outputs: A Boolean value describing whether the ball was out of
            bounds and has been resolved."""
        outside_bounds = False
        if not (lower_pos.x < self.new_pos.x < upper_pos.x):
            overlap = self.new_pos.x - (lower_pos.x if lower_pos.x >= self.new_pos.x else upper_pos.x)
            new_position = (self.new_pos.x - overlap * 2, self.new_pos.y)
            line = LineSegment(Vector2D(0, 0), Vector2D(0, 1))
            self.collide(line)
            self.new_pos.set(new_position)
            self.centre.set(self.new_pos)
            outside_bounds = True
        if not (lower_pos.y < self.new_pos.y < upper_pos.y):
            overlap = self.new_pos.y - (lower_pos.y if lower_pos.y >= self.new_pos.y else upper_pos.y)
            new_position = (self.new_pos.x, self.new_pos.y - overlap * 2)
            line = LineSegment(Vector2D(0, 0), Vector2D(1, 0))
            self.collide(line)
            self.new_pos.set(new_position)
            self.centre.set(self.new_pos)
            outside_bounds = True
        return outside_bounds

    def get_collisions(self, balls, rails, lower_pos, upper_pos):
        """ A method that handles all of the collision physics of the ball with
            everything else on the table, ensuring that all collisions are
            resolved correctly and that the ball (and balls collided with) have
            the correct positions and velocities.
              Inputs: balls (an list/tuple of Ball objects that contains all the
            balls to be collided with), rails (a list/tuple of LineSegment
            objects that represent the rails/edges of the table to be collided
            with), lower_pos (a 2DVector object representing the top left of the
            bounding box holding the ball (the table), upper_pos (a 2DVector
            object representing the bottom right of the bounding box holding the
            ball (the table)).
              Outputs: Returns a list of balls that have been hit (collided with)
              by the ball in this collision check."""
        hit = []
        for ball in balls:
            if ball != self and ball.can_collide and self.check_collision(ball):
                hit.append(ball)
                self.collide(ball)
                self.colliding, ball.colliding = True, True
        for rail in rails:
            if self.check_collision(rail):
                self.hit_rail = True
                self.collide(rail)
        if not self.hit_rail:
            self.hit_rail = self.resolve_bounding_box_collision(lower_pos,
                                                                upper_pos)        
        return hit
