; Multiplication in cells: #0 = #0 * #1

; NOTE: I really don't want to implement this, but it is possible.

; How it would work (with input values 3 and 5):
; #-2 #-1 #00 #01 #02 #03
;   0   0   3   5   0   0
;   3   0   0   5   0   0
;   3   0   0   5   5   0
;   3   0   5   0   5   0
;   3   0   5   0   0   5
;   2   0   5   0   0   5
;   2   0   0   5   0   5
;   2   0   0   5   5   5
;   2   0   5   0   5   5
;   2   0   5   0   0  10
;   1   0   5   0   0  10
;   1   0   0   5   0  10
;   1   0   0   5   5  10
;   1   0   5   0   5  10
;   1   0   5   0   0  15
;   0   0   5   0   0  15
;   0   0   0   0   0  15
;   0   0  15   0   0   0


; I tried implementing it, but I realized it was too stupid and stopped:
       v
 >v    < v
      >^ <
    >vo>>^<
      v
      v
     v>^<
     >^ ^<
     ^v
  >v <<
      ^
  >>/>^<
  ^^v  v
    >v<<
       ^
   >>/>^<
   ^^#
