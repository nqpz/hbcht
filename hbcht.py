#!/usr/bin/env python3

# hbcht: a combined interpreter and compiler for the Half-Broken Car in Heavy
# Traffic programming language

# Copyright (C) 2011, 2012, 2013  Niels G. W. Serup

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING.txt file or http://www.wtfpl.net/ for more details.

"""
Half-Broken Car in Heavy Traffic is an esoteric programming language, and hbcht
is a reference implementation of a combined compiler/interpreter for the
language.

This program supports both interpreting a program, compiling a program to a
custom binary format and then running the program, compiling it into Python
code, and compiling it into C code.

Note that though this program is covered by the GNU Affero General Public
License, any code generated by it (when compiling) is not. That code is
considered data output by a program. Whoever made this program generate the
code will legally own that code.

The official language documentation is included in the README that comes with
this program and is also available at <http://metanohi.name/projects/hbcht/>.
"""

import sys
import os
from optparse import OptionParser
import array
import random
import io
import struct
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
     'HBCHT', 'PYTHON', 'C', 'BRAINFUCK'
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
    'hbc': HBCHT, 'hbcht': HBCHT, 'py': PYTHON, 'python': PYTHON, 'c': C,
#    'bf': BRAINFUCK, 'brainfuck': BRAINFUCK
    }

_opcode_to_const_map = {ord(k): v for k, v in {
    'v': DECREMENT, '^': INCREMENT, '<': PREV,
    '>': NEXT, '/': IF, '#': EXIT, 'o': CAR
    }.items()}

_valid_directions = (UP, RIGHT, DOWN, LEFT)
_accepted_languages = (HBCHT, PYTHON, C) #, BRAINFUCK)
_base_mem_ops = (DECREMENT, INCREMENT, PREV, NEXT)

_ops_to_dirs_map = {
    DECREMENT: DOWN, INCREMENT: UP, PREV: LEFT, NEXT: RIGHT
    }
_compl_action_map = {
    DECREMENT: INCREMENT, INCREMENT: DECREMENT, PREV: NEXT, NEXT: PREV
    }


# Python code output
####################
_python_code_wrapper = '''\
import sys
import random
import itertools
import collections

def run(*inputs, **kwds):
    format_output = kwds.get('format_output')
{inputsconv}
    for x in inputs:
        if x < 0:
            raise Exception('input values must be non-negative')
    cells = {{}}
    for i in range(len(inputs)):
        cells[i] = inputs[i]
    cells = collections.defaultdict(int, cells)
{codebody}
    action = action_0
    i, j = 0, random.choice((0, {codebeginnings}))
    while True:
        ret = action(i)
        if ret is None:
            break
        action, i = ret
    cells = sorted(filter(lambda kv: kv[1] != 0, cells.items()),
                   key=lambda kv: kv[0])
{outputconv}
    return out
'''
_python_code_wrapper_intext = '''\
    inputs = tuple(map(ord, ''.join(map(str, inputs))))
'''
_python_code_wrapper_not_intext = '''\
    ninputs = []
    for x in inputs:
        try:
            ninputs.append(int(x))
        except ValueError:
            ninputs.extend(map(ord, x))
    inputs = ninputs
'''
_python_code_wrapper_outtext = '''\
    out = ''.join(chr(v) for k, v in cells)
'''
_python_code_wrapper_not_outtext = '''\
    if format_output:
        if cells:
            fmt = '{{0:{0}d}}: {{1}}'.format(max(len(str(
                                             cells[x][0])) for x in (0, -1)))
            out = '\\n'.join(fmt.format(k, v) for k, v in cells)
        else:
            out = '(empty)'
        out += '\\n'
    else:
        out = cells
'''

_python_code_cmdline = b'''
if __name__ == '__main__':
    sys.stdout.write(run(*sys.argv[1:], format_output=True))
'''

###############

# C code output
###############

_c_template = b'''
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <time.h>
#include <string.h>

typedef struct {
    int *items;
    int length;
} IntList;

typedef struct {
    int *items;
    int length;
    int offset;
} HBCHTList;

typedef struct {
    IntList *positive;
    IntList *negative;
} HBCHTCells;

void hbcht_intlist_init(IntList **list) {
    *list = (IntList*) malloc(sizeof(IntList));
    if (*list == NULL) exit(EXIT_FAILURE);
    (*list)->length = 0;
    (*list)->items = (int*) malloc(0);
    if ((*list)->items == NULL) exit(EXIT_FAILURE);
}

void hbcht_list_init(HBCHTList **list) {
    *list = (HBCHTList*) malloc(sizeof(HBCHTList));
    if (*list == NULL) exit(EXIT_FAILURE);
    (*list)->length = 0;
    (*list)->offset = 0;
    (*list)->items = (int*) malloc(0);
    if ((*list)->items == NULL) exit(EXIT_FAILURE);
}

void hbcht_cells_init(HBCHTCells **cells) {
    *cells = (HBCHTCells*) malloc(sizeof(HBCHTCells));
    if (*cells == NULL) exit(EXIT_FAILURE);
    hbcht_intlist_init(&((*cells)->positive));
    hbcht_intlist_init(&((*cells)->negative));
}

void hbcht_intlist_destroy(IntList *list) {
    free(list->items);
    free(list);
}

void hbcht_list_destroy(HBCHTList *list) {
    free(list->items);
    free(list);
}

void hbcht_cells_destroy(HBCHTCells *cells) {
    hbcht_intlist_destroy(cells->positive);
    hbcht_intlist_destroy(cells->negative);
    free(cells);
}

void hbcht_intlist_append(IntList *list, int num) {
    list->length++;
    list->items = (int*) realloc(list->items, sizeof(int) * list->length);
    if (list->items == NULL) exit(EXIT_FAILURE);
    list->items[list->length - 1] = num;
}

void hbcht_inc_cell_list(IntList *list, int pos, int inc) {
    int i, olen;
    if (pos < list->length)
        list->items[pos] += inc;
    else {
        olen = list->length;
        list->length += pos - list->length + 1;
        list->items = (int*) realloc(list->items, sizeof(int)
                                     * list->length);
        if (list->items == NULL) exit(EXIT_FAILURE);
        for (i = olen; i < list->length - 1; i++)
            list->items[i] = 0;
        list->items[list->length - 1] = inc;
    }
}

void hbcht_inc_cell(HBCHTCells *cells, int pos, int inc) {
    if (pos >= 0)
        hbcht_inc_cell_list(cells->positive, pos, inc);
    else
        hbcht_inc_cell_list(cells->negative, -pos - 1, inc);
}

void hbcht_dec_cell(HBCHTCells *cells, int pos, int dec) {
    hbcht_inc_cell(cells, pos, -dec);
}

int hbcht_get_cell_value(HBCHTCells *cells, int pos) {
    if (0 <= pos && pos < cells->positive->length)
        return cells->positive->items[pos];
    else if (-cells->negative->length - 1 < pos && pos < 0)
        return cells->negative->items[-pos - 1];
    else
        return 0;
}

HBCHTList* hbcht_cells_to_list(HBCHTCells *cells) {
    HBCHTList *l;
    int *tl;
    int i, j;
    hbcht_list_init(&l);

    l->length = cells->negative->length + cells->positive->length;
    if (l->length == 0)
        return l;

    l->offset = cells->negative->length;
    l->items = (int*) realloc(l->items, sizeof(int) * l->length);
    if (l->items == NULL) exit(EXIT_FAILURE);
    i = 0;
    for (j = cells->negative->length - 1; j >= 0; j--, i++) {
        l->items[i] = cells->negative->items[j];
    }
    for (j = 0; j < cells->positive->length; j++, i++) {
        l->items[i] = cells->positive->items[j];
    }

    j = l->length;
    for (i = l->length - 1; i >= 0; i--) {
        if (l->items[i] == 0)
            (l->length)--;
        else
            break;
    }
    if (l->length == 0)
        return l;
    if (j != l->length) {
        l->items = (int*) realloc(l->items, sizeof(int) * l->length);
        if (l->items == NULL) exit(EXIT_FAILURE);
    }
    return l;
}

HBCHTList* hbcht_run(int inputs[], int length) {
    HBCHTCells *cells;
    HBCHTList *list;
    int i, random;
    srand(time(NULL));
    random = rand() % 4;
    hbcht_cells_init(&cells);
    for (i = 0; i < length; i++) {
        if (inputs[i] < 0)
            return NULL;
        hbcht_inc_cell(cells, i, inputs[i]);
    }
    i = 0;

    HBCHT_BODY;

 hbchtposend:
    list = hbcht_cells_to_list(cells);
    hbcht_cells_destroy(cells);
    return list;
}

char* hbcht_run_format(int inputs[], int length) {
    HBCHTList *a = hbcht_run(inputs, length);
    char *retstr;
    int i;
    if (a == NULL)
        return NULL;
    #ifdef OUTPUTASTEXT
    retstr = (char*) malloc(sizeof(char) * (a->length + 1));
    if (retstr == NULL) exit(EXIT_FAILURE);
    int j;
    for (i = 0, j = 0; j < a->length; j++) {
        if (a->items[j] != 0) {
            retstr[i] = (char) a->items[j];
            i++;
        }
    }
    retstr[i] = '\\0';
    #else
    if (a->length > 0) {
        int slen, slentmp;
        char fmt[10];
        char tstr[12];
        char rtstr[25];
        sprintf(tstr, "%d", -a->offset);
        slen = strlen(tstr);
        sprintf(tstr, "%d", a->length - a->offset);
        slentmp = strlen(tstr);
        if (slentmp > slen)
            slen = slentmp;
        sprintf(fmt, "%%%dd: %%d\\n", slen);
        retstr = (char*) malloc(sizeof(char) * (a->length * 25 + 1));
        slen = 0;
        for (i = 0; i < a->length; i++) {
            if (a->items[i] != 0) {
                sprintf(rtstr, fmt, i - a->offset, a->items[i]);
                slentmp = strlen(rtstr);
                strcpy(retstr, rtstr);
                retstr += slentmp;
                slen += slentmp;
            }
        }
        retstr -= slen;
    }
    else {
        retstr = (char*) malloc(sizeof(char) * 8);
        strcpy(retstr, "(empty)");
    }
    #endif
    hbcht_list_destroy(a);
    return retstr;
}

IntList* hbcht_text_to_ints(char* argv[], int argc) {
    IntList *l;
    int i, j;
    hbcht_intlist_init(&l);

    #ifdef INPUTASTEXT
    for (i = 0; i < argc; i++) {
        j = 0;
        while (argv[i][j] != '\\0') {
            hbcht_intlist_append(l, argv[i][j]);
            j++;
        }
    }
    #else
    char *end;
    int num;
    for (i = 0; i < argc; i++) {
        errno = 0;
        num = (int) strtol(argv[i], &end, 10);
        if (!(errno != 0 || *end != 0 || end == argv[i]))
            hbcht_intlist_append(l, num);
        else {
            j = 0;
            while (argv[i][j] != '\\0') {
                hbcht_intlist_append(l, argv[i][j]);
                j++;
            }
        }
    }
    #endif
    return l;
}
'''

_c_template_mainfunc = b'''
int main (int argc, char* argv[]) {
    IntList *il = hbcht_text_to_ints(++argv, argc - 1);
    char *result = hbcht_run_format(il->items, il->length);
    int ret;
    hbcht_intlist_destroy(il);
    if (result == NULL) {
        fprintf(stderr, "input values must be non-negative\\n");
        ret = EXIT_FAILURE;
    }
    else {
        printf("%s", result);
        ret = EXIT_SUCCESS;
    }
    free(result);
    return ret;
}
'''

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
    def __init__(self, file=None, data=None, inputastext=None,
                 outputastext=None):
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
        if data[8] == 1:
            if self.inputastext is None:
                self.inputastext = True
        if data[9] == 1:
            if self.outputastext is None:
                self.outputastext = True
        data = data[10:]
        data = struct.unpack('<' + 'I' * (len(data) // 4), data)
        commands = tuple((data[i], data[i + 1]) for i in range(3, len(data), 2))
        for x, a in filter(lambda x: x[0] in (GOTO, IF), commands):
            if a >= len(commands):
                raise CarError('code position out of scope')
        return commands, data[:3]

    def _create_commands(self, data):
        """Create a tuple of commands from source code"""
        lines = []
        idone, odone = False, False
        for line in data.split(b'\n'):
            if line.startswith(b'@intext'):
                if self.inputastext is None:
                    self.metadata['inputastext'] = True
                    self.inputastext = True
                idone = True
            elif line.startswith(b'@outtext'):
                if self.outputastext is None:
                    self.metadata['outputastext'] = True
                    self.outputastext = True
                odone = True
            else:
                # remove eventual comment
                m = re.match(br'(.*?);', line)
                if m:
                    line = m.group(1)
                line = line.rstrip()
                if line:
                    lines.append(line)
        if not idone:
            if self.inputastext:
                self.metadata['inputastext'] = True
        if not odone:
            if self.outputastext:
                self.metadata['outputastext'] = True
        if not lines:
            raise CarError('no source code')
        min_indent = len(lines[0]) # temporary
        for line in lines:
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            if indent < min_indent:
                min_indent = indent
        else:
            lines = tuple(x[min_indent:] for x in lines)

        #self.raw_board = '\n'.join(lines) # for an eventual curses simulator

        board = []
        has_car, has_exit = False, False
        y = 0
        for line in lines:
            row = array.array('B')
            x = 0
            for c in line:
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
        commands, begs, xys = [], [], [None]
        for direc in _valid_directions:
            begs.append(len(commands))
            self._path_to_commands(board, car_start_pos, direc,
                                   commands, xys, pos_ids)
        begs = begs[1:] # first path always starts at position 0
        return commands, begs

    def _path_to_commands(self, board, car_pos, direc, commands, xys, pos_ids):
        x, y = car_pos
        begin_pos = len(commands)
        while True:
            p = NOP
            while p == NOP:
                if direc == UP:
                    y = (y - 1) % len(board)
                elif direc == DOWN:
                    y = (y + 1) % len(board)
                elif direc == RIGHT:
                    x = (x + 1) % len(board[y])
                elif direc == LEFT:
                    x = (x - 1) % len(board[y])
                p = board[y]
                try:
                    p = p[x]
                except IndexError:
                    p = NOP
            action = None
            if p == DECREMENT and direc != LEFT:
                action = DECREMENT
            elif p == INCREMENT and direc != RIGHT:
                action = INCREMENT
            elif p == PREV and direc != UP:
                action = PREV
            elif p == NEXT and direc != DOWN:
                action = NEXT
            elif p == IF:
                action = IF
            elif p == EXIT:
                commands.append((EXIT, 0))
                break
            if action:
                pc = commands[-1] if commands else (None, None)
                pcx, pca = pc
                aok = action in _base_mem_ops
                if aok:
                    direc = _ops_to_dirs_map[action]
                if aok and pcx == action:
                    pc[1] += 1
                elif aok and pcx == _compl_action_map[action]:
                    if pca > 1:
                        pc[1] -= 1
                    else:
                        del commands[-1]
                        pp = xys[-1]
                        if pp:
                            del pos_ids[pp]
                            del xys[-1]
                else:
                    pos = pos_ids.get((x, y))
                    if pos is not None:
                        if pos >= begin_pos and not IF in (x for x, a in commands[pos:]):
                            raise CarError('infinite loop present')
                        commands.append((GOTO, pos))
                        break
                    if action in _base_mem_ops:
                        pos_ids[(x, y)] = len(commands)
                        xys.append((x, y))
                    if action == DECREMENT:
                        commands.append([DECREMENT, 1])
                    elif action == INCREMENT:
                        commands.append([INCREMENT, 1])
                    elif action == PREV:
                        commands.append([PREV, 1])
                    elif action == NEXT:
                        commands.append([NEXT, 1])
                    elif action == IF:
                        ndirec = RIGHT if direc == UP else DOWN if direc == RIGHT else \
                            LEFT if direc == DOWN else UP if direc == LEFT else None
                        cid = len(commands)
                        commands.append((None, None)) # temporary
                        xys.append((x, y))
                        pos_ids[(x, y)] = len(commands) - 1
                        self._path_to_commands(board, (x, y), ndirec, commands, xys, pos_ids)
                        commands[cid] = (IF, len(commands))
        
    def run(self, input, bruterun=False, directions=None, format_output=False):
        """
        run(input:list, bruterun:bool=False, directions:[dir]|dir,
            format_output:bool=False)
        
        Run the program. If directions is None, pick the car's start direction
        at random (what the language documentation specifies).
        """
        if bruterun:
            directions = _valid_directions
        elif not directions:
            directions = (random.choice(_valid_directions),)
        else:
            if not isinstance(directions, collections.Iterable):
                directions = (directions,)
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
                if outs[0]:
                    _fmt = '{{:{}d}}: {{}}'.format(max(max(len(str(
                                        out[i][0])) for i in (0, -1)) for out in outs))
                    outs = tuple('\n'.join(_fmt.format(k, v) for k, v in out)
                                 for out in outs)
                else:
                    outs = tuple('(empty)' for out in outs)
        if not format_output:
            return outs
        if len(outs) == 1:
            if self.outputastext:
                return outs[0]
            else:
                return outs[0] + '\n'
        else:
            return '\n'.join('{}:\n{}{}'.format(_path_to_dir_map[i], outs[i], '\n'
                                                if not self.outputastext else '')
                             for i in range(len(outs)))

    def _interpret(self, path, *cells):
        cells = collections.defaultdict(int, 
            {i: cells[i] for i in range(len(cells))})
        commands, begs = self.commands, self.command_beginnings
        if path == 0:
            j = 0 ######
        else:     # current command #
            j = begs[path - 1] ######
        i= 0 # current cell
        while True:
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
                    continue
            elif x == GOTO:
                j = a # go to the operation in address a
                continue
            elif x == EXIT:
                break
            j += 1
        return sorted(filter(lambda kv: kv[1] != 0, cells.items()),
                      key=lambda kv: kv[0])

    def compile(self, outfile=None, language='hbc', functiononly=False,
                overwrite=False):
        """
        Compile the program into either the custom HBC format, C code, or
        Python code.

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
        begs = self.command_beginnings
        inptext, outtext = self.metadata['inputastext'], \
            self.metadata['outputastext']
        {
            HBCHT: self._hbcht_compile,
            PYTHON: self._python_compile,
            C: self._c_compile,
            BRAINFUCK: self._pseudo_brainfuck_compile
        }[lang](f, funconly, commands, begs, inptext, outtext)

    @staticmethod
    def _hbcht_compile(f, funconly, commands, begs, inptext, outtext):
        f.write(b'\1hbcht\1\2' +
                (b'\1' if inptext else b'\2') +
                (b'\1' if outtext else b'\2'))
        f.write(struct.pack('<III', *begs))
        for x, a in commands:
            f.write(struct.pack('<II', x, a))

    @staticmethod
    def _get_gotos(commands):
        return set(sorted(a for x, a in filter(
                    lambda kv: kv[0] in (GOTO, IF) and kv[1] != 0, commands)))

    @staticmethod
    def _python_compile(f, funconly, commands, begs, inptext, outtext):
        gotos = CarProgram._get_gotos(commands)
        code, ddd, dd, d = '', ' ' * 0, ' ' * 4, ' ' * 8
        code += dd + 'def action_0(i):\n'
        j = 0
        last_had_skip = False
        for x, a in commands:
            if j in begs:
                code += dd + 'def action_{}(i):\n'.format(j)
            elif j in gotos:
                if not last_had_skip:
                    code += d + 'return (action_{j}, i)\n'.format(j=j)
                code += dd + 'def action_{j}(i):\n'.format(j=j)
            if x == DECREMENT:
                code += d + 'cells[i] -= {}\n'.format(a)
            elif x == INCREMENT:
                code += d + 'cells[i] += {}\n'.format(a)
            elif x == PREV:
                code += d + 'i -= {}\n'.format(a)
            elif x == NEXT:
                code += d + 'i += {}\n'.format(a)
            elif x == GOTO:
                code += d + 'return (action_{}, i)\n'.format(a)
            elif x == IF:
                code += d + 'if cells[i] != cells[i - 1]:\n' + \
                    d + dd + 'return (action_{}, i)\n'.format(a)
            elif x == EXIT:
                code += d + 'return None\n'
                if not j + 1 in begs and j + 1 not in gotos:
                    code += dd + 'def action_{}(i):\n'.format(j + 1)
            last_had_skip = x in (GOTO, EXIT)
            j += 1

        if not funconly:
            f.write(b'#!/usr/bin/env python\n')
        f.write(b'# Generated by hbcht <http://metanohi.name/projects/hbcht/>\n')
        f.write(_python_code_wrapper.format(
                inputsconv=_python_code_wrapper_intext if inptext else
                _python_code_wrapper_not_intext,
                outputconv=_python_code_wrapper_outtext if outtext else
                _python_code_wrapper_not_outtext,
                codebeginnings=', '.join(map(str, begs)),
                codebody=code
                ).encode())
        if not funconly:
            f.write(_python_code_cmdline)

    @staticmethod
    def _pseudo_brainfuck_compile(f, funconly, commands, begs, inptext, outtext):
        raise Exception('compiler not implented yet')
        # These are just mutterings.
        gotos = CarProgram._get_gotos(commands)
        code = ''
        code += '0\n'
        j = 0
        last_had_skip = False
        for x, a in commands:
            if j in begs:
                code += '\n{}:'.format(j)
            elif j in gotos:
                if not last_had_skip:
                    code += '{j}'.format(j=j)
                code += '\n{j}:'.format(j=j)
            if x == DECREMENT:
                code += '-' * a
            elif x == INCREMENT:
                code += '+' * a
            elif x == PREV:
                code += '<' * a
            elif x == NEXT:
                code += '>' * a
            elif x == GOTO:
                code += '{}'.format(a)
            elif x == IF:
                code += '''
<[)+>+<(-])>[-<(+)>]<(>
[)+>+<(-])>[-<(+)>]
<[->-<]
[[-]<[-]>({}][-]<[-]>(
'''.format(a)
            elif x == EXIT:
                code += '#'
                if not j + 1 in begs and j + 1 not in gotos:
                    code += '\n{}:'.format(j + 1)
            last_had_skip = x in (GOTO, EXIT)
            j += 1

        f.write(b'// Start in one of these states: 0, ' + ', '.join(map(str, begs)).encode() + b'\n')
        f.write(code.encode())
            
    @staticmethod
    def _c_compile(f, funconly, commands, begs, inptext, outtext):
        f.write(b'// Generated by hbcht <http://metanohi.name/projects/hbcht/>\n')
        if inptext:
            f.write(b'#define INPUTASTEXT\n')
        if outtext:
            f.write(b'#define OUTPUTASTEXT\n')
        ht = 'hbchtpos'
        write = lambda t: f.write(t.encode())
        f.write(b'#define HBCHT_BODY \\\n')
        write('switch (random) {{ \\\ncase 0: goto {}0; break; \\\n'.format(ht));
        for i in range(len(begs)):
            write('case {i}: goto {h}{x}; break; \\\n'.format(i=i + 1, x=begs[i], h=ht));
        f.write(b'} \\\n');

        gotos = CarProgram._get_gotos(commands)
        j = 0
        last_had_skip = False
        write('{}0: \\\n'.format(ht))
        for x, a in commands:
            if j in begs:
                write('{}{}: \\\n'.format(ht, j))
            elif j in gotos:
                if not last_had_skip:
                    write('goto {h}{j}; \\\n'.format(h=ht, j=j))
                write('{h}{j}: \\\n'.format(h=ht, j=j))
            if x == DECREMENT:
                write('hbcht_dec_cell(cells, i, {}); \\\n'.format(a))
            elif x == INCREMENT:
                write('hbcht_inc_cell(cells, i, {}); \\\n'.format(a))
            elif x == PREV:
                write('i -= {}; \\\n'.format(a))
            elif x == NEXT:
                write('i += {}; \\\n'.format(a))
            elif x == GOTO:
                write('goto {}{}; \\\n'.format(ht, a))
            elif x == IF:
                write('if (hbcht_get_cell_value(cells, i) != \
hbcht_get_cell_value(cells, i - 1)) \\\n    goto {}{}; \\\n'.format(ht, a))
            elif x == EXIT:
                write('goto {}end; \\\n'.format(ht))
                if not j + 1 in begs and j + 1 not in gotos:
                    write('{}{}: \\\n'.format(ht, j + 1))
            j += 1
            last_had_skip = x in (GOTO, EXIT)
        
        f.write(_c_template)
        if not funconly:
            f.write(_c_template_mainfunc)

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
C code, or Python code (works as both 2.6+ and 3.x code).

The '-' character can be used to symbolize standard in and/or standard out.

Documentation for the Half-Broken Car in Heavy Traffic language can be found in
the README file that may have accompanied this program, or at
<http://metanohi.name/projects/hbcht/>. Run `pydoc3 hbcht' to see documentation
for using hbcht as a Python module.

Note that though this program is covered by the GNU Affero General Public
License, any code generated by it (when compiling) is not. That code is
considered data output by a program. Whoever made this program generate the
code will legally own that code.

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
necessary if the language cannot be guessed from the file extension of
OUTFILE. Valid choices: python, c, bf, hbc
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
                o.directions[i] = _direction_text_to_const_map[
                    o.directions[i][0].lower()]
            except KeyError:
                parser.error('{} is not a valid direction'.format(
                        o.directions[i]))
        inputs = []
        for x in a[1:]:
            try:
                inputs.append(int(x))
            except ValueError:
                inputs.append(x)
        _run = lambda c: c.run(inputs, bruterun=o.bruterun,
                               directions=o.directions, format_output=True)
    try:
        c = CarProgram(file=a[0], inputastext=o.inputastext,
                       outputastext=o.outputastext)
        c.load_data()
        out = _run(c)
        if out is not None:
            print(out, end='')
    except CarError as e:
        print('hbcht: error:', str(e), file=sys.stderr)
    except Exception as e:
        print('hbcht: error:', str(e), file=sys.stderr)
        import traceback
        print(traceback.format_exc().rstrip(), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    parse_args()
