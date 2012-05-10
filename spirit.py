#!/usr/bin/env python

import fcntl
import itertools
import os
import select
import shlex
import sys

STDIN  = sys.stdin.fileno()
STDOUT = sys.stdout.fileno()

class Command(object):
    def __init__(self, command):
        self.args = shlex.split(command)
        self.name = self.args[0]
        self.pid = 0

    def _create_subprocess(self):
        from_parent, self.stdin = os.pipe()
        self.stdout, to_parent = os.pipe()

        pid = os.fork()
        if pid == 0: # child
            os.dup2(from_parent, STDIN)
            os.dup2(to_parent, STDOUT)
            os.close(self.stdin)
            os.close(self.stdout)
            os.execvp(self.name, self.args)
        else: # parent
            os.close(from_parent)
            os.close(to_parent)
            self._set_non_blocking(self.stdin)
            self._set_non_blocking(self.stdout)
            return pid

    def _set_non_blocking(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def read(self, n):
        return os.read(self.stdout, n)

    def write(self, data):
        return os.write(self.stdin, data)

    def __call__(self, input=None):
        if self.pid == 0:
            self._create_subprocess()            
        self.write(input or "")
        os.close(self.stdin)
        output = []
        while True:
            extra = self.read(4096)
            if extra:
                output.append(extra)
            else:
                break
        os.waitpid(self.pid, 0)
        self.pid = 0
        return "".join(output)

    def iter(self, input=None):
        if self.pid == 0:
            self._create_subprocess()

        if input is None:
            input = []
        elif isinstance(input, str):
            input = [input]
        def iter_char(iterable):
            for string in iterable:
                for char in string:
                    yield char
        input = iter_char(input)

        readers, writers = [self.stdout], [self.stdin]
        while True:
            if not readers and not writers:
                break
            _readers, _writers, _ = select.select(readers, writers, [])
            if _readers:
                c = os.read(_readers[0], 1)
                if c:
                    yield c
                else:
                    os.close(_readers[0])
                    readers.pop()
            elif _writers:
                try:
                    datum = input.next()
                    os.write(_writers[0], datum)
                except StopIteration:
                    os.close(_writers[0])
                    writers.pop()
        os.waitpid(self.pid, 0)
        self.pid = 0

