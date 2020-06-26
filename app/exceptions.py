class invalidCMDError(Exception): # The CMD is of invalid format
    pass

class nonPythonError(Exception): # The first word of the command is not python nor python2 nor python3
    pass

class DuplicateError(Exception): # Two files exist with the same name
    pass

class DirectoryError(Exception): # Given directory doesn't exist or duplicate directories
    pass

class PathError(Exception): # Path not valid
    pass

class fileNotFoundError(Exception): # file name not found
    pass

class CodeError(Exception): # Syntax error found during AST generation
    def __init__(self,args):
        self.args = args