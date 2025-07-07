import sys

class Logger(object):
    """
    Production grade loggers can be used but I prefer using
    this as it works with just the print statement.
    """
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.terminal.flush()
        self.log.flush()

    def flush(self):
        pass
