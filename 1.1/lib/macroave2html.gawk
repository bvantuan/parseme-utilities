#This script formats the PARSEME shared task macro-average results into HTML tables for display.
#Parameters:
#	ARGV[1] = a phenomenon e.g. Discontinuous, Single-token, etc.
# Stdin is a space-separated CSV format with the following fields:
#	System Track P-MWE R-MWE F-MWE Rank
# The output is an HTML table for the given phenomenon.

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
print "<h2 id=\"avg-" ARGV[1] "\">" ARGV[1] " VMWEs</h2>"
delete ARGV[1]

print "<table>"
print "<tbody>"
print "<tr><th rowspan=\"2\">System</th><th rowspan=\"2\">Track</th><th rowspan=\"2\">#Langs</th><th colspan=\"4\">MWE-based</th></tr>"

print "<tr><th>P</th><th>R</th><th>F1</th><th>Rank</th></tr>"

track=""
}

{
if (NR!=1) {
	#Separate tracks by a thick line
	if ( ((track=="open") && ($2=="closed")) || ((track=="closed") && ($2=="open")) ) {
		print "<tr style=\"border-top: 4px solid\">"
    prevfm = -1
    rank=0
  }
	else {
		print "<tr>"
  }    
	print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td><td>" $6 "<td>" $3 "</td><td>" $4 "</td><td><b>" $5 "</b></td><td>" $7 "</td></tr>"
	track = $2
}
}

END {
#Print the table closing tags
print "</tbody>"
print "</table>"
print "<br/>"
print "<a href=\"#top-menu\">↑ Back to top</a>"
}



