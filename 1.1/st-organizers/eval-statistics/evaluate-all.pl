#!/usr/bin/perl

#  CALL WITH "./evaluate-all.pl REGEXP"
#  will evaluate all the files matching regexp and output a "results.txt" in the same dictionary
#  (use with caution as multiple files in the same directory will result in overwriting)
#
#
# To evaluate all submissions to the Parseme shared, type :
# ./evaluate-all.pl ../results/*/*/test.system.parsemetsv
#
# To evaluate one language (FR):
# ./evaluate-all.pl ../results/*/FR/test.system.parsemetsv
#
# To evaluate one system (ADAPT.closed):
# ./evaluate-all.pl ../results/ADAPT.closed/*/test.system.parsemetsv
#

$filecount = 0;
$count = 1;


while ($filecount <= @ARGV-1) {

    $infile = $ARGV[$filecount];
    @subfolders = split (/\//, $infile);

    $numberFolders = $#subfolders;
    $language = $subfolders[$numberFolders-1];
    #print "LANGUAGE: $language\n";
    $goldfile="../$language/parsemetgz/OUT/test.parsemetsv";

    pop @subfolders; 
    $outfolder = join "/", @subfolders;
    
    system ("./evaluate.py  $goldfile $infile > $outfolder/results.txt");
    #system ("./evaluate.py  ../FR/parsemetgz/OUT/test.parsemetsv ../results/SZEGED.open/FR/test.system.parsemetsv");
 
$filecount++;

}
