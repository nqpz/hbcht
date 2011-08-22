#!/usr/bin/env python3

# hbcht: a combined interpreter and compiler for the Half-Broken Car in Heavy
# Traffic programming language

# Copyright (C) 2011  Niels Serup

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with This program.  If not, see <http://www.gnu.org/licenses/>.

"""

"""

import sys
import os
from optparse import OptionParser
import array
import random
import io
import re
import collections
import itertools
import locale

def _traverse(it):
    for x in it: pass
(lambda vardict, consts: _traverse(vardict.__setitem__(x, i)
                          for x, i in itertools.zip_longest(
            consts, range(len(consts)))))(
    sys.modules[__name__].__dict__,
    ('NOP', 'DECREMENT', 'INCREMENT', 'PREV', 'NEXT', 'IF', 'GOTO', 'EXIT',
     'CAR',
     'UP', 'RIGHT', 'DOWN', 'LEFT',
     'HBCHT', 'PYTHON', 'C'
     ))

_direction_text_to_const_map = {
    'u': UP, 'r': RIGHT, 'd': DOWN, 'l': LEFT
    }

_direction_to_path_map = {
    UP: 0, RIGHT: 1, DOWN: 2, LEFT: 3
    }

_path_to_dir_map = {
    0: 'up', 1: 'right', 2: 'down', 3: 'left'
    }

_language_text_to_const_map = {
    'py': PYTHON, 'python': PYTHON, 'c': C
    }

_opcode_to_const_map = {ord(k): v for k, v in {
    'v': DECREMENT, '^': INCREMENT, '<': PREV,
    '>': NEXT, '/': IF, '#': EXIT, 'o': CAR
    }.items()}

_valid_directions = (UP, RIGHT, DOWN, LEFT)
_accepted_languages = (HBCHT, PYTHON, C)

class CarError(Exception):
    pass

class CarProgram:
    """
    A Half-Broken Car in Heavy Traffic compiler/interpreter wrapper

    Normal usage:

    >>> c = CarProgram('myprogram.hb')
    >>> c.load_data()
    >>> out = c.run() # if you just want to run it, or
    >>> c.compile('myprogramcompiled.hbc') # if you want to compile it into
                                  # HBCHT's own simple, portable format, or
    >>> c.compile('myprogram.c')  # which will translate it into C code

    Many options are available to make CarProgram adjustable.
    """
    def __init__(self, file=None, data=None, inputastext=False,
                 outputastext=False):
        """
        A file or a data string must be specified.
        """
        self.file, self.data = file, data
        self.inputastext, self.outputastext = inputastext, outputastext

    def load_data(self):
        """Parse data."""
        if not self.file and not self.data:
            raise CarError('no program data')
        if self.file:
            try:
                self.data = self.file.read()
            except AttributeError:
                if self.file == '-':
                    self.file = 0
                with open(self.file, 'rb') as f:
                    self.data = f.read()
        if isinstance(self.data, str):
            self.data = self.data.encode(locale.getpreferredencoding())
        self.metadata = {'inputastext': False, 'outputastext': False}
        self.commands, self.command_beginnings = self._parse_data(self.data)

    def _parse_data(self, data):
        # Header test
        try:
            # data[6] contains version information
            compcond = data[0] == 1 and data[1:6] == b'hbcht' and data[7] == 2
        except IndexError:
            compcond = False
        if compcond:
            return self._extract_commands(data)
        else:
            return self._create_commands(data)

    def _extract_commands(self, data):
        """Extract commands from data that comes from a compiled program"""
        version = data[6]
        if version > 1:
            raise CarError('only version 1 is supported')
        if data[8] == b'\1':
            if self.inputastext is None:
                self.inputastext = True
        if data[9] == b'\1':
            if self.outputastext is None:
                self.outputastext = True
        data = data[9:]
        data = struct.unpack('<' + 'I' * len(data) // 4)
        return data[3:], data[:3]

    def _create_commands(self, data):
        """Create a tuple of commands from source code"""
        lines = []
        for line in data.split(b'\n'):
            if line.startswith(b'@intext'):
                self.metadata['inputastext'] = True
                if self.inputastext is None:
                    self.inputastext = True
            elif line.startswith(b'@outtext'):
                self.metadata['outputastext'] = True
                if self.outputastext is None:
                    self.outputastext = True
            else:
                # remove eventual comment
                m = re.match(br'(.*?);', line)
                if m:
                    line = m.group(1)
                line = line.rstrip()
                if line:
                    lines.append(line)
        if not lines:
            raise CarError('no source code')
        min_indent = len(lines[0]) # temporary
        for line in lines:
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            if indent < min_indent:
                min_indent = indent
        if indent != 0:
            lines = tuple(x[indent:] for x in lines)

        #self.raw_board = '\n'.join(lines) # for an eventual curses simulator

        board = []
        has_car, has_exit = False, False
        y = 0
        for line in lines:
            row = array.array('B')
            for c in line:
                x = 0
                try:
                    op = _opcode_to_const_map[c]
                except KeyError:
                    op = NOP
                if op == CAR:
                    if has_car:
                        raise CarError('program can only have one car')
                    has_car = True
                    car_pos = (x, y)
                    row.append(NOP)
                else:
                    row.append(op)
                if op == EXIT:
                    if has_exit:
                        raise CarError('program can only have one exit')
                    has_exit = True
                x += 1
            board.append(row)
            y += 1
        if not has_car:
            raise CarError('program must have one car')
        if not has_exit:
            raise CarError('program must have one exit')
        return self._board_to_commands(board, car_pos)

    def _board_to_commands(self, board, car_start_pos):
        pos_ids = {}
        commands, begs = [], []
        for direc in _valid_directions:
            begs.append(len(commands))
            self._path_to_commands(board, car_start_pos, direc,
                                   commands, pos_ids)
                    
        begs = begs[1:] # first path always starts at position 0
        return commands, begs

    def _path_to_commands(self, board, car_pos, direc, commands, pos_ids):
        x, y = car_pos
        while True:
            p = board[y][x]
            while p == NOP:
                if direc == UP:
                    y = (y - 1) % len(board)
                elif direc == DOWN:
                    y = (y + 1) % len(board)
                elif direc == RIGHT:
                    x = (x + 1) % len(board[y])
                elif direc == LEFT:
                    x = (x - 1) % len(board[y])
                try:
                    p = board[y][x]
                except IndexError:
                    p = NOP
            pos = pos_ids.get((x, y))
            if pos is not None:
                commands.append((GOTO, pos))
                break
            else:
                pos_ids[(x, y)] = len(commands)
                if p == DECREMENT and direc != LEFT:
                    commands.append((DECREMENT, 1))
                    direc = DOWN
                elif p == INCREMENT and direc != RIGHT:
                    commands.append((INCREMENT, 1))
                    direc = UP
                elif p == PREV and direc != UP:
                    commands.append((PREV, 1))
                    direc = LEFT
                elif p == NEXT and direc != DOWN:
                    commands.append((NEXT, 1))
                    direc = RIGHT
                elif p == IF:
                    ndirec = RIGHT if direc == UP else DOWN if direc == RIGHT else \
                        LEFT if direc == DOWN else UP if direc == LEFT else None
                    cid = len(commands)
                    self._path_to_commands(board, (x, y), ndirec, commands, pos_ids)
                    commands.insert(cid, (IF, len(commands)))
                elif p == EXIT:
                    commands.append((EXIT, 0))
                    break
        
    def run(self, input, bruterun=None, directions=None, format_output=False):
        """Run the program."""
        if bruterun:
            directions = _valid_directions
        elif not directions:
            directions = (random.choice(_valid_directions),)
        else:
            for x in directions:
                if x not in _valid_directions:
                    raise CarError('invalid direction {}'.format(repr(x)))
        paths = tuple(_direction_to_path_map[x] for x in directions)
        if not isinstance(input, collections.Iterable):
            input = (input,)
        if self.inputastext:
            input = tuple(map(ord, ''.join(map(str, input))))
        else:
            ninput = []
            for x in input:
                if isinstance(x, str):
                    ninput.extend(map(ord, x))
                else:
                    ninput.append(x)
            input = ninput

        outs = tuple(self._interpret(path, *input) for path in paths)

        if self.outputastext:
            outs = tuple(''.join(chr(v) for k, v in out) for out in outs)
        else:
            if format_output:
                _fmt = '{{:{}d}}: {{}}'.format(max(len(str(out[i][0]))
                                                   for i in (0, -1)))
                outs = tuple('\n'.join(_fmt.format(k, v) for k, v in out) for out in outs)
        if not format_output:
            return outs
        if len(outs) == 1:
            return outs[0]
        else:
            return '\n\n'.join('{}:\n{}'.format(_path_to_dir_map[i], outs[i])
                               for i in range(len(outs)))

    def _interpret(self, path, *cells):
        cells = collections.defaultdict(int, 
            {i: cells[i] for i in range(len(cells))})
        commands, begs = self.commands, self.command_beginnings
        if path == 0:
            j = 0 ##########
        else:     # current command #
            j = begs[path] ##########
        i= 0 # current cell
        while j < len(commands):
            x, a = commands[j] # operation, argument
            if x == DECREMENT:
                cells[i] -= a
            elif x == INCREMENT:
                cells[i] += a
            elif x == PREV:
                i -= a
            elif x == NEXT:
                i += a
            elif x == IF:
                if cells[i] != cells[i - 1]:
                    j = a # go to the operation in address a
            elif x == GOTO:
                j = a # go to the operation in address a
            elif x == EXIT:
                break
        else:
            # The program jumped to an operation outside its scope
            raise CarError('did not exit program properly; no EXIT code found')
        return sorted(filter(lambda kv: v != 0, cells.items()),
                      key=lambda kv: kv[0])

    def compile(self, outfile=None, language=None, functiononly=False,
                overwrite=False):
        """
        Compile the program into either a custom format, C code, or Python
        code.

        If outfile is None, return the compiled byte string. If functiononly,
        only create the core function, i.e. no command line parsing
        function. If overwrite, overwrite outfile if it exists.
        """
        if isinstance(outfile, str):
            if not overwrite and os.path.exists(outfile):
                raise CarError('output file already exists')
            if not language:
                ext = outfile.rsplit('.', 1)
                if len(ext) == 1:
                    raise CarError('cannot guess language from filename')
                language = ext[-1]
        no_support = False
        if isinstance(language, str):
            try:
                language = _language_text_to_const_map[language.lower()]
            except KeyError:
                no_support = True
        elif language not in _accepted_languages:
            no_support = True
        if no_support:
            raise CarError('no support for language {}'.format(
                    repr(language)))
        if outfile is None:
            f = io.BytesIO()
        elif isinstance(outfile, str):
            if outfile == '-':
                outfile = 1
            f = open(outfile, 'wb')
        self._compile(f, language, functiononly)
        if outfile is None:
            return f.getvalue()
        elif isinstance(outfile, str):
            f.close()

    def _compile(self, f, lang, funconly):
        commands = self.commands
        if lang == HBCHT:
            f.write(b'\1hbcht\1\2' +
                    '\1' if self.metadata['inputastext'] else '\2' +
                    '\1' if self.metadata['outputastext'] else '\2')
            f.write(struct.pack('<III', *command_beginnings))
            for x, a in commands:
                f.write(struct.pack('<II', x, a))

class _SimplerOptionParser(OptionParser):
    """A simplified OptionParser"""

    def format_description(self, formatter):
        self.description = self.description.strip()
        return OptionParser.format_description(self, formatter)

    def format_epilog(self, formatter):
        return self.epilog.strip() + '\n'

    def add_option(self, *args, **kwds):
        try: kwds['help'] = kwds['help'].strip()
        except KeyError: pass
        return OptionParser.add_option(self, *args, **kwds)

def parse_args(cmdargs=None):
    """
    parse_args(cmdargs: [str] = sys.argv[1:])

    Act based on command line arguments.
    """

    if cmdargs is None:
        cmdargs = sys.argv[1:]
    parser = _SimplerOptionParser(
        prog='hbcht',
        usage='Usage: %prog [OPTION]... INFILE [INPUT...|OUTFILE]',
        version='''\
hbcht 0.1.0
Copyright (C) 2011  Niels Serup
License AGPLv3+: GNU AGPL version 3 or later <http://gnu.org/licenses/agpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.\
''',
        description='''
a combined interpreter and compiler for the Half-Broken Car in Heavy Traffic
programming language
''',
        epilog='''
If you specify no options, the Half-Broken Car in Heavy Traffic program in
INFILE will be interpreted, input will be fetched from any command line
arguments after INFILE, and output will be printed to standard out.

When compiling, programs can be compiled into a very simple format consisting
of metadata and little-endian 4-byte blocks which store commands (the default),
C code, or Python code (works as both 2.5+ and 3.x code).

The '-' character can be used to symbolize standard in and/or standard out.

Documentation for the Half-Broken Car in Heavy Traffic language can be found in
the README file that may have accompanied this program, or at
<http://metanohi.name/projects/hbcht/>. Run `pydoc3 hbcht' to see documentation
for using hbcht as a Python module.

Examples:
  Run the program in `test.hb' with the number 4 in the first memory cell:
    hbcht test.hb 4

  Run the right-going path instead of a random path (3 and 11 in the first two
  memory cells):
    hbcht -d right test1.hb 3 11

  Run all paths with the ordinals for A, B, and C in the first three memory
  cells (in ASCII and UTF-8, A, B, C = 65, 66, 67):
    hbcht -b test2.hb ABC

  Do the same, except read what seems like a number as a string (in ASCII and
  UTF-8, 7, 8, 9 = 55, 56, 57):
    hbcht -b -t test2.hb 789

  Run the left and down paths:
    hbcht -d left -d down otherexample.hb 99 13402 11934119203312221

  Compile a program:
    hbcht -c test.hb out.hbc

  Run the compiled program:
    hbcht out.hbc 22

  Compile it into C code:
    hbcht -c test.hb out.c

  Compile it into Python code:
    hbcht -c test.hb out.py

  Compile only the actual hbcht function into C code, i.e. do not create a main
  function (this can also be done with other programming languages):
    hbcht -f -c test.hb out.c

  Compile source code from standard in into C code and send it to standard out:
    hbcht -c - -l c -
''')

    parser.add_option('-b', '--brute-run', dest='bruterun',
                      action='store_true', help='''
run all four paths of the program
''', default=False)

    parser.add_option('-d', '--direction', dest='directions',
                      metavar='l[eft]|r[ight]|d[own]|u[p]',
                      action='append', help='''
run only this path and any other given paths instead of picking one at
random. Can be set more than once.
''', default=[])

    parser.add_option('-l', '--language', dest='language',
                      metavar='LANGUAGE', help='''
choose which language the program should be compiled into. This option is only
necessary if the language cannot be guessed from the file extension of OUTFILE
''')

    parser.add_option('-c', '--compile', dest='compile',
                      action='store_true', help='''
compile the program instead of running it
''', default=False)

    parser.add_option('-f', '--function-only', dest='functiononly',
                      action='store_true', help='''
when compiling, create only the core function, i.e. no command-line argument
parsing
''', default=False)

    parser.add_option('-t', '--input-as-text', dest='inputastext',
                      action='store_true', help='''
see all input as text instead of numbers
''')

    parser.add_option('-T', '--not-input-as-text', dest='inputastext',
                      action='store_false', help='''
do not see all input as text instead of numbers. Overwrites `@intext' command
in program file if present
''')

    parser.add_option('-s', '--output-as-text', dest='outputastext',
                      action='store_true', help='''
show output as a text string instead of a list of numbers
''')

    parser.add_option('-S', '--not-output-as-text', dest='outputastext',
                      action='store_false', help='''
do not show output as a text string instead of a list of numbers. Overwrites
`@outtext' command in program file if present
''')

    parser.add_option('-y', '--overwrite-file', dest='overwrite',
                      action='store_true', help='''
when compiling, overwrite the output file if it exists
''', default=False)

    o, a = parser.parse_args(cmdargs)
    if len(a) < 1 or (o.compile and len(a) < 2):
        parser.error('not enough arguments')
    if o.compile:
        _run = lambda c: c.compile(a[1], language=o.language,
                                   functiononly=o.functiononly,
                                   overwrite=o.overwrite)
    else:
        for i in range(len(o.directions)):
            try:
                o.directions[i] = _direction_text_to_const_map[o.directions[i]]
            except KeyError:
                parser.error('{} is not a valid direction'.format(
                        o.direction[i]))
        _run = lambda c: c.run(a[1:], bruterun=o.bruterun,
                               directions=o.directions, format_output=True)
    try:
        c = CarProgram(file=a[0], inputastext=o.inputastext,
                       outputastext=o.outputastext)
        c.load_data()
        out = _run(c)
    except Exception as e:
        print('hbcht: error:', str(e), file=sys.stderr)
        import traceback
        print(traceback.format_exc().rstrip(), file=sys.stderr)
        sys.exit(1)
    if out is not None:
        print(out)

if __name__ == '__main__':
    parse_args()
