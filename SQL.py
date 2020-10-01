""" SQL module
Functions:
  None.
Classes:
 - Database
Description:
  A module used to create a Database object that can interface with a database
file, allowing the server to store information about users. Allows modification
of database automatically during the runtime of the code."""

# external imports
import sqlite3


class Database:
    """ A class used to represent a loaded/created database, interacted with
        using SQL commands using the sqlite3 python module."""

    def __init__(self, name):
        """ The constructor for the Database class. Loads and connects to the
            database with the given name, whether it exists or not.
              Inputs: name (a string that details the filename (and/or relative
            path) of the database file).
              Outputs: None."""
        if not name.endswith(".db"):
            name += ".db"
        self.name = name
        self.__connection = sqlite3.connect(self.name)
        self.__cursor = self.__connection.cursor()
        self.connected = True

    @property
    def exists(self):
        """ A property that returns a Boolean value that describes whether a
            database with the given name actually exists, so that it can be
            created if it does not. No inputs, Boolean output."""
        # retrieve list of names of tables that exist
        tables = self.query("SELECT name FROM sqlite_master")
        return len(tables) > 0

    def query(self, query, parameters=None):
        """ This method is used to perform an SQL query on the database,
            allowing alteration of the database, retrieval of data etc.
              Inputs: query (a string/docstring containing the SQL statement to
            be executed, as well as '?' symbols for any parameters to be
            replaced) and parameters (a list or tuple of values that are used to
            fill any '?' parameter spaces within the given SQL query).
              Outputs: any results of the SQL query, in the form of a tuple
            containing the queried information."""
        if not self.connected:
            return
        if parameters is None:
            self.__cursor.execute(query)
        else:
            self.__cursor.execute(query, parameters)
        return self.__cursor.fetchall()

    def commit_changes(self):
        """ Actually commits any changes to the database made by SQL queries so
            that they will take effect on the actual database.
              Inputs: None.
              Outputs: None."""
        self.__connection.commit()

    @property
    def lastrowid(self):
        """ Returns the id (primary key integer) of the last row accessed by
            the cursor.
              Inputs: None.
              Outputs: An integer (or None) representing the primary key integer
            ID of the last row accessed by the cursor (of the last table
            accessed by the cursor)."""
        return self.__cursor.lastrowid

    def close(self):
        """ This method closes the database connection so that you are no longer
            connected to the database and no more queries/requests can be used
            on the database.
              Inputs: None.
              Outputs: None."""
        self.__connection.close()
        self.connected = False

    def __del__(self):
        """Ensures that when the database object is deleted, its connection is
           first closed beforehand."""
        self.close()
