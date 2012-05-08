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
        from_parent, self.stdin = os.pipe()
        self.stdout, to_parent = os.pipe()

        if os.fork() == 0: # child
            os.dup2(from_parent, STDIN)
            os.dup2(to_parent, STDOUT)
            os.close(self.stdin)
            os.close(self.stdout)
            os.execvp(self.name, self.args)
        else: # parent
            os.close(from_parent)
            os.close(to_parent)

    def read(self, n):
        return os.read(self.stdout, n)

    def write(self, data):
        return os.write(self.stdin, data)

    def __call__(self, input):
        self.write(input)
        os.close(self.stdin)
        output = []
        while True:
            extra = self.read(4096)
            if extra:
                output.append(extra)
            else:
                break
        return "".join(output)

