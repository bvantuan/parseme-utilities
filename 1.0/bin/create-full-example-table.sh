#!/bin/bash

guidelinespath=$1

cd $guidelinespath
find c_* body.html | 
grep "c_.*body.html$" |
sort | 
xargs cat | 
../bin/extractHTMLex.py -
