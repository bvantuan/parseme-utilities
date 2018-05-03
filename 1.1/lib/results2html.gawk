#This script formats the PARSEME shared task evaluation results into HTML tables for display.
#Parameters:
#	ARGV[1] = language code
# The input file is in a space-separated CSV format with the following fields:
#	System Track P-token R-token F-token P-MWE R-MWE F-MWE Rank-token Rank-MWE
#	X-token and X-MWE are token-based and MWE-based P/R/F results 
# The output is an HTML table for the given language.

BEGIN {
#Print the language section and the table heading
#print "<!DOCTYPE html>"
#print "<html>"
#print "<head>"
#print "<style>"
#print "table, th, td { "
#print "    text-align:center;"
#print "    border-collapse: collapse;"
#print "    border: 1px solid black;"
#print "    padding: 5px;"
#print "}"
#print "</style>"
#print "</head>"
#print "<body>"

print "<!----------------------->"
print "<h1>" ARGV[1] "</h1>"
delete ARGV[1]

print "<table>"
print "<tbody>"
print "<tr><th rowspan=\"2\">System</th><th rowspan=\"2\">Track</th><th colspan=\"4\">Token-based results</th><th colspan=\"4\">MWE-based results</th></tr>"

print "<tr><th>Precision</th><th>Recall</th><th>F-measure</th><th>Rank</th><th>Precision</th><th>Recall</th><th>F-measure</th><th>Rank</th></tr>"

track=""
}

{
if (NR!=1) {
	#Separate tracks by a thick line
	if ( ((track=="open") && ($2=="closed")) || ((track=="closed") && ($2=="open")) )
		print "<tr style=\"border-top: 4px solid\">"
	else
		print "<tr>"
	print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td><td>" $3 "</td><td>" $4 "</td><td>" $5 "</td><td>" $9 "</td><td>" $6 "</td><td>" $7 "</td><td>" $8 "</td><td>" $10 "</td>"
	track = $2
}
}

END {
#Print the table closing tags
print "</tbody>"
print "</table>"
#print "</body>"
#print "</html>"
}



