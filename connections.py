""" connections module
Functions:
 - retrieve_server_location
Classes:
  None.
Description:
  A small module containing a function that retrieves server connection location
information, i.e. the host and port that the server is hosted on."""

# external imports
import os


def retrieve_server_location():
    """ This function retrieves the host and port information that is stored in
        the server_info/conn_info.txt file, and then checks their validity. If
        not valid, it uses a defaut server location that is hard coded in.
          Inputs: None.
          Outputs: host (a string detailing the IPv4 address of the host server
        e.g. 127.0.0.1) and port (an integer describing the port which the
        server is hosted on, e.g. 64532)."""
    if not os.path.isdir("server_info"):
        # if file doesn't exist, write a file with default hard-coded values.
        print("Connection information file not found. Creating new file with default information.")
        os.mkdir("server_info")
        host = "192.168.0.15"
        port = 64532
        with open("server_info/conn_info.txt", "w+") as info_file:
            info_file.write("host: {}\nport: {}".format(host, port))
            info_file.close()
    else:
        try:
            with open("server_info/conn_info.txt", "r") as info_file:
                host = info_file.readline().strip().split(": ")[-1]
                port = int(info_file.readline().strip().split(": ")[-1])
                info_file.close()
        except (FileNotFoundError, ValueError, TypeError) as e:
            print("Server information in file is invalid. Resetting sever information...")
            host = "192.168.0.15"
            port = 64532
            with open("server_info/conn_info.txt", "w") as info_file:
                info_file.write("host: {}\nport: {}".format(host, port))
                info_file.close()
            print("Server information reset.")
    return host, port
    
