""" vectors module
Functions:
 - is_numeric (wrapper)
 - is_vector (wrapper)
Classes:
 - Vector2D
Description:
  A module containing a 2D Vectors object that is used for the majority of
maths and positioning throughout the system."""

#external imports
import math


def is_numeric(func):
    """ A wrapper that checks whether a single value input into a function is
        numeric, and raises a TypeError if not.
          Inputs: any singular object
          Outputs: the result of calling the function with the amount if it is
        numeric, otherwise raises a TypeError and returns nothing."""
    def wrapper(self, amount):
        if isinstance(amount, (int, float)):
            return func(self, amount)
        else:
            raise TypeError("Value must be numeric.")
    return wrapper


def is_vector(func):
    """ A wrapper that checks whether a single value input into a function is a
        vector, and raises a TypeError if not.
          Inputs: any singular object
          Outputs: the result of calling the function with the amount if it is
        numeric, otherwise raises a TypeError and returns nothing."""
    def wrapper(self, obj):
        if isinstance(obj, Vector2D):
            return func(self, obj)
        else:
            raise TypeError("Input must be a vector quantity.")
    return wrapper


class Vector2D:
    """ A data object that represents a 2-dimensional vector, i.e. two floats
        which represent x- and y-components"""

    def __init__(self, *args):
        """ Constructor for the a 2 dimensional vector.
              Inputs: a variable number of arguments. Either a singular tuple,
            list or Vector2D object, or two integers / decimals that represent
            the x- and y- components of the vector. Any incorrect input formats
            will result in a ValueError being raised.
              Outputs: None."""
        # Checks whether a valid tuple/list format
        if isinstance(args[0], (tuple, list)) and len(args[0]) >= 2:
            self.x = args[0][0]
            self.y = args[0][1]
        elif isinstance(args[0], Vector2D):
            self.x = args[0].x
            self.y = args[0].y
        else:
            # Checks whether input is two integers or floats
            if not (len(args) >= 2 and \
                    isinstance(args[0], (int, float)) and \
                    isinstance(args[1], (int, float))):
                raise ValueError("Unable to create 2D Vector object based upon the input data.")
            self.x = args[0]
            self.y = args[1]

    @property
    def x(self):
        return self.__x

    @x.setter
    @is_numeric
    def x(self, x):
        self.__x = x

    @x.getter
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    @y.setter
    @is_numeric
    def y(self, y):
        self.__y = y

    @y.getter
    def y(self):
        return self.__y

    def set(self, vector):
        """ A method that attempts to set both values of the vector to other
            input values.
              Inputs: the new values of the vector, as a tuple, list or
            Vector2D object.
              Outputs: None, raises a ValueError if an input tuple or list is
            not of length 2 or a TypeError if the input vector is not of a
            valid type."""
        if isinstance(vector, (tuple, list)):
            if len(vector) != 2:  # check whether the input tuple/list contains 2 elements (the x- and y- components)
                raise ValueError("Must be a tuple/list containing 2 items.")
            else:
                self.x = vector[0]
                self.y = vector[1]
        elif isinstance(vector, Vector2D):
            self.x = vector.x
            self.y = vector.y
        else:
            raise TypeError("Must input a valid vector to be set.")
    
    def __str__(self):
        """ Creates the string representation of the Vector.
              Inputs: None
              Outputs: a string vector representation in the format '(x, y)'."""
        return "(" + str(self.x) + ", " + str(self.y) + ")"

    @is_vector
    def __iadd__(self, vector):
        """ Iteratively adds another vector to the vector.
              Inputs: any singular vector
              Outputs: itself (a Vector2D object, because it is using iterative
            addition)."""
        self.x += vector.x
        self.y += vector.y
        return self

    @is_vector
    def __add__(self, vector):
        """ A method to calculate the result of adding the vector and another
            input vector.
              Inputs: any singular vector
              Outputs: the result of the vector addition (a Vector2D object)."""
        return Vector2D(self.x + vector.x, self.y + vector.y)

    @is_vector
    def __radd__(self, vector):
        """ A method for reverse adding two vectors together provided that the
            reverse does not work.
              Inputs: any singular vector
              Outputs: the result of the vector addition (a Vector2D object)."""
        return self.__add__(vector)

    @is_vector
    def __isub__(self, vector):
        """ Iteratively subtracts a vector from the vector.
              Inputs: any singular vector
              Outputs: itself (a Vector2D object, because it is using iterative
            subtraction)."""
        self.x -= vector.x
        self.y -= vector.y
        return self

    @is_vector
    def __sub__(self, vector):
        """ A method to calculate the result of subtracting an input vector
            from the vector itself.
              Inputs: any singular vector
              Outputs: the result of the vector subtraction (a Vector2D object).
        """
        return Vector2D(self.x - vector.x, self.y - vector.y)

    @is_numeric
    def __imul__(self, amount):
        """ Iteratively multiplies the vector by an input scalar number.
              Inputs: an integer or float to multiply the vector by.
              Outputs: itself (a Vector2D object, because it is using iterative
            multiplication)."""
        self.x *= amount
        self.y *= amount
        return self
    
    @is_numeric
    def __mul__(self, amount):
        """ A method to calculate the result of multiplying the vector by an
            input scalar number.
              Inputs: an integer or float to multiply the vector by.
              Outputs: the result of the vector and scalar multiplication (a
            Vector2D object)."""
        return Vector2D(self.x * amount, self.y * amount)

    @is_numeric
    def __rmul__(self, amount):
        """ A method to calculate the result of reverse multiplying the vector
            by an input scalar number
              Inputs: an integer or float to multiply the vector by.
              Outputs: the result of the vector and scalar multiplication (a
            Vector2D object)."""
        return self.__mul__(amount)

    @is_numeric
    def __itruediv__(self, amount):
        """ Iteratively divides (floating point division, includes decimal) the
            vector by an input scalar number
              Inputs: an integer or float to divide the vector by.
              Outputs: itself (a Vector2D object, because it is using iterative
            division)."""
        if amount == 0:
            raise ZeroDivisionError("Cannot divide a vector by zero.")
        else:
            self.x /= amount
            self.y /= amount
            return self

    @is_numeric
    def __truediv__(self, amount):
        """ A method to calculate the result of dividing the vector by an input
            scalar number
              Inputs: an integer or float to divide the vector by.
              Outputs: the result of the vector and scalar division (a Vector2D
            object)."""
        if amount == 0:
            raise ZeroDivisionError("Cannot divide a vector by zero.")
        else:
            return Vector2D((self.x / amount) if amount != 0 else self.x, \
                            (self.y / amount) if amount != 0 else self.y)

    def __neg__(self):
        """ A method to return the negative value of the vector. Returns the
            Vector2D object representing itself but negative.
              Inputs: None
              Outputs: the negative version of itself (a Vector2D object)."""
        return self * -1

    @is_vector
    def __lt__(self, vector):
        """ Compares to see if the vector itself is smaller than an input vector
            in magnitude.
              Inputs: any Vector2D object to be compared with.
              Outputs: a Boolean value - True if the vector is less than the
            input vector, False if it is equal to or larger."""
        return self.magnitude_squared < vector.magnitude_sqared

    @is_vector
    def __le__(self, vector):
        """ Compares to see if the vector itself is smaller than or equal to an
            input vector in magnitude.
              Inputs: any Vector2D object to be compared with.
              Outputs: a Boolean value - True if the vector is less than or
            equal to the input vector, False if it is larger."""
        return self.magnitude_squared <= vector.magnitude_sqared

    @is_vector
    def __eq__(self, vector):
        """ Compares exactly to see if the components of the vector and another
            input vector are equal.
              Inputs: any Vector2D object to be compared with.
              Outputs: a Boolean value - True if the vectors are equivalent,
            False if they are not."""
        # compares exactly - not just magnitude unlike other comparisons
        return self.x == vector.x and self.y == vector.y

    @is_vector
    def __ne__(self, vector):
        """ Compares exactly to see if either of the components of the vector
            and another input vector are not equal.
              Inputs: any Vector2D object to be compared with
              Outputs: a Boolean value - True if the vector is not equal to the
            input vector, False if they are equal."""
        # compares exactly - not just magnitude unlike other comparisons
        return self.x != vector.x or self.y != vector.y

    @is_vector
    def __ge__(self, vector):
        """ Compares to see if the vector itself is greater than or equal to an
            input vector in magnitude.
              Inputs: any Vector2D object to be compared with.
              Outputs: a Boolean value - True if the vector is greater than or
            equal to the input vector, False if it is less."""
        return self.magnitude_squared >= vector.magnitude_sqared

    @is_vector
    def __gt__(self, vector):
        """ Compares to see if the vector itself is greater than an input vector
            in magnitude.
              Inputs: any Vector2D object to be compared with.
              Outputs: a Boolean value - True if the vector is greater than the
            input vector, False if it is equal to or less."""
        return self.magnitude_squared > vector.magnitude_sqared

    @property
    def magnitude(self):
        """ A property equal to the magnitude of the vector.
              Inputs: None.
              Outputs: Returns a float detailing the vector's magnitude."""
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def magnitude_squared(self):
        """ A property equal to the magnitude of the vector raised to the power
            of two - used more frequently than magnitude itself for simple
            magnitude comparisons because square rooting is CPU expensive and so
            should be avoided if possible.
              Inputs: None.
              Outputs: Returns a float detailing the magnitude squared."""
        # Function made to save square rooting as that can be quite expensive.
        return self.x**2 + self.y**2

    def normalise(self):
        """ This method normalises the vector, so that it retains its direction
            whilst gaining a magnitude of one. It does this by dividing the
            vector by its magnitude.
              Inputs: None.
              Outputs: None."""
        magnitude = self.magnitude
        if magnitude != 0:
            self.x = self.x / magnitude
            self.y = self.y / magnitude

    def normalise_result(self):
        """ This method returns the result of normalising a vector without
            actually changing the original vector, so that this result can be
            used in further calculation.
              Inputs: None.
              Outputs: A normalised copy of the vector (a Vector2D object with
            a magnitude of 1, unless the Vector is (0, 0))."""
        magnitude = self.magnitude
        if magnitude != 0:
            return Vector2D((self.x/magnitude) if magnitude != 0 else self.x, \
                            (self.y/magnitude) if magnitude != 0 else self.y)
        else:
            return Vector2D(0, 0)

    @is_vector
    def dot_product(self, vector):
        """ A method that returns the dot product of the vector and another
            given vector. Is equal to a.x * b.x + a.y * b.y == |a||b|cos(theta),
            where theta is the angle between vectors a and b in radians.
              Inputs: any Vector2D object.
              Outputs: the dot product of this vector and the input vector (an
            integer or float)."""
        return self.x * vector.x + self.y * vector.y

    def round(self, number=0):
        """ A method that rounds each component of the vector to a given number
            of decimal places.
              Inputs: number (an optional integer >= 0 detailing the number of
            decimal places to round to, defaults to zero).
              Outputs: None."""
        self.x = round(self.x, number)
        self.y = round(self.y, number)
        if number == 0:
            self.x = int(self.x)
            self.y = int(self.y)

    def round_result(self, number=0):
        """ This method returns the result of rounding the Vector2D's components
            to a given number of decmial places.
              Inputs: number (an optional integer >= 0 detailing the number of
            decimal places to round to, defaults to zero).
              Outputs: A rounded copy of this vector (a Vector2D object)."""
        new_vector = self.copy()
        new_vector.round(number=number)
        return new_vector

    def perpendicular(self):
        """ This method returns a Vector2D object that contains a vector
            perpendicular to this vector and equal in magnitude.
              Inputs: None.
              Outputs: The perpendicular Vector2D object."""
        return Vector2D(-self.y, self.x)

    def copy(self):
        """ This method returns a Vector2D object that is an exact copy of the
            vector.
              Inputs: None.
              Outputs: A Vector2D object identical to this vector."""
        return Vector2D(self.x, self.y)

    def __getitem__(self, key):
        """ A method used to enable tuple() and list() casting of the Vector2D
            by representing it is a list in the format (x, y).
              Inputs: key (integer)
              Outputs: None."""
        return([self.x, self.y][key])

