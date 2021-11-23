from   multiprocessing import Value, Lock

import logging
import sys
import time
import os

clear = '\033[2K\033[1G'
up    = f'{clear}\033[F'
space = '    '
logging.basicConfig(stream = sys.stdout, level = logging.INFO, format = f'{clear}%(asctime)s %(message)s', datefmt = "[%Y-%m-%d %H:%M:%S]")
logging.getLogger().handlers[0].terminator = ''
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)
    
def msg(text, inline = False, delete = 0, indent = 0):
    """
    Verbose message to print.

    Args:
        text (str)    : Message to print to sys.stdout.
        inline (bool) : If True, prints over the current line.
        delete (int)  : Number of previous lines to delete before printing.
        indent (int)  : Number of indentations (4 spaces) to indent text message by.
    """
    text = f'{space * indent}{text}' + ('' if inline else '\n')
    for _ in range(delete):
        logging.info(up)
    logging.info(text)


def print_dict(d):
    """
    Prints contents of dictionary using the msg function.

    Args:
        d (dict) : Dictionary of parameters. 
    """
    m    = max(len(key) for key in d)
    sep  = f'\n{clear}{" " * 23}'
    end  = f'\n{clear}{" " * 22}'
    text = '{' + f'{sep}' + f'{sep}'.join([f'{key:{m}s} : {val}' for key, val in d.items()]) + f'{end}' + '}'
    msg(text)


def _eta(seconds):
    """
    Computes eta in [hours,] minutes, seconds.

    Args:
        seconds (float): Time in seconds.

    Returns:
        str: [hours,] minutes, seconds
    """
    minutes, seconds = divmod(seconds, 60)
    hours  , minutes = divmod(minutes, 60)
    if hours:
        return f'{hours:.0f}h {minutes:02.0f}m {seconds:02.0f}s'
    return f'{minutes:02.0f}m {seconds:02.0f}s'

class Update():
    """
    Update class designed for verbose print outs in loops.
    
    Args:
        obj (object) : Object to iterate over.
        msg (str)    : Base string to print out during object iteration.
        final (str)  : Final string to print out once object has been iterated.
        eta (bool)   : If True, includes estimated eta to print outs.
    """
    def __init__(self, obj, msg = '', final = None, eta = False):
        self.obj   = iter(obj)
        self.msg   = msg
        self._msg  = ''
        self.num   = len(obj)
        self.i     = 0
        self.final = final
        self.eta   = eta
        self.time  = time.time()

    def compute_msg(self):
        per     = self.i / self.num
        msg     = f'{self.msg} {self.i:,d} of {self.num:,d} ({per:.2%})'
        if self.eta and (self.num > self.i > 1):
            delta = time.time() - self.time
            eta   = delta / self.i * (self.num - self.i)
            msg   = f'{msg} | eta {_eta(eta)}'
        self._msg = msg

    def __iter__(self):
        return self

    def __next__(self):
        final = (self.num == self.i)
        if final:
            if self.final:
                msg(self.final)
            raise StopIteration
        self.i += 1
        self.compute_msg()
        msg(self._msg, inline = True)
        return next(self.obj)

class Waiting():

    def __init__(self, during, after, inline = False, delete = 0):
        self.inline = inline
        self.delete = delete
        self.during = during
        self.after  = after
        
    def __enter__(self):
        msg(f'{self.during}', inline = self.inline)

    def __exit__(self, *args):
        msg(f'{self.after}', delete = self.delete)

class Executing(Waiting):

    def __init__(self, file, inline = False, delete = 0):
        super().__init__(f'executing {file}', f'executed {file}', inline, delete)

class Computing(Waiting):

    def __init__(self, file, inline = True, delete = 0):
        super().__init__(f'computing {file}', f'computed {file}', inline, delete)

class Counter():

    def __init__(self, message, verbose = 0):
        self.val      = Value('i', 0)
        self.lock     = Lock()
        self.verbose  = verbose
        self.message  = message

    def increment(self):
        with self.lock:
            self.val.value += 1
            msg(self.message.format(self.val.value), inline = self.val.value % self.verbose if self.verbose else True)

    def value(self):
        with self.lock:
            return self.val.value