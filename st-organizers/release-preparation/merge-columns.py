#!/usr/bin/python3
#This script merges two .cupt files in that some columns from the first files are repleaced with the corresponding column from the 2nd file
#Both files must have exctly the same sentences in the same order and the same comments.
#Parameters:
#  $1 = file with columns to be replaced 
#  $2 = file with data to put into file $11 
#  $3 = column to be copied from $2 to $1
#Sample call
#    ./merge-columns.py train.cupt train.udpipe-2.10.cupt 3 (copies the LEMMA command)

import argparse

import sys

#declare CUPT_COLUMNS = ["ID", "FORM", "LEMMA", "UPOS", "XPOS", "FEATS", "HEAD", "DEPREL", "DEPS", "MISC", "PARSEME:MWE"]

#################
# total arguments
parser = argparse.ArgumentParser(description="This script merges two .cupt files in that some columns from the first files are replaced with the corresponding columns from the 2nd file",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("fileToUpdate", help="File in which some columns are to be replaced")
parser.add_argument("updateSource", help="File from which some columns are to be take and inserted into the toUpdate file")
parser.add_argument("column", type=int, help="Column to be copied from updateSource to fileToUpdate")
args = parser.parse_args()
config = vars(args)
#print(config)
if (int(sys.argv[3]) > 11):
   print("The number of the column to replace should not be more than 11")
   exit(-1)
col=int(sys.argv[3])

#Process command line parameters
fileTo = open(sys.argv[1], "r")
#print("fileTo=", fileTo)
fileFrom = open(sys.argv[2], "r")

lineTo = fileTo.readline()
lineFrom = fileFrom.readline()

while lineTo:
   if (lineTo.startswith("#") or (lineTo in ['\n', '\r\n'])):
      print(lineTo, end='')
   else:
      lineToSplit = lineTo.split("\t")
      #print(lineToSplit)
      lineFromSplit = lineFrom.split("\t")
      #print(lineFromSplit)
      valueToInsert = lineFromSplit[col-1]
      lineToSplit[col-1] = valueToInsert
      lineNew = '\t'.join(lineToSplit)
      print(lineNew, end='')
   lineTo = fileTo.readline()
   lineFrom = fileFrom.readline()





