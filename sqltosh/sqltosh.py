"""
SQLtoSH is an sql interpreter for browsing and manipulating files/structure in a Shell environment.
"""

import sys
import platform
import re
import time
import math

# Rich is a 3rd party library for displaying 'rich' text in the terminal.
from rich.console import Console
from rich.table import Table
from rich import box
from os import path, walk, scandir, system
from pwd import getpwuid
from grp import getgrgid
from operator import itemgetter


class Prompt():
    def __init__(self):
        if not self.supported_platform():
            sys.exit(1)

        self.header_color = 'bold magenta'

        self.columns = [
            'name',
            'type',
            'created_on',
            'last_modified',
            'last_accessed',
            'file_size',
            'permissions',
            'owner',
            'group',
            ]

        self.statements = {
            'select': self.select,
            'insert': self.insert,
            'delete': self.delete,
            'update': self.update,
        }

        self.keywords = {
            'where': self.where,
            'sort by': self.sort_data,
        }
        self.commands = {
            'help': 'Displays this help message',
            'exit': 'Exits the session, cleaning up any temporary data',
            'clear': 'Clears the screen',
        }
        self.host_platform = platform.system()
        self.greet()


    def prompt(self):
        start_prompt = 'sqltosh> '
        newline_prompt = '    ...> '

        try:
            # Initial query
            query = input(start_prompt)

            # Continue to prompt user until query ends with ;
            if not re.search(';$', query):
                while not re.search(';$', query):
                    query += ' ' + input(newline_prompt)

        except (EOFError, KeyboardInterrupt):
            self.exit()

        # remove the delimiter ';'
        self.execute(query[:-1])
        

    def execute(self, query):
        """ Executes the query submitted by the user, by routing it to the correct method
        """

        if query in self.commands.keys():
            self.command(query)

        else:
            query = query.split()

            statement = query[0].lower()

            if statement in self.statements:
                try:
                    # Try executing the function associated with the statement
                    # Pass query without the statement ie, remove 'select'
                    self.statements[statement](query[1:])
                except Exception as e:
                    print(e)

            else:
                console.print(f"ERROR 1064 (42000) at line 0: You have an error in your SQL syntax; (Hint): invalid statement: {query[0]}")
            

    def command(self, query):
        if query == 'help':
            self.help()

        elif query == 'exit':
            self.exit()
        
        elif query == 'clear':
            self.clear()


    def help(self):
        help_table = Table(show_header=True, header_style=self.header_color)
        help_table.add_column("Commands")
        help_table.add_column("Description")
        help_table.box = box.SIMPLE_HEAD
        for k, v in self.commands.items():
            help_table.add_row(k, v)
        console.print(help_table)


    def exit(self):
        # add any necessary cleanup
        console.print("Goodbye.")
        sys.exit(0)


    def clear(self):
        try:
            system('clear')
        except Exception:
            pass


    def supported_platform(self):
        """ Check if platform is supported
        """
        supported_platforms = ['Linux', 'Darwin']

        if platform.system() not in supported_platforms:
            console.print(f"Sorry, [bold red]{platform.system()}[/bold red] is not supported")
            return False
        return True


    def login(self, user, password):
        """ Switches to a user
        """
        pass


    def select(self, query):
        """ Searches the filesystem

        returns a structured table containing the search results
        """

        columns = self.columns if query[0] == '*' else []

        if not columns:
            for counter, q in enumerate(query, start=1):
                if q.lower() == 'from':
                    query = query[counter:]
                    break
                
                if re.search(',$', q):
                    q = q[:-1]

                if q not in self.columns:
                    console.print(f"ERROR 1054 (42S22) at line 0: Unknown column '{q}' in 'field list'")
                    return False
                else:
                    columns.append(q)
        else:
            # remove * and from
            query = query[2:]
        
        try:
            directory = query[0]
            # Remove the directory name from the query
            query = query[1:]
        except IndexError:
            console.print(f"ERROR 1064 (42000) at line 0: You have an error in your SQL syntax; (Hint): missing directory / path")
            return False

        # if query:
        #     self.execute(query)


        table = Table(title=f"{directory}", show_header=True, header_style=self.header_color, box=box.SQUARE)
        table.add_column('', justify="right")
        for col in columns:
            table.add_column(col.upper(), justify="right" if col == 'file_size' else "left")

        files = self.get_files(directory)

        files = self.sort_data(files, 'name')

        if not files:
            return False

        for counter, f in enumerate(files):
            table.add_row(str(counter), 
                *[(f[x]) for x in columns],
                style = 'bold blue' if 'directory' in f['type'] else 'bold green' if 'file' in f['type'] else 'bold yellow',
            )

        console.print(table)
        console.print(f"{len(files)} rows in set (0.00 sec)")
        print()
        

    def sort_data(self, data, key, desc=None):
        """ Sort a list of dictionaries by key
        """
        return sorted(data, key=itemgetter(key), reverse=True if desc else False)



    def insert(self, query):
        pass

    def update(self, query):
        pass

    def delete(self, query):
        pass


    def get_files(self, directory):

        # check if directory exists
        if not path.exists(directory):
            console.print(f"ERROR 1146 (42S02) at line 0: Directory {directory} doesn't exist")
            return False
        
        # get all files in the path
        files = []


        with scandir(directory) as dir_contents:
            for entry in dir_contents:
                try:
                    file_stat = entry.stat()

                    try:
                        owner = getpwuid(file_stat.st_uid).pw_name
                    except:
                        owner = 'Unknown'

                    try:
                        group = getgrgid(file_stat.st_gid).gr_name
                    except:
                        group = "Unknown"

                    files.append({
                        'name': entry.name,
                        'type': ':spiral_notepad:  file' if entry.is_file() else ':open_file_folder: directory' if entry.is_dir() else ':question: Unknown',
                        'created_on': self.convert_epoch(file_stat.st_ctime),
                        'last_modified': self.convert_epoch(file_stat.st_mtime),
                        'last_accessed': self.convert_epoch(file_stat.st_atime),
                        'file_size': self.convert_size(file_stat.st_size),
                        'permissions': self.convert_unix_permissions(str(oct(file_stat.st_mode))[-3:]),
                        'owner': owner,
                        'group': group,
                    })
                except FileNotFoundError:
                    files.append({
                        'name': entry.name,
                        'type': ':spiral_notepad:  file' if entry.is_file() else ':open_file_folder: directory' if entry.is_dir() else ':question: Unknown',
                        'created_on': 'Unknown',
                        'last_modified': 'Unknown',
                        'last_accessed': 'Unknown',
                        'file_size': 'Unknown',
                        'permissions': 'Unknown',
                        'owner': 'Unknown',
                        'group': 'Unknown',
                    })


        return files

    def convert_unix_permissions(self, mode):
        permissions = {
            '7': 'rwx',
            '6': 'rw-',
            '5': 'r-x',
            '4': 'r--',
            '3': '-wx',
            '2': '-w-',
            '1': '--x',
            '0': '---',
        }
        

        perms = ''
        for n in mode:
            perms += permissions[n]

        return perms
            
    def convert_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

    def where(self):
        pass

    def convert_epoch(self, epoch):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))

    def greet(self):
        console.print('\n' + "Welcome to the sqltosh monitor :desktop_computer: . Commands end with [bold magenta];[/bold magenta].")
        console.print("Server version: [bold magenta]1.0.0a[/bold magenta] SqltoSH Server (MIT)")
        console.print("\n")
        console.print("Type 'help;' for help." + '\n')


if __name__ == '__main__':
    console = Console()

    new_prompt = Prompt()

    while True:
        new_prompt.prompt()