Half-Broken Car in Heavy Traffic (HBCHT)

+ The car cannot turn left; any relative left turns will be ignored along with
  their memory effects
+ Start values cannot be negative, but end values can
+ The car cannot go out of bound; if it exits to the right, it reenters to the
  left, etc.
+ Values can be arbitrarily large. An interpreter or compiler without this
  feature is valid, but not perfect.

If a program file contains a line that starts with `@intext', it will see input
as text and convert the text to ordinals before running the core function.

If a program file contains a line that starts with `@outtext', it will show
output as a text string instead of a list of numbers.

o car
> go right, next memory cell
< go left, previous memory cell
^ go up, increment
v go down, decrement
/ go right if the current memory cell has the same value as the previous memory
  cell, else continue (if the previous memory cell does not exist, its value is zero)
# exit, return/print (there can only be one exit)
