#!/usr/bin/python3
#This script splits a text file in the .conllu or .cupt format
#into subfiles each of which does not exceed a certain size (in MBs).
#Sentences integrity and order are preserved.
#Parameters:
#  $1 = file to split 
#  $2 = maximum size in MB 
#The subfiles are named like the original file with .1, .2, etc. extensions
#Sample call
#    ./split-conllu.py test.cupt 4

import sys

########################"
# Read and return one sentence from a .conllu or a .cupt file
def readSent(f):
   curr_sent = ""
   while True:
      line = f.readline()
      curr_sent = curr_sent + line
      if not line or line in ['\n', '\r\n']:  #If empty line, the sentence is finished
         return curr_sent

#################
# total arguments
argc = len(sys.argv)

#Process command line parameters
file = sys.argv[1]
maxMb = int(sys.argv[2])
#print("file", file)
#print("maxMb", maxMb)

#Initialisations
#Maximum size of a file in bytes
#maxSize = maxMb * pow(2,20)
maxSize = maxMb * 1000000
print("maxSize=",maxSize)
currSize = 0  #Size of the current file in bytes
currSentSize = 0  #Size of the current sentence
newSize = 0   #Size of the current file after adding the new sentence
currFileIndex = 1   #Index of the current file to create
currOutFile = file + "." + str(currFileIndex)
#print ("currOutFile=", currOutFile)

with open(file) as f:
   outFile = open(currOutFile, "w")
   currSent = readSent(f)
   while currSent != "":
      currSentSize = len(currSent.encode('utf-8'))
      newSize = currSize + currSentSize
      #print("currSentSize=",currSentSize," currSize=", currSize," newSize=",newSize," maxSize=",maxSize)
      if newSize >= maxSize:
         outFile.close()
         currFileIndex = currFileIndex + 1
         currOutFile = file + "." + str(currFileIndex)
         outFile = open(currOutFile, "w")
         currSize = 0
         #print("newSize=",newSize, " currSize=", currSize)
      outFile.write(currSent)
      currSize = currSize + currSentSize
      currSent = readSent(f)

