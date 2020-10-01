""" data module
Functions:
  None.
Classes:
 - Stack
 - Queue
 - BlockedQueue
 - Characters
 - Validator
Description:
  A module that stores classes related to data storage, organisation, management
and data validation. This generally handles additional data structures not
supported by python used in the system, such as stacks and queues which enable
the system to use LIFO and FIFO data structures. It also contains BlockedQueue,
a special Queue data type utilising semaphores to restrict access to common
resources for networked communication, and contains a validator class for data
validation."""

# external imports
from threading import Semaphore
import re


class Stack:
    """ A variable-length LIFO data structure where each item is added to the
        top of the stack."""

    def __init__(self, *args):
        """ The constructor for a stack.
              Inputs: Takes any number of any items to put in the stack.
              Outputs: None."""
        self.items = [*args]

    @property
    def is_empty(self):
        """ A property that returns a Boolean value detailing whether the stack
            is empty (it has no items)."""
        return len(self.items) == 0

    def __len__(self):
        """ A method that returns the length of the stack (an integer)."""
        return self.items.__len__()

    def push(self, item):
        """ This method pushes a new item to the top of the stack, so that it
            will be the last item in.
              Inputs: item (any object that is to be pushed to the stack).
              Outputs: None."""
        self.items.append(item)

    def pop(self):
        """ This method pops an item from the stack, removing it from the stack
            and returning it.
              Inputs: None.
              Outputs: The item that was currently occupying the last (top)
            space in the stack."""
        if len(self.items) == 0:
            return None
        else:
            last_item = self.items[-1]
            self.items = self.items[:-1]
            return last_item

    def remove(self):
        """ This method removes an item from the top of the stack, removing it
            from the stack and not returning it.
              Inputs: None.
              Outputs: None."""
        if len(self.items) != 0:
            self.items = self.items[:-1]

    def peek(self):
        """ This method peeks at the top item of the stack, returning it but not
            removing it from the stack.
              Inputs: None.
              Outputs: The item that was currently occupying the last (top)
            space in the stack."""
        if len(self.items) > 0:
            return self.items[-1]
        else:
            return None

    def clear(self):
        """ This method completely clears the stack, removing all items from it.
              Inputs: None.
              Outputs: None."""
        self.items = []


class Queue:
    """ A variable-length FIFO data structure where each item is added to the
        back of the queue."""
    
    def __init__(self, *args):
        """ The constructor for the Queue class.
              Inputs: Takes any number of any objects to put in the queue.
              Outputs: None."""
        self.items = [*args]
        
    def __len__(self):
        """ A method that returns the length of the queue (an integer)."""
        return self.items.__len__()

    def enqueue(self, item):
        """ This method is used to add an item to the end / back of a queue.
              Inputs: Any item / object to be added to the end of the queue.
              Outputs: None."""
        self.items.append(item)

    def dequeue(self):
        """ This method is used to remove and return an item from the front of
            the queue.
              Inputs: None.
              Outputs: The item that was occupying the front place in the queue.
        """
        if len(self.items) == 0:
            return None
        else:
            return self.items.pop(0)

    @property
    def is_empty(self):
        """ A property that returns a Boolean value detailing whether the queue
            is empty (it has no items)."""
        return len(self.items) == 0

    def clear(self):
        """ This method completely clears the queue, removing all items from it.
              Inputs: None.
              Outputs: None."""
        self.items = []

    def remove(self):
        """ This method removes the first item in the queue and does not return
            it to the user.
              Inputs: None.
              Outputs: None."""
        self.items = self.items[1:]

    def peek(self):
        """ This method peeks at the first item in the queue without actually
            removing it from the queue.
              Inputs: None.
              Outputs: The item that was occupying the front place in the queue.
        """
        if len(self.items) == 0:
            return None
        return self.items[-1]


class BlockedQueue(Queue):
    """ A variable-length FIFO data structure where each item is added to the
        back of the queue. Combined with asynchronous threading sempahores such
        that when an item is requested from the queue, the current thread will
        wait, until another item has been added to the queue (useful for
        avoiding constant while loops using the CPU)."""

    def __init__(self, *args):
        """ The constructor for a blocked queue. Identical to a normal queue
            except for a length semaphore attribute.
              Inputs: Takes any number of any individual items to put in the
            blocked queue.
              Outputs: None."""
        Queue.__init__(self, *args)
        self.length = Semaphore(0)

    def enqueue(self, item):
        """ This method is used to add an item to the end / back of the blocked
            queue, also releasing (incrementing) the length semaphore so that
            any waiting dequeue() process can continue.
              Inputs: Any item / object to be added to the back of the queue.
              Outputs: None."""
        Queue.enqueue(self, item)
        self.length.release()

    def dequeue(self):
        """ This method is used to remove and return an item from the front of
            the queue, also acquiring (decrementing) the length semaphore so
            that it will wait until there is an enqueued item to remove if not.
              Inputs: None.
              Outputs: The item that was occupying the front place in the queue.
        """
        self.length.acquire()
        if len(self.items) > 0:
            return self.items.pop(0)

    def remove(self):
        """ This method removes the first item in the queue and does not return
            it to the user.
              Inputs: None.
              Outputs: None."""
        self.length.aquire()
        super().remove()


class Characters:
    """ A basic class that stores different sets of characters used by
        validators (so that they do not have to be stored in all validators for
        memory efficiency."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    lower_case = [letter for letter in letters]
    upper_case = [letter for letter in letters.upper()]
    numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    quotation = ['"', "'"]
    parantheses = ["(", ")", "{", "}", "[", "]"]
    currency = ["£", "$", "€", "¤", "¢", "¥", "₧", "ƒ"]
    symbols = [symbol for symbol in "!%^&*-_=+#~@;:/?.>,<\|`¬"]


class Validator:
    """ The validator class takes inputs and validates whether the inputs meet
        certain conditions set as attributes in the class. This is a class that
        enforces input validation for protective programming."""

    def __init__(self, spaces=True, upper_case=True, lower_case=True,
                 parantheses=True, numbers=True, symbols=True, quotation=True,
                 currency=True, custom_chars=None, banned_phrases=None,
                 regex=None, min_length=None, max_length=None):
        """ The constructor for a validator class, where certain allowed and
            disallowed inputs are specified for use in user input validation.
              Inputs: spaces (an optional Boolean detailing whether spaces are
            allowed in the input), upper_case (an optional Boolean detailing
            whether upper case characters are allowed in the input), lower_case
            (an optional Boolean detailing whether lower case characters are
            allowed in the input), parantheses (an optional Boolean detailing
            whether parantheses are allowed in the input), numbers (an optional
            Boolean detailing whether numeric characters are allowed in the
            input), symbols (an optional Boolean detailing whther generic
            symbols, excluding quotation and parantheses and currency, are
            allowed in the input), quotation (an optional Boolean detailing
            whether quotation characters are allowed in the input), currency (an
            optional Boolean detailing whether currency characters e.g. £ or $
            are allowed in the input), custom_chars (either None, a string
            featuring all the banned characters and no others or a list of
            banned characters (strings of length 1). Optionally included.),
            banned_phrases (optionally either None or a list of strings
            containing phrases that cannot be included in the input, although
            this only checks if they are an independent word), regex (optionally
            either None or string, a regular expression that inputs must meet in
            order to be valid), and min_length (None or an integer >= 0) and
            max_length (None or an integer >= 0) detailing the maximum and
            minimum allowed length of the input.
              Outputs: None."""
        self.min_length = min_length
        self.max_length = max_length
        self.spaces_allowed = spaces
        self.upper_case_allowed = upper_case
        self.lower_case_allowed = lower_case
        self.parantheses_allowed = parantheses
        self.numbers_allowed = numbers
        self.symbols_allowed = symbols
        self.quotation_allowed = quotation
        self.currency_allowed = currency
        self.custom_chars = custom_chars
        self.banned_phrases = banned_phrases
        self.regex = regex

    def copy(self):
        """ This method returns a copy of the validator with all of the exact
            same settings, e.g. for when you want the same settings with slight
            modification.
              Inputs: None.
              Outputs: a Validator object that is identical to self."""
        return Validator(spaces=self.spaces_allowed, upper_case=self.upper_case_allowed, lower_case=self.lower_case_allowed, parantheses=self.parantheses_allowed, numbers=self.numbers_allowed, symbols=self.symbols_allowed, quotation=self.quotation_allowed, currency=self.currency_allowed, custom_chars=self.custom_chars, banned_phrases=self.banned_phrases, regex=self.regex, min_length=self.min_length, max_length=self.max_length)
    
    def validate(self, input_string):
        """ This method validates a given input according to the settings
            (attributes) of the validator, describing the problem if there is
            something invalid with the input.
              Inputs: input_string (a string (generally user-input) containing
            text that is to be validated.
              Outputs: a tuple - the item at index zero is a Boolean that
            details whether the input was valid or not. In the case that the
            input was not valid, a second item is included in the tuple which is
            a string containing a short error message that describes why the
            input_string did not meet the Validator's requirements."""
        if self.min_length is not None:
            if len(input_string) < self.min_length:
                return (False, "Input is too short. It must be at least {} characters long.".format(self.min_length))
        if self.max_length is not None:
            if len(input_string) > self.max_length:
                return (False, "Input is too long. It must be at most {} characters long.".format(self.max_length))
        characters_list = [[self.spaces_allowed, [" "]],
                           [self.upper_case_allowed, Characters.upper_case],
                           [self.lower_case_allowed, Characters.lower_case],
                           [self.parantheses_allowed, Characters.parantheses],
                           [self.numbers_allowed, Characters.numbers],
                           [self.symbols_allowed, Characters.symbols],
                           [self.quotation_allowed, Characters.quotation],
                           [self.currency_allowed, Characters.currency]]
        if self.custom_chars is not None:
            characters_list.append([True, list(self.custom_chars.keys())])
        allowed_chars = []
        for check_type in characters_list:
            if check_type[0]:
                allowed_chars += check_type[1]
        for char in input_string:
            if char not in allowed_chars:
                return (False, "Input contains non-allowed characters.")
        if self.banned_phrases is not None:
            for phrase in self.banned_phrases:
                if phrase.lower() in input_string.lower().split(" "):  # only checks for whole words
                    return (False, "Input contains a banned phrase.")
        if self.custom_chars is not None:
            # checks amount of each limited character for limit being exceeded
            for allowed_char in self.custom_chars:
                if self.custom_chars[allowed_char] is None:
                    # i.e. None == no limit, so just don't check.
                    continue
                current_num = 0
                allowed_amount = self.custom_chars[allowed_char]
                for char in input_string:
                    if char == allowed_char:
                        current_num += 1
                        if current_num > allowed_amount:
                            return (False, "Input can only use {} {} {}.".format(allowed_char, allowed_amount, "time" if allowed_amount == 1 else "times"))
        if self.regex is not None:
            if not self.regex.fullmatch(input_string):
                return (False, "Input is not in a correct, valid format.")
        return (True,)
