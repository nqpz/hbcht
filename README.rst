========================================
Half-Broken Car in Heavy Traffic (HBCHT)
========================================

Half-Broken Car in Heavy Traffic is a difficult programming language with only
5 combined operators and direction "signs" for 2D grids.

hbcht is a Python 3.1+ combined compiler/interpreter for the language.

License
=======

mege is free software under the terms of the Do What The Fuck You Want To Public
License (WTFPL); see the file COPYING.txt. The author of mege is Niels G. W. Serup,
contactable at ngws@metanohi.name.

Contact
=======

The author of hbcht is Niels G. W. Serup. Bug reports and suggestions should be sent
to ngws@metanohi.name for the time being.


Installation
============

Get the newest version of hbcht at
https://github.com/nqpz/hbcht/

Extract hbcht from the downloaded file, cd into it and run this in a
terminal::

  # python3 setup.py install


Language documentation
======================

This is the official documentation of HBCHT.

HBCHT is a 2D grid-based programming language. You are a car fighting to get to
the exit of a very chaotic highway. You have to follow the signs, but whenever
you do that, you also change your memory. The value of your current memory cell
can be incremented or decremented and your memory cell index can change. You
can also find signs that tell you to turn either right or not turn at all,
depending on your memory.

The car can drive in four directions: up, right, down, and left. Because of the
chaos, you never know which direction the car is headed when the program
starts. This makes it easy to randomize the output.

To make things worse (actually, it's to make programming in HBCHT possible), you
cannot turn left (relative to your current direction) because your car is
half-broken. You can drive straight ahead, you can turn right, and you can
reverse.

Markers
-------

::

  o car
  # exit, return/print


Operations
----------

::

  > go right, next memory cell
  < go left, previous memory cell
  ^ go up, increment
  v go down, decrement
  / go right if the current memory cell has the same value as the previous
    memory cell, else continue (if the previous memory cell does not exist,
    its value is zero)

Rules
-----
+ There can be only one car and only one exit
+ The car cannot turn left; any relative left turns will be ignored along with
  their memory effects
+ The program always starts at memory cell #0
+ All memory cells have the value 0 by default
+ Input values cannot be negative, but values returned by a program can
+ The car cannot go out of bound; if it exits to the right, it reenters to the
  left, etc.
+ Values cannot be input to memory cells below memory cell #0, but the program
  can set values in these
+ Values can be arbitrarily large. An interpreter or compiler without this
  feature is valid, but not perfect (note that hbcht's C translator uses
  32-bit ints and is thereby not perfect).

A semicolon denotes a comment. Anything from the semicolon to the end of the
line is ignored.

If a program file contains a line that starts with ``@intext``, it will see
input as text and convert the text to ordinals before running the core
function.

If a program file contains a line that starts with ``@outtext``, it will show
output as a text string instead of a list of numbers.


Use
===

As a command-line tool
----------------------

Run ``hbcht`` to use it. Run ``hbcht --help`` to see how to use it.

As a module
-----------

To find out how to use it, run::

  $ pydoc3 hbcht


Examples
--------

There are a few examples in the ``examples`` directory.
