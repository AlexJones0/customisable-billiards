""" client module
Functions:
 - None.
Classes:
 - Connection
 - OfflineGame
 - NetworkedGame
 - EditorGame
 - ReplayTable
 - ReplayGame
 - PoolSim
Description:
  The main program used by the user to run the client-side part of the program.
Features all of the simulation classes (offline simulations, online simulations,
the table edtior and simulation replays) used to simulate and interact with
different features of the system. It also holds the PoolSim class, which
controls the main loop of the client program and contains the GUI and
simulations. This manages pygame (and hence window updates, the program clock,
control updates etc.) is from which all other objects are either directly or
indirectly instantiated. Contains everything needed to produce playable and
interactive simulations for clients, and also manages needed networked
communication with the server for online games."""

# external modules
import pygame
import os
import time
import random
import math
import socket
import json
from threading import Thread


# initiate the pygame and pygame.font modules.
pygame.init()
pygame.font.init()


# custom-made modules
import config
import events
from vectors import Vector2D
from interface import Button, Label, Container, scale_position
from GUI import Menu_System
from drawables import DrawableBall, DrawableTable
from data import Queue, BlockedQueue
from connections import retrieve_server_location
from controls import ControlsObject


class Connection:
    """ This class creates and manages the network connection between the
        client and the server, utilising Queue data structures to send and 
        receive and process information."""
    
    def __init__(self, host, port):
        """ The constructor for a Connection object - creates a connection with
            the given server.
              Inputs: host (a string containing the ipv4 address of the
            computer that the server is hosted on), and port (a string or
            integer containing the port that the ipv4 that the Billiards server
            is being hosted upon at the given host address).
              Outputs: None."""
        self.commands = {}
        self.connection_socket = socket.socket(socket.AF_INET, 
                                               socket.SOCK_STREAM)
        original_timeout = self.connection_socket.gettimeout()
        self.connection_socket.settimeout(5)
        self.connection_socket.connect((host, int(port)))
        self.connection_socket.setsockopt(socket.IPPROTO_TCP, 
                                          socket.TCP_NODELAY, 1)
        self.connection_socket.settimeout(original_timeout)
        self.send_queue = BlockedQueue()
        self.receive_queue = BlockedQueue()
        self.in_use = False
        self.waiting = False
        self.error = None
        self.ignore_received = ["received", "update_server_cue_position", 
                                "update_cue_position"] 
        # a list of communication commands that the connection does not care
        # whether was received or not.

    def rebind(self, host, port):
        """ In the case that the connection is no longer in use (i.e. the user
            disconnected) but you want to reconnect it to the server or change
            to a different sever, this method rebinds the connection socket to
            a different/new host and port, resetting/changing the connection.
              Inputs: host (a string containing the ipv4 address of the 
            computer that the server is hosted on), and port (a string or
            integer containing the port that the ipv4 that the Billiards server
            is being hosted upon at the given host address).
              Outputs: None."""
        self.connection_socket = socket.socket(socket.AF_INET, 
                                               socket.SOCK_STREAM)
        self.connection_socket.connect((host, port))
        self.connection_socket.setsockopt(socket.IPPROTO_TCP, 
                                          socket.TCP_NODELAY, 1)
        self.send_queue.clear()
        self.receive_queue.clear()

    def __apply_error(self, error):
        """ This method is called when an exception has trigged (an error has
            occurred), and it disables the connection, stopping it from
            attempting to make further communication.
              Inputs: error (a string containing a message of the error that
            has occurred, which will be eventually displayed to the user by the
            main loop).
              Outputs: None."""
        self.in_use = False
        self.waiting = False
        self.send_queue.clear()
        self.receive_queue.clear()
        self.error = error

    def __receive_data(self):
        """ This method is responsible for receiving data from the network
            buffer that was sent by the server, and recording it in the
            received data queue (self.receive_queue) for use there.
              Inputs: None (a continuous while loop that receives data from
            network buffer).
              Outputs: None (any data received is added to self.receive_queue).
        """
        try:
            while self.in_use:
                data = self.connection_socket.recv(1024)
                if data is not None:
                    full_data = data.decode()
                    while not full_data.endswith("#"):  # catch in case message is longer than 1024 bytes.
                        data = self.connection_socket.recv(1024)
                        full_data += data.decode()
                    data = full_data.split("#")
                    # splits in case multiple messages received at once
                    for item in data[:-1]:
                        print(f'RECEIVED: {item}')
                        request = json.loads(item)
                        if request["command"] == "received":
                            self.waiting = False
                        else:
                            self.receive_queue.enqueue(request)
        except:
            self.__apply_error("Unable to connect with server - it may be offline or may not exist. Please try again later.")

    def __process_data(self):
        """ This method processes received data that is retrieved from the 
            receive queue (self.receive_queue). This is kept seperate from
            receiving the data as it means that even if a process gets stuck or
            takes a long time, the __receive_data method can keep receiving 
            data and adding it to the queue.
              Inputs: None.
              Outputs: None (calls other functions that may have many differing 
            effects)."""
        while self.in_use:
            request = self.receive_queue.dequeue()
            if request is not None:
                if request["command"] not in self.ignore_received:
                    self.send_queue.enqueue({"command": "received"})
                if "args" in request.keys():
                    self.commands[request["command"]](*request["args"])
                else:
                    self.commands[request["command"]]()

    def __send_data(self):
        """ This method sends data that is in the send queue (self.send_queue)
            to the server, allowing bidirectional communication with the server
            (you can send whilst also receiving).
              Inputs: None (retrieves information from self.send_queue).
              Outputs: None (sends messages over the network to the server)."""
        try:
            prev_data = None
            while self.in_use:
                data = self.send_queue.dequeue()
                if data is not None:
                    time_elapsed = 0
                    times_resent = 0
                    # wait for last sent piece of data to be confirmed received
                    while self.waiting:
                        time.sleep(0.05)
                        time_elapsed += 0.05
                        if time_elapsed > 3:
                            # resend data if not received in 3 seconds.
                            if times_resent == 3:
                                self.__apply_error("No longer receiving communication from server. The connection may have been lost. Please try again later.")
                                break
                            time_elapsed -= 5
                            times_resent += 1
                            # splits up data into packets of 1024 bytes.
                            for i in range(0, len(prev_data) - 1, 1024):
                                encoded_str = str.encode(prev_data[i:i+1024])
                                self.connection_socket.send(encoded_str)
                    if "args" in data.keys() and not isinstance(data["args"], (tuple, list)):
                        try:
                            data["args"] = tuple(data["args"])
                        except TypeError:
                            data["args"] = (data["args"],)
                    print(f'SENDING: {data}')
                    jsondata = json.dumps(data) + "#"  # add an EOF character
                    if data["command"] not in self.ignore_received:
                        prev_data = jsondata
                        self.waiting = True
                    # splits up data into packets of 1024 bytes.
                    for i in range(0, len(jsondata) - 1, 1024):
                        encoded_str = str.encode(jsondata[i:i+1024])
                        self.connection_socket.send(encoded_str)
        except (ConnectionRefusedError, ConnectionResetError) as e:
            self.__apply_error("Unable to send data to server - it may be offline. Please try again later.")

    def add_commands(self, commands):
        """ This method adds a set of commands to the Connection object that 
            can be called by incoming communication, allowing the server to 
            interface with the rest of the program.
              Inputs: commands (a dictionary of key-value pairs of commands
            where the key is the string that must be sent as the "command" key
            value in the message and the value is the subroutine that is to be
            called).
              Outputs: None."""
        for command in commands:
            self.commands[command] = commands[command]

    def start(self):
        """ This method actually starts the Connection, meaning that it can
            begin to receive, process and send data. This is done in 3 new
            seperate threads so all three can happen at once without blocking
            each other.
              Inputs: None.
              Outputs: None."""
        self.in_use = True
        Thread(target=self.__receive_data, daemon=True).start()
        Thread(target=self.__process_data, daemon=True).start()
        Thread(target=self.__send_data, daemon=True).start()
        #daemon=True so threads will terminate when main process ends.


class OfflineGame:
    """ The OfflineGame class holds all the rules, controls and information 
        about an offline simulation of 8-ball pool that can be played by two 
        players on the same program/computer."""
    
    def __init__(self, settings, screen, controls_obj):
        """ The constructor for the OfflineGame class, creating the basic 
            attributes for 8-ball pool.
              Inputs: settings (a dictionary containing predetermined setting
            attribute values), screen (a pygame.Surface object which the game 
            should be drawn to for user interaction), and controls_obj (a 
            ControlsObject object which contains the user's control state, 
            which is updated by the main loop).
              Outputs: None."""
        self.settings = settings
        self._screen = screen
        self._controls = controls_obj
        self._time = 1 / self.settings["fps"]  # time of game/physics updates
        self.in_game = False
        self._quitting = False
        font_size = 0.0442086 * self.settings["window_height"]
        screen_ratio = self.settings["screen_width"]/self.settings["screen_height"]
        if screen_ratio < 16/9:
            font_size *= 0.75  
            # change size if not standard screen ratio so text fits on screen
        self._message_font = pygame.font.SysFont(self.settings["message_font"],
                                                 int(font_size))
        padding_size = Vector2D(self.settings["window_width"] / 300, 
                                self.settings["window_height"] / 150)
        self._quit_button = Button(self._controls, "Quit", 
                                   font=self._message_font, target=self._quit,
                                   outline_padding=padding_size, 
                                   text_padding=padding_size)
        window_vector = Vector2D(self.settings["window_width"], 
                                 self.settings["window_height"])
        self._quit_button.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.98, 0.98), object_size=self._quit_button.size, scale_from=Vector2D(1,1))
        self._table_shift = Vector2D(0, 0)
        self._table = None
        self._event = None  # a variable that stores the current event.

    def _quit(self):
        """ This method stops and quits the offline game client.
              Inputs: None.
              Outputs: None."""
        events.event_queue.clear()
        self.in_game = False
        self._quitting = True

    def _scale_values(self):
        """ This method scales the values of pixels per metre for the client
            window and table settings, ensuring that the table will fit the
            screen and will not be larger than that.
              Inputs: None.
              Outputs: None (the "ppm" key-value pair in the settings 
            dictionary is changed)."""
        length_metres = self.settings["table_length"] + 2 * self.settings["ball_radius"]
        width_metres = self.settings["table_width"] + 2 * self.settings["ball_radius"]
        max_width = 0.8 * self.settings["window_width"]
        max_height = 0.8 * self.settings["window_height"]
        ppm = config.calculate_ppm(length_metres, width_metres, 
                                   self.settings["window_width"],
                                   self.settings["window_height"], 
                                   self.settings["table_area_fraction"])
        # Scales the ppm value so the whole table will fit the screen in case 
        # of irregular dimensions (e.g. length = 100 x the width)
        while ppm * length_metres > max_width or ppm * width_metres > max_height:
            if ppm > 1:
                ppm -= 1
            else:
                ppm /= 1.1
        self.settings["ppm"] = ppm

    def _construct_table(self):
        """ This method creates the table object and other objects associated
            with the table such as the cue. It also works out the 'table shift
            factor' which is the amount everything should be shifted by to be 
            drawn to the centre of the screen.
              Inputs: None.
              Outputs: None."""
        x_pos = (self.settings["window_width"] / self.settings["ppm"] - self.settings["table_length"]) / 2
        y_pos = (self.settings["window_height"] / self.settings["ppm"] - self.settings["table_width"]) / 2
        # instantiates the table based on given table information, composed within the CueGame object
        self._table_shift = Vector2D(x_pos, y_pos)
        self._table = DrawableTable(Vector2D(0, 0), self.settings)

    def _calculate_racking_position(self):
        """ This method calculates the position at which balls should start 
            being racked from in order for them all to fit nicely on the table,
            using the current saved simulation settings.
              Inputs: None.
              Outputs: rack_pos (a Vector2D representing the position the 
            racked balls should be placed from)."""
        racked_length = 9.4 * self.settings["ball_radius"]
        starting_width = self._table.width / 2
        starting_length = self._table.length / 4 * 3
        cutoff_length = self._table.length / 20 * 19
        # ensure that all racked balls fit on the selected table size
        if racked_length + starting_length > cutoff_length:
            starting_length = cutoff_length - racked_length
        return Vector2D(starting_length, starting_width)

    def _place_balls(self):
        """ This method adds all of the necessary ball objects to the table, 
            according to configuration settings, for 8-ball pool. Colours and
            position settings are created according to standard 8-ball rules,
            with a black 8-ball, a white cue-ball and 7 spotted and 7 striped
            coloured balls.
              Inputs: None.
              Outputs: None."""
        if self.settings["save_replay"]:
            game_ball_info = []
        self._spotted_balls = []
        self._striped_balls = []
        y_offset = 0  # x- and y- offset values used to create the racked triangular pattern of balls
        x_offset = 0
        balls_info = [(1, (240, 240, 0)), (2, (0, 0, 255)), (3, (255, 0, 0)), 
                      (4, (128, 0, 128)), (5, (255, 165, 0)), (6, (0, 255, 0)), 
                      (7, (128, 0, 0))]
        balls_info = balls_info + [(num[0] + 8, num[1]) for num in balls_info]
        racking_position = self._calculate_racking_position()
        for i in range(1, 6):
            for j in range(i):
                if i == 3 and j == 1:  # position of the 8-ball
                    ball_info = (8, (0, 0, 0))
                else:
                    ball_info = random.choice(balls_info)
                    balls_info.remove(ball_info)
                shift_vector = Vector2D(
                    x_offset, 
                    y_offset + self.settings["ball_radius"] * 2.2 * j
                )
                ball_pos = racking_position + shift_vector
                striped = True if ball_info[0] > 8 else False
                ball = DrawableBall(ball_pos, self.settings, ball_info[1],
                                    striped=striped, number=ball_info[0])
                if striped:
                    self._striped_balls.append(ball)
                elif ball_info[0] != 8:
                    self._spotted_balls.append(ball)
                self._table.add_ball(ball)
                if self.settings["save_replay"]:
                    game_ball_info.append(ball_info)
            y_offset -= self.settings["ball_radius"] * 1.1
            x_offset += self.settings["ball_radius"] * 2
        # the cue ball is then placed at a specific point on the table separate 
        # of the others.
        ball_pos = Vector2D(self._table.length / 3, self._table.width / 2)
        cue_ball = DrawableBall(ball_pos, self.settings, (255, 255, 255), 
                                can_focus=True)
        self._table.add_ball(cue_ball)
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({"type": "ball_info", 
                                     "data": game_ball_info})

    def _reset_state(self):
        """ This method is responsible for resetting the variables related to
            the state of the game, e.g. allowing the game to easily be reset.
              Inputs: None.
              Outputs: None."""
        self._break = True
        self._open = True
        self._p1_balls = []
        self._p2_balls = []
        self._p1_is_striped = False
        self._can_shoot = True
        self._can_pass_turn = False
        if self.settings["save_replay"]:  # used for replays
            self.saved_moves.append({"type": "reset_state"})

    def setup_game(self):
        """ This method actually sets up and starts the game so that it can be
            interacted with by users. It calls the creation of basic 
            information required for the game, and the creation of objects such
            as the tables and balls. It is an overarching setup function that 
            mostly calls other functions.
              Inputs: None.
              Outputs: None (fully sets up game for interacting with in 
            updates)."""
        self._scale_values()
        # creates size of side balls so that there is space for 9 balls to be 
        # displayed at the side of the screen:
        side_ball_length = (self.settings["ball_radius"] * (self.settings["side_ball_scale"] + 0.5) * self.settings["ppm"] * 6)
        self._side_ball_scale = int(self.settings["screen_height"] * self.settings["scale_height"] / side_ball_length)
        font_size = int(0.0442086 * self.settings["window_height"])
        self._text_font = pygame.font.SysFont(self.settings["message_font"],
                                              font_size)
        if self.settings["save_replay"]: # used for replays
            self.saved_moves = [time.localtime(), {"type": "match_settings", 
                                                   "data": self.settings}]
        # create the table & other objects & variables related to the game
        self._construct_table()
        self._place_balls()
        self._reset_state()
        self._player_turn = 1
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({"type": "starting_player", 
                                     "data": self._player_turn})
        self.in_game = True

    @property
    def _other_turn(self):
        """ A property that returns the turn of the player who it isn't, i.e. 
            an integer that is 1 or 2."""
        return 2 if self._player_turn == 1 else 1

    def _place_ball(self, pos):
        """ This method places the currently held ball at a given position on
            the table.
              Inputs: pos (a Vector2D object that represents the position to
            place the held ball on the table).
              Outputs: None."""
        if self.settings["save_replay"]: # used for replays
            pos = tuple(pos)
            self.saved_moves.append({
                "type": "place_ball", "data": pos,
                "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                "holding": self._table.holding.number if self._table.holding is not None else 0
            })
        pos = Vector2D(pos)
        self._table.holding.new_pos.set(pos)
        self._table.holding.representation.centre.set(pos)
        self._table.holding.can_collide = True
        self._table.holding.can_show = True
        self._table.holding = None

    def _check_focus(self, mouse_pos):
        """ This method checks whether the mouse is clicking on and attempting
            to focus on a ball.
              Inputs: mouse_pos (a Vector2D object representing the position of
            the mouse on the table (i.e. if the table is shifted, this should
            be the shifted position of the mouse on the table)).
              Outputs: None."""
        for ball in self._table.balls:
            if ball.can_focus and ball.representation.contains(mouse_pos) and \
              ball is not self._table.holding:
                self._table.cue.set_focus(ball)
                break

    def _attempt_ball_place(self, mouse_pos, mouse_pressed):
        """ This method attempts to place the held ball based on the current
            mouse position and state.
              Inputs: mouse_pos (a Vector2D object representing the position of
            the mouse on the table (i.e. if the table is shifted, this should
            be the shifted position of the mouse on the table)), and 
            mouse_pressed (a list of Booleans or equivalent detailing whether
            different mouse buttons are pressed, where the zero index 
            represents if left mouse button is pressed).
              Outputs: None (attempts to place the ball)."""
        # update the ball to be at the mouse position
        self._table.holding.can_show = True
        self._table.holding.new_pos = mouse_pos
        self._table.holding.centre = mouse_pos
        radius_vector = Vector2D(self._table.holding.radius,
                                 self._table.holding.radius)
        lower_pos = self._table.pos + radius_vector
        upper_pos = self._table.upper_pos - radius_vector
        # check if ball within correct boundaries.
        if lower_pos.x <= mouse_pos.x <= upper_pos.x and \
          lower_pos.y <= mouse_pos.y <= upper_pos.y and mouse_pressed[0]:
            # check that the ball is not placed in pocket
            for pocket in self._table.pockets:
                if pocket.contains(mouse_pos):
                    return
            # check that ball is not colliding with other balls on placement
            for ball in self._table.balls:
                if ball is not self._table.holding and ball.representation.contains(mouse_pos, extra=self._table.holding.radius):
                    return
            # updates position of ball and places on table
            self._place_ball(mouse_pos)

    def _mouse_controls(self):
        """ This method controls the controls of the offline simulation related
            to the mouse's position and pressed state, including focusing on 
            balls and attempting to place a ball in hand.
              Inputs: None.
              Outputs: None."""
        mouse_pos = self._controls["mouse_position"]
        mouse_pressed = self._controls["mouse_pressed"]
        if not self._table.in_motion:
            mouse_pos = Vector2D(mouse_pos)
            mouse_pos /= self.settings["ppm"]
            mouse_pos -= self._table_shift
            # handle focusing the cue on a specific ball
            if mouse_pressed[0]:
                self._check_focus(mouse_pos)
            # handle the user having the ball in hand.
            if self._table.holding is not None:
                self._attempt_ball_place(mouse_pos, mouse_pressed)

    def _use_cue(self):
        """ This method is called when the cue should be used to hit the cue
            ball as a result of controls.
              Inputs: None (uses the cue's methods and attributes).
              Outputs: None."""
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({
                "type": "make_shot", 
                "data": (self._table.cue.focus.number, self._table.cue.angle, self._table.cue.force),
                "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                "holding": self._table.holding.number if self._table.holding is not None else 0})
        self._table.cue.use()
        self._can_shoot = False
        self._can_pass_turn = False
        self._check_state = True

    def _keyboard_controls(self):
        """ This method controls the controls of the offline simulation related
            to the keyboard's state and which keys are pressed, including
            changes to cue angle and displacement, as well as the ability to 
            use the cue.
              Inputs: None.
              Outputs: None."""
        pressed_keys = self._controls["keys_pressed"]
        if self._table.cue.active:
            # updates cue to reflect changes from keyboard controls
            self._table.cue.update_positions()
            self._table.cue.update_ray()
            # make keyboard controls 40x slower if pressing left control key
            r = 0.025 if pressed_keys[306] else 1
            # handle cue movement
            if pressed_keys[276] or pressed_keys[97]:  # a or left arrow key
                self._table.cue.angle -= self.settings["cue_angle_rate"] * r
            if pressed_keys[275] or pressed_keys[100]:  # d or right arrow key
                self._table.cue.angle += self.settings["cue_angle_rate"] * r
            if pressed_keys[273] or pressed_keys[119]:  # w or up arrow key
                self._table.cue.change_offset(-self.settings["cue_offset_rate"] * r)
            if pressed_keys[274] or pressed_keys[115]:  # s or down arrow key
                self._table.cue.change_offset(self.settings["cue_offset_rate"] * r)
            # handle hitting with the cue.
            if pressed_keys[32] and self._can_shoot:  # space bar
                self._use_cue()

    def _handle_controls(self):
        """ This method is responsible for handling all of the user input / 
            controls, calling other functions that update the control handling.
              Inputs: None (uses user controls in ControlsObject set in the 
            main loop).
              Outputs: None.""" 
        self._quit_button.do_controls()
        self._mouse_controls()
        self._keyboard_controls()
        
    def _draw_ball_state(self, surface):
        """ This method draws the state of the balls on the table to the 
            screen. It displays the ball that each player has left to pocket on
            either side of the screen, and these are updated as more balls are 
            pocketed.
              Inputs: surface (a pygame.Surface object that the ball state 
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        scaled_radius = self._side_ball_scale * self.settings["ball_radius"] * self.settings["ppm"]
        x_offset = int(scaled_radius * 0.2)  # x-offset from the sides
        starting_y = self.settings["window_height"] - self._table.width * self.settings["ppm"] - scaled_radius
        starting_y = starting_y // 2  # starting y-coordinate
        y_step = 2 * self.settings["ball_radius"] * self.settings["ppm"] * (self._side_ball_scale + 0.5)
        current_y = starting_y
        for ball in self._p1_balls:
            ball.draw(surface, scale=self._side_ball_scale,
                      alternate_pos=(x_offset, current_y))
            current_y += y_step
        current_y = starting_y
        for ball in self._p2_balls:
            ball.draw(surface, scale=self._side_ball_scale, alternate_pos=(self.settings["window_width"] - x_offset - 2 * scaled_radius, current_y))
            current_y += y_step

    def _draw_game_state(self, surface):
        """ This method draws the game state to the screen, indicating which
            player's turn it is and which type of balls they have to pot in 
            case they don't remember or know.
              Inputs: surface (a pygame.Surface object that the ball state
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        if self._open:
            player_turn = self._message_font.render(
                "Player {}'s turn".format(self._player_turn),
                1, (0, 0, 0)
            )
        else:
            ball_type = "striped" if (self._p1_is_striped and self._player_turn == 1) or (not self._p1_is_striped and self._player_turn == 2) else "spotted"
            player_turn = self._message_font.render(
                "Player {}'s turn ({})".format(self._player_turn, ball_type),
                1, (0, 0, 0)
            )
        label_position = (self.settings["window_width"] / 100,
                          self.settings["window_height"] / 200)
        surface.blit(player_turn, label_position)

    def _draw_to_screen(self, surface):
        """ This method is responsible for drawing everything related to the
            game on a surface so that the user can see the state of the
            simulation and can interact with the simulation.
              Inputs: surface (a pygame.Surface object that the simulation 
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        self._table.draw(surface, shift=self._table_shift)
        self._draw_game_state(surface)
        self._quit_button.draw(surface)
        self._draw_ball_state(surface)

    def _close_table(self, p1_is_striped):
        """ This method closes the table, meaning that the table is no longer 
            open (anyone can hit any ball except the 8-ball) because someone
            has pocketed a coloured ball.
              Inputs: p1_is_striped (a Boolean value detailing whether player 1
            is striped or not as a result of closing the table (as if it is, 
            player 2 is spotted, or if not, player 1 is spotted and player 2 is
            striped)).
              Outputs: None (adds a message to the event queue and changes
            values of attributes)."""
        # we wait till later to actually close the table (self._open = False) 
        # to not interfere with other checks.
        self._p1_is_striped = p1_is_striped
        if p1_is_striped:
            self._p1_balls = self._striped_balls
            self._p2_balls = self._spotted_balls
        else:
            self._p1_balls = self._spotted_balls
            self._p2_balls = self._striped_balls
        message_string = ("The table is no longer open.\n" +
                          "Player {} must pot spotted (1-7) balls and\n" +
                          "Player {} must pot striped (9-15) balls to win.")
        message_string = message_string.format(2 if self._p1_is_striped else 1, 
                                               1 if self._p1_is_striped else 2)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font,
                                      message_length=6)
        events.event_queue.enqueue(message)

    def _open_table_check(self):
        """ This method checks whether the table should close or not given that
            the table is open. It does this by applying the rules of 8-ball 
            pool. If you hit the 8-ball first the table will always stay open,
            and if you pocket a coloured (non-eight or -cue ball) ball then the
            table is no longer open.
              Inputs: None (looks as the table's state attributes).
              Outputs: returns a Boolean value that describes whether the table
            should be closed or not."""
        if len(self._table.hit) > 0 and \
          self._table.hit[0] is self._table.eight_ball:
            return False  # if 8-ball is hit first, no foul is incurred but the
            # table stays open regardless of pockets
        for ball in self._table.pocketed:
            if ball is not self._table.eight_ball and \
              ball is not self._table.cue_ball:
                self._close_table((ball.striped and self._player_turn == 1) or (not ball.striped and self._player_turn == 2))
                return True
        return False

    def _break_check(self):
        """ This method checks the rule implementation pertaining to 8-ball
            pool breaks (the opening shots). Pocketing the 8-ball means the
            break must be redone. If 4 unique balls do not hit the rail and
            there are no pockets, the break can be optionally redone (and if
            the cue ball is pocketed).
              Inputs: None (looks at the table's state attributes)
              Outputs: returns two Boolean values. The first describes whether
            or not a foul has been incurred and the foul penalty should be 
            applied, whereas the second describes whether or not the short must
            be redone (with no choice, you are forced to redo the break)."""
        foul = False
        force_redo = False
        if len(self._table.pocketed)==0 and len(self._table.rail_contacts)<4:
            print("Fouled by failure to pocket or make 4 unique numbered rail contacts.")
            foul = True
        else:
            for ball in self._table.pocketed:
                if ball is self._table.eight_ball:
                    foul = True
                    force_redo = True
                elif ball is self._table.cue_ball:
                    foul = True
        return foul, force_redo

    def _victory_check(self):
        """ This method checks the rule implementation pertaining victory, 
            determining whether a victory state has been achieved by either
            user. This happens because of an 8-ball being pocketed, either 
            legally (the pocketing player's victory) or illegaly (the other
            player's victory).
              Inputs: None (looks at the table's state attributes).
              Outputs: returns either None or an integer (of 1 or 2), detailing
            the victor of the game. If None, the win condition has not been met 
            yet and nobody has won the game. If 1 or 2, then the player that
            matches this number is the one who has won the game (1 is player 1 
            and 2 is player 2)."""
        for index, ball in enumerate(self._table.pocketed):
            if ball is self._table.eight_ball:
                player_balls = self._p1_balls if self._player_turn == 1 else self._p2_balls
                # if open table or not potted all other balls or potted 8-ball 
                # on the same turn as the last coloured ball
                if index != 0 or self._open or len(player_balls) != 0:
                    return self._other_turn
                else:
                    return self._player_turn

    def _foul_check(self):
        """ This method checks the rule implementation pertaining to whether a
            foul has been incurred. This happens when: no balls are hit by the
            cue ball, no balls contact the rail AND no balls are pocketed, a 
            non-player ball is hit first by the cue ball, or by pocketing the 
            cue ball.
              Inputs: None (looks at the table's state attributes).
              Outputs: returns a Boolean value that describes whether a foul 
            has been incurred."""
        fouls = []
        if len(self._table.hit) == 0:
            fouls.append("Fouled by failure to hit any ball.")
        player_balls = self._p1_balls if self._player_turn == 1 else self._p2_balls
        if not self._open and len(self._table.hit) > 0 and \
          self._table.hit[0] not in player_balls:  
            # if first hit is not one of your own balls, check foul conditions
            if self._table.hit[0] == self._table.eight_ball:
                if len(player_balls) != 0:
                    fouls.append("Fouled by hitting the 8-ball first when you still have balls left to pocket.")
            else:
                fouls.append("Fouled by hitting one of your opponent's balls first instead of your own.")
        if len(self._table.pocketed)==0 and len(self._table.rail_contacts)==0:
            fouls.append("Fouled by failure to either pocket a ball or hit a numbered ball into a rail.")
        elif len(self._table.pocketed) == 1 and \
          self._table.pocketed[0] is self._table.cue_ball:
            fouls.append("Fouled by failure to either pocket a ball or hit a numbered ball into a rail.")
        for ball in self._table.pocketed:
            if ball not in player_balls:
                # no need to handle 8-ball here as that is in _victory_check
                if ball == self._table.cue_ball:
                    fouls.append("Fouled by pocketing the cue ball.")
                    break
        if len(fouls) > 0:
            for foul in fouls:
                print(foul)
            print("---")
            return True
        else:
            return False

    def _remove_pocketed_balls(self):
        """ This method removes all pocketed balls from the player's ball lists
            and simultaneously checks whether the current player can continue
            or not based on the pockets. If they pocketed one of their own 
            balls then they are elligible to continue (provided that they 
            haven't fouled), unless the table is open and they hit the 8-ball 
            first (then they cannot continue no matter what happens). There is
            no penalty for pocketing your opponent's balls.
              Inputs: None (looks at the table's state attributes).
              Outputs: returns a Boolean value that describes whether the 
            current player can continue their turn or not."""
        can_continue = False
        for ball in self._table.pocketed:
            if ball in self._p1_balls:
                # check if the player can continue their turn
                if not can_continue and self._player_turn == 1:
                    can_continue = True
                self._p1_balls.remove(ball)
            elif ball in self._p2_balls:
                if not can_continue and self._player_turn == 2:
                    can_continue = True
                self._p2_balls.remove(ball)
        # if the 8-ball is hit first on an open table, the player can never 
        # continue their turn regardless of pockets
        if self._open and len(self._table.hit) > 0 and \
          self._table.hit[0] is self._table.eight_ball:
            return False
        return can_continue

    def _redo(self):
        """ This overarching method calls other functions which fully reset the
            state of the table so that the game can be restarted, generally 
            because of an illegal break in which the 8-ball was pocketed. The 
            table, balls and complete game state are all recreated.
              Inputs: None.
              Outputs: None."""
        self._table.balls.clear()
        del self._table
        self._construct_table()
        self._place_balls()
        self._reset_state()
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({"type": "redo_match", "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                                     "holding": self._table.holding.number if self._table.holding is not None else 0})

    def _force_redo_message(self):
        """ This method displays a Message Event to the user, telling them that
            they are forced to redo the break because the other player pocketed
            the 8-ball in the break.
              Inputs: None.
              Outputs: None (modifies event queue)."""
        events.event_queue.clear()
        message_string = "Player {} has made an illegal break.\nPlayer {} must redo the illegal break because the\n8-ball was pocketed."
        message_string = message_string.format(self._player_turn,
                                               self._other_turn)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font)
        events.event_queue.enqueue(message)
        self._player_turn = self._other_turn

    def _keep(self):
        """ This method is called when the player keeps the other player's 
            illegal break, and hence allows the player to continue in a non-
            break state.
              Inputs: None.
              Outputs: None."""
        self._break = False
        self._can_shoot = True
        self._check_state = True
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({"type": "keep_break", "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                                     "holding": self._table.holding.number if self._table.holding is not None else 0})

    def _redo_choice(self, redo_func=None, keep_func=None):
        """ This method gives the player a choice between redoing or keeping
            their opponent's illegal break, displaying the option to the user
            through an event with buttons that call redo and keep functions.
              Inputs: redo_func (an optional subroutine or None which should be
            called by the redo button when pressed by a player. Leaving this as
            None defaults to self._redo) and keep_func (an optional subroutine
            or None which should be called by the keep button when pressed by a
            player. Leaving this as None defaults to self._keep).
              Outputs: None."""
        if redo_func is None: redo_func = self._redo
        if keep_func is None: keep_func = self._keep
        padding_size = Vector2D(self.settings["window_width"]/350, 
                                self.settings["window_height"]/250)
        padding_args = {"outline_padding": padding_size, 
                        "text_padding": padding_size}
        redo_event = events.ButtonEvent(self._controls, self._screen, "Redo", 
                                        redo_func, font=self._message_font, 
                                        padding_args=padding_args)
        keep_event = events.ButtonEvent(self._controls, self._screen, "Keep", 
                                        keep_func, font=self._message_font, 
                                        padding_args=padding_args)
        redo_event.condition = keep_event.is_pressed
        window_vector = Vector2D(self.settings["window_width"], 
                                 self.settings["window_height"])
        event_pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.02, 0.98), object_size=redo_event.button.size, scale_from=Vector2D(0,1))
        redo_event.button.pos = event_pos
        keep_event.condition = redo_event.is_pressed
        keep_event.button.pos = event_pos + Vector2D(redo_event.button.size.x + padding_size.x * 2, 0)
        message_string = "Player {} has made an illegal break.\nPlayer {} has the option of accepting the break positions\nor redoing the break themselves."
        message_string = message_string.format(self._player_turn, 
                                               self._other_turn)
        message_event = events.MessageEvent(self.settings, self._screen, 
                                            message_string, self._message_font,
                                            condition=[redo_event.is_pressed, 
                                                       keep_event.is_pressed])
        events.event_queue.enqueue(
            events.MultiEvent(redo_event, keep_event, message_event)
        )

    def _apply_foul_penalty(self):
        """ This method applies the foul penalty when a player fouls. It is 
            responsible for switching the turns and giving the opponent the 
            cue ball in hand to place wherever they would like.
              Inputs: None.
              Outputs: None."""
        message_string = "Player {} has fouled.\nPlayer {} now has the cue ball in hand."
        message_string = message_string.format(self._player_turn, 
                                               self._other_turn)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font)
        events.event_queue.enqueue(message)
        self._table.holding = self._table.cue_ball
        self._table.cue_ball.can_show = False
        self._table.cue_ball.can_collide = False
        self._table.cue.remove_focus()
        self._table.cue_ball.vel.set((0, 0))

    def _pass_turn(self):
        """ This method passes a player's turn, which is an option available 
            once the player has pocketed one of their own balls without 
            fouling, and has the option to continue or pass their turn. This
            method will switch the turn, and display an event highlighting that
            the pass has occurred.
              Inputs: None.
              Outputs: None."""
        message_string = "Player {} has passed their turn.\nIt is now player {}'s turn."
        message_string = message_string.format(self._player_turn, 
                                               self._other_turn)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font, 
                                      message_length=3)
        events.event_queue.enqueue(message)
        self._can_pass_turn = False
        self._player_turn = self._other_turn
        if self.settings["save_replay"]: # used for replays
            self.saved_moves.append({"type": "pass_turn", "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                                     "holding": self._table.holding.number if self._table.holding is not None else 0})

    def _victory(self, victor):
        """ This method displays the victor of the game to the users through 
            the event queue.
              Inputs: victor (an integer that is either 1 or 2, describing 
            which player (player 1 or 2) won the game).
              Outputs: None (changes the event queue)."""
        self._can_shoot = False
        events.event_queue.clear()
        message_string = "Congratulations player {}! You have won the game."
        message_string = message_string.format(victor)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font, 
                                      message_length=8)
        events.event_queue.enqueue(message)

    def _unable_to_pass(self):
        """ This method returns whether the player is unable to pass their 
            turn. Used for the conditional pass turn button to know that the
            player can no longer pass their turn.
              Inputs: None.
              Outputs: a Boolean value - True if the current player is unable
            to pass their turn, False if the current player is able to pass 
            their turn."""
        return not self._can_pass_turn

    def _continue_turn(self, pass_func=None):
        """ This method is called to allow a player to continue their turn
            after having pocketed one of their own balls previously without
            fouling. This gives them the option to pass their turn through an
            event, and displays a message saying they can continue their turn.
              Inputs: pass_func (an optional subroutine that passes the current
            player's continued turn, and is called when the pass turn button is
            pressed. If left as None then this defaults to self._pass_turn.
              Outputs: None (displays events through the event queue)."""
        if pass_func is None: pass_func = self._pass_turn
        self._can_pass_turn = True
        padding_size = Vector2D(self.settings["window_width"]/350,
                                self.settings["window_height"]/250)
        padding_args = {"outline_padding": padding_size, 
                        "text_padding": padding_size}
        pass_event = events.ButtonEvent(self._controls, self._screen,
                                        "Pass turn", pass_func, 
                                        font=self._message_font, 
                                        padding_args=padding_args, 
                                        condition=self._unable_to_pass)
        window_vector = Vector2D(self.settings["window_width"], 
                                 self.settings["window_height"])
        event_pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.02, 0.98), object_size=pass_event.button.size, scale_from=Vector2D(0,1))
        pass_event.button.pos = event_pos
        message_string = "Player {} can continue because they potted\none of their balls."
        message_string = message_string.format(self._player_turn)
        message = events.MessageEvent(self.settings, self._screen, 
                                     message_string, self._message_font,
                                     message_length=3, 
                                     condition=pass_event.is_pressed)
        events.event_queue.enqueue(
            events.MultiEvent(pass_event, message)
        )

    def _apply_rules(self, stop_open, foul, force_redo, victor, can_continue):
        """ This method is an overarching, general method that applies all of
            the results of the rules, given that all of the checks have been
            performed. These changes are gathered together because they need to
            be implemented in the correct order to avoid affecting other 
            checks. First we apply any illegal breaks, then we look for 
            victories, then continuing turns. We also apply statements to 
            conditionally end the break and open states.
              Inputs: stop_open (a Boolean detailing whether the open table
            should be ended according to the 8-ball pool rules), foul (a 
            Boolean detailing whether a foul has been incurred by the current 
            player), force_redo (a Boolean only relevant for the break checks 
            which details whether the opposing player will be forced to redo 
            the break because the current player pocketed the 8-ball in the 
            break), victor (either None or an integer that is 1 or 2. This
            represents the player who has won the game - None means no victory
            has been reached, 1 or 2 means player 1 or 2), and can_continue (a
            Boolean representing whether the current player can continue their
            turn or not).
              Outputs: a Boolean value detailing whether the game has ended 
            after the rules have been applied (i.e. the victor is not None).
            False means the game is not over, True means that it has ended."""
        can_shoot = True
        if self._break and foul:
            if force_redo:
                self._force_redo_message()
                self._redo()
                return False
            else:
                self._redo_choice()
                can_shoot = False
                self._check_state = False
            self._player_turn = self._other_turn
        elif victor is not None:
            self._victory(victor)
            return True
        elif foul:
            self._apply_foul_penalty()
            self._player_turn = self._other_turn
        elif can_continue:
            self._continue_turn()
        else:  #the shot was legal and so no rules are implemented.
            message_string = "Player {}'s turn has ended.\nIt is now player {}'s turn."
            message_string = message_string.format(self._player_turn, 
                                                   self._other_turn)
            message = events.MessageEvent(self.settings, self._screen, 
                                          message_string, self._message_font, 
                                          message_length=3)
            events.event_queue.enqueue(message)
            self._player_turn = self._other_turn
        # act upon other changes now that all other rules have been applied.
        if self._break and not foul:
            self._break = False
        if stop_open:
            self._open = False
        self._can_shoot = can_shoot  # restricts ability to shoot, i.e. if a choice must be made (e.g. illegal break)
        self._table.reset_counts()
        return False

    def _check_game_state(self):
        """ This method checks the state of the game according to all of the 
            predefined rules of 8-ball pool. It is an overarching method that
            calls all the individual rule check functions, including: open
            table checks, break checks, victory checks, foul checks and 
            continuation checks. It also calls the function that applies these
            rules, and hence is a method that can be called after a player's
            shot has finished to generally apply all rules.
              Inputs: None.
              Outputs: the Boolean output of self._apply_rules, i.e. a Boolean
            value detailing whether the game has ended or not. False means the
            game is not over, True means that the game has ended."""
        stop_open, force_redo, victor = False, False, None
        if self._open:
            stop_open = self._open_table_check()
        if self._break:
            foul, force_redo = self._break_check()
        else:
            victor = self._victory_check()
            foul = self._foul_check()
        can_continue = self._remove_pocketed_balls()
        return self._apply_rules(stop_open, foul, force_redo, 
                                 victor, can_continue)

    def _handle_events(self):
        """ This method handles displaying events from the event queue one
            event at a time. It repeatedly attempts to resolve events with each
            update until it can remove them, and then dequeues and displays the
            next event. It also handles quitting checks, because the simulation
            will only quit when all the events in the event queue are empty.
              Inputs: None (uses events.event_queue).
              Outputs: a Boolean value detailing whether the simulation should
            be quit. True means the simulation should be stopped, False means
            that it is not finished (either still events left to resolve or 
            victory conditions have not yet been met) and should continue being
            updated."""
        if self._event is None:  # check whether ready to handle the next event
            if not events.event_queue.is_empty:
                # dequeue an event from the queue if one available
                self._event = events.event_queue.dequeue()
                self._event.resolve()
                if self._event.can_remove:
                    del self._event
                    self._event = None
            elif self._quitting:
                self.in_game = False
                return True
        else:
            self._event.resolve()
            # keep trying to resolve the current event
            if self._event.can_remove:
                self._event = None
        # last, check for a forced quit (despite events still ongoing).
        return (self._quitting and not self.in_game)

    def update(self):
        """ The overarching method responsible for updating all aspects of the
            simulation over a period of time. It updates the physics engine,
            manages different input controls, draws all needed information to
            the screen, manages events of the game, and applies all of the
            rules of 8-ball pool. It does this by calling many other individual
            methods that perform these seperate functions.
              Inputs: None.
              Outputs: a Boolean value detailing whether the game should quit
            and the simulation should stop being displayed. True means that the
            simulation should be stopped and deleted, False means that it is
            not finished and should continue being updated."""
        self._handle_controls()
        self._table.update(self._time)
        self._draw_to_screen(self._screen)
        # handle game rule checks
        if not (self._table.in_motion or self._can_shoot) and \
          self._table.previously_in_motion and self._check_state:
            self._quitting = self._check_game_state()
        return self._handle_events()


class NetworkedGame(OfflineGame):
    """ The NetworkedGame class handles playing an online, networked game of
        pool. It controls client-side aspects, such as sending and receiving
        messages, managing controls and drawing to the screen."""

    def __init__(self, settings, screen, controls_obj, connection_obj,
                 lobby_info=None):
        """ The constructor for the NetworkedGame class, creating the basic 
            attributes and online commands interfaces for networked 8ball pool.
              Inputs: settings (a dictionary containing predetermined setting
            attribute values), screen (a pygame.Surface object which the game
            should be drawn to for user interaction), controls_obj (a 
            ControlsObject object which contains the user's control state,
            which is updated by the main loop), connection_obj (a Connection
            object that holds the user's connection to a server on which the
            networked game will be played), and lobby_info (an optional tuple
            or None that contains basic information about the a lobby being
            created by the user to play in. The first element is the lobby's
            name, and the second is its password (None == no password).).
              Outputs: None."""
        super().__init__(settings, screen, controls_obj)
        self.updated_settings = False
        self.commands = {
            "load_settings": self._load_settings,
            "create_game": self._create_game,
            "place_ball": self._place_ball,
            "hit_ball": self._hit_ball,
            "close_table": self._close_table,
            "keep": self._keep,
            "foul": self._apply_foul_penalty,
            "force_redo_message": self._force_redo_message,
            "redo_choice": self._redo_choice,
            "victory": self._victory,
            "pass_turn": self._pass_turn,
            "start_next_turn": self._start_next_turn,
            "update_cue_position": self.__update_cue_position,
            "change_cue_data_required": self.__change_cue_data_state,
            "end_game": self.__end_game
        }
        cue_update_rate = 30  # the maximum number of times per second the cue position will be sent / received
        self.cue_data_required = True
        self.cue_update_time = 1 / cue_update_rate
        self.__last_cue_data_time = 0.0
        self.__prev_cue_data = None
        self._can_place = False
        self._connection = connection_obj
        self._connection.add_commands(self.commands)
        self._event = None  # initialised here instead of in the _create_game
        # method so that when redoing illegal breaks, the message event is not
        # overwridden (as redoing the illegal break relies on calling the 
        # _create_game method again)
        self.lobby_info = lobby_info

    def _load_settings(self, settings):
        """ This method loads given settings into the NetworkedGame client so
            that the client can correctly create the table and update the
            simulation with the correct values. This is generally intended to
            be called with information passed by a received networked message.
              Inputs: settings (a dictionary containing predetermined setting
            attribute values used in construction & display of the simulation).
              Outputs: None (changes self.settings and related attributes)."""
        for key in settings.keys():
            self.settings[key] = settings[key]
        self.settings["base_cue_offset"] = self.settings["ball_radius"] + 0.01
        self.settings["max_cue_offset"] = self.settings["base_cue_offset"]+0.5
        self._time = 1 / self.settings["fps"]
        self.updated_settings = True

    def setup_game(self):
        """ This method begins the lobby communication with the server. It
            updates the player's setting preferences (e.g. send and receive cue
            data) so the server knows what to send it, and if it is the player
            creating the lobby then it sends the lobby information. It tells
            the server that it is ready to begin the game, and then will wait
            until the server is ready to start.
              Inputs: None.
              Outputs: None (does directly output to pygame's GUI)."""
        self._connection.send_queue.enqueue({'command': 'receive_cue_data', 'args': (self.settings["online_show_cue_position"],)})
        if self.lobby_info is not None:
            self._connection.send_queue.enqueue({"command": "create_lobby", "args": ("connection", self.settings, *self.lobby_info)})
        self._connection.send_queue.enqueue({"command": "ready"})
        
        waiting_label = Label("Connected to server. Waiting...", 
                              font=self._message_font)
        quit_button = Button(self._controls, "Quit", font=self._message_font,
                             target=self._quit)
        upper_pos = Vector2D(self.settings["window_width"], 
                             self.settings["window_height"])
        waiting_label.pos = scale_position(Vector2D(0, 0), upper_pos, Vector2D(0.5, 0.5), scale_from=Vector2D(0.5, 0.5), object_size=waiting_label.size)
        quit_button.pos = scale_position(Vector2D(0, 0), upper_pos, Vector2D(0.98, 0.98), scale_from=Vector2D(0.98, 0.98), object_size=quit_button.size)

        self._screen.fill(self.settings["background_colour"])
        waiting_label.draw(self._screen)
        quit_button.draw(self._screen)
        pygame.display.flip()
        # create small self-contained GUI loop here whilst waiting for lobby to
        # be ready to connect. This is done here instead of in main update()
        # loop of NetworkedGame to avoid an extra conditional check being
        # performed in every call of update() for the main PoolSim object.
        while not (self.in_game and self.updated_settings) and \
          not self._quitting and self._connection.in_use:
            self._controls["events"] = pygame.event.get()
            self._controls["mouse_position"] = Vector2D(pygame.mouse.get_pos())
            quit_button.do_controls()
            pygame.event.pump()

    def _place_balls(self, balls_info):
        """ This method adds all of the necessary ball objects to the table,
            according to the lobby settings and the positions and colours of
            different balls received from communication with the server.
            Colours and position settings are created by the server according
            to standard 8-ball rules, with a black 8-ball, a white cue-ball and
            7 spotted and 7 striped coloured balls.
              Inputs: balls_info (a list of tuples, each of which contain 3
            elements. The first element of each tuple is an integer detailing
            the ball's number (or None if the ball is not numbered). The second
            element describes the ball's position on the table, relative to the
            top left corner (middle of the top left pocket). The third element
            describes the ball's colour as a 3-integer RGB tuple or list).
              Outputs: None."""
        self._spotted_balls = []
        self._striped_balls = []
        for info in balls_info:
            ball_num = info[0]
            striped = True if ball_num > 8 else False
            ball = DrawableBall(Vector2D(info[2]), self.settings, info[1],
                                number=ball_num, striped=striped)
            if striped:
                self._striped_balls.append(ball)
            elif ball_num != 8:
                self._spotted_balls.append(ball)
            self._table.add_ball(ball)
        # The cue ball is then placed at a specific seperate point. This is
        # always the same and hence does not have to be received from a server.
        ball_pos = Vector2D(self._table.length / 3, self._table.width / 2)
        cue_ball = DrawableBall(ball_pos, self.settings, (255, 255, 255), 
                                can_focus=True)
        self._table.add_ball(cue_ball)
        if self.settings["save_replay"]:  # used for replays
            self.saved_moves.append({"type": "ball_info", "data": [ball_info[:2] for ball_info in balls_info]}) 

    def _reset_state(self):
        """ This method is responsible for resetting the variables related to
        the state of the game, e.g. allowing the game to easily be reset. It is
        the same as OfflineGame, except it also sets self._can_place to True.
              Inputs: None.
              Outputs: None."""
        super()._reset_state()
        self._can_place = True

    def _create_game(self, balls_info, turn):
        """ This method is responsible for actually creating the simulation and
            all of the objects used within it, and is generally intended to be
            called by the server when the lobby is ready to be started (as
            opposed to the main loop). It is responsible for creating the table
            and placing balls according to the server's sent positions, and
            setting up attributes related to game rules.
              Inputs: balls_info (a list of tuples, each of which contain 3 
            elements. The first element of each tuple is an integer detailing
            the ball's number (or None if the ball is not numbered). The second
            element describes the ball's position on the table, relative to the
            top left corner (middle of the top left pocket). The third element
            describes the ball's colour as a 3-integer RGB tuple or list.), and
            turn (an integer of 1 or 2 describing what the client's player 
            number / turn is (the user is either player 1 or 2 according to the
            lobby)).
              Outputs: None."""
        self.turn = turn
        self._scale_values()
        side_ball_length = (self.settings["ball_radius"] * (self.settings["side_ball_scale"] + 0.5) * self.settings["ppm"] * 6)
        self._side_ball_scale = int(self.settings["screen_height"] * self.settings["scale_height"] / side_ball_length)
        font_size = int(0.0442086 * self.settings["window_height"])
        self._text_font = pygame.font.SysFont(self.settings["message_font"],
                                              font_size)
        self._quitting = False
        self._construct_table()

        if self.settings["save_replay"]:
            # We have to check whether the replay's saved moves already exist.
            # This is because in order to redo the game, the server re-calls 
            # create_game(), which would reset the moves list (not wanted).
            if hasattr(self, "saved_moves"):
                self.saved_moves.append({"type": "redo_match", "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls],
                                         "holding": self._table.holding.number if self._table.holding is not None else 0})
            else:
                self.saved_moves = [
                    time.localtime(), 
                    {"type": "match_settings", "data": self.settings},
                    {"type": "starting_player", 
                     "data": self.settings["starting_player"]}
                ]

        self._place_balls(balls_info)
        self._reset_state()
        self._player_turn = self.settings["starting_player"]
                
        if self.settings["online_show_cue_position"]:
            if self.turn != self._player_turn:
                self._table.cue.can_focus = True
                if not self.settings["auto_focus"]:
                    self._table.attempt_focus()
        else:
            if self.turn != self._player_turn:
                self._table.cue.remove_focus()
                self._table.cue.can_focus = False
                self._table.cue.ray = None
            else:
                self._table.cue.can_focus = True
                
        self.in_game = True

    def _place_ball(self, pos):
        """ This method places the currently held ball at a given position on
            the table.
              Inputs: pos (a list object that represents the position to place
            the held ball on the table).
              Outputs: None."""
        if self.turn == self._player_turn and self._can_place:  
            # if you are the one placing the ball, tell the server.
            self._can_place = False
            self._connection.send_queue.enqueue({"command": "place_ball",
                                                 "args": (tuple(pos),)})
            return
        super()._place_ball(pos)
        # if it is not your turn but you want to see the cue position and you
        # have the auto focus setting disabled, we need to call the table's
        # _attempt_focus() method after the ball is placed.
        if self.turn != self._player_turn and self.settings["online_show_cue_position"]:
            self._table.cue.can_focus = True
            if not self.settings["auto_focus"]:
                self._table.attempt_focus()

    def _check_focus(self, mouse_pos):
        """ This method checks whether the mouse is clicking on and attempting
            to focus on a ball. It is an extension of OfflineGame._check_focus
            as it also checks whether it is the player's turn.
              Inputs: mouse_pos (a Vector2D object representing the position of
            the mouse on the table (i.e. if the table is shifted, this should
            be the shifted position of the mouse on the table)).
              Outputs: None."""
        if self.turn == self._player_turn:
            super()._check_focus(mouse_pos)

    def _attempt_ball_place(self, mouse_pos, mouse_pressed):
        """ This method attempts to place the held ball based on the current
            mouse position and state. It is an extension of the OfflineGame's
            _attempt_ball_place method as it also checks whether 
            self._can_place is True.
              Inputs: mouse_pos (a Vector2D object representing the position of
            the mouse on the table (i.e. if the table is shifted, this should
            be the shifted position of the mouse on the table)), and
            mouse_pressed (a list of Booleans or equivalent detailing whether
            different mouse buttons are pressed, where index 0 represents
            if left mouse button is pressed).
              Outputs: None (attempts to place the ball)."""
        if self._can_place:
            super()._attempt_ball_place(mouse_pos, mouse_pressed)

    def _hit_ball(self, number, force, angle):
        """ This method is called to hit a specific ball on the table using the
            cue, with a specific direction and power.
              Inputs: number (an Integer representing the number of the ball on
            the table that is being hit, or None to represent an unnumbered 
            ball), force (an integer or float representing the force that the
            cue is hitting the focused ball within in Newtons) and angle (a
            float or integer representing the angle in radians that the cue is
            positioned at when hitting the ball).
              Outputs: None."""
        if self.settings["save_replay"]:  # used for replays
            self.saved_moves.append({"type": "make_shot", "data": (number, angle, force), "positions": [(ball.number, tuple(ball.pos)) for ball in self._table.balls], "holding": self._table.holding.number if self._table.holding is not None else 0})
        for ball in self._table.balls:
            if ball.number == number:
                self._table.cue.set_focus(ball)
                break
        self._table.cue.angle = angle
        self._table.cue.force = force
        self._table.cue.use()
        self._can_shoot = False
        self._can_pass_turn = False
        self._table.cue.remove_focus()

    def _use_cue(self):
        """ This method is called when the cue should be used to hit the cue
            ball as a result of controls.
              Inputs: None (uses the cue's methods and attributes).
              Outputs: None."""
        number = self._table.cue.focus.number
        force = self._table.cue.force
        angle = self._table.cue.angle
        self._connection.send_queue.enqueue({
            "command": "hit_ball",
            "args": ("connection", number, force, angle)}
        )
        self._hit_ball(number, force, angle)

    def _handle_controls(self):
        """ This method is responsible for handling all of the user input /
            controls, calling other functions that update the control handling.
              Inputs: None (uses user controls in ControlsObject set in the
            main loop).
              Outputs: None.""" 
        if self.turn == self._player_turn:
            super()._handle_controls()
        else:
            if self._table.cue.active:
                self._table.cue.update_positions()
            self._quit_button.do_controls()

    def _draw_game_state(self, surface):
        """ This method draws the game state to the screen, indicating which
            player's turn it is and which type of balls they have to pot in
            case they don't remember or know.
              Inputs: surface (a pygame.Surface object that the ball state
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        identifier = "you" if self.turn == self._player_turn else "them"
        if self._open:
            message = f"Player {self._player_turn}'s turn ({identifier})"
        else:
            ball_type = "striped" if (self._p1_is_striped and self._player_turn == 1) or (not self._p1_is_striped and self._player_turn == 2) else "spotted"
            message = f"Player {self._player_turn}'s turn ({ball_type}) ({identifier})"
        player_turn = self._message_font.render(message, 1, (0, 0, 0))
        blit_pos = [self.settings["window_width"] / 96,
                    self.settings["window_height"] / 216]
        surface.blit(player_turn, blit_pos)

    def _quit(self):
        """ This method stops and quits the online networked game client,
            sending a message to tell the server that the user / client has
            quit the game.
              Inputs: None.
              Outputs: None."""
        self._connection.send_queue.enqueue({"command": "quit", 
                                             "args": ("connection",)})
        super()._quit()
    
    def __end_game(self, text):
        """ This method tells the users that the game has ended, through the
            use of the event system, and sets the game to end once the event is
            done being displayed.
              Inputs: text (a string containing a message that is displayed to
            users at the end of the game before the game ends and they are
            forced to quit).
              Outputs: None (changes events.event_queue)."""
        events.event_queue.clear()
        self._event = None
        message = events.MessageEvent(self.settings, self._screen, text,
                                      self._message_font, message_length=5)
        events.event_queue.enqueue(message)
        self._quitting = True

    def _redo_online(self):
        """ This method sends a message to the server detailing that the user
            would like to redo an illegal break.
              Inputs: None.
              Outputs: None (communicates with the server)."""
        self._connection.send_queue.enqueue({"command": "redo"})

    def _keep_online(self):
        """ This method sends a message to the server detailing that the user
            would like to keep an illegal break.
              Inputs: None.
              Outputs None (communicates with the server)."""
        self._connection.send_queue.enqueue({"command": "keep"})

    def _redo_choice(self):
        """ This method gives the player a choice between redoing or keeping
            their opponent's illegal break, displaying the option to the user
            through an event with buttons that call _redo_online and 
            _keep_online functions.
              Inputs: None.
              Outputs: None."""
        super()._redo_choice(redo_func=self._redo_online, 
                             keep_func=self._keep_online)

    def _apply_foul_penalty(self, foul_reasons):
        """ This method applies the foul penalty when a player fouls. It is
            responsible for switching the turns and giving the opponent the cue
            ball in hand to place wherever they would like.
              Inputs: foul_reasons (a list containing the reason(s) for the
            foul. Each foul is printed to the console).
              Outputs: None."""
        super()._apply_foul_penalty()
        for foul in foul_reasons:
            print(foul)
        print("---")
        if self.turn != self._player_turn:
            self._table.cue_ball.can_show = True
            self._can_place = True

    def _pass_turn(self):
        """ This method passes a player's turn, which is an option available
            once the player has pocketed one of their own balls without
            fouling, and has the option to continue or pass their turn. This
            method will switch the turn, and display an event highlighting that
            the pass has occurred.
              Inputs: None.
              Outputs: None."""
        super()._pass_turn()
        self._player_turn = self._other_turn
        self._table.cue.reset_positioning()
        self._table.cue.update_ray()

    def _pass_online(self):
        """ This methods sends a message to the server detailing that the user
            would like to pass their turn. It removes their ability to interact
            with the cue from the client-side also.
              Inputs: None.
              Outputis: None."""
        self._connection.send_queue.enqueue({"command": "pass_turn"})
        self._can_shoot = False
        self._table.cue.remove_focus()

    def _continue_turn(self):
        """ This method is called to allow a player to continue their turn
            after having pocketed one of their own balls previously without 
            fouling. This gives them the option to pass their turn through an
            event, and displays a message saying they can continue their turn.
              Inputs: None.
              Outputs: None."""
        super()._continue_turn(pass_func=self._pass_online)

    def _start_next_turn(self, continued_turn, is_break, is_open, can_shoot):
        """ Starts the next player turn acording to input conditions - the
            server will call this function over the network to start the next
            turn. It first determines whether it should stay in the current
            player's turn or switch player turn, then it determines if (and if
            so, where) the cue should focus. It updates some table conditions
            such as break and open tables, and finally it removes pocketed
            balls and resets the table's counts.
              Inputs: continued_turn (a Boolean value detailing whether the
            current player's turn is continued and they have the option to pass
            their turn), is_break (a Boolean value detailing whether the
            current turn is a break or not), is_open (a Boolean value detailing
            whether the table is open on the current turn or not (i.e. any
            balls can be pocketed except the cue- and 8-ball)), and can_shoot
            (a Boolean value detailing whether the current player (whose turn
            it is) can shoot the cue or not. e.g. they can not when making an
            illegal break decision).
              Outputs: None."""
        if continued_turn:
            if self.turn == self._player_turn:
                self._continue_turn()
            else:
                message_string = "Player {} can continue because they potted\none of their balls."
                message_string = message_string.format(self._player_turn)
                message = events.MessageEvent(
                    self.settings, 
                    self._screen,
                    message_string, 
                    self._message_font,
                    message_length=3
                )
                events.event_queue.enqueue(message)
        else:
            self._player_turn = self._other_turn
        if self.settings["online_show_cue_position"]:
            if self.turn != self._player_turn:
                self._table.cue.can_focus = True
                # have to add an extra statement because if you don't want to
                # auto-focus but still want to see the cue position movement, 
                # then I need to have a statement that makes it focus when it 
                # is not your turn.
                if not self.settings["auto_focus"]:
                    self._table.attempt_focus()
                self._table.cue.ray = None
        else:
            if self.turn != self._player_turn:
                self._table.cue.remove_focus()
                self._table.cue.can_focus = False
                self._table.cue.ray = None
            else:
                self._table.cue.can_focus = True
        if self._table.holding is not None:
            self._table.holding.can_show = False
        self._break = is_break
        self._open = is_open
        self._can_shoot = can_shoot
        for ball in self._table.pocketed:
            if ball in self._p1_balls:
                self._p1_balls.remove(ball)
            elif ball in self._p2_balls:
                self._p2_balls.remove(ball)
        self._table.reset_counts()

    def __update_cue_position(self, new_data):
        """ This method updates the position (angle and offset) of the cue to
            match new input data. Used to show how the opponent is using the 
            cue in networked games.
              Inputs: new_data (a tuple containing two floats or integers. The
            first number should be the angle of the cue in radians, and the
            second number is the current offset of the cue from the centre of
            its focused ball in metres).
              Outputs: None (changes the cue attributes)."""
        if new_data is not None:
            self._table.cue.angle = new_data[0]
            self._table.cue.current_offset = new_data[1]

    def __change_cue_data_state(self, new_state):
        """ This method updates the cue data required state, which describes 
            whether the Networked client should send cue positional data to the
            server at regular intervals (because another client on the server
            has requested it).
              Inputs: new_state (a Boolean value detailing whether the client
            is required to send cue positional data to the user - True means
            data should be sent, False means it should not).
              Outputs: None."""
        self.cue_data_required = new_state

    def _victory(self, victor):
        """ This method updates the simulation to reflect that a victory has
            occurred. It displays a message to the user depending on whether
            they won or lost, and sets the _quitting flag to True.
              Inputs: victor (an Integer that is either 1 or 2 describing the
            player that won the game).
              Outputs: None."""
        self._can_shoot = False
        events.event_queue.clear()
        self._event = None
        if victor == self.turn:
            message_string = "Congratulations! You have won the game."
        else:
            message_string = "Player {} won the game! Better luck next time.".format(victor)
        message = events.MessageEvent(self.settings, self._screen, 
                                      message_string, self._message_font, 
                                      message_length=8)
        events.event_queue.enqueue(message)
        self._quitting = True

    def _send_cue_data(self):
        """ This method checks whether the client needs to send cue positional
            data to the server, and if it does, then it collects and sends this
            data.
              Inputs: None.
              Outputs: None (communicates with the server)."""
        if self.cue_data_required and self.turn == self._player_turn and \
          not self._table.in_motion:
            current_time = time.time()
            if current_time - self.__last_cue_data_time > self.cue_update_time:
                cue_data = (self._table.cue.angle, 
                            self._table.cue.current_offset)
                self.__last_cue_data_time = current_time
                if cue_data != self.__prev_cue_data:  
                    # we only send data if it is different to last data sent.
                    self._connection.send_queue.enqueue({"command": "update_server_cue_position", "args": (cue_data,)})
                    self.__prev_cue_data = cue_data

    def update(self):
        """ The overarching method responsible for updating all aspects of the
            simulation over a period of time. It updates the physics engine,
            manages different input controls, draws all needed information to
            the screen, manages events of the game, and communicates
            information with the server. It does this by calling many other
            individual methods that perform these seperate functions.
              Inputs: None.
              Outputs: a Boolean value detailing whether the game should quit
            and the simulation should stop being displayed. True means that the
            simulation should be stopped and deleted, False means that it is
            not finished and should continue being updated."""
        if not self.in_game:  
            # if not in game yet, i.e. waiting or connecting, don't update.
            return self._quitting
        self._handle_controls()
        self._table.update(self._time)
        self._draw_to_screen(self._screen)
        self._send_cue_data()
        if not self._table.in_motion and self._table.previously_in_motion:
            self._connection.send_queue.enqueue({"command": "finished_drawing",
                                                 "args": ("connection",)})
        return self._handle_events()


class EditorGame(OfflineGame):
    """ The EditorGame class handles playing an offline, editable game of pool.
        It lets you place custom balls in custom positions and make shots that
        are physically simulated so that you can practice custom scenarios."""

    def __init__(self, *args, **kwargs):
        """ The constructor for the EditorGame class, creating the basic
            attributes for 8-ball pool & an interface for editing the table.
              Inputs: [the same inputs as OfflineGame.__init__()]
            settings (a dictionary containing predetermined setting attribute
            values), screen (a pygame.Surface object which the game should be
            drawn to for user interaction), and controls_obj (a ControlsObject
            object which contains the user's control state, which is updated by
            the main loop).
              Outputs: None."""
        super().__init__(*args, **kwargs)
        self._init_overlay_elements()
        self._edit_mode = True
        self._ball_colours = [(240, 240, 0), (0, 0, 255), (255, 0, 0),
                              (128, 0, 128), (255, 165, 0), (0, 255, 0),
                              (128, 0, 0)]  # list of colours for the other 
        # balls to randomly draw from.
        self._current_ball_number = 1
        self._ball_limit = 32  # changeable ball limit that is hard-coded.
        self._on_prev_click = False

    def _init_overlay_elements(self):
        """ This method creates all of the UI elements used in the practice
            editor's overlay, and also positions them on the screen so that
            they can be clearly displayed to the user when drawn and controlled.
              Inputs: None.
              Outputs: None."""
        window_vector = Vector2D(self.settings["window_width"], 
                                 self.settings["window_height"])
        padding_size = window_vector / 100
        button_size = Vector2D(self.settings["window_width"] / 350, 
                               self.settings["window_height"] / 250)
        
        self._change_mode_button = Button(self._controls, "Enter Play Mode", 
                                          font=self._message_font, 
                                          target=self._switch_mode,
                                          outline_padding=button_size,
                                          text_padding=button_size)
        self._cue_ball_button = Button(self._controls, "Cue Ball", 
                                       font=self._message_font,
                                       target=self._add_cue_ball, 
                                       outline_padding=button_size, 
                                       text_padding=button_size)
        self._eight_ball_button = Button(self._controls, "8-Ball", 
                                         font=self._message_font,
                                         target=self._add_eight_ball, 
                                         outline_padding=button_size, 
                                         text_padding=button_size)
        self._other_ball_button = Button(self._controls, "Other Ball", 
                                         font=self._message_font,
                                         target=self._add_other_ball, 
                                         outline_padding=button_size, 
                                         text_padding=button_size)
        self._clear_button = Button(self._controls, "Clear Table", 
                                    font=self._message_font,
                                    target=self._clear_table,
                                    outline_padding=button_size, 
                                    text_padding=button_size)
        self._delete_last_button = Button(self._controls, "Delete Last", 
                                          font=self._message_font,
                                          target=self._delete_last_ball, 
                                          outline_padding=button_size, 
                                          text_padding=button_size)
        self._bin_button = Button(self._controls, "Bin", 
                                  font=self._message_font,
                                  target=self._remove_held_ball, 
                                  outline_padding=button_size, 
                                  text_padding=button_size)

        # create containers to position the UI elements in groups on the screen
        self._top_middle_container = Container(3, 1, edge_padding=Vector2D(0,0), inner_padding=padding_size*10)
        self._top_middle_container.add_elements(self._delete_last_button, 
                                                self._bin_button, 
                                                self._clear_button)
        self._bottom_middle_container = Container(3, 1, edge_padding=Vector2D(0,0), inner_padding=padding_size)
        self._bottom_middle_container.add_elements(self._cue_ball_button, 
                                                   self._eight_ball_button, 
                                                   self._other_ball_button)
        self._change_mode_button.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.02, 0.98), object_size=self._change_mode_button.size, scale_from=Vector2D(0, 1))
        self._bottom_middle_container.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.5, 0.98), object_size=self._bottom_middle_container.size, scale_from=Vector2D(0.5, 1))
        self._top_middle_container.pos = scale_position(Vector2D(0, 0), window_vector, Vector2D(0.5, 0.02), object_size=self._top_middle_container.size, scale_from=Vector2D(0.5, 0))
        self._hideable_elements = [self._cue_ball_button, 
                                   self._eight_ball_button, 
                                   self._other_ball_button,
                                   self._clear_button, 
                                   self._delete_last_button, 
                                   self._bin_button]


    def _switch_mode(self):
        """ This method switches the table between 'edit mode' and 'play mode',
            so that the users can independently edit the table scenario and
            then actually play the table and simulate the physics of their
            shots.
              Inputs: None.
              Outputs: None."""
        if self._table.holding is None:
            if not self._table.in_motion:
                self._table.cue.can_focus = self._edit_mode
                self._edit_mode = not self._edit_mode
                for ui_element in self._hideable_elements:
                    ui_element.active = self._edit_mode
                self._change_mode_button.text = "Enter Play Mode" if self._edit_mode else "Enter Edit Mode"
                if self._edit_mode:
                    self._table.cue.remove_focus()
            elif events.event_queue.is_empty:
                message_string = "You cannot change mode whilst balls are still in motion."
                message = events.MessageEvent(self.settings, self._screen,
                                              message_string, 
                                              self._message_font, 
                                              message_length=2)
                events.event_queue.enqueue(message)
        elif events.event_queue.is_empty:
            message_string = "You cannot change mode whilst holding a ball."
            message = events.MessageEvent(self.settings, self._screen,
                                          message_string, self._message_font, 
                                          message_length=1.5)
            events.event_queue.enqueue(message)

    def _remove_held_ball(self):
        """ This method removes the currently held ball, removing it from the
            hand and entirely deleting the ball object. This is used when the
            user switches to play mode whilst still having a ball in hand.
              Inputs: None.
              Outputs: None."""
        if self._table.holding is not None:
            self._table.balls.remove(self._table.holding)
            if self._table.holding == self._table.cue_ball:
                self._table.cue_ball = None
            self._table.holding = None

    def _check_ball_limit(self):
        """ This method checks whether the ball limit has been reached when
            trying to add another ball and if it is, displays a message to the
            user through the event system to tell them that their ball limit
            has been reached.
              Inputs: None.
              Outputs: a Boolean value describing whether the ball limit has
            been reached - if True, it has and no more balls can be placed, if
            False, it has not."""
        if len(self._table.balls) >= self._ball_limit:
            if events.event_queue.is_empty:
                message_string = "The ball limit of {} has been reached.".format(self._ball_limit)
                message = events.MessageEvent(self.settings, self._screen,
                                              message_string, 
                                              self._message_font, 
                                              message_length=1)
                events.event_queue.enqueue(message)
            return True
        return False

    def _add_cue_ball(self):
        """ This method adds a cue ball to the table, first checking if a ball
            can be added, and, if it can, creating it and adding it to the
            player's hand so that they can place it on the table.
              Inputs: None.
              Outputs: None."""
        if self._check_ball_limit():
            return
        if self._table.cue_ball is None:
            self._remove_held_ball()
            self._table.holding = DrawableBall(Vector2D(0,0), self.settings, 
                                               (255, 255, 255), can_focus=True)
            self._table.holding.new_pos.set(self._controls["mouse_position"])
            self._table.add_ball(self._table.holding)
        else:
            if events.event_queue.is_empty:
                message_string = "You cannot have more than one cue ball."
                message = events.MessageEvent(self.settings, self._screen,
                                              message_string, 
                                              self._message_font, 
                                              message_length=1)
                events.event_queue.enqueue(message)

    def _add_eight_ball(self):
        """ This method adds an 8-ball to the table, first checking if a ball
            can be added, and, if it can, creating it and adding it to the
            player's hand so that they can place it on the table.
              Inputs: None.
              Outputs: None."""
        if self._check_ball_limit():
            return
        self._remove_held_ball()
        self._table.holding = DrawableBall(Vector2D(0,0), self.settings,
                                           (0, 0, 0), striped=False, number=8)
        self._table.holding.new_pos.set(self._controls["mouse_position"])
        self._table.add_ball(self._table.holding)

    def _add_other_ball(self):
        """ This method adds an other ball (a normal, coloured ball that is not
            an 8-ball or a cue-ball) to the table, first checking if a ball can
            be added, and, if it can, creating it and adding it to the player's
            hand so that they can place it on the table.
              Inputs: None.
              Outputs: None."""
        if self._check_ball_limit():
            return
        self._remove_held_ball()
        # randomly decides if striped or not
        is_striped = True if random.randint(0, 1) == 1 else False
        colour = random.choice(self._ball_colours)
        self._table.holding = DrawableBall(Vector2D(0,0), self.settings,
                                           colour, striped=is_striped, 
                                           number=self._current_ball_number)
        self._table.holding.new_pos.set(self._controls["mouse_position"])
        self._table.add_ball(self._table.holding)
        if self._current_ball_number == 7:  
            # skips 8 being a possible other-ball number to avoid confusion
            self._current_ball_number = 9
        elif self._current_ball_number == 99:  
            # stops balls from being above double digits; loops around.
            self._current_ball_number = 1
        else:
            self._current_ball_number += 1

    def _clear_table(self):
        """ This method clears the table of all balls so that the user can
            start adding balls from the beginning again.
              Inputs: None.
              Outputs: None."""
        del self._table.balls
        self._table.balls = []
        self._table.holding = None
        self._table.cue_ball = None

    def _delete_last_ball(self):
        """ This method deletes the last ball that was added to the table. It
            first checks if there is a ball in hand to remove that, and if not
            checks if there is actually a ball to remove, and if there is it
            will then remove that ball completely from the table.
              Inputs: None.
              Outputs: None."""
        if self._table.holding is not None:
            self._table.holding = None
        if len(self._table.balls) == 0:
            return
        # remove and return last ball (we return because we might need to 
        # clear the table's cue_ball attribute also.)
        removed_ball = self._table.balls.pop(len(self._table.balls) - 1) 
        if removed_ball is self._table.cue_ball:
            self._table.cue_ball = None
        del removed_ball

    def setup_game(self):
        """ This method actually sets up and starts the editor so that it can
            be interacted with by users. It calls the creation of basic 
            information required for the game, and the creation of the table
            object. It is an overarching setup function for starting the game.
              Inputs: None.
              Outputs: None."""
        self._scale_values()
        self._text_font = pygame.font.SysFont(self.settings["message_font"], 32)
        self._event = None
        self._construct_table()
        self._reset_state()
        self._table.cue.can_focus = False
        self._quitting = False
        self.in_game = True

    def _place_ball(self, pos):
        """ This method places the currently held ball at a given position on
            the table. It will also change the _on_prev_click attribute to True
            to reflect that a click-based action has occurred.
              Inputs: pos (a Vector2D object that represents the position to
            place the held ball on the table).
              Outputs: None."""
        if not self._on_prev_click:
            super()._place_ball(pos)
        self._on_prev_click = True

    def _check_focus(self, mouse_pos):
        """ This method checks whether the mouse is clicking on and attempting
            to focus on a ball.
              Inputs: mouse_pos (a Vector2D object representing the position of
            the mouse on the table (i.e. if the table is shifted, this should
            be the shifted position of the mouse on the table)).
              Outputs: None."""
        for ball in self._table.balls:
            if ball.representation.contains(mouse_pos):
                if not self._edit_mode and ball.can_focus:
                    self._table.cue.set_focus(ball)
                elif self._edit_mode and self._table.holding is None and \
                  not self._on_prev_click:  # check for picking a ball up
                    self._table.holding = ball
                    # we remove and re-add the ball to ensure it is on top of others when drawn
                    self._table.balls.remove(ball)
                    self._table.add_ball(ball)
                    self._on_prev_click = True
                break

    def _handle_controls(self):
        """ This method is responsible for handling all of the user input /
            controls for the practice mode. This is like normal game controls
            but also checks controls for other UI elements.
              Inputs: None.
              Outputs: None."""
        super()._handle_controls()
        if self._on_prev_click and not self._controls["mouse_pressed"][0]:
            self._on_prev_click = False  # stops repeat focusing when held down
        self._change_mode_button.do_controls()
        self._bottom_middle_container.do_controls()
        self._top_middle_container.do_controls()

    def _draw_overlay(self, surface):
        """ This method draws the overlay of the editor to a given surface
            (screen) so that the user can see and interact with the editor.
            This covers all the different buttons, including the ability to
            change modes, add new balls, remove balls and quit.
              Inputs: surface (a pygame.Surface object that the overlay will be
            drawn to).
              Outputs: None (draws and modifies the given surface object)."""
        self._change_mode_button.draw(surface)
        self._bottom_middle_container.draw(surface)
        self._top_middle_container.draw(surface)
        self._quit_button.draw(surface)

    def _draw_to_screen(self, surface):
        """ This method is responsible for drawing everything related to the
            game on a surface so that the user can see the state of the
            simulation and can interact with the simulation.
              Inputs: surface (a pygame.Surface object that the simulation
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        self._table.draw(surface, draw_balls=False, draw_cue=False, 
                         shift=self._table_shift)
        self._draw_overlay(surface)
        for ball in self._table.balls:
            if ball.can_show:
                ball.draw(surface, shift=self._table_shift)
        self._table.cue.draw(surface, shift=self._table_shift)

    def _state_check(self):
        """ This method checks the state of the most recent shot made in the
            editor simulation, determining whether any foul conditions have
            been met, and counting how many eight balls and other balls have
            been pocketed, so that this feedback can be later sent back to the
            user.
              Inputs: None (looks at self._table's attributes).
              Outputs: returns three values - the first value is a list
            containing a variable number of strings (0 to 3), where each string
            details a different foul condition that has been met, the second
            value is an integer >= 0 describing the number of 8-balls pocketed
            in the last shot, and the third value is an integer >= 0 describing
            the number of other (coloured, non-8 and non-cue) balls pocketed in
            the last shot."""
        fouls = []
        eight_balls = 0
        other_balls = 0
        if len(self._table.hit) == 0:
            fouls.append("Fouled by failure to hit any ball.")
        if len(self._table.rail_contacts) == 0 and (len(self._table.pocketed) == 0 or (len(self._table.pocketed) == 1 and self._table.pocketed[0] is self._table.cue_ball)):
            fouls.append("Fouled by failure to either pocket a ball or hit a numbered ball into a rail.")
        for ball in self._table.pocketed:
            if ball is self._table.cue_ball:
                fouls.append("Fouled by pocketing the cue ball.")
            elif ball.number == 8:
                eight_balls += 1
            else:
                other_balls += 1
        return fouls, eight_balls, other_balls

    def _apply_rules(self):
        """ This method handles the results of any applied rules (a shot state
            check). This displays the information about the last shot to the
            user as an event, showing the number of pocketed other (coloured)
            balls and 8-balls, and detailing any fouls that have been made if
            they have.
              Inputs: None (the method does the state check itself).
              Outputs: None (changes events.event_queue and many attributes).
        """
        fouls, eight_balls, other_balls = self._state_check()
        self._table.reset_counts()
        message_string = "Pocketed {} normal {} & {} 8-{}."
        if len(fouls) > 0:
            message_string += "\nFouls:"
            for foul in fouls:
                message_string += "\n - {}".format(foul)
        message_string = message_string.format(
            other_balls, 
            "ball" if other_balls == 1 else "balls",
            eight_balls,
            "ball" if eight_balls == 1 else "balls"
        )
        message_length = 3 if len(fouls) == 0 else 5
        events.event_queue.clear()
        self._event = None
        message = events.MessageEvent(self.settings, self._screen,
                                      message_string, self._message_font,
                                      message_length=message_length)
        events.event_queue.enqueue(message)
        self._can_shoot = True

    def update(self):
        """ The overarching method responsible for updating all aspects of the
            practice simulation over a period of time. It updates the physics
            engine, manages different input controls, draws all needed
            information to the screen, manages events of the game, and applies
            shot rule checks if necessary. It does this by calling many other
            individual methods that perform these seperate functions.
              Inputs: None.
              Outputs: a Boolean value detailing whether the game should quit
            and the simulation should stop being displayed. True means that the
            simulation should be stopped and deleted, False means that it is
            not finished and should continue being updated."""
        self._handle_controls()
        self._table.update(self._time)
        self._draw_to_screen(self._screen)
        
        if not self._table.in_motion and self._table.previously_in_motion and \
          self._check_state:
            self._apply_rules()

        return self._handle_events()


class ReplayTable(DrawableTable):
    """ This class holds all the information about the pool table currently in
        use to show a replay, as well as the objects that occupy that table
        such as the cue and the balls. This is slightly different from the
        normal pool table used in the simulations because it has been changed
        to not remove the balls from the table's list of balls, so that they
        can be un-hidden if the user goes back in the replay."""

    def resolve_pockets(self):
        """ A method which will check for and resolve all incidences of pockets 
            on the table, hiding them from the table and stopping their
            interaction with the rest of the table, or placing the ball in hand
            if it is the cue ball.
              Inputs: None.
              Outputs: None."""
        for ball in self.balls:
            if ball.vel.x != 0 or ball.vel.y != 0:  # first checks if moving for efficiency - balls that haven't moved can't have been pocketed.
                for pocket in self.pockets:
                    if pocket.contains(ball.centre):
                        self.pocketed.append(ball)
                        if ball is self.cue_ball:
                            self.holding = ball
                            self.cue.remove_focus()
                        ball.can_show = False
                        ball.can_collide = False
                        ball.vel.set((0, 0))
                        break


class ReplayGame(OfflineGame):
    """ The ReplayGame class handles replaying a recorded game of pool. It lets
        users manipulate the replay and the simulation speed to be able to
        observe the replay of a game in detail."""

    def __init__(self, settings, screen, controls_obj, replay_info):
        """ The constructor for the ReplayGame class, creating the basic
            attributes for an 8-ball pool replay.
              Inputs: settings (a dictionary containing predetermined setting
            attribute values), screen (a pygame.Surface object which the game
            should be drawn to for user interaction), controls_obj (a
            ControlsObject object which contains the user's control state,
            which is updated by the main loop), and replay_info (a list (which
            contains dictionaries that detail the data of each move in the
            replay), describing the match information that is to be replayed.
            Generally loaded from a replay file first).
              Outputs: None."""
        super().__init__(settings, screen, controls_obj)
        self._init_overlay_elements()
        self._auto_mode = False
        self._auto_wait_time = 1.5
        self._speed = 1.0  # multiplier of the speed of the game
        self._lower_speed_limit = 0.5
        self._upper_speed_limit = 2.0
        self._speed_change_amount = 0.25  # step amount of speed multiplier
        self._original_fps = self.settings["fps"]
        self._end_cue_positioning_thread = False  # Boolean describing whether to end the thread controlling cue positioning.
        self._moving_cue = False
        self._cue_in_position = False
        self._last_update_time = time.time()
        self._replay_info = replay_info
        self._current_replay_index = 0
        self._ball_info = None
        self._moves = {"ball_info": self._place_balls,
                       "reset_state": self._reset_state,
                       "place_ball": self._place_ball,
                       "make_shot": self._make_shot,
                       "redo_match": self._redo,
                       "keep_break": self._keep,
                       "pass_turn": self._pass_turn}

    def _init_overlay_elements(self):
        """ This method creates all of the UI elements used in the replay
            viewer's overlay, and also positions them on the screen so that
            they can be clearly displayed to the user when drawn & controlled.
              Inputs: None.
              Outputs: None."""
        window_vector = Vector2D(self.settings["window_width"], 
                                 self.settings["window_height"])
        padding_size = window_vector / 100
        button_padding = Vector2D(self.settings["window_width"] / 350,
                                  self.settings["window_height"] / 250)

        self._back_button = Button(self._controls, "Back",
                                   font=self._message_font,
                                   target=self._prev_move, press_time=0.05,
                                   outline_padding=button_padding, 
                                   text_padding=button_padding)
        self._next_button = Button(self._controls, "Next",
                                   font=self._message_font, 
                                   target=self._next_move, press_time=0.05,
                                   outline_padding=button_padding,
                                   text_padding=button_padding)
        self._auto_button = Button(self._controls, "Auto Mode Off", 
                                   font=self._message_font, 
                                   target=self._change_auto_mode, 
                                   outline_padding=button_padding, 
                                   text_padding=button_padding)
        self._slow_down_button = Button(self._controls, "<<<",
                                        font=self._message_font, 
                                        target=self._slow_down,
                                        outline_padding=button_padding, 
                                        text_padding=button_padding)
        self._speed_label = Label(
            "1.00x speed", 
            font=self._message_font, 
            background_colour=self.settings["background_colour"],
            text_colour=(0, 0, 0), 
            outline_padding=button_padding, 
            text_padding=button_padding
        )
        self._speed_up_button = Button(self._controls, ">>>",
                                       font=self._message_font, target=self._speed_up,
                                       outline_padding=button_padding,
                                       text_padding=button_padding)
        self._hide_overlay_button = Button(self._controls, "Hide Overlay",
                                           font=self._message_font, 
                                           target=self._change_overlay_state,
                                           outline_padding=button_padding,
                                           text_padding=button_padding)
        
        # create containers to position the UI elements in groups on the screen
        self._top_middle_container = Container(3, 1, edge_padding=Vector2D(0,0), inner_padding=padding_size)
        self._top_middle_container.add_elements(self._slow_down_button, 
                                                self._speed_label,
                                                self._speed_up_button)
        self._bottom_middle_container = Container(3, 1, edge_padding=Vector2D(0,0), inner_padding=padding_size)
        self._bottom_middle_container.add_elements(self._back_button, 
                                                   self._next_button, 
                                                   self._auto_button)
        
        self._top_middle_container.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.5, 0.02), object_size=self._top_middle_container.size, scale_from=Vector2D(0.5, 0))
        self._bottom_middle_container.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.5, 0.98),object_size=self._bottom_middle_container.size, scale_from=Vector2D(0.5, 1))
        self._hide_overlay_button.pos = scale_position(Vector2D(0,0), window_vector, Vector2D(0.02, 0.98), object_size = self._hide_overlay_button.size, scale_from=Vector2D(0, 1))
        
        self._hideable_elements = [self._back_button, self._next_button, 
                                   self._auto_button, self._slow_down_button,
                                   self._speed_label, self._speed_up_button]

    def _redo(self):
        """ This method fully resets the state of the table so that the game
            can be restarted, generally because of an illegal break in which
            the 8-ball was pocketed in the replay. The table, balls and
            complete game state are all recreated, and a message is displayed
            to the user.
              Inputs: None.
              Outputs: None."""
        super()._redo()
        events.event_queue.clear()
        message_string = "The illegal break is being redone."
        message = events.MessageEvent(self.settings, self._screen,
                                      message_string, self._message_font,
                                      message_length=1.5)
        events.event_queue.enqueue(message)

    def _keep(self):
        """ This method is called when the player keeps the other player's
            illegal break, and hence allows the player to continue in a non-
            break state. In the context of a replay, all this does is display
            a message to the user explaining that at this point in the game,
            the illegal break was kept.
              Inputs: None.
              Outputs: None."""
        super()._keep()
        events.event_queue.clear()
        message_string = "The illegal break has been kept."
        message = events.MessageEvent(self.settings, self._screen, message_string,
                                      self._message_font, message_length=1.5)
        events.event_queue.enqueue(message)

    def _construct_table(self):
        """ This method creates the table object and other objects associated
            with the table such as the cue. It also works out the 'table shift
            factor' which is the amount everything should be shifted by to be
            drawn to the centre of the screen.
              Inputs: None.
              Outputs: None."""
        x_pos = (self.settings["window_width"] / self.settings["ppm"] - self.settings["table_length"]) / 2
        y_pos = (self.settings["window_height"] / self.settings["ppm"] - self.settings["table_width"]) / 2
        self._table_shift = Vector2D(x_pos, y_pos)
        self._table = ReplayTable(Vector2D(0, 0), self.settings)

    def _create_game(self):
        """ This method actually creates the scaling sizes and table based upon
            settings so that the replay can be viewed and simulated. The replay
            has already been started by this point per say but this actually
            allows users to see the table.
              Inputs: None.
              Outputs: None."""
        self._scale_values()
        self._text_font = pygame.font.SysFont(self.settings["message_font"], 32)
        self._event = None
        self._quitting = False
        self._construct_table()  # create table now that settings are loaded
        self.in_game = True

    def _process_move(self, move):
        """ This method processes the next move in the replay, loading the
            information about what happens in the move. This can include
            loading the match's initial settings, setting the starting player,
            updating the position of balls on the table, making a cue shot and
            placing a ball.
              Inputs: move (a dictionary containing information about the move
            that should be processed and loaded into the replay).
              Outputs: None."""
        print("REPLAY: {}".format(move["type"]))
        try:
            if move["type"] == "match_settings":
                config.update_nonvisual_settings(self.settings, move["data"])
                self.settings["save_replay"] = False  # we do not save a replay of a replay
                self.settings["auto_focus"] = False  # we do not want the cue to be unnecessarily focused during replay
                self._time = 1 / self.settings["fps"]
                self._create_game()
            elif move["type"] == "starting_player":
                self._player_turn = move["data"]
            elif move["type"] == "ball_info":
                self._ball_info = move["data"]
                self._table.cue.remove_focus()
                # remove current balls to avoid duplicates
                for ball in self._table.balls:
                    del ball
                self._table.balls = []
                self._table.cue_ball = None
                self._place_balls()
            elif "data" in move:
                holding_num = move["holding"]
                self._table.holding = self._find_ball(holding_num) if holding_num != 0 else None
                self._moves[move["type"]](move["data"])
            else:
                self._moves[move["type"]]()
        except:
            message = "Unable to process a move in the replay due to file modification / corruption.\nThe replay will now end."
            event = events.MessageEvent(self.settings, self._screen, message,
                                        self._message_font, message_length=5)
            events.event_queue.enqueue(event)
            self._quitting = True

    def _check_end_cue_rotation(self):
        """ This method checks whether to end the cue rotation early, i.e. when
            the user skips to the next move in the replay or goes back a move,
            and hence the cue rotation should be stopped. It then stops the cue
            moving if necessary.
              Inputs: None.
              Outputs: None."""
        if self._end_cue_positioning_thread:
            self._moving_cue = False
            self._table.cue.remove_focus()
            return True
        else:
            return False

    def _rotate_cue(self, angle, force):
        """ This method rotates and moves the cue so that it assumes a given
            angle and position. It does this in order to simulate the cue
            movement made by the player in the replay, which makes the replay
            seem like a much more more natural, human-played game. Intended to
            be threaded so that this is done simultaneously to other player
            controls, but does not necessarily have to be.
              Inputs: angle (a float or integer describing the angle in radians
            at which the cue is to be positioned), force (a float or integer
            describing the force in Newtons, which the cue hits the ball with,
            used to determine the offset that the cue should be moved to from
            the ball to make this shot possible).
              Outputs: None. """
        wait_time = 1 / self.settings["fps"]
        add_to_angle = self._table.cue.angle < angle
        add_to_offset = self._table.cue.force < force
        angle_rate = self.settings["cue_angle_rate"]
        while not self._end_cue_positioning_thread and \
          (add_to_angle and self._table.cue.angle < angle) or \
          (not add_to_angle and self._table.cue.angle > angle):
            if add_to_angle:
                self._table.cue.angle += angle_rate
            else:
                self._table.cue.angle -= angle_rate
            time.sleep(wait_time)  # move at a regular rate for smooth movement
            if self._check_end_cue_rotation():
                return
        offset_rate = self.settings["cue_offset_rate"]
        while not self._end_cue_positioning_thread and \
          (add_to_offset and self._table.cue.force < force) or \
          (not add_to_offset and self._table.cue.force > force):
            if add_to_offset:
                self._table.cue.change_offset(offset_rate)
            else:
                self._table.cue.change_offset(-offset_rate)
            time.sleep(wait_time)
            if self._check_end_cue_rotation():
                return
        if self._check_end_cue_rotation():
            return
        # sets to exact angle and force afterwards in case of slight errors due
        # to movement in steps. 
        self._table.cue.angle = angle
        self._table.cue.force = force
        self._cue_in_position = True

    def _find_ball(self, number):
        """ This method finds and returns the actuall ball object fom the list
            of balls on the table given the unique number of that ball. In the
            case that somehow there is multiple repeats (which should not
            typically happen), this will default to the first ball.
              Inputs: number (an integer (or None) that describes the number of
            the ball to be returned).
              Outputs: a Ball or DrawableBall object that has a number
            attribute which matches the input number."""
        for ball in self._table.balls:
            if ball.number == number:
                return ball

    def _make_shot(self, data):
        """ This function reproduces a shot that is made in the replay. It
            first focuses the cue on the correct ball, and then starts
            rotating the cue in position to make the shot.
              Inputs: data (a list containing 3 elements. The first element
            should either be an integer or more typically None, representing
            the number of the ball that was shot by the cue. The second element
            should be a float or integer describing the angle in radians at
            which the cue was positioned when the shot was made, and the third
            element should be a float or integer describing the force with
            which the cue should hit the ball).
              Outputs: None."""
        self._table.cue.set_focus(self._find_ball(data[0]))
        self._cue_in_position = False
        self._end_cue_positioning_thread = False
        self._moving_cue = True
        Thread(target=self._rotate_cue, args=data[1:]).start()

    def _set_positions(self, positions, holding):
        """ This method sets the positions of a set of the balls on the table.
            Any balls on the table that are not included within the list of
            balls are hidden so that only the ball data given is shown. This is
            generally used when skipping ahead to the next move.
              Inputs: positions (a list of tuples, where each tuple contains
            the position data for one ball. Each tuple within the list should
            contain two elements, the first being the number of the ball (an
            integer or None) and the second being a list, tuple or Vector2D
            object containing the position that the ball should be set to) and
            holding (an integer or None containing the number of the ball that
            is in hand. Unlike how None is used in the rest of the program to
            represent no number, here None represents no ball in hand whilst 0
            represents no number).
              Outputs: None (changes the positions and states of ball objects
            on the table)."""
        preset_numbers = [ball[0] for ball in positions]  # creates a list of numbers of all the balls that are currently in play
        for ball in self._table.balls:
            if ball.number in preset_numbers:
                ball.can_collide = True
                ball.can_show = True
            else:
                ball.vel = Vector2D(0, 0)
                ball.can_collide = False
                ball.can_show = False
                # We can't delete the balls but only hide them and disable
                # collision because the replay might need them later if
                # returning to a previous move.
        if self._table.holding is not None and self._table.holding.number not in preset_numbers:
            self._table.holding = None  # not strictly required - only cue ball should be held - but this creates a more robust solution.
        for ball_data in positions:
            ball = self._find_ball(ball_data[0])
            ball.vel = Vector2D(0, 0)
            ball.new_pos = Vector2D(ball_data[1])
            ball.update_position()
        self._table.holding = self._find_ball(holding) if holding!=0 else None
        if self._table.holding is not None:
            self._table.holding.can_collide = False
            if self._table.holding is self._table.cue.focus:
                self._table.cue.remove_focus()

    def _prev_move(self):
        """ This method goes back to the previous move in the replay. If a move
            is currently being simulated, then this button will return to the
            start of the move, using the positions stored in the current move
            of the replay. Otherwise, it loads and performs the previous move,
            if one exists.
              Inputs: None (uses loaded replay data that is saved upon
            instantiation).
              Outputs: None."""
        if self._current_replay_index > 0:
            if self._auto_mode:
                self._change_auto_mode()
            prev_move = self._replay_info[self._current_replay_index]
            print("REPLAY: rewinding move - " + str(prev_move["type"]))
            self._current_replay_index -= 1
            if self._moving_cue:
                self._moving_cue = False
                self._end_cue_positioning_thread = True
            to_remove = 0
            while "positions" not in prev_move:
                to_remove += 1
                # check if there are no more moves to regress. If there are not
                # then there is no need to do anything, just return.
                if self._current_replay_index - to_remove < 0:
                    return
                prev_move = self._replay_info[self._current_replay_index-to_remove]
            self._remove_pocketed_balls()
            self._set_positions(prev_move["positions"], prev_move["holding"])
            if prev_move["type"] == "place_ball":
                held_ball = self._find_ball(prev_move["holding"])
                held_ball.can_show = False

    def _progress_setting_moves(self):
        """ This method progresses through any non-significant moves of the
            replay that load the match settings, starting player and ball
            position information, or completely reset the simulation's state.
            This is automatically done at the start of a replay so that the
            user will not have to hit next 3 or so times before they can
            actually see the first significant move (shot) of the replay.
              Inputs: None.
              Outputs: None."""
        move = self._replay_info[self._current_replay_index]
        while move["type"] in ["match_settings", "ball_info", 
                               "reset_state", "starting_player"]:
            self._process_move(move)
            self._current_replay_index += 1
            if self._current_replay_index == len(self._replay_info):
                return
            move = self._replay_info[self._current_replay_index]

    def _next_move(self):
        """ This method progresses onto the next move in the replay. If a move
            is currently being simulated, then this button will skip to the end
            of the move, using the positions stored in the next move of the
            replay. Otherwise, it loads and performs the next move.
              Inputs: None (uses loaded replay data that is saved upon
            instantiation).
              Outputs: None."""
        self._current_replay_index += 1
        if self._current_replay_index < len(self._replay_info):
            if self._table.in_motion or self._moving_cue:  # if a move is currently being simulated, skip that move.
                if self._moving_cue:
                    self._moving_cue = False
                    self._end_cue_positioning_thread = True
                # retrieve position data by looking at future moves
                next_move = self._replay_info[self._current_replay_index]
                to_add = 0
                while "positions" not in next_move:
                    to_add += 1
                    if self._current_replay_index+to_add >= len(self._replay_info):
                        return  # no more replay moves to simulate so return.
                    next_move = self._replay_info[self._current_replay_index + to_add]
                self._remove_pocketed_balls()
                self._set_positions(next_move["positions"], 
                                    next_move["holding"])
                if next_move["type"] == "place_ball":  
                    # hides the held ball until next turn is started.
                    self._find_ball(next_move["holding"]).can_show = False
                self._current_replay_index -= 1  # wait until actually called again to do next move - this move is skipped but the next move is not started.
            else:
                # first skip any non-player moves (e.g. loading settings) until
                # the next significant move.
                self._progress_setting_moves()
                next_move = self._replay_info[self._current_replay_index]
                self._process_move(next_move)
        else:
            self._current_replay_index -= 1
            
    def _change_auto_mode(self):
        """ This method changes the mode of the replay viewer between automatic
            mode and manual mode. In automatic mode, the replay will
            automatically progress onto the next move after a small amount of
            time with no input, so that the replay can be watched like a video
            of the actual game. In automatic mode, the user must press the
            "next" button to continue.
              Inputs: None.
              Outputs: None."""
        self._auto_mode = not self._auto_mode
        self._auto_button.text = "Auto Mode On" if self._auto_mode else "Auto Mode Off"
        self._last_update_time = time.time()

    def _slow_down(self):
        """ This method slows down the speed of the simulation replay. It does
            this by simulating for the same periods of time (so that the
            physics simulation does not change) as the original game, but
            changes the frames per second of the replay viewer. It decreases
            the speed multiplicative factor by a set amount each time, down to
            a lower limit.
              Inputs: None.
              Outputs: None."""
        if self._speed > self._lower_speed_limit:
            self._speed -= self._speed_change_amount
            if self._speed < self._lower_speed_limit:
                self._speed = self._lower_speed_limit
            self.settings["fps"] = int(self._original_fps * self._speed)
            self._speed_label.text = "{:.2f}x speed".format(self._speed)

    def _speed_up(self):
        """ This method speeds up the speed of the simulation replay. It does
            this by simulating for the same periods of time (so that the
            physics simulation does not change) as the original game, but
            changes the frames per second of the replay viewer so that these
            updates are made more frequently. It increases the multiplicative
            speed factor by a set amount each time, up to an upper limit.
              Inputs: None.
              Outputs: None."""
        if self._speed < self._upper_speed_limit:
            self._speed += self._speed_change_amount
            if self._speed > self._upper_speed_limit:
                self._speed = self._upper_speed_limit
            self.settings["fps"] = int(self._original_fps * self._speed)
            self._speed_label.text = "{:.2f}x speed".format(self._speed)

    def _change_overlay_state(self):
        """ This method changes the state of the overlay, either hiding or
            revealing the overlay.
              Inputs: None.
              Outputs: None."""
        for element in self._hideable_elements:
            element.active = not element.active
        if self._hide_overlay_button.text == "Hide Overlay":
            self._hide_overlay_button.text = "Show Overlay"
        else:
            self._hide_overlay_button.text = "Hide Overlay"

    def __replay_load_failure(self):
        """ This method is called when the replay has failed to load because of
            data corruption. It displays a message to the user telling them
            that the replay could not be loaded using the event system, and
            flags the replay to be quit by the main update loop after the
            message has finished being displayed.
              Inputs: None.
              Outputs: None."""
        events.event_queue.clear()
        message = "Unable to load the replay at this time. \nThe replay data for this game has been corrupted."
        event = events.MessageEvent(self.settings, self._screen, message,
                                    self._message_font, message_length=5)
        events.event_queue.enqueue(event)
        self._quitting = True
        self.in_game = True  # we have to start the game so that the event
        # containing the error message can be displayed to the user.

    def setup_game(self):
        """ This method actually starts the replay, checking the validity of
            the loaded replay data and then if possible, progressing any
            initial non-significant moves that change the settings.
              Inputs: None.
              Outputs: None."""
        available_moves = list(self._moves.keys()) + ["match_settings", "starting_player"]
        nodata_moves = ["reset_state", "pass_turn", "redo_match", "keep_break"]
        for move in self._replay_info:
            move_keys = move.keys()
            if "type" in move_keys:
                if move["type"] not in available_moves or ("data" not in move_keys and move["type"] not in nodata_moves):
                    self.__replay_load_failure()
                    return
            else:
                self.__replay_load_failure()
                return
        self._progress_setting_moves()
        self._current_replay_index -= 1  # go back 1 move so that the replay
        # starts with the replay index on the first player-made move.

    def _place_balls(self):
        """ This method places ball objects on the table according to the
            settings specified by the replay, using the same numbers and
            colours as those stored in the replay. This places the racked
            coloured balls and 8-ball as well as the cue ball.
              Inputs: None (uses self._ball_info) so that the data does not
            have to be re-collected every time this move is returned to or the
            table is reset.
              Outputs: None."""
        balls_info = self._ball_info.copy()
        self._spotted_balls = []
        self._striped_balls = []
        y_offset = 0  # x- and y- offset values to create the racked triangular
        x_offset = 0  # pattern of balls on the table.
        racking_position = self._calculate_racking_position()
        for i in range(1, 6):
            for j in range(i):
                ball_info = balls_info.pop(0)  # by processing balls in the
                # same order they were saved, we can preserve every balls'
                # number, colour and position in the replay.
                shift_vector = Vector2D(x_offset, y_offset + self.settings["ball_radius"] * 2.2 * j)
                ball_pos = racking_position + shift_vector
                striped = True if ball_info[0] > 8 else False
                ball = DrawableBall(ball_pos, self.settings, ball_info[1],
                                    striped=striped, number=ball_info[0])
                if striped:
                    self._striped_balls.append(ball)
                elif ball_info[0] != 8:
                    self._spotted_balls.append(ball)
                self._table.add_ball(ball)
            y_offset -= self.settings["ball_radius"] * 1.1
            x_offset += self.settings["ball_radius"] * 2
        # The cue ball is then placed at a specific point on the table separate 
        # of the others.
        ball_pos = Vector2D(self._table.length / 3, self._table.width / 2)
        cue_ball = DrawableBall(ball_pos, self.settings, (255, 255, 255),
                                can_focus=True)
        self._table.add_ball(cue_ball)

    def _handle_controls(self):
        """ This method is responsible for handling all of the user input /
            controls, calling other functions that update the control handling.
            In the case of a replay, this simply updates the cue's positioning
            due to automatic replay movement (which changes the cue's
            attributes) and checks different UI element interactions.
              Inputs: None (uses user controls in ControlsObject set in the
            main loop).
              Outputs: None.""" 
        if self._table.cue.active:
            self._table.cue.update_positions()
            self._table.cue.update_ray()
        self._top_middle_container.do_controls()
        self._bottom_middle_container.do_controls()
        self._hide_overlay_button.do_controls()
        self._quit_button.do_controls()

    def _draw_overlay(self, surface):
        """ This method draws the overlay of the replay system to a given
            surface (screen) so that the user can see and interact with the
            loaded replay.
              Inputs: surface (a pygame.Surface object that the overlay will be
            drawn to).
              Outputs: None (draws and modifies the given surface object)."""
        self._top_middle_container.draw(surface)
        self._bottom_middle_container.draw(surface)
        self._hide_overlay_button.draw(surface)
        self._quit_button.draw(surface)

    def _draw_to_screen(self, surface):
        """ This method is responsible for drawing everything related to the
            replay on a surface so that the user can see the state of the
            replay and can interact with it.
              Inputs: surface (a pygame.Surface object that the simulation
            should be drawn to).
              Outputs: None (updates the surface object directly)."""
        self._table.draw(surface, shift=self._table_shift)
        self._draw_overlay(surface)

    def _remove_pocketed_balls(self):
        """ This method removes any balls that were pocketed during the replay
            from the list of each player's remaining balls and resets the
            table's temporary count variables.
              Inputs: None.
              Outputs: None (directly modifies self._p1_balls and
            self._p2_balls)."""
        for ball in self._table.pocketed:
            if ball in self._p1_balls:
                self._p1_balls.remove(ball)
            elif ball in self._p2_balls:
                self._p2_balls.remove(ball)
        self._table.reset_counts()

    def _check_cue_state(self):
        """ This method checks whether the cue has finished any required
            movements, and then makes a shot with the cue so that any shots
            made can properly be replayed.
              Inputs: None.
              Outputs: None."""
        if self._cue_in_position:
            self._moving_cue = False
            self._end_cue_positioning_thread = True
            self._table.cue.use()
            self._player_turn = self._other_turn
            self._cue_in_position = False  

    def update(self):
        """ This method updates the replay, simulating any move that is
            currently being processed, ensuring that everything is correctly
            drawn to the screen and that the user controls are managed
            correctly, and handling the events related to the game.
              Inputs: None.
              Outputs: None."""
        # check whether already quit before the game has started, i.e. the
        # replay data was corrupt and the replay should be exited.
        if self._table is None and self._quitting:
            self._handle_events()
            return not self.in_game
            
        self._check_cue_state()
        self._table.update(self._time)
        self._draw_to_screen(self._screen)
        self._handle_controls()

        if not self._table.in_motion and not self._quitting:  
            # applies any checks and manages automatic mode.
            if self._table.previously_in_motion:  # if shot just finished
                self._remove_pocketed_balls()
                self._last_update_time = time.time()
            if self._auto_mode and not self._moving_cue and (time.time() - self._last_update_time) > (self._auto_wait_time / self._speed):
                self._next_move()  # automatically progress to the next move
                self._last_update_time = time.time()

        # custom event handling
        if self._handle_events():
            self.settings["fps"] = self._original_fps
            return True
        else:
            return False


class PoolSim:
    """ The main loop of the client-side program responsible for creating and
        managing the GUI, Connection, timer (clock), and any created game
        objects. Regulates the entirity of the client-side program."""

    def __init__(self):
        """ The constructor for the PoolSim object, which creates the clock
            (timer), screen for the GUI, a control object and a list of several
            basic commands that can be used to communicate with a server.
              Inputs: None.
              Outputs: None."""
        pygame.init()
        pygame.font.init()
        self.settings = config.settings
        display_info_obj = pygame.display.Info()
        self.settings["screen_width"] = display_info_obj.current_w
        self.settings["screen_height"] = display_info_obj.current_h
        self.__update_window()  # updates the window display date
        self.__clock = pygame.time.Clock()
        self.__in_game = False
        self.__controls = ControlsObject({"mouse_pressed": [], 
                                          "control_events": [],
                                          "keys_pressed": [], 
                                          "mouse_position": []})
        self.__GUI = Menu_System(self.__screen, self.__update_window,
                                 self.__create_game,
                                 self.__connection_creation_interface,
                                 self.settings, self.__controls)
        self.host, self.port = retrieve_server_location()
        self.__connection = None
        self.connected = None
        self.__game = None
        self.__create_networked_game = False  # a flag describing whether to
        # create a networked game, used so that its instantiation is called
        # from the main thread and not a receiving thread, so that the game is
        # not started from the receiving thread (as this will lock the thread
        # until the game starts).
        self.commands = {
            "receive_lobbies": self.__GUI.load_lobby_data,
            "action_failure": self.__GUI.display_message,
            "login_success": self.__GUI.login_success,
            "join_success": self.__lobby_join_success,
            "display_message": self.__GUI.display_message,
            "account_creation_success": self.__GUI.account_creation_success,
            "request_lobby_password": self.__GUI.load_lobby_password_menu,
            "receive_user_statistics": self.__GUI.receive_statistics,
            "receive_leaderboard": self.__GUI.load_leaderboard_category
        }
        font_size = int((0.03 * self.settings["window_height"]) / 0.6876)
        self.__message_font = pygame.font.SysFont(self.settings["message_font"], font_size)

    def __create_game(self, game_state, *args, **kwargs):
        """ This method creates the simulation and starts it so that it can be
            updated in the main update loop and interacted with by the user. It
            either creates a OfflineGame, NetworkedGame, EditorGame or a 
            ReplayGame.
              Inputs: game_state (a string describing the game state that
            should be created, i.e. either "offline", "online", "editor" or
            "replay") and any extra data that the simulation objects might
            require in the form of *args and **kwargs.
              Outputs: None."""
        game_state = game_state.lower().strip()
        if game_state == "offline":
            self.__game = OfflineGame(self.settings, self.__screen, 
                                      self.__controls, *args, **kwargs)
        elif game_state == "online":
            self.__game = NetworkedGame(self.settings, self.__screen, 
                                        self.__controls, self.__connection,
                                        *args, **kwargs)
        elif game_state == "editor":
            self.__game = EditorGame(self.settings, self.__screen,
                                     self.__controls, *args, **kwargs)
        elif game_state == "replay":
            self.__game = ReplayGame(self.settings, self.__screen,
                                     self.__controls, *args, **kwargs)
        else:
            return
        self.__in_game = True
        self.__game.setup_game()

    def __create_connection(self):
        """ This method attempts to create a connection with the server hosted
            at the saved host ip address and port for online communication and
            interaction.
              Inputs: None (uses saved host and port settings).
              Outputs: None."""
        try:
            if self.__connection is not None:  
                # if a connection object already exists, then just reconnect.
                self.__connection.rebind(self.host, self.port)
                self.__connection.start()
            else:
                self.__connection = Connection(self.host, self.port)
                self.__connection.add_commands(self.commands)
                self.__connection.start()
                self.__GUI.add_connection(self.__connection)
            self.connected = True
        except:
            self.connected = False

    def __connection_creation_interface(self):
        """ This method displays the interface when (attempting to) create a
            connection with the server, communicating this with the user.
              Inputs: None.
              Outputs: None."""
        connecting_label = Label("Connecting to the server...", 
                                 font=self.__message_font)
        upper_pos = Vector2D(self.settings["window_width"], 
                             self.settings["window_height"])
        connecting_label.pos = scale_position(Vector2D(0, 0), upper_pos, Vector2D(0.5, 0.5), scale_from=Vector2D(0.5, 0.5), object_size=connecting_label.size)
        self.__screen.fill(self.settings["background_colour"])
        connecting_label.draw(self.__screen)
        pygame.display.flip()
        self.connected = None
        Thread(target=self.__create_connection).start()
        # temporarily overrides the main loop whilst connecting to server.
        while self.connected is None:  
            pygame.event.pump()
        # updates GUI object with connection status.
        self.__GUI.update_server_connection_status(self.connected)

    def __update_window(self):
        """ This method updates the size and type of the display window that is
            drawn, based upon the current settings that are stored within the
            settings configuration. This can create a fullscreen, windowed
            borderless or windowed (any size) window.
              Inputs: None (uses self.settings).
              Outputs: None."""
        if self.settings["display_mode"] == "fullscreen":
            self.settings["scale_width"], self.settings["scale_height"] = 1, 1
            self.settings["window_width"] = self.settings["screen_width"]
            self.settings["window_height"] = self.settings["screen_height"]
            self.__screen = pygame.display.set_mode((self.settings["window_width"], self.settings["window_height"]), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)  # | (pipe) denotes bitwise-OR
        elif self.settings["display_mode"] == "windowed borderless":
            self.settings["scale_width"], self.settings["scale_height"] = 1, 1
            self.settings["window_width"] = self.settings["screen_width"]
            self.settings["window_height"] = self.settings["screen_height"]
            os.environ['SDL_VIDEO_WINDOW_POS'] = "0, 0"
            self.__screen = pygame.display.set_mode((self.settings["window_width"], self.settings["window_height"]), pygame.NOFRAME)
        else:  # windowed mode
            self.settings["window_width"] = int(self.settings["screen_width"] * self.settings["scale_width"])
            self.settings["window_height"] = int(self.settings["screen_height"] * self.settings["scale_height"])
            os.environ['SDL_VIDEO_WINDOW_POS'] = "0, 30"
            self.__screen = pygame.display.set_mode((self.settings["window_width"], self.settings["window_height"]))
        pygame.display.set_caption(self.settings["caption"])

    def __save_match(self, move_history):
        """ This method saves a recorded offline or online game to a file in
            the replays directory, so that it can later be replayed and watched
            by the ReplayGame class.
              Inputs: move_history (a list of dictionaries describing all of
            the moves that occurred during the runtime of the game. Each
            dictionary represents one move and contains different data such as
            ball "positions", any ball that the player is "holding", the "type"
            of the move and any "data" related to the move).
              Outputs: None (creates and writes to a new file)."""
        if not os.path.isdir("replays"):  
            # if the replays directory does not exist, create it.
            print("Replay folder not found. Creating new folder.")
            os.mkdir("replays")
        if isinstance(self.__game, NetworkedGame):
            # check for NetworkedGame instance first because a NetworkedGame
            # would be considered an instance of OfflineGame. This is because
            # python's isinstance() function also consideres subclasses
            # an instance of the superclass (and the NetworkedGame class 
            # inherits from the OfflineGame class).
            game_state = "ONLINE"
        elif isinstance(self.__game, OfflineGame):
            game_state = "OFFLINE"
        else:
            game_state = "GENERIC"
        name_to_format = "%Y-%m-%d_%H-%M-%S_{}".format(game_state)
        replay_name = time.strftime(name_to_format, move_history[0])  # the first index of move_history is always the time that game started.
        with open("replays\\"+str(replay_name)+".json", "w+") as replay_file:
            json.dump(move_history[1:], replay_file)
            replay_file.close()

    def __lobby_join_success(self):
        """ This method is called when an online lobby is successfully
            connected to, clearing the GUI and indicating that the
            NetworkedGame object needs to be created.
              Inputs: None.
              Outputs: None."""
        self.__GUI.clear()
        self.__create_networked_game = True

    def __update_controls(self):
        """ This method updates the stored controls object with any current /
            new user input controls.
              Inputs: None.
              Outputs: None."""
        self.__controls["mouse_pressed"] = pygame.mouse.get_pressed()
        self.__controls["events"] = pygame.event.get()
        self.__controls["keys_pressed"] = pygame.key.get_pressed()
        self.__controls["mouse_position"] = Vector2D(pygame.mouse.get_pos())

    def __manage_connection_status(self):
        """ This method checks for and handles any errors that might have occurred
            with the connection to the server. If in an online game you are removed,
            and the error with the connection is communicated with the user.
              Inputs: None.
              Outputs: None."""
        if self.connected and not self.__connection.in_use and \
          self.__connection.error is not None:
            if self.__in_game and isinstance(self.__game, NetworkedGame):
                del self.__game
                self.__in_game = False
            self.__GUI.active = True
            self.__GUI.menu_stack.clear()
            self.__GUI.load_menu(self.__GUI.main_menu)
            self.__GUI.display_message(self.__connection.error)
            self.connected = False

    def __update(self):
        """ This method updates the main PoolSim loop, which in turn updates
            the entirity of the program. This manages the time management,
            drawing and controls of the GUI, any simulation / game that is
            currently in progress, pygame event handling and handling the
            ending of any simulations or games (and any relevant saving /
            loading that is required).
              Inputs: None.
              Outputs: a Boolean value detailing whether the program has
            finished and should quit and stop being updated, causing the
            program to finish execution. False means that the program should no
            longer be updated and should quit, True means it should continue
            updating and should not quit."""
        self.__clock.tick(self.settings["fps"])
        self.__screen.fill(self.settings["background_colour"])
        self.__update_controls()
        self.__manage_connection_status()
        
        for event in self.__controls["events"]:
            if event.type == pygame.QUIT:  # user quits the program
                return False

        if not self.__in_game:
            if self.__create_networked_game:
                self.__create_networked_game = False
                self.__create_game("online")
            has_quit = self.__GUI.update()
        else:
            has_quit = False
            self.__in_game = self.__game.in_game
            if self.__game.update():
                if self.settings["save_replay"]: # used for replays
                    self.__save_match(self.__game.saved_moves)
                del self.__game
                self.__GUI.active = True
                self.__GUI.menu_stack.clear()
                self.__GUI.load_menu(self.__GUI.main_menu)
                self.__in_game = False

        pygame.display.flip()  # updates the pygame output display to the user
        return not has_quit

    def start(self):
        """ This method starts the program's main loop so that the user can
            interact with the program. It continues looping and updating the
            program until certain conditions in the program cause self.__update
            to return False (e.g the quit button on the main menu has been
            pressed), at which point it stops.
              Inputs: None.
              Outputs: None."""
        while self.__update():
            continue


pool_sim = PoolSim()
pool_sim.start()
quit()
