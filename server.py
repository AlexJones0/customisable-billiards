""" server module
Functions:
 - retrieve_competitive_settings
Classes:
 - Connection
 - Lobby
 - Server
Description:
  The main program used to run the server, which will host online networked
games of 8-ball pool. Contains a server able to connect with a database,
updating and retrieving information to communication this information to users
that connect to the server. Features a robust lobby system in which users can
create their own personal lobbies with custom settings, names and passwords to
play with other users seperately online. Also contains the ability to handle
networked game simulation on the server side and user statistics and leaderboard
calculation functionality."""

# external imports
import socket
import json
import random
import time
import os
from threading import Thread
from math import sqrt, pi


# custom imports
import SQL
import encryption
from data import Queue, BlockedQueue
from vectors import Vector2D
from simulation import Table, Ball
from config import update_nonvisual_settings
from connections import retrieve_server_location


if not os.path.isdir("server_info"):
    print("server_info file directory not found. Resetting server information.")
    os.mkdir("server_info")


def retrieve_competitive_settings():
    """ This function retrieves the standard competitve setting information that
        is stored in the server_info/standard_settings.json file as a dictionary
        of settings. This is used to create competitive lobbies and determine if
        certain user created lobbies are competitive.
          Inputs: None.
          Outputs: the dictionary containing the competitive settings, with
        various string keys with float/ingeger value counterparts."""
    generic_settings = {"fps": 240, "table_length": 2.61, "table_width": 1.31,
                        "hole_factor": 1.92, "ball_radius": 0.0286,
                        "gravity": 9.80665, "time_of_cue_impact": 0.001,
                        "max_cue_force": 1200, "table_coeff_of_rest": 0.6,
                        "coeff_of_static_friction": 0.4,
                        "coeff_of_rolling_friction": 0.04, "ball_mass": 0.17,
                        "air_density": 1.225, "ball_coeff_of_drag": 0.45,
                        "ball_coeff_of_rest": 0.96, "limiting_vel": 0.005,
                        "starting_player": random.randint(1, 2)}
    if not os.path.isdir("server_info"):
        print("standard settings file not found. Creating new standard settings file.")
        os.mkdir("server_info")
        with open("server_info/standard_settings.json", "w+") as s_file:
            json.dump(generic_settings, s_file)
            s_file.close()
        settings = generic_settings
    else:
        try:
            with open("server_info/standard_settings.json", "r") as s_file:
                settings = json.loads(s_file.read())
                s_file.close()
        except (FileNotFoundError, ValueError, TypeError, json.decoder.JSONDecodeError) as e:
            print("Settings information is unreadable. Loading generic competitive settings and recreating standard settings file.")
            settings = generic_settings
            with open("server_info/standard_settings.json", "w") as s_file:
                json.dump(generic_settings, s_file)
                s_file.close()
            print("Settings information reset.")
    return settings


competitive_settings = retrieve_competitive_settings()


class Connection:
    """ This class creates and manages the network connection between the server
        itself and a singular client. It uses threaded queue data structures to
        send and receive and process information, and manage bidirectional
        communication with clients."""

    def __init__(self, connection, address, commands=None):
        """ The constructor for a Connection object - uses an existing
            connection that the server has made.
              Inputs: connection (a socket.connection object containing the
            connection between the server and a specific client), address (a
            tuple/list with two elements. The first is a string contaiing the
            IPv4 address of the client that is being connected with, and the
            second is an integer which is the port being communicated on by the
            client), and commands (an optional dictionary containing the
            commands that can be called by the client. Each key is a specific
            string and each value should be a method/function to be called).
              Outputs: None."""
        self.id = None
        self.username = None
        self.failed_logins = 0
        self.connection = connection
        self.address = address
        if commands is None:
            commands = {}
        commands["logout"] = self.logout
        commands["ready"] = self.__ready
        commands["receive_cue_data"] = self.__change_reception_state
        commands["disconnect"] = self.disconnect
        self.commands = commands
        self.send_queue = BlockedQueue()
        self.receive_queue = BlockedQueue()
        self.in_use = True
        self.can_delete = False
        self.waiting = False
        self.in_lobby = False
        self.can_start = False
        self.receive_cue_data = True
        self.updated_cue_data = False  # flag to represent whether the cue data
        # reception option has been updated or not. We then define a list of the
        # types of messages that are not important to receive/send
        self.__ignore_received = ["received",
                                  "update_cue_position",
                                  "update_server_cue_position",
                                  "disconnect"]
        print("CONNECTED TO BY {}:{}".format(*self.address))

    def __apply_error(self):
        """ This method is called when an exception has trigged (an error has
            occured), and it disables the connection, stopping it from
            attempting to make further communication.
              Inputs: None.
              Outputs: None."""
        self.in_use = False
        self.waiting = False
        self.send_queue.clear()
        self.can_delete = not self.in_lobby

    def __receive_data(self):
        """ This method is responsible for receiving data from the network
            buffer that was sent by the client, and recording it in the client's
            received queue (self.receive_queue) for use there.
              Inputs: None (a continuous while loop that receives data from
            network buffer).
              Outputs: None (any data received is added to self.receive_queue).
        """
        try:
            while self.in_use:
                # receives 1024 bytes of data at a time
                data = self.connection.recv(1024)
                if data is not None:
                    full_data = data.decode()
                    while not full_data.endswith("#"):
                        # keep receiving message until that message ends.
                        data = self.connection.recv(1024)
                        full_data += data.decode()
                    # split in case multiple messages received at once.
                    data = full_data.split("#")
                    for item in data[:-1]:
                        print('RECEIVED {} from {}:{}'.format(item,
                                                              *self.address))
                        request = json.loads(item)
                        if request["command"] == "received":
                            self.waiting = False
                        else:
                            self.receive_queue.enqueue(request)
        except ConnectionResetError:
            self.__apply_error()
        except:
            print("An error has occured in communication with client {}, connected to on {}:{}".format(self.id, *self.address))
            self.__apply_error()

    def __process_data(self):
        """ This method processes received data that is retrieved from the
            receive queue (self.receive_queue). This is kept seperate from
            receiving the data as it means that even if a process gets stuck or
            takes a long time, the __receive_data method can keep receiving data
            and adding it to the queue.
              Inputs: None.
              Outputs: None (calls other functions that may have differing
            effects)."""
        while self.in_use:
            request = self.receive_queue.dequeue()
            if request is not None:
                if request["command"] not in self.__ignore_received:
                    self.send_queue.enqueue({"command": "received"})
                if "args" in request.keys():
                    self.commands[request["command"]](*[self if arg == "connection" else arg for arg in request["args"]])
                else:
                    self.commands[request["command"]]()

    def __send_data(self):
        """ This method sends data that is in the send queue (self.send_queue)
            to the client, allowing bidirectional communication with each client
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
                    while self.waiting:
                        # wait for last sent data to be confirmed received
                        # this is necessary for accurate client simulations
                        time.sleep(0.05)
                        time_elapsed += 0.05
                        if time_elapsed > 5:
                            # if been waiting 5 seconds for response, resend.
                            if times_resent == 3:
                                self.__apply_error()
                                return
                            time_elapsed -= 5
                            times_resent += 1
                            # split up data into packets of 1024 b and sends
                            for i in range(0, len(prev_data) - 1, 1024):
                                encoded_str = str.encode(prev_data[i:i+1024])
                                self.connection.send(encoded_str)
                    if "args" in data.keys() and not isinstance(data["args"], 
                                                                (tuple, list)):
                        try:
                            data["args"] = tuple(data["args"])
                        except TypeError:
                            data["args"] = (data["args"],)
                    print('SENDING {} to {}:{}'.format(data, *self.address))
                    jsondata = json.dumps(data) + "#"
                    if data["command"] not in self.__ignore_received:
                        prev_data = jsondata
                        self.waiting = True
                    for i in range(0, len(jsondata)-1, 1024):
                        self.connection.send(str.encode(jsondata[i:i+1024]))
        except (ConnectionRefusedError, ConnectionResetError) as e:
            print("An error has occured in communication with client {}, connected to on {}:{}".format(self.id, *self.address))
            self.__apply_error()

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

    def logout(self):
        """ This method logs the client out of their account, updating the
            Connection's id, username and number of failed login attempts to
            reflect this.
              Inputs: None.
              Outputs: None."""
        self.id = None
        self.username = None
        self.failed_logins = 0

    def disconnect(self):
        """ This method disconnects the client connection, allowing them to exit
            without any errors.
              Inputs: None
              Outputs: None."""
        self.in_use = False
        self.send_queue.enqueue(None)
        self.receive_queue.enqueue(None)
    
    def __ready(self):
        """ This method modifies the 'can_start' attribute flag to reflect that
            the client/player has set up all needed settings and is ready to
            start the networked game.
              Inputs: None.
              Outputs: None."""
        self.can_start = True

    def __change_reception_state(self, receive_state):
        """ This method changes a player's cue data reception state. For example,
            if True, this signifies that the player wishes to receive cue
            positional data - if False, then the player does not wish for this
            data. Either way, it also updates the self.updated_cue_data flag to
            True to represent that this setting has been updated.
              Inputs: receive_state (a Boolean describing whether cue data
            should be sent to the client during a networked game or not).
              Outputs: None."""
        self.receive_cue_data = receive_state
        self.updated_cue_data = True

    def start(self):
        """ This method actually starts the Connection, meaning that it can
            begin to receive data from the client, process the data and send
            data to the client. This is done in 3 new seperate threads so all
            three can happen at once without blocking each other.
              Inputs: None.
              Outputs: None."""
        self.in_use = True
        Thread(target=self.__receive_data).start()
        Thread(target=self.__process_data).start()
        Thread(target=self.__send_data).start()
        

class Lobby:
    """ This class represents a lobby, which is a small instance of the pool
        game that can be created and joined by users. Each lobby manages an
        individual game, making it easy for users to choose to access or create
        a certain lobby and play the game independently of everybody else on the
        server."""

    def __init__(self, id_num, name="Pool Game", password=None, settings=None):
        """ The constructor for an individual Lobby instance. This loads basic
            informations such as the commands that will be available to users,
            the settings of the simulation used in the lobby, and many other
            required attributes.
              Inputs: id_num (an integer representing the unique identification
            number of the lobby, used by the server to distinguish between and
            refer to certain servers), name (an optional string which defaults
            to 'Pool Game' that details the name of the lobby), password (an
            optional string or None that describes the password required to
            access the lobby - None indicates no password required) and settings
            (an optional dictionary or None that contains the simulation
            settings to be used by the lobby. Leaving this blank will simply
            load the standard settings stored in
            server_info/standard_settings.json).
              Output: None."""
        self.id = id_num
        self.name = name
        self.password = password
        self.to_delete = False
        self.is_competitive = False
        self.commands = {"place_ball": self.__place_ball,
                         "hit_ball": self.__hit_ball,
                         "keep": self.__keep,
                         "redo": self.__redo,
                         "pass_turn": self.__pass_turn,
                         "finished_drawing": self.__finished_drawing,
                         "update_server_cue_position": self.__update_cue_state,
                         "quit": self.player_quit}
        self.players = []
        self.pending = []
        if settings is None:
            self.settings = competitive_settings
        else:
            self.settings = settings
        self.p1_stats = {"ShotsMade": 0, "BallPockets": 0,
                         "OpponentBallPockets": 0, "Fouls": 0}
        self.p2_stats = self.p1_stats.copy()
        self.victor = None
        self.finished = 0.0  # stores timestamp when the game finished
        self.started = 0.0  # stores timestamp when the game started
        self.checked = True
        self.do_check = False
        self.send_cue_data = True
        self.__cue_data = None
        self.__prev_cue_data = None
        cue_update_rate = 30
        self.__cue_update_time = 1 / cue_update_rate
        self.__cue_data_last_sent = 0.0  # timestamp when last cue data sent.
        self.__time = 1 / self.settings["fps"]

    def player_quit(self, player):
        """ This method updates the lobby to reflect a specified player (client
            connection) quitting. It tells the remaining player that the game
            has ended because the opponent has quit, and that they win. It then
            sets them as the victor and calls for a normal lobby ending.
              Inputs: player (a Connection object which contains the connection
            to the client / player who quit the game).
              Outputs: None."""
        victory_message = {"command": "end_game", "args": ("Your opponent has quit the game. Congratulations, you win!",)}
        # we must add the extra exclusion check for whether players are in lobby
        # for the case that players exit in quick succession - we don't want to
        # send an event to the other player who just quit.
        excluded = [player] + [p for p in self.players if not p.in_lobby]
        self.send_players(victory_message, exclude=excluded)
        if len(self.players) >= 2 or self.started > 1:
            victor = 1 if player is self.players[1] else 2
        else:
            victor = None  # nobody wins if they quit before the game started.
        self.end_game(victor)

    def __calculate_racking_position(self):
        """ This method calculates the position at which balls should start
            being racked from in order for them all to fit nicely on the table,
            using the current saved simulation settings.
              Inputs: None.
              Outputs: None."""
        racked_length = 9.4 * self.settings["ball_radius"]
        starting_width = self.__table.width / 2
        starting_length = self.__table.length / 4 * 3
        cutoff_length = self.__table.length / 20 * 19
        # ensure that all racked balls fit on the selected table size
        if racked_length + starting_length > cutoff_length:
            starting_length = cutoff_length - racked_length
        return Vector2D(starting_length, starting_width)
    
    def __construct_objects(self):
        """ This method constructs all of the objects that are used in the
            simulation of the pool game. This includes the table and balls. No
            shift factor is calculated for the table because the server does not
            need to draw it and hence does not need a table shift.
              Inputs: None.
              Outputs: a lsist of 16 three-element tuples, each of which
            represent a ball on the table. The first element is an integer or
            None representing the number of that ball (None = no number). The
            second is a tuple that contains 3 integers, describing the colour of
            that ball as an RGB value. The third is a two item tuple containing
            integers/floats that detail the position of the balls relative to
            the top left corner of the table as x- and y-coordinates."""
        self.__table = Table(Vector2D(0, 0), self.settings)
        y_offset, x_offset = 0, 0
        # create predefined colour & number information for generation of balls
        balls_info = [(1, (240, 240, 0)), (2, (0, 0, 255)), (3, (255, 0, 0)),
                      (4, (128, 0, 128)), (5, (255, 165, 0)), (6, (0, 255, 0)),
                      (7, (128, 0, 0))]
        balls_info = balls_info + [(num[0] + 8, num[1]) for num in balls_info]
        to_send = []
        self.__spotted_balls = []
        self.__striped_balls = []
        racking_position = self.__calculate_racking_position()
        for i in range(1, 6):
            for j in range(i):
                if i == 3 and j == 1:
                    ball_info = (8, (0, 0, 0))
                else:
                    ball_info = random.choice(balls_info)
                    balls_info.remove(ball_info)
                shift_vector = Vector2D(x_offset, y_offset + self.settings["ball_radius"] * 2.2 * j)
                ball_pos = racking_position + shift_vector
                striped = True if ball_info[0] > 8 else False
                ball = Ball(ball_pos, self.settings, striped=striped,
                            number=ball_info[0])
                to_send.append((ball_info[0], ball_info[1], tuple(ball_pos)))
                if striped:
                    self.__striped_balls.append(ball)
                elif ball_info[0] != 8:
                    self.__spotted_balls.append(ball)
                self.__table.add_ball(ball)
            y_offset -= self.settings["ball_radius"] * 1.1
            x_offset += self.settings["ball_radius"] * 2
        # the cue ball is then placed at a specific seperate point on the table.
        ball_pos = Vector2D(self.__table.length / 3, self.__table.width / 2)
        cue_ball = Ball(ball_pos, self.settings)
        self.__table.add_ball(cue_ball)
        return to_send

    def __reset_state(self):
        """ This method resets the state of the table in the lobby, starting the
            game from the beginning. It sets up variables related to the state
            of the table and player 1 and 2, but does not reset any existing
            player statistics counts.
              Inputs: None.
              Outputs: None."""
        self.__p1 = self.players[0]
        self.__p2 = self.players[1]
        self.__break = True
        self.__open = True
        self.__p1_balls = []
        self.__p2_balls = []
        self.__player_turn = self.settings["starting_player"]
        self.__p1_is_striped = None
        self.__check_state = False
        self.__can_shoot = True
        self.__can_pass_turn = False
        self.checked = True

    @property
    def __other_turn(self):
        """ A property that returns the turn of the player who it is not, i.e.
            an integer that is 1 or 2."""
        return 2 if self.__player_turn == 1 else 1

    def __create_game(self):
        """ This method actually creates the game, calling functions to create
            the table and reset the state of the game. It also tells all of the
            players to load the settings and create the game also, so that the
            game can be played on the network.
              Inputs: None.
              Outputs: None."""
        self.send_players({"command": "load_settings", 
                           "args": (self.settings,)})
        ball_info = self.__construct_objects()
        self.__reset_state()
        for player in self.players:
            player.send_queue.enqueue({"command": "create_game", "args": (ball_info, 1 if player is self.__p1 else 2)})

    def send_players(self, message, exclude=[]):
        """ This method sends a message to all of the players within the lobby,
            or all but a few. We exclude instead of include because in most 
            cases we will want to send all players the information.
              Inputs: message (any object that can be cast to a string, the 
            message to be sent to the server) and exclude (a list of Connection
            objects that the message should not be sent to.
              Outputs: None (directly sends messages to certain players)."""
        for player in self.players:
            if player not in exclude:
                player.send_queue.enqueue(message)

    def start(self):
        """ This method starts the lobby, waiting for players to connect and 
            load their chosen settings for use by the lobby. It checks if the 
            game being played is competitive or not, records the time at which 
            the game was started, and begins the updating process loop for the
            lobby.
              Inputs: None.
              Outputs: None."""
        self.started = 1  # temporarily sets started to 1 so the server knows not to start it again.
        while not (self.players[0].can_start and self.players[1].can_start):
            time.sleep(0.5) # wait until both players are able to start.

        # we next wait for 8 seconds for both players to update with cue data 
        # preferences. If there is no response, we just continue on as is.
        started_waiting = time.time()
        while not (self.players[0].updated_cue_data and \
                   self.players[1].updated_cue_data
                  ) and (time.time() - started_waiting < 8):
            time.sleep(0.5)
        
        if not (self.players[0].receive_cue_data or \
                self.players[1].receive_cue_data):
            self.send_cue_data = False
            self.send_players({"command": "change_cue_data_required",
                                  "args": (False, )})
        elif not self.players[0].receive_cue_data:
            self.players[1].send_queue.enqueue({"command": "change_cue_data_required", "args": (False, )})
        elif not self.players[1].receive_cue_data:
            self.players[0].send_queue.enqueue({"command": "change_cue_data_required", "args": (False, )})
        # clients & server have True as default so no else statement needed.
        self.is_competitive = self.password is None  # Lobbies must be public to be competitive
        if self.is_competitive: # if not identical to 3d.p., not competitive
            for key in self.settings:
                if key != "starting_player" and round(self.settings[key], 3) != round(competitive_settings[key], 3):
                    self.is_competitive = False 
                    break
        self.started = time.time()
        self.__create_game()
        self.__update()

    def add_player(self, player):
        """ This methods adds a new player to the lobby. It ensures that the
            lobby has a reference to the player's connection, gives the 
            player's connection new commands that can be used to interact with
            the lobby, and sets the player as being in a lobby.
              Inputs: player (a Connection object that contains the connection
            to the client that is being added to the lobby).
              Outputs: None."""
        self.players.append(player)
        player.add_commands(self.commands)
        player.in_lobby = True

    def __pass_turn(self):
        """ This method passes the turn of the current player in the lobby.
            This will swap the current turn, and will communicate with players
            both to pass the turn and to continue the next turn.
              Inputs: None.
              Outputs: None."""
        self.send_players({"command": "pass_turn"})
        self.send_players({"command": "start_next_turn",
                           "args": (False, self.__break, self.__open, True)})
        self.__player_turn = self.__other_turn

    def __place_ball(self, ball_pos):
        """ This method places the current ball in hand onto a given position
            on the table so that it can be hit and interacted with again. This
            also updates the players of the ball's new position and removes the
            held ball from the table object.
              Inputs: ball_pos (a tuple/list/vector2D object containing the 
            position that the held ball should be placed at as an x-y coord 
            where (0, 0) represents the middle of the top left pocket).
              Outputs: None."""
        self.__table.holding.new_pos.set(ball_pos)
        self.__table.holding.update_position()
        self.__table.holding.can_collide = True
        self.__table.holding = None
        self.send_players({"command": "place_ball", "args": (ball_pos,)})

    def __hit_ball(self, player, number, force, angle):
        """ This method hits a given ball in the table, with a certain force at
            a certain angle, allowing players to make a shot and progress the
            game. It also updates the "shots made" statistics for the players,
            communicates the ball hit with the players, and flags that checks 
            need to be carried out at the end of the turn.
              Inputs: player (a Connection object / None containing the 
            connection with the client that performed the shot. This is used so 
            we don't need to inform them about the hit again), number (an 
            integer or None containing the number of the ball that has been 
            hit, where None represents an unnumbered ball), force (a float / 
            integer representing the force in Newtons with which the ball has 
            been hit) and angle (a float/integer representing the angle in 
            radians at which the cue was positioned when hitting the ball).
              Outputs: None."""
        if player is self.__p1:
            self.p1_stats["ShotsMade"] += 1
        else:
            self.p2_stats["ShotsMade"] += 1
        for ball in self.__table.balls:
            if ball.number == number:
                ball.apply_force(self.settings["time_of_cue_impact"], force, 
                                 angle - pi)
                break
        self.send_players({"command": "hit_ball", 
                           "args": (number, force, angle)}, exclude=[player])
        self.checked = False
        self.do_check = True
        self.pending = self.players.copy()

    def __close_table(self, p1_is_striped):
        """ This method closes the table, meaning that the table is no longer
            open (anyone can hit any ball except the 8-ball) because someone
            has pocketed a coloured ball.
              Inputs: p1_is_striped (a Boolean value detailing whether player 1
            is striped or not as a result of closing the table (as if it is,
            player 2 is spotted, or if not, player 1 is spotted and player 2 is
            striped)).
              Outputs: None."""
        # we wait until later to actually close the table (self._open = False) 
        # to not interfere with other game rule checks
        self.__p1_is_striped = p1_is_striped
        if p1_is_striped:
            self.__p1_balls = self.__striped_balls
            self.__p2_balls = self.__spotted_balls
        else:
            self.__p1_balls = self.__spotted_balls
            self.__p2_balls = self.__striped_balls

    def __open_table_check(self):
        """ This method checks whether the table should close or not given that
            the table is open. It does this by applying the rules of 8-ball
            pool. If you hit the 8-ball first the table will always stay open,
            and if you pocket a coloured (non-eight or -cue ball) ball then the
            table is no longer open.
              Inputs: None (looks as the table's state attributes).
              Outputs: returns a Boolean value that describes whether the table
            should be closed or not."""
        if len(self.__table.hit) > 0 and \
          self.__table.hit[0] is self.__table.eight_ball:
            return False  # if 8-ball is hit first, no foul is incurred but the table stays open regardless of pockets
        for ball in self.__table.pocketed:
            if ball not in [self.__table.eight_ball, self.__table.cue_ball]:
                self.__close_table((ball.striped and self.__player_turn == 1) or (not ball.striped and self.__player_turn == 2))
                return True
        return False

    def __break_check(self):
        """ This method checks the rule implementation pertaining to 8-ball 
            pool breaks (the opening shot). Pocketing the 8-ball means the 
            break must be redone. If 4 unique balls do not hit the rail and
            there are no pockets, the break can be optionally redone (and if
            the cue ball is pocketed).
              Inputs: None (looks at the table's state attributes).
              Outputs: returns two Boolean values. The first describes whether
            or not a foul has been incurred and the foul penalty should be 
            applied, whereas the second describes whether or not the short must
            be redone (with no choice, you are forced to redo the break)."""
        foul = False
        force_redo = False
        if len(self.__table.pocketed) == 0 and \
          len(self.__table.rail_contacts) < 4:
            foul = True
        else:
            for ball in self.__table.pocketed:
                if ball is self.__table.eight_ball:
                    foul = True
                    force_redo = True
                elif ball is self.__table.cue_ball:
                    foul = True
        return foul, force_redo

    def __victory_check(self):
        """ This method checks the rule implementation pertaining to victory,
            determining whether a victory state has been achieved by either
            player. This happens because of an 8-ball being pocketed, either
            legally (the pocketing player's victory) or illegaly (the other 
            player's victory).
              Inputs: None (looks at the table's state attributes).
              Outputs: returns either None or an integer (of 1 or 2), detailing
            the victor of the game. If None, the win condition has not been met
            yet and nobody has won the game. If 1 or 2, then the player that
            matches this number is the one who has won the game (1 is player 1
            and 2 is player 2)."""
        for index, ball in enumerate(self.__table.pocketed):
            if ball is self.__table.eight_ball:
                player_balls = self.__p1_balls if self.__player_turn == 1 else self.__p2_balls
                # if open table or not potted all other balls or potted 8-ball on same turn as other last ball
                if index != 0 or self.__open or len(player_balls) != 0:
                    return self.__other_turn
                else:
                    return self.__player_turn

    def __foul_check(self):
        """ This method checks the rule implementation pertaining to whether a
            foul has been incurred. This happens when: no balls are hit by the
            cue ball, no balls contact the rail AND no balls are pocketed, a 
            non-player ball is hit first by the cue ball, or by pocketing the
            cue ball.
              Inputs: None (looks at the table's state attributes).
              Outputs: returns a Boolean value that describes whether a foul
            has been incurred, and foul reasons, which is a List giving the 
            reason(s) for the foul if one occured."""
        fouls = []
        if len(self.__table.hit) == 0:
            fouls.append("Fouled by failure to hit any ball.")
        player_balls = self.__p1_balls if self.__player_turn == 1 else self.__p2_balls
        if not self.__open and len(self.__table.hit) > 0 and self.__table.hit[0] not in player_balls:  # if first hit is not one of your own balls
            if self.__table.hit[0] == self.__table.eight_ball:
                if len(player_balls) != 0:
                    fouls.append("Fouled by hitting the 8-ball first when you still have balls left to pocket.")
            else:
                fouls.append("Fouled by hitting one of your opponent's balls first instead of your own.")
        if len(self.__table.pocketed) == 0 and \
          len(self.__table.rail_contacts) == 0:
            fouls.append("Fouled by failure to either pocket a ball or hit a numbered ball into a rail.")
        elif len(self.__table.pocketed) == 1 and \
          self.__table.pocketed[0] is self.__table.cue_ball:
            fouls.append("Fouled by failure to either pocket a ball or hit a numbered ball into a rail.")
        for ball in self.__table.pocketed:
            if ball is self.__table.cue_ball:
                # no need to handle 8-ball here as that is in __victory_check
                fouls.append("Fouled by pocketing the cue ball.")
                break
        return (len(fouls) > 0), fouls

    def __remove_pocketed_balls(self):
        """ This method removes all pocketed balls from the player's ball lists
            and simultaneously checks whether the current player can continue
            or not based on the pockets. If they pocketed one of their own
            balls then they are elligible to continue (provided that they
            haven't fouled), unless the table is open and they hit the 8-ball
            first (then they cannot continue no matter what happens). There is
            no penalty for pocketing your opponent's balls. This also records
            stats about ball and opponent ball pockets for both players.
              Inputs: None (looks at the table's state attributes).
              Outputs: returns a Boolean value that describes whether the 
            current player can continue their turn or not."""
        can_continue = False
        for ball in self.__table.pocketed:
            if ball in self.__p1_balls:
                # check if the player can continue their turn
                if not can_continue and self.__player_turn == 1:
                    can_continue = True
                if self.__player_turn == 1:
                    self.p1_stats["BallPockets"] += 1
                else:
                    self.p2_stats["OpponentBallPockets"] += 1
                self.__p1_balls.remove(ball)
            elif ball in self.__p2_balls:
                if not can_continue and self.__player_turn == 2:
                    can_continue = True
                if self.__player_turn == 2:
                    self.p2_stats["BallPockets"] += 1
                else:
                    self.p1_stats["OpponentBallPockets"] += 1
                self.__p2_balls.remove(ball)
        # If the 8-ball is hit first on an open table, the player cannot 
        # continue their turn regardless of pockets
        if self.__open and len(self.__table.hit) > 0 and \
          self.__table.hit[0] is self.__table.eight_ball:
            return False
        return can_continue

    def __redo(self, forced=False):
        """ A method that fully resets the state of the table so that the game
            can be restarted, generally because of an illegal break in which
            the 8-ball was pocketed. The table, balls and complete game state
            are all recreated, and the player who did not initially start gets
            to start this time.
              Inputs: None.
              Outputs: None."""
        if forced:
            self.settings["starting_player"] = self.__other_turn
        else:
            self.settings["starting_player"] = self.__player_turn
        self.__create_game()

    def __keep(self):
        """ This method is called when the player keeps the other player's
            illegal break, and hence allows the player to continue in a non-
            break state. It ends the break, allows the player to shoot and once
            again gets ready to check the state of the game after a shot has 
            been made, also informing other players to keep the break.
              Inputs: None.
              Outputs: None."""
        self.__break = False
        self.__can_shoot = True
        self.__check_state = True
        self.send_players({"command": "keep"})

    def __apply_foul_penalty(self):
        """ This method applies the foul penalty when a player fouls. It is 
            responsible for switching the turns and giving the opponent the cue
            ball in hand to place wherever they would like, removing the held
            ball from the table temporarily, and updating player foul stats.
              Inputs: None.
              Outputs: None."""
        if self.__player_turn == 1:
            self.p1_stats["Fouls"] += 1
        else:
            self.p2_stats["Fouls"] += 1
        self.__table.holding = self.__table.cue_ball
        self.__table.cue_ball.can_collide = False
        self.__table.cue_ball.vel = Vector2D(0, 0)
        self.__player_turn = self.__other_turn
        
    def end_game(self, victor):
        """ This method ends the lobby/game as a result of a win condition
            being met or somebody quitting the game. If a win condition was met
            or the quit was valid (after the game has started), a victor will
            be recorded and their id will be retrieved. The players will then 
            be removed from the lobby and allowed to join other lobbies again,
            and any players who quit will become deleteable by the server. The
            lobby is also flagged to delete.
              Inputs: victor (an integer of 1 or 2 or None describing the
            victor of the game. None means no victor, 1 means player 1 i.e. 
            self.players[0] and 2 means player 2 i.e. self.players[1]).
              Outputs: None."""
        self.finished = time.time()
        if victor is not None:
            self.victor = victor
            self.victor_id = self.players[0].id if victor == 1 else self.players[1].id
        for player in self.players:
            player.in_lobby = False
            if not player.in_use:  # i.e. if the player has quit the lobby but couldn't be deleted because the lobby needs to do cleanup first
                player.can_delete = True
            player.can_start = False
        self.to_delete = True

    def __apply_rules(self, stop_open, foul, foul_reasons, force_redo,
                      victor, can_continue):
        """ This method is an overarching, general method that applies all of
            the results of the rules, given that all of the checks have been
            performed. These changes are gathered together because they need to
            be implemented in the correct order to avoid affecting other checks. 
            First we apply any illegal breaks, then we look for victories, then
            continuing turns. We also apply statements to conditionally end the
            break and open states.
              Inputs: stop_open (a Boolean detailing whether the open table 
            should be ended according to the 8-ball pool rules), foul (a 
            Boolean detailing whether a foul has been incurred by the current 
            player), foul_reasons (a List detailing the reason(s) for the
            applied foul, if one exists), force_redo (a Boolean only relevant
            for the break checks which details whether the opposing player will
            be forced to redo the break because the current player pocketed the
            8-ball in the break), victor (either None or an integer that is 1
            or 2. This represents the player who has won the game - None means
            no victory has been reached, 1 or 2 means player 1 or 2), and
            can_continue (a Boolean representing whether the current player can
            continue their turn or not).
              Outputs: None."""
        can_shoot = True
        if self.__break and foul:
            if force_redo:
                self.send_players({"command": "force_redo_message"})
                self.__redo(forced=True)
                # if forcing redo, no need to start the next turn or check 
                # victory, fouls etc. so just return here
                return
            else:
                for player in self.players:
                    if player is self.__p1 and self.__player_turn == 2 or \
                      player is self.__p2 and self.__player_turn == 1:
                        player.send_queue.enqueue({"command": "redo_choice"})
                        break
                can_shoot = False
                self.__check_state = False
            self.__player_turn = self.__other_turn
            self.__can_pass_turn = False
        elif victor is not None:
            self.send_players({"command": "victory",
                               "args": (victor,)})
            self.end_game(victor)
            return  # return early so as not to start the next turn.
        elif foul:
            self.__can_pass_turn = False
            self.send_players({"command": "foul", "args": (foul_reasons,)})
            self.__apply_foul_penalty()
        elif can_continue:
            self.__can_pass_turn = True
        else:  # nothing happened, a legal break so no rules are implemented.
            self.__player_turn = self.__other_turn
            self.__can_pass_turn = False
        # act upon final changes now that all other rules have been applied.
        if self.__break and not foul:
            self.__break = False
        if stop_open:
            if not force_redo:
                self.send_players({"command": "close_table",
                                      "args": (self.__p1_is_striped,)})
            self.__open = False
        self.__can_shoot = can_shoot  # restricts ability to shoot, e.g. if a choice must be made.
        self.__table.reset_counts()
        state_information = (self.__can_pass_turn, self.__break, 
                             self.__open, self.__can_shoot)
        self.send_players({"command": "start_next_turn", 
                           "args": state_information})

    def __update_cue_state(self, new_data):
        """ This method updates the cue state, receiving new information about
            the cue's offset and its angle, so that it can later send this 
            information to other clients so that they can see the cue position.
              Inputs: new_data (a tuple containing two floats or integers. The
            first number should be the angle of the cue from the ball in 
            radians, and the second number is the current offset of the cue
            from the centre of its focused ball in metres).
              Outputs: None."""
        self.__cue_data = new_data

    def __check_game_state(self):
        """ This method checks the state of the game according to all of the
            predefined rules of 8-ball pool. It is an overarching method that
            calls all the individual rule check functions, including: open
            table checks, break checks, victory checks, foul checks and
            continuation checks. It also calls the function that applies these
            rules, and hence is a method that can be called after a player's
            shot has finished to generally apply all rules.
              Inputs: None.
              Outputs: None."""
        stop_open, force_redo = False, False
        foul_reasons, victor = None, None
        if self.__open:
            stop_open = self.__open_table_check()
        if self.__break:
            foul, force_redo = self.__break_check()
        else:
            victor = self.__victory_check()
            foul, foul_reasons = self.__foul_check()
        can_continue = self.__remove_pocketed_balls()
        self.checked = True
        self.__apply_rules(stop_open, foul, foul_reasons, 
                           force_redo, victor, can_continue)

    def __finished_drawing(self, player):
        """ This method is used to update the lobby with the knowledge that a
            client has finished drawing, removing them from the pending list of
            players who are being waited on.
              Inputs: connection (a Connection object storing the server's
            connection with the client who has finished drawing).
              Outputs: None."""
        self.pending.remove(player)

    def __send_cue_data(self, current_time=0.0):
        """ This method checks whether the server needs to send cue positional
            data to the clients, and if it does, then it sends this data.
              Inputs: current_time (an optional integer or float representing
            the current time as a timestamp in seconds, defaults to 0. If it is
            left as 0, the program will use the current timestamp).
              Outputs: None."""
        if current_time == 0:
            current_time = time.time()
        if not self.__table.in_motion and self.send_cue_data and \
          (current_time - self.__cue_data_last_sent > self.__cue_update_time):
            self.__cue_data_last_sent = current_time
            if self.__cue_data != self.__prev_cue_data:  # only send if changed
                self.__prev_cue_data = self.__cue_data
                player = self.__p2 if self.__player_turn == 1 else self.__p1
                if player.receive_cue_data:
                    player.send_queue.enqueue({"command": "update_cue_position", "args": (self.__cue_data,)})

    def __update(self):
        """ This method continually updates the Lobby whilst it is in use,
            simulating the table physics, communicating with users, applying
            any relevant rule checks and managing and sending cue data.
              Inputs: None.
              Outputs: None."""
        while self.started and not self.finished:
            if not self.checked:  #  only update table when a shot is made
                self.__table.update(self.__time)
            current_time = time.time()
            if not self.__table.in_motion:
                if not self.checked and self.do_check and \
                 len(self.pending) == 0:
                    # we use an attribute self.checked instead of comparing
                    # table.previously_in_motion like on the client side
                    # because we additionally have to wait for all users to 
                    # finish simulating the shot first.
                    self.__check_game_state()
                    self.do_check = False
                self.__send_cue_data(current_time=current_time)
                time.sleep(self.__cue_update_time)


class Server:
    """ The server object can be used by clients to play managed, online,
        networked games. The server manages connections with clients as well as
        user accounts, performs lobby management and deletion, and interacts
        with a locally stored database to process different game and user data,
        and in some cases also serves as an intermediary between clients and
        the database."""

    def __init__(self, host, port, max_connections=16):
        """ The constructor for a Server. Stores basic information about the
            server such as its host, port and maximum connections. It also
            generates empty lists for storing client connections, lobbies and
            competitive lobbies. It automatically creates 3 competitive lobbies
            so that there are always 3 present, and also creates a list of
            commands that connecting clients can use to interact with the
            server. Finally it calls for the loading of rank information for
            use in game statistics.
              Inputs: host (a string containing the IPv4 address that the
            server is being hosted on), and port (an integer between 0 and
            65535 representing the port at which the server should be hosted
            on), max_connections (an integer that defaults to 16, describing
            the maximum number of connected clients that the server can host).
              Outputs: None."""
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.competitive_settings = competitive_settings
        self.connections = []
        self.lobbies = []
        self.competitive_lobbies = []
        for i in range(3):
            self.competitive_lobbies.append(
                Lobby(i, 
                      name="Competitive Game", 
                      settings=self.competitive_settings
                )
            )
        self.lobbies += self.competitive_lobbies
        self.current_lobby_id = 3  # starts at 3 because 3 competitive lobbies have already been made.
        self.in_use = True
        self.database_queue = BlockedQueue()
        self.processed_queue = Queue()
        self.database = None
        self.current_request_id = 0
        self.commands = {
            "create_lobby": self.__create_new_lobby,
            "retrieve_lobbies": self.__retrieve_lobbies,
            "join_lobby": self.__join_existing_lobby,
            "login": self.__login_attempt,
            "create_new_account": self.__create_new_account,
            "retrieve_user_statistics": self.__retrieve_user_statistics,
            "request_leaderboard": self.__retrieve_leaderboard,
            "change_password": self.__change_password
        }
        self.__ranks = {}
        self.__retrieve_ranks()

    def __retrieve_ranks(self):
        """ This method retrives information about competitive ranks stored
            within the server_info/ranks.txt text file. It attempts to read the
            file, and in the case that it exists and it is valid, will 
            successfully parse each line for the rank name, lower bound and
            upper bound, where these boundaries are floats (0 <= bound <= 1)
            representing the win rate over the last 50 games required to be in
            the boundary of that rank. In case of overlap, the rank that comes
            first in the file will be used.
              Inputs: None (checks for and reads from server_info/ranks.txt).
              Outputs: None (modifies the self.__ranks attribute)."""
        if not os.path.exists("server_info/ranks.txt"):
            print("server_info/ranks.txt was not found. Please add the rank information.\nNo ranks have been loaded.")
        else:
            try:
                with open("server_info/ranks.txt", "r") as rank_file:
                    for line in rank_file:
                        rank_info = line.split(":")
                        rank_info = [rank_info[0]] + rank_info[1].strip().split("-")
                        self.__ranks[rank_info[0]] = tuple([float(num) for num in rank_info[1:]])
                    rank_file.close()
                    print("Rank information has been successfully loaded:")
            except (TypeError, ValueError, IndexError) as e:
                print("The rank information file is corrupted and cannot be correctly loaded.")
                print("Please ensure that the file is in a valid format. {} ranks have been loaded.".format(len(self.__ranks)))
        print(self.__ranks)

    def __await_connections(self):
        """ This function keeps listening for new connections by clients to the
            server, and creating Connection objects and adding them to the
            server lists when they join so that they can interact with and be
            managed by the server. Because this will make an infinite loop
            whilst the server is in use, this is designed to be threaded.
              Inputs: None.
              Outputs: None."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                print("STARTING SERVER ON {}:{}".format(self.host, self.port))
                s.bind((self.host, self.port))
                s.listen(self.max_connections)
                print("WAITING FOR CONNECTIONS...")
            except OSError as e:
                if not str(e).startswith("[WinError 10048]"):
                    print("UNABLE TO START SERVER AS THE HOST ADDRESS STORED IN THE server_info/conn_info.txt FILE IS INCORRECT. CLOSING SERVER IN 8 SECONDS...")
                    time.sleep(8)
                    self.in_use = False  # disables server
                    self.database_queue.enqueue(None)  # update database queue so that it checks self.in_use and sees that operation has ended.
                    return
                print("UNABLE TO START SERVER AS PORT {} IS IN USE. ATTEMPTING ANOTHER PORT.".format(self.port))
                self.port += 1
                if self.port > 65535:
                    self.port = 10001  # avoids first 10000 ports
                Thread(target=self.__await_connections).start() 
                return  # starts another thread within this thread but then 
                # returns to break the current thread, in effect creating a 
                # brand new thread to await connections on.
            while self.in_use:
                if len(self.connections) == self.max_connections:
                    time.sleep(2.5)  # don't listen for new connections when server is at max capacity    
                else:
                    if len(self.connections) != 0:
                        print("AWAITING FURTHER CONNECTIONS...")
                    connection, address = s.accept()
                    try:
                        connection = Connection(connection, address, 
                                                self.commands.copy())
                        connection.start()
                        self.connections.append(connection)
                    except:
                        print("FAILED CONNECTION MADE FROM {}:{}".format(*address))

    def __process_database_requests(self):
        """ This method processes requests made for database queries. It reads
            from the server's database queue, which other threads may add 
            requests to in order to retrieve information. This method is 
            designed to be threaded as it uses an infinte while loop whilst in
            use so it can process requests as other processes occur. Adds any 
            results from the SQL database queries to a "processed queue" with
            the same id that they were submitted with so that other parts of
            the program can retrieve this information.
              Inputs: None (reads self.database_queue).
              Outputs: None."""
        self.database = SQL.Database("server_info/UserInformation")
        if not self.database.exists:
            print("Database not found. Creating new database.")
            self.__create_database_tables()
        else:
            # check for any tables missing in the database.
            db_tables = self.database.query("SELECT name FROM sqlite_master")
            db_tables = [info[0] for info in db_tables]
            missing_tables = [table for table in ["Users", "UserCredentials", "Games", "GameUsers"] if table not in db_tables]
            if len(missing_tables) != 0:
                print("The database has been found but is corrupted. Recreating the database.")
                # specify each table by name in case of other restricted tables
                if "UserCredentials" in db_tables: 
                    self.database.query("DROP TABLE UserCredentials;")
                if "GameUsers" in db_tables: 
                    self.database.query("DROP TABLE GameUsers;")
                if "Games" in db_tables: 
                    self.database.query("DROP TABLE Games;")
                if "Users" in db_tables: 
                    self.database.query("DROP TABLE Users;")
                self.__create_database_tables()

        while self.in_use:
            request = self.database_queue.dequeue()
            if request is not None:
                # requests are in the format: 
                # (receive_data, request_id, request, parameters)
                # where receive_data is the data to receive and request_id is a
                # unique numeric identifier.
                f_request = request[2].split("\n")
                f_request = " ".join([line.strip() for line in f_request])
                if request[3] is not None:
                    f_request = f_request.replace("?", "{}")
                    parameters = ["\"{}\"".format(parameter) if isinstance(parameter, str) else parameter for parameter in request[3]]
                    f_request = f_request.format(*parameters)
                print('QUERYING THE DATABASE: {}'.format(f_request))
                requested_data = self.database.query(*request[2:])
                if request[0] == "lastrowid":  # special case for querying the ID (primary key) of the last row accessed.
                    self.processed_queue.enqueue([request[1], 
                                                  self.database.lastrowid])
                elif request[0]:
                    self.processed_queue.enqueue([request[1]] + requested_data)
                if not request[2].upper().startswith("SELECT"):
                    self.database.commit_changes()  # commit changes if needed.
                
    def __add_db_request(self, request, parameters=None, receive=True):
        """ This method is responsible for adding a request to the database
            queue and receiving the result. Given an SQL query, and optional
            parameters for the SQL query as well as a reciece parameter, the 
            request is added to the database and required information is
            returned when the request has been processed.
              Inputs: request (a string containing the SQL query to be given to
            the server. Any values that are to be replaced by the optional
            given parameters should be marked with a '?'), parameters (an
            optional list/tuple or None containing any parameters that should
            be executed alongside the SQL to fill in any question marks in the
            SQL) and receive (either a Boolean describing whether to receive
            data or not or a string containing an optional argument to be used
            by the request, e.g. "lastrowid").
              Outputs: returns variable data because this is the result of the
            database query. Typically a tuple or multi-dimensional tuple
            containing the data that has been selected from the table, or an
            integer if returning the last row's id, or None if no information
            is being returned."""
        if parameters is not None:
            if not isinstance(parameters, (tuple, list)):
                parameters = (str(parameters),)
                # if just a single parameter, put into a tuple format that can
                # be iterated over by the database's execute functionality.
            elif isinstance(parameters, list):
                parameters = tuple(parameters)
        request_id = self.current_request_id
        self.current_request_id += 1
        self.database_queue.enqueue((receive, request_id, request, parameters))
        if receive == "lastrowid" or receive:
            found = False
            while not found:
                data = self.processed_queue.peek()
                if data is not None and data[0] == request_id:
                    self.processed_queue.remove()
                    to_send = data[1:]
                    if len(to_send) == 1:
                        return to_send[0]  # if just a tuple containing one
                        # item, just return the item alone.
                    else:
                        return to_send
                else:
                    time.sleep(0.1)  # wait for the request to be processed.
        
    def __create_database_tables(self):
        """ This method creates the networked database from nothing in the case
            that for some reason the database does not yet exist. This means
            that even if the database is lost for some reason, information will
            still be recorded which can later be merged with an actual database
            for example. This creates the four tables (Users, UserCredentials, 
            Games, and GameUsers specifically).
              Inputs: None.
              Outputs: None (creates new database tables in database file)."""
        self.database.query("""
            CREATE TABLE Users (
                UserID INTEGER NOT NULL, 
                Username TEXT NOT NULL, 
                Email TEXT, 
                TimeCreated REAL, 
                LastLogIn REAL,
                GamesPlayed INTEGER, 
                Victories INTEGER, 
                CompetitivePlayed INTEGER,
                PRIMARY KEY (UserID)
            )"""
        )
        self.database.query("""
            CREATE TABLE UserCredentials (
                UserID INTEGER NOT NULL, 
                Password TEXT NOT NULL,
                FOREIGN KEY (UserID) REFERENCES Users (UserID) 
                ON UPDATE CASCADE ON DELETE RESTRICT
            )
        """
        )
        self.database.query("""
            CREATE TABLE Games (
                GameID INTEGER NOT NULL, 
                TimeStarted REAL,
                TimeCompleted REAL, 
                IsCompetitive BOOLEAN NOT NULL, 
                Victor INTEGER NOT NULL,
                PRIMARY KEY (GameID),
                FOREIGN KEY (Victor) REFERENCES Users (UserID)
            )"""
        )
        self.database.query("""
            CREATE TABLE GameUsers (
                GameID INTEGER NOT NULL, 
                UserID INTEGER NOT NULL, 
                ShotsMade INTEGER, 
                BallPockets INTEGER, 
                OpponentBallPockets INTEGER, 
                Fouls INTEGER,
                FOREIGN KEY (GameID) REFERENCES Games (GameID)
                ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY (UserID) REFERENCES Users (UserID)
                ON UPDATE CASCADE ON DELETE RESTRICT
            )"""
        )

    def __get_secured_password(self, password):
        """ This method is used to make a password more secure so that it can
            be safely stored in the database. A salt is generated (to prevent 
            rainbow tables and dictionary attacks) and the password is hashed
            with the salt. The hashed password is then also encrypted to make
            the hash unreadable. This adds two layers of security to the 
            password, making user account security much greater.
              Inputs: password (a string containing the plaintext password that
            is to be made more secure for database entry).
              Outputs: a string containing the encrypted hash value of the 
            hashed password."""
        hashed_pass = encryption.hash_text(password)
        secured_pass = encryption.encrypt(r"$-£Vs+i^)]XIUzocb{%Al¬tG=hU_QzG0Lk)rm-oC2Dyccj?¬yM1RMcBx_vX)&l;yggpANSd@)¬L>$]{\qEwN!W<}03F£I\CV>.Ckh£7X`)%-_NwWs:)*:^Siyn8o£+bDkm3e(V.B0wAV*6GP5ktdrTE_72jZO\KTk,5}U)£cPj$m:M4M`{2)r.q=ad[C8@£85Iq4Yp@p/J1s0?9fEkp=rX<gd&pv41V|f5?:¬KdRC(n.)oyj6ePoI<!93t)4tgy@fu^doz2AVK97~J=[6&/h)v)F:-S29_/y==)~HGmJKv;FFBO_Z9.pc0X>J9:I9GgDvGWD21,[ppF\lO<3-8wZlo7>w¬Ka@-Od3}|>C7cHkFW58O=5y*%`7;&8¬IV|xbfOehC¬=e^-%p+A^F1ABoTFM1fxr8<SD4iCcP\pFG~\ZH£|0?q2c\ybv|/,PU:JV/r,Zu_$r]2~ChJ&xjvQe7uC8dP*jO>,<5kHM>x09pFI+yLN@uITu@dbLR)|\¬\^I+fi",
                                          hashed_pass)
        return secured_pass

    def __create_new_account(self, player, username, password, email):
        """ This method creates a new user account, first checking that there
            are no existing users with the same username or email. If the user
            is unique, then this creates the new user's information within the
            networked database, and communicates with the user that account
            creation was a success. If not, then it communicates the failure
            with the user.
              Inputs: player (the Connection object with the client that is
            creating the connection), username (a string containing the
            encrypted username information that has been sent across the
            network), password (a string containing the encrypted password
            information that has been sent across the network), email (a string
            containing the encrypted email information that has been sent
            across the network). All 3 inputs are encrypted seperately so that
            even if one is compromised, the user account is still as secure as
            possible.
              Outputs: None."""
        username = encryption.decrypt(r"CP-]m@f)qN]¬xDLv74}{:Ba¬9gGhpfO7{8-2^-i1t?_DG*hk%jon6+4/_?1CGaSLzsW[vIR^9_>,U8SuN?=p0ry&-$+>nkN\f|VPPr0=p|$t<N£<^g{^%pB3)0~[^~*Y9qU$[[[K,SFpw,ffRdRW7jtQ,pw^KRA<£Jj0/=M}2W^UEA-|rm*AmCOM¬{*/@LFReOixVqHdY64*3DTJT:0sv%$F<({J*1CU^C00-LOKOWaiIF2nK[$9GQOZGdfbZ&{hel1/C<|NPdXt!£EpkNL&-NCgFy¬$JGflSh!%N$~K,|+3!c?GI)£TX{\$uVB]jrBJ!AL^L3a<}RM]v*80_Ox]1f%5r4d+}G@=Oj<(n?|mi(CiXv{9YSpKb^gKr5Q|A0|<:ICPNpD??gV++(/.r7V=X>DL]K[~d`TN.%Y)£1w_|_n?2oyA(?gQ`(Fa`Ha]tx,=;=yj]ZT|£o;&(E:_+tK6)[$dK5xW6=>T`l\xS@R$YL.{P£=?dRmJqR,c6E_,h,)A",
                                      username)
        password = encryption.decrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                      password)
        email = encryption.decrypt(r"4_yx7JN|qxHN<8W*lr2)R|l{g¬AO!3<~\NZh7tB(W[,sYJzvT?4[{JT{o$oShLw4ALFx~|s!BrCpfva|o!JMx7vHnIZ<NZ%£Wk.?3aaC¬};wwbE£}F`Z{j1{wSk£C£uHw&z,|6u~%=*!*2gxG[iSl&^u3F]5GAJ2/1N2/|V&d%/G2MN`U)[mmb1£^~[N+`iy:AmHy+<R_IVGG@H*d(<ZQ[B`7tI¬[s<Tpis!prd?T8pOz6c£A£<jV)tc)WsJ¬:z%I/WjAan?N{V|?:YdMP¬(40qiOby¬Y)4v}`t[>HGl3I;@YVO4^<-Wnbx<p1]@e{Q4rhl|xCD77k=iYq!Kdt;]h>^[{{W4GOfMN1Qj(M>v*rl-}vErJSJt$£o4PgamKLOwIpF/fr7/A<4Qp¬M&eI%mUvfc;~$\l£Nsr=Z8lZMg(WB7g/i>Q3y£!9c9]C46$DTe&d{eaOIp[x]P,+8)]_TYmTo(p)2}P5N1U,PhHFeRf}(Py&&_h6<iX@zk;1v&Xh>3",
                                   email)

        matching_users = self.__add_db_request("SELECT UserID FROM Users WHERE Username=? LIMIT 1", username)
        if len(matching_users) != 0:
            error = "A user with that username already exists"
            player.send_queue.enqueue({"command": "action_failure",
                                       "args": (error,)})
            return
        matching_users = self.__add_db_request("SELECT UserID FROM Users WHERE Email=? LIMIT 1", email)
        if len(matching_users) != 0:
            error = "A user with that email already exists."
            player.send_queue.enqueue({"command": "action_failure",
                                       "args": (error,)})
            return

        # create the user and retrieve their user ID.
        user_id = self.__add_db_request("""
            INSERT INTO Users (
                Username, 
                Email, 
                TimeCreated, 
                GamesPlayed, 
                Victories, 
                CompetitivePlayed
            ) 
            VALUES (?, ?, ?, 0, 0, 0)""", 
            (username, email, time.time()), receive="lastrowid")
        
        # hashes and encrypts password for safer storage in database
        secure_password = self.__get_secured_password(password)
        self.__add_db_request("INSERT INTO UserCredentials (UserID, Password) VALUES (?, ?)", 
                              (user_id, secure_password), receive=False)
        player.send_queue.enqueue({"command": "account_creation_success"})

    def __check_user_online(self, user_id):
        """ This method checks whether any currently online users have a 
            matching ID to a specified ID. Typically used to check whether a
            user account is already logged into the server or not.
              Inputs: user_id (an integer containing a user's unique UserID to
            be searched for).
              Outputs: a Boolean value describing whether the user is online or
            not (True = online, False = Not)."""
        for connection in self.connections:
            if connection.id == user_id:
                return True
        return False

    def __login_attempt(self, user, username, password):
        """ This method attempts to log the user in, checking the validity of
            their entered username and password. It first searches for whether
            the user exists, and if it does, retrieves the hashed password
            value for comparison with the sent password. It tracks failed
            logins and does not allow a user with 5 failed logins to continue
            attempting to log in. If successful, it updates the user's
            Connection with their user information.
              Inputs: user (the Connection object storing the connection with
            the client that is logging in), username (a string containing the
            input username that has been encrypted), and password (a string
            containing the input password that has been encrypted).
              Outputs: None (logs in user if correct & communicates result with
            the client)."""
        if user.failed_logins >= 5:
            error = "Exceeded maximum number of login attempts. Please try again later."
            user.send_queue.enqueue({"command": "action_failure", 
                                     "args": (error,)})
            return
        username = encryption.decrypt(r"CP-]m@f)qN]¬xDLv74}{:Ba¬9gGhpfO7{8-2^-i1t?_DG*hk%jon6+4/_?1CGaSLzsW[vIR^9_>,U8SuN?=p0ry&-$+>nkN\f|VPPr0=p|$t<N£<^g{^%pB3)0~[^~*Y9qU$[[[K,SFpw,ffRdRW7jtQ,pw^KRA<£Jj0/=M}2W^UEA-|rm*AmCOM¬{*/@LFReOixVqHdY64*3DTJT:0sv%$F<({J*1CU^C00-LOKOWaiIF2nK[$9GQOZGdfbZ&{hel1/C<|NPdXt!£EpkNL&-NCgFy¬$JGflSh!%N$~K,|+3!c?GI)£TX{\$uVB]jrBJ!AL^L3a<}RM]v*80_Ox]1f%5r4d+}G@=Oj<(n?|mi(CiXv{9YSpKb^gKr5Q|A0|<:ICPNpD??gV++(/.r7V=X>DL]K[~d`TN.%Y)£1w_|_n?2oyA(?gQ`(Fa`Ha]tx,=;=yj]ZT|£o;&(E:_+tK6)[$dK5xW6=>T`l\xS@R$YL.{P£=?dRmJqR,c6E_,h,)A",
                                      username)
        password = encryption.decrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                      password)
        info = self.__add_db_request("""
            SELECT Users.UserID, UserCredentials.Password
            FROM Users, UserCredentials
            WHERE Users.Username=? AND Users.UserID=UserCredentials.UserID""",
            username)
        if len(info) == 0:
            error = "Login information is invalid."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            return
        if isinstance(info, tuple):
            user_info = info
        else:
            user_info = info[0]
        user_id = user_info[0]
        user_password = user_info[1]
        enc_key = r"$-£Vs+i^)]XIUzocb{%Al¬tG=hU_QzG0Lk)rm-oC2Dyccj?¬yM1RMcBx_vX)&l;yggpANSd@)¬L>$]{\qEwN!W<}03F£I\CV>.Ckh£7X`)%-_NwWs:)*:^Siyn8o£+bDkm3e(V.B0wAV*6GP5ktdrTE_72jZO\KTk,5}U)£cPj$m:M4M`{2)r.q=ad[C8@£85Iq4Yp@p/J1s0?9fEkp=rX<gd&pv41V|f5?:¬KdRC(n.)oyj6ePoI<!93t)4tgy@fu^doz2AVK97~J=[6&/h)v)F:-S29_/y==)~HGmJKv;FFBO_Z9.pc0X>J9:I9GgDvGWD21,[ppF\lO<3-8wZlo7>w¬Ka@-Od3}|>C7cHkFW58O=5y*%`7;&8¬IV|xbfOehC¬=e^-%p+A^F1ABoTFM1fxr8<SD4iCcP\pFG~\ZH£|0?q2c\ybv|/,PU:JV/r,Zu_$r]2~ChJ&xjvQe7uC8dP*jO>,<5kHM>x09pFI+yLN@uITu@dbLR)|\¬\^I+fi"
        if not encryption.compare_to_hashed(password, encryption.decrypt(enc_key, user_password)):
            error = "Login information is invalid."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            user.failed_logins += 1
            return
                  
        if self.__check_user_online(user_id):
            error = "Account already logged in. Please close your other logged in session."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            return
                  
        user.id = user_id
        user.username = username
        self.__add_db_request("""
            UPDATE Users
            SET LastLogIn=?
            WHERE Users.UserID=?""",
            (time.time(), user_id), receive=False)
        user.send_queue.enqueue({"command": "login_success"})

    def __change_password(self, user, password, new_password):
        """ This method changes a user's password to a new password.
               Inputs: user (the Connection object that stores the connection
            with the client) and new_password (a string containing the
            encrypted new password to be used by the user).
              Outputs: None."""
        if user.id is None:  # i.e. user is not logged in.
            error = "You cannot change passwords because you are not logged in."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            return
        current_password = encryption.decrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                              password)
        user_password = self.__add_db_request("""
            SELECT UserCredentials.Password
            FROM Users, UserCredentials
            WHERE Users.Username=? AND Users.UserID=UserCredentials.UserID""",
            user.username)[0]
        enc_key = r"$-£Vs+i^)]XIUzocb{%Al¬tG=hU_QzG0Lk)rm-oC2Dyccj?¬yM1RMcBx_vX)&l;yggpANSd@)¬L>$]{\qEwN!W<}03F£I\CV>.Ckh£7X`)%-_NwWs:)*:^Siyn8o£+bDkm3e(V.B0wAV*6GP5ktdrTE_72jZO\KTk,5}U)£cPj$m:M4M`{2)r.q=ad[C8@£85Iq4Yp@p/J1s0?9fEkp=rX<gd&pv41V|f5?:¬KdRC(n.)oyj6ePoI<!93t)4tgy@fu^doz2AVK97~J=[6&/h)v)F:-S29_/y==)~HGmJKv;FFBO_Z9.pc0X>J9:I9GgDvGWD21,[ppF\lO<3-8wZlo7>w¬Ka@-Od3}|>C7cHkFW58O=5y*%`7;&8¬IV|xbfOehC¬=e^-%p+A^F1ABoTFM1fxr8<SD4iCcP\pFG~\ZH£|0?q2c\ybv|/,PU:JV/r,Zu_$r]2~ChJ&xjvQe7uC8dP*jO>,<5kHM>x09pFI+yLN@uITu@dbLR)|\¬\^I+fi"
        if not encryption.compare_to_hashed(current_password, encryption.decrypt(enc_key, user_password)):
            error = "The entered user password is not valid."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            return
        new_password = encryption.decrypt(r"H!vG&@|Cd50f?*O¬YymVE¬j<*3g;fPH}00EtR(B\p^oW\M&D_Jeyl__UbSr2£GDWIy!Q!}[Q(y+z*(9c%}P33;,-$i?bX£HA}/Vrng*{SGSdV>A@Jjm/?qYA;n?VF5M3.rqKX:,nE:93C}|K/1>_vVh+sS;Me9:HL/Di.{$bLct(/.LE;YA[x.wl¬bjBXKe\Ee:&]zz.*Yk]axN0moL[h?}-£6Y5`6,$Y25OBrb1|Q(-GGI^r£,YIK&>viMDAE3+;£r£>X/&x4D7X¬M¬taO(>=&]ipb]X?XDZG]4|\@L`e7VC+~T]p|$65t<Xt{MDkreC|}1.5{uzJ0<1Qhe(tYmEVc)a~-<&yH!y\WA/6!x£6:7V760P6A?fu_*N)0Kz@z07OQDm78$&c&VYY&%I{~*£SZ6FQEU;mNEAs4ruT\zP8[@>4G2fhvAPr|)hAefDe%T4w`;}=kZBaq!buE^F;NP`uz@d&H@UtQ={87U2o5gcCi(G\¬/VjRo8%`xM,iidujZ",
                                          new_password)
        new_hashed_pass = self.__get_secured_password(new_password)
        self.__add_db_request("""
            UPDATE UserCredentials
            SET Password=?
            WHERE UserCredentials.UserID=?""",
            (new_hashed_pass, user.id), receive=False)
        success_message = "Your password has been successfully altered."
        user.send_queue.enqueue({"command": "display_message",
                                 "args": (success_message,)})

    def __create_new_lobby(self, player, user_settings, name, password=None):
        """ This method is called when a user creates a new custom lobby, and
            creates a lobby with the specified input settings, name and
            password. It also adds the player themselves to the lobby after it
            has been created, and adds the lobby the the server's list of
            current existing lobbies.
              Inputs: player (a Connection object containing the connection to
            the client that is creating the lobby, to be added to the lobby
            when it is started), user_settings (a dictionary containing all of
            the custom settings that the user would like the lobby to use),
            name (a string containing the name of the lobby that will be
            displayed to other players in the lobby browser) and password (a
            string containing the password that will be required to access the
            lobby created by the user. By default this is None, meaning that 
            the lobby has no password).
              Outputs: None."""
        lobby_settings = {}
        update_nonvisual_settings(lobby_settings, user_settings)
        lobby_settings["starting_player"] = random.randint(1, 2)
        if name.lower() == "competitive game":
            # stop impersonation of server-made competitive lobbies
            name += " (user created)"
        new_lobby = Lobby(self.current_lobby_id, name=name, 
                          password=password, settings=lobby_settings)
        self.current_lobby_id += 1
        new_lobby.add_player(player)
        self.lobbies.append(new_lobby)

    def __retrieve_lobbies(self, player, num_limit=0):
        """ This method retrieves a list of existing lobbies from the server
            for use elsewhere, e.g. so players can view the list of lobbies and
            select a lobby to join.
              Inputs: player (a Connection object containing the connection
            with the client that is requesting the lobbies so that the
            information can be sent back to them), and num_limit (an optional
            integer describing the number of lobbies to be requested from the
            server. Defaults to 0 which is used to represent no limit i.e. 
            retrieve all the lobbies).
              Outputs: a two-dimensional list where each inner list contains
            the information about one individual lobby. The first element is 
            the lobby's unique integer ID that can be used to refer to that
            lobby uniquely, the second is an integer describing the number of
            players currently in the lobby, and the third element is a Boolean
            describing whether the lobby is password protected or not)."""
        to_send = self.lobbies.copy()
        if num_limit != 0:
            to_send = to_send[:num_limit]
        to_send = [[lobby.id, lobby.name, len(lobby.players), lobby.password is not None] for lobby in to_send]
        player.send_queue.enqueue({"command": "receive_lobbies",
                                   "args": (to_send,)})

    def __find_lobby(self, requested_id):
        """ This function takes a given integer representing a lobby id and
            finds the lobby object in the list of the server's lobbies
            (self.lobbies) that corresponds to that unique ID.
              Inputs: requested_id (an integer representing the unique ID of
            the lobby being searched for).
              Outputs: either a Lobby object with a .id that matches the given
            ID, or None if no lobby with a matching ID number can be found."""
        for lobby in self.lobbies:
            if lobby.id == requested_id:
                return lobby

    def __join_existing_lobby(self, player, lobby_id, password=""):
        """ This method is used to let a client join a certain lobby. It should
            be called with the client object and the lobby_id, where the server
            will then search for the lobby and attempt to add the user to the 
            lobby. It will communicate any errors in joining lobbies with the
            user and will request a password if necessary.
              Inputs: player (a Connection object containing the connection
            with the client that is attempting to join a lobby), lobby_id (an
            integer containing the unique identifer number of the lobby) and
            password (a string containing the user's input password that will
            be compared to the lobby's password to validate that the user can
            enter the lobby).
              Outputs: None."""
        if player.in_lobby:  # if already in a lobby, cannot join another.
            return
        lobby = self.__find_lobby(lobby_id)
        if lobby is not None:
            if len(lobby.players) < 2:
                if lobby.password is not None:
                    if password == "":  # if no password given, send a request
                        player.send_queue.enqueue({"command": "request_lobby_password"})
                    elif lobby.password == password:
                        player.send_queue.enqueue({"command": "join_success"})
                        lobby.add_player(player)
                    else:
                        error = "The entered lobby password is incorrect."
                        player.send_queue.enqueue({"command": "action_failure",
                                                   "args": (error,)})
                else:
                    player.send_queue.enqueue({"command": "join_success"})
                    lobby.add_player(player)
            else:
                error = "The requested lobby is full."
                player.send_queue.enqueue({"command": "action_failure",
                                           "args": (error,)})
        else:
            error = "The requested lobby either cannot be found or no longer exists."
            player.send_queue.enqueue({"command": "action_failure",
                                       "args": (error,)})

    def __record_game_stats(self, lobby):
        """ This method records the statistics of a game of 8-ball pool that
            has been finished. It looks at the lobby for details such as the
            game's start and end times, mode and victor, and also retrives the
            stats for player 1 and 2. It records the game as a record in the 
            database's Games table and also adds two new GameUser entries with
            the same ids to record each user's statistics in the game.
              Inputs: lobby (a Lobby object that has finished its game and 
            needs to have its statistics recorded to the networked database).
              Outputs: None."""
        game_id = self.__add_db_request("""
            INSERT INTO Games (
                TimeStarted, 
                TimeCompleted, 
                IsCompetitive, 
                Victor
            ) 
            VALUES (?, ?, ?, ?)""",
            (lobby.started, lobby.finished, 
             lobby.is_competitive, lobby.victor_id), 
            receive="lastrowid")
        user_info = [(game_id, lobby.players[0].id, 
                      lobby.p1_stats["ShotsMade"], 
                      lobby.p1_stats["BallPockets"], 
                      lobby.p1_stats["OpponentBallPockets"], 
                      lobby.p1_stats["Fouls"]),
                     (game_id, lobby.players[1].id, 
                      lobby.p2_stats["ShotsMade"], 
                      lobby.p2_stats["BallPockets"], 
                      lobby.p2_stats["OpponentBallPockets"], 
                      lobby.p2_stats["Fouls"])]
        for user_stats in user_info:
            self.__add_db_request("""
                INSERT INTO GameUsers (
                    GameID, 
                    UserID, 
                    ShotsMade, 
                    BallPockets, 
                    OpponentBallPockets, 
                    Fouls) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                user_stats, receive=False)
        for i in range(2):
            user_id = lobby.players[i].id
            self.__add_db_request("""
                UPDATE Users 
                SET GamesPlayed = GamesPlayed + 1, 
                    Victories = Victories + ?, 
                    CompetitivePlayed = CompetitivePlayed + ?
                WHERE UserID = ?""",
                (1 if lobby.victor_id == user_id else 0, 
                 1 if lobby.is_competitive else 0, user_id), receive=False)
        # if any players have quit (they are not in use), 
        # they can be deleted now that their stats are recorded.
        for player in lobby.players:
            player.can_delete = not player.in_use

    def __retrieve_user_statistics(self, user):
        """ This method retrives all of the statistical information about the
            user and sends it to the user so that it can be displayed in the 
            statistics menu.
              Inputs: user (a Connection object containing the connection with
            the client that is requesting their account's information).
              Outputs: None."""
        user_info = self.__retrieve_user_account_info(user)
        competitive_info = self.__retrieve_user_competitive_info(user)
        if user_info[2] > 0:  # if played games > 0
            last_game_info = self.__retrieve_user_last_game_info(user)
        else: # default info if no last game played.
            last_game_info = (0, "N/A", "N/A", 0, 0, 0, 0) 
        max_winstreak_info = self.__retrieve_user_max_winstreak(user)
        to_send = {"Username": user_info[0], 
                   "Account Age": user_info[1],
                   "Competitive Rank": competitive_info[2], 
                   "Length": last_game_info[0],
                   "Competitive": last_game_info[1], 
                   "Win/Loss?": last_game_info[2],
                   "Shots Made": last_game_info[3], 
                   "Ball Pockets": last_game_info[4],
                   "Wrong Pockets": last_game_info[5], 
                   "Fouls": last_game_info[6],
                   "Games Played": user_info[2], 
                   "Victories": user_info[3],
                   "Overall Win Rate": user_info[4], 
                   "Competitive Matches Played": competitive_info[0],
                   "Competitive Win Rate": competitive_info[1], 
                   "Max Winstreak": max_winstreak_info}
        generic_statistics = self.__retrieve_user_generic_stats(user)
        for category in generic_statistics:
            to_send[category] = generic_statistics[category]
        user.send_queue.enqueue({"command": "receive_user_statistics",
                                 "args": (to_send,)})

    def __retrieve_user_account_info(self, user):
        """ This method retrieves basic information related to a user account.
              Inputs: user (a Connection object holding a connection with the
            user whose information is wanted).
              Outputs: Returns a list of competitive info. The first element is
            a string containing the user's username, the second is a float
            containing the account age in seconds, the third is an integer
            number of total games played by the user, the fourth is an integer
            number of victories achieved by the user and the fifth is a float
            (0 <= value <= 1) containing the user's win rate on the scale of 0
            to 1."""
        user_info = self.__add_db_request("""
            SELECT Username,
                   TimeCreated,
                   GamesPlayed,
                   Victories,
                   CAST(Victories as FLOAT) / GamesPlayed AS WinRate
            FROM Users
            WHERE UserID=?""", 
            user.id)
        return [user_info[0]]+[time.time() - user_info[1]]+list(user_info[2:])

    def __retrieve_user_competitive_info(self, user):
        """ This method retrieves detailed information related to a user's 
            competitive play history.
              Inputs: user (a Connection object holding a connection with the
            user whose information is wanted).
              Outputs: Returns a tuple of competitive info. The first tuple 
            element is the user's competitive games played (an integer), the
            second is their competitive win rate (a float) and the third is a 
            string containing the user's competitive rank based upon preset
            rank information."""
        competitive_played_info = self.__add_db_request("""
            SELECT COUNT(*),
                   CAST(SUM(CASE WHEN Games.Victor=? THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS WinRate
            FROM Games, 
                 GameUsers
            WHERE Games.GameID = GameUsers.GameID
                  AND GameUsers.UserID = ?
                  AND Games.IsCompetitive""", 
            (user.id, user.id))
        if competitive_played_info[0] < 20: # comp games played < 20 -> no rnak
            return [*competitive_played_info, "Unranked"]
        last_win_rate = self.__add_db_request("""
            SELECT CAST(SUM(CASE WHEN Victor=? THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS WinRate
            FROM (
                    SELECT Games.Victor
                    FROM Games, 
                            GameUsers
                    WHERE Games.GameID = GameUsers.GameID
                        AND Games.IsCompetitive
                        AND GameUsers.UserID = ?
                    ORDER BY Games.GameID DESC
                    LIMIT 50
                 )""", 
            (user.id, user.id))[0]
        for rank in list(self.__ranks.keys())[::-1]:  # in descending order
            if self.__ranks[rank][0] <= last_win_rate <= self.__ranks[rank][1]:
                return [*competitive_played_info, rank]
        # one last extra catch case for if no ranks exist.
        return [*competitive_played_info, "Unranked"]

    def __retrieve_user_last_game_info(self, user):
        """ This method retrieves detailed information related to a user's last
            played game.
              Inputs: user (a Connection object holding a connection with the
            user whose information is wanted).
              Outputs: Returns a tuple of last game info. The first element is
            an integer describing the length of the game in seconds, the second
            is a string describing the competitive state of the game, the third
            is a string detailing whether the last game was a "WIN" or "LOSS",
            the fourth is the integer number of shots made in the game, the
            fifth is the integer number of balls pocketed, the sixth is the
            integer number of opponent's bals pocketed, and the seventh is the
            integer number of fouls made in the game."""
        last_game_info = self.__add_db_request("""
            SELECT Games.TimeStarted,
                   Games.TimeCompleted,
                   Games.IsCompetitive,
                   Games.Victor,
                   GameUsers.ShotsMade,
                   GameUsers.BallPockets,
                   GameUsers.OpponentBallPockets,
                   GameUsers.Fouls
            FROM Games, 
                 GameUsers
            WHERE Games.GameID = GameUsers.GameID
              AND GameUsers.UserID = ?
            ORDER BY Games.GameID DESC
            LIMIT 1""", 
            user.id)
        length = last_game_info[1] - last_game_info[0]
        is_competitive = "YES" if last_game_info[2] else "NO"
        was_won = "WIN" if last_game_info[3] == user.id else "LOSS"
        return (length, is_competitive, was_won, last_game_info[4], 
                last_game_info[5], last_game_info[6], last_game_info[7])

    def __retrieve_user_max_winstreak(self, user):
        """ This method retrieves a user's highest winsteak (several wins in a
            row) in their games.
              Inputs: user (a Connection object holding a connection with the
            user whose information is wanted).
              Outputs: Returns an integer describing the highest number of
            games won in a row by the user."""
        return self.__add_db_request("""
        WITH RunGroups AS (
                SELECT G1.GameID, G1.Victor,
                      (
                        SELECT COUNT(*) 
                        FROM Games G2, GameUsers
                        WHERE G2.Victor <> G1.Victor
                          AND G2.GameID < G1.GameID
                          AND G2.GameID = GameUsers.GameID
                          AND GameUsers.UserID = ?
                      ) AS RunGroup
                FROM Games G1, GameUsers
                WHERE G1.GameID = GameUsers.GameID
                  AND GameUsers.UserID = ?
        ), 
        Runs AS (
                 SELECT COUNT(*) AS RunLength
                 FROM RunGroups
                 WHERE Victor = ?
                 GROUP BY RunGroup
                 ORDER BY MIN(GameID)
        )
        SELECT MAX(RunLength)
        FROM Runs""",
            (user.id, user.id, user.id)
        )[0]

    def __retrieve_user_generic_stats(self, user):
        """ This method retrieves other generic information related to a user's
            play history along with statistical analysis (total, mean, 
            variance). This includes: duration of matches, shots made, ball 
            pockets, opponent ball pockets and fouls.
              Inputs: user (a Connection object holding a connection with the 
            user whose information is wanted).
              Outputs: Returns a dictionary containing a variety of statistical
            information. Generally keys for data are in the format 'Total x', 
            'Mean x' or 'x Variance' where x is the variable."""
        statistics = {}
        time_stats = self.__add_db_request("""
            WITH UserStatistics AS (
                SELECT Games.TimeCompleted - Games.TimeStarted AS Time
                FROM Games, 
                     GameUsers
                WHERE Games.GameID = GameUsers.GameID
                  AND GameUsers.UserID=?
            )
            SELECT SUM(Time) AS Total,
                   AVG(TIME) AS Mean,
                   (SUM(Time * Time) - SUM(Time) * SUM(Time) / COUNT(Time)) / COUNT(Time) as Variance
            FROM UserStatistics""", 
            user.id)
        time_stats = [0 if item is None else item for item in time_stats]
        statistics["Total Time Played"] = time_stats[0]
        statistics["Mean Time Played"] = round(time_stats[1], 3)
        statistics["Time Played Deviation"] = round(sqrt(time_stats[2]), 3)  
        # all other stats follow the same format as above, we do time seperately
        # because it requires different database queries.
        other_stats = {"ShotsMade": "Shots Made",
                       "BallPockets": "Pocketed Balls",
                       "OpponentBallPockets": "Wrong Pockets",
                       "Fouls": "Times Fouled"}  
        # key:value pair represents ' database field name : displayed name '
        for field in other_stats:
            display_name = other_stats[field]
            measures = self.__add_db_request(f"""
                SELECT SUM({field}) AS Total,
                       AVG({field}) AS Mean,
                       (SUM({field} * {field}) - SUM({field}) * SUM({field}) / CAST(COUNT({field}) AS FLOAT)) / COUNT({field}) AS Variance
                FROM GameUsers
                WHERE GameUsers.UserID=?""",
                user.id)
            measures = [0 if item is None else item for item in measures]
            statistics[f'Total {display_name}'] = measures[0]
            statistics[f'Mean {display_name}'] = round(measures[1], 3)
            statistics[f'{display_name} Variance'] = round(measures[2], 3)
        return statistics

    def __retrieve_leaderboard(self, user, category):
        """ This method retrieves a leaderboard, displaying the top 5 users in
            a given category, and sends the leaderboard back to the user that
            requested it.
              Inputs: user (a Connection object containing the connection with
            the client that requested the leaderboard), and category (a string
            containing the name of the category being requested by the client).
              Outputs: None (sends the leaderboard directly back to the user)."""
        available_categories = ["GamesPlayed", "Victories", 
                                "WinRate", "CompetitivePlayed"]
        if category not in available_categories:
            error = "That category does not exist."
            user.send_queue.enqueue({"command": "action_failure",
                                     "args": (error,)})
            return
        if category == "WinRate":
            top_players = self.__add_db_request("""
                SELECT Username, 
                       CAST(Victories as FLOAT) / GamesPlayed AS WinRate 
                FROM Users 
                WHERE GamesPlayed > 10 
                ORDER BY WinRate DESC, Username ASC
                LIMIT 5""")
        else:
            top_players = self.__add_db_request(f"""
                SELECT Username, 
                       {category} 
                FROM Users 
                ORDER BY {category} DESC, Username ASC
                LIMIT 5""")
        # catch for the case there is only 1 person in the leaderboard
        if isinstance(top_players, tuple):
            top_players = [top_players]  # if 1 person, send as list, not tuple
        percentage_categories = ["WinRate"]
        if category in percentage_categories:
            # we apply any additional formatting to turn certain categories' 
            # data into a percentage format
            top_players = [(player[0], str(round(player[1] * 100, 3)) + "%") for player in top_players]
        user.send_queue.enqueue({"command": "receive_leaderboard", 
                                 "args": (top_players,)})
    
    def __manage_players(self):
        """ This method checks all of the existing connections to detect if
            any are no longer in use (e.g. the user forcibly closed the 
            connection). It performs cleanup by removing them from any lobbies
            which they may be in, and then deleting them from the server's list
            of existing connections.
              Inputs: None.
              Outputs: None."""
        for connection in self.connections:
            if not connection.in_use:
                if connection.in_lobby:
                    for lobby in self.lobbies:
                        if connection in lobby.players:
                            lobby.player_quit(connection)
                            break
                if connection.can_delete:
                    if connection.id is not None:
                        print("DELETING USER {}: {}".format(connection.id, connection.username))
                    else:
                        print("DELETING AN UNLOGGED USER.")
                    self.connections.remove(connection)
                    del connection

    def __manage_competitive_lobbies(self):
        """ This method manages the competitive lobbies, detecting if any of
            the currently available 3 have been filled and are in use. If so,
            it will create a new competitive lobby and add it to the list of
            available lobbies so that there are always 3 open competitive 
            lobbies available.
              Inputs: None.
              Outputs: None."""
        to_remove = []
        for lobby in self.competitive_lobbies:
            if len(lobby.players) >= 2 or lobby.to_delete:
                to_remove.append(lobby)
                lobby_id = self.current_lobby_id
                self.current_lobby_id += 1
                new_lobby = Lobby(lobby_id, name="Competitive Game")
                new_lobby.settings = self.competitive_settings
                self.competitive_lobbies.append(new_lobby)
                self.lobbies.append(new_lobby)
        for lobby in to_remove:
            self.competitive_lobbies.remove(lobby)

    def __manage_lobbies(self):
        """ This method manages the lobbies contained by the server in general.
            It checks if any lobbies have finished their game and are completed,
            at which point it will call for the lobby and its players' stats to
            be recored in the database before removing and deleting the lobby. 
            It also checks if any lobbies need to be started and starts them in
            their own new thread if so.
              Inputs: None.
              Outputs: None."""
        for lobby in self.lobbies:
            if not lobby.started and len(lobby.players) == 2:
                print("STARTING LOBBY {}".format(lobby.id))
                Thread(target=lobby.start).start()
            if lobby.to_delete:
                if lobby.victor is not None:
                    print("RECORDING AND DELETING LOBBY {}".format(lobby.id))
                    self.__record_game_stats(lobby)
                else:
                    # do not record for a lobby that was not used (started).
                    print("DELETING LOBBY {}".format(lobby.id))
                self.lobbies.remove(lobby)
                del lobby

    def __update(self):
        """ This method continually updates, manages and cleans the server. It
            calls other management methods that check and update the state of
            the server whilst the server is in use. It does this continually at
            a set rate.
              Inputs: None.
              Outputs: None."""
        while self.in_use:
            self.__manage_players()
            self.__manage_competitive_lobbies()
            self.__manage_lobbies()     
            time.sleep(1)

    def start(self):
        """ This method actually starts up the server so that it can be
            connected to by users and they can interact with it. Creates two
            new threads: one to listen for new connections, and another to 
            process database requests. It then calls for the continual updating
            of the server.
              Inputs: None.
              Outputs: None."""
        Thread(target=self.__await_connections).start()
        Thread(target=self.__process_database_requests, daemon=True).start()
        # daemon=True so when the main thread finishes, this thread will close.
        self.__update()


host, port = retrieve_server_location()
billiards_server = Server(host, port, max_connections=64)
billiards_server.start()
