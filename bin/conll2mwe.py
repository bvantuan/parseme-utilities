#! /usr/bin/env python3

#import csv
import argparse
import sys
import os
import re

def getNextConllSentence(tsv_content):
    sentenceBlock = []
    for line in tsv_content:
        if line.strip()=='':
            if sentenceBlock:
                return sentenceBlock
            continue
        row = line.strip().split('\t')
        if len(row)>0 and re.match('[0-9]',row[0][0]):
            sentenceBlock.append(row)
    return None

#-----------------------------
# fileds in conllSentence:
# 0: rank
# 1: surface
# 3: coarse PoS (V for verbs) see http://www.corpusitaliano.it/static/documents/POS_ISST-TANL-tagset-web.pdf
# 4: fine PoS (for nsp)
#
# output should have the following fields: 
# 0: rank
# 1: surface
# 2: nsp
# 3: mwe
# 4: pos
#
# For nsp we check if the current or following surface token is a specific punctuation char  
##-----------------------------
def convertConllSentenceItalian(conllSentence):
    parsemeTsvSentence = []
    for row in conllSentence:
        rank = row[0]
        surface = row[1]
        output_row = [rank, surface, '', '']
        if row[3]=='V':
            output_row.append('V')
        # if current is clitic pronoun (PC) and previous ends with '-' join them together
        if row[4]=="PC" and parsemeTsvSentence and parsemeTsvSentence[-1][1].endswith('-'):
            parsemeTsvSentence[-1][1] = parsemeTsvSentence[-1][1][:-1] + surface
            continue
        # if current ends with apostrophe or previous is [(]+ the current word should have nsp
        if surface.endswith("'") or re.match('[(]',surface):
            output_row[2]='nsp'
        # if current is [,;:.?!)]+ the previous word should have nsp         
        if parsemeTsvSentence and re.match('[,;:.?!)]+',row[1]):
            parsemeTsvSentence[-1][2]='nsp'           
        parsemeTsvSentence.append(output_row)
    return parsemeTsvSentence

def removeSubtokens(parsemeTsvSentence):    
    newParsemeTsvSentence = []
    to_skip = 0
    for r in parsemeTsvSentence:
        if to_skip > 0: # skip current sub-token
            to_skip -= 1
            continue
        newParsemeTsvSentence.append(r)
        rank = r[0]
        if '-' in rank:
            indexes = [int(i) for i in rank.split('-')]
            assert len(indexes)==2
            to_skip = indexes[1]-indexes[0]+1 # '3-4' -> 4-3+1=2, '3-5' -> 5-3+1=3 
    return newParsemeTsvSentence

#-----------------------------
# fileds in conllSentence:
# 0: rank
# 1: surface
# 3: coarse PoS (V for verbs) see http://www.corpusitaliano.it/static/documents/POS_ISST-TANL-tagset-web.pdf
# 4: fine PoS (for nsp)
#
# output should have the following fields: 
# 0: rank
# 1: surface
# 2: nsp
# 3: mwe
# 4: pos
#
# For nsp we check if the current or following surface token is a specific punctuation char  
##-----------------------------
def convertConllSentenceSpanish(conllSentence):
    parsemeTsvSentence = []
    for row in conllSentence:
        rank = row[0]
        surface = row[1]
        output_row = [rank, surface, '', '']
        if row[3]=='VERB':
            output_row.append('V')
        # if current ends with apostrophe or previous is [(]+ the current word should have nsp
        if surface.endswith("'") or re.match('[(]',surface):
            output_row[2]='nsp'
        # if current is [,;:.?!)]+ the previous word should have nsp         
        if parsemeTsvSentence and re.match('[,;:.?!)]+',row[1]):
            parsemeTsvSentence[-1][2]='nsp'           
        parsemeTsvSentence.append(output_row)
    removeSubtokens(parsemeTsvSentence)
    return parsemeTsvSentence

#-----------------------------
# fileds in conllSentence:
# 0: rank
# 1: surface
# 3: coarse PoS (V for verbs) see http://www.corpusitaliano.it/static/documents/POS_ISST-TANL-tagset-web.pdf
# 4: fine PoS (for nsp)
#
# output should have the following fields: 
# 0: rank
# 1: surface
# 2: nsp
# 3: mwe
# 4: pos
#
# For nsp we check if the current or following surface token is a specific punctuation char  
##-----------------------------
def convertConllSentenceFrench(conllSentence):
    parsemeTsvSentence = []
    for row in conllSentence:
        rank = row[0]
        surface = row[1]
        output_row = [rank, surface, '', '']
        if row[3]=='VERB':
            output_row.append('V')
        # if current ends with apostrophe or previous is [(]+ the current word should have nsp
        if surface.endswith("'") or re.match('[(]',surface):
            output_row[2]='nsp'
        # if current is [,;:.?!)]+ the previous word should have nsp         
        if parsemeTsvSentence and re.match('[,;:.?!)]+',row[1]):
            parsemeTsvSentence[-1][2]='nsp'           
        parsemeTsvSentence.append(output_row)
    removeSubtokens(parsemeTsvSentence)
    return parsemeTsvSentence

def writeParsemeTsvSentence(parsemeTsvSentence, output_mwe_content):    
    # make sure the rank is correct
    for i in range(len(parsemeTsvSentence)):
        parsemeTsvSentence[i][0] = str(i+1)
    # add empty line at the end
    parsemeTsvSentence.append([])
    # write to output file
    output_mwe_content.writelines('\t'.join(row)+'\n' for row in parsemeTsvSentence)

def convertConll2Parseme(inputFile, language, number_of_files, sentences_per_file):
    with open(inputFile, 'rt') as f_conll_in:    
        file_index = 0        
        while True:
            file_index += 1   
            if file_index > number_of_files:
                return
            outputFile = inputFile[:-len('.conll')] + "_" + str(file_index).zfill(3) + '.mwe.tsv'
            i = 0
            with open(outputFile, 'wt') as f_mwe_out:
                while True:
                    conllSentence = getNextConllSentence(f_conll_in)
                    if conllSentence == None:
                        return     
                    i += 1
                    convertConllSentenceLanguage = LANG_CONVERSION_FUNC[language]          
                    parsemeTsvSentence = convertConllSentenceLanguage(conllSentence)
                    writeParsemeTsvSentence(parsemeTsvSentence, f_mwe_out)                
                    if i==sentences_per_file:
                        break

LANG_CONVERSION_FUNC = {
    'italian': convertConllSentenceItalian,
    'spanish': convertConllSentenceSpanish,
    'french': convertConllSentenceFrench,
}

#####################################################

def valid_input_file(file_name):
    if not file_name.endswith('.conll'):
        raise argparse.ArgumentTypeError("File name must end with '.conll'")
    return file_name

parser = argparse.ArgumentParser(description="Convert from CONLL to parseme-tsv-pos format.")
parser.add_argument("FILE", type=valid_input_file, help="An input CONLL file")
parser.add_argument("--language", type = str.lower, choices = LANG_CONVERSION_FUNC.keys(), help="The input language", required=True) 
parser.add_argument("--NoF", type = int, default=1, help="The number of output files")
parser.add_argument("--SpF", type = int, default=-1, help="The number of sentences per file")

class Main(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        filename = self.args.FILE
        language = self.args.language
        number_of_files = self.args.NoF
        sentences_per_file = self.args.SpF        
        convertConll2Parseme(filename, language, number_of_files, sentences_per_file)

def main():
    Main(parser.parse_args()).run()

#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()
