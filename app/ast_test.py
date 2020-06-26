# This module collects the packages to be installed from the AST installs them in an already open conda environment in the host machine and returns problematic modules

import ast
import sys
import os
import re
import shutil
import subprocess

import app.files_list as files_list
import app.exceptions as exceptions

from pypi_name import pypiName

# This list of built-in modules for py 2 and 3 was taken from a third party pip package called 'stdlib_list', these packages are built-in packages of python 3.7 and python 2.7 respectively
# The stdlib_list allows us to get the packages of any python version
built_in_modules3 = {'__future__', '__main__', '_dummy_thread', '_thread', 'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2', 'cProfile', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys', 'compileall', 'configparser', 'contextlib', 'contextvars', 'copy', 'copyreg', 'crypt', 'csv', 'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils', 'doctest', 'dummy_threading', 'email', 'ensurepip', 'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'macpath', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'zipapp', 'zipfile', 'zipimport', 'zlib'}

built_in_modules2 = {'AL', 'BaseHTTPServer', 'Bastion', 'CGIHTTPServer', 'ColorPicker', 'ConfigParser', 'Cookie', 'DEVICE', 'DocXMLRPCServer', 'EasyDialogs', 'FL', 'FrameWork', 'GL', 'HTMLParser', 'MacOS', 'MimeWriter', 'MiniAEFrame', 'Nav', 'PixMapWrapper', 'Queue', 'SUNAUDIODEV', 'ScrolledText', 'SimpleHTTPServer', 'SimpleXMLRPCServer', 'SocketServer', 'StringIO', 'Tix', 'Tkinter', 'UserDict', 'UserList', 'UserString', 'W', '__builtin__', '__future__', '__main__', '_winreg', 'abc', 'aepack', 'aetools', 'aetypes', 'aifc', 'al', 'anydbm', 'applesingle', 'argparse', 'array', 'ast', 'asynchat', 'asyncore', 'atexit', 'audioop', 'autoGIL', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'bsddb', 'buildtools', 'bz2', 'cPickle', 'cProfile', 'cStringIO', 'calendar', 'cd', 'cfmfile', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys', 'commands', 'compileall', 'compiler', 'contextlib', 'cookielib', 'copy', 'copy_reg', 'crypt', 'csv', 'ctypes', 'curses', 'datetime', 'dbhash', 'dbm', 'decimal', 'difflib', 'dircache', 'dis', 'distutils', 'dl', 'doctest', 'dumbdbm', 'dummy_thread', 'dummy_threading', 'email', 'ensurepip', 'errno', 'exceptions', 'fcntl', 'filecmp', 'fileinput', 'findertools', 'fl', 'flp', 'fm', 'fnmatch', 'formatter', 'fpectl', 'fpformat', 'fractions', 'ftplib', 'functools', 'future_builtins', 'gc', 'gdbm', 'gensuitemodule', 'getopt', 'getpass', 'gettext', 'gl', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'hotshot', 'htmlentitydefs', 'htmllib', 'httplib', 'ic', 'icopen', 'imageop', 'imaplib', 'imgfile', 'imghdr', 'imp', 'importlib', 'imputil', 'inspect', 'io', 'itertools', 'jpeg', 'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging', 'macerrors', 'macostools', 'macpath', 'macresource', 'mailbox', 'mailcap', 'marshal', 'math', 'md5', 'mhlib', 'mimetools', 'mimetypes', 'mimify', 'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multifile', 'multiprocessing', 'mutex', 'netrc', 'new', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev', 'parser', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'popen2', 'poplib', 'posix', 'posixfile', 'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'quopri', 'random', 're', 'readline', 'resource', 'rexec', 'rfc822', 'rlcompleter', 'robotparser', 'runpy', 'sched', 'select', 'sets', 'sgmllib', 'sha', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'spwd', 'sqlite3', 'ssl', 'stat', 'statvfs', 'string', 'stringprep', 'struct', 'subprocess', 'sunau', 'sunaudiodev', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'thread', 'threading', 'time', 'timeit', 'token', 'tokenize', 'trace', 'traceback', 'ttk', 'tty', 'turtle', 'types', 'unicodedata', 'unittest', 'urllib', 'urllib2', 'urlparse', 'user', 'uu', 'uuid', 'videoreader', 'warnings', 'wave', 'weakref', 'webbrowser', 'whichdb', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpclib', 'zipfile', 'zipimport', 'zlib'}

# AST analyzer to gather info from Import and ImportFrom nodes
class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats = {"imports":[],"from":[]}

    def visit_Import(self,node):
        for alias in node.names:
            self.stats["imports"].append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self,node):
        for alias in node.names:
            self.stats["from"].append(alias.name)
        self.stats['imports'].append(node.module)
        self.generic_visit(node)

    def report(self):
        imprts = self.stats["imports"]
        return imprts

# The below module collects the packages and modules imported by the script and tries conda installing or pip installing them after it ensures it is not a built in or user defined module, if its not able to conda or pip install then its reported to user
# Takes in a python filepath and its foldername and returns the problematic packages of the script
def get_imports(path,foldername,user_defined_modules):
    import_sets = set()
    with open(path,'r') as source:
            try:
                tree = ast.parse(source.read())
            except Exception as e:
                raise exceptions.CodeError(e.args) # args contain information about syntax error to show to user

            analyzer = Analyzer()
            analyzer.visit(tree)
            imprts  = analyzer.report()
            for i in range(0,len(imprts)):
                import_sets.add(imprts[i].split('.')[0])
    
    packages_to_ask_user = []
    docker_pkgs = []

    for i in import_sets:
        if(not(i in user_defined_modules) and not(i in built_in_modules2) and not(i in built_in_modules3)):
            if(not pypiName(i)):
                docker_pkgs.append(i)
            else:
                packages_to_ask_user.append(i)
                
    return (packages_to_ask_user,docker_pkgs)
