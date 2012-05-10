#!/usr/bin/env python

import os
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
            return pid

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
        self.write(input or "")
        os.close(self.stdin)
        while True:
            c = self.read(1)
            if c:
                yield c
            else:
                break
        os.waitpid(self.pid, 0)
        self.pid = 0

