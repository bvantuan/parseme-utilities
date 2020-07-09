#This script formats the PARSEME shared task general macro-average results into HTML tables for display.
# Stdin is a space-separated CSV format with the following fields:
#	System Track P-token R-token F-token P-MWE R-MWE F-MWE Rank-token Rank-MWE
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
print "<h2 id=\"avg-general\">General ranking</h2>"

print "<table>"
print "<tbody>"
print "<tr><th rowspan=\"2\">System</th><th rowspan=\"2\">Track</th><th rowspan=\"2\">#Langs</th><th colspan=\"4\">Unseen MWE-based</th><th colspan=\"4\">MWE-based</th><th colspan=\"4\">Token-based</th></tr>"

print "<tr><th>P</th><th>R</th><th>F1</th><th>Rank</th><th>P</th><th>R</th><th>F1</th><th>Rank</th><th>P</th><th>R</th><th>F1</th><th>Rank</th></tr>"

track=""
}

{
if (NR!=1) {
	#Separate tracks by a thick line
	if ( ((track=="open") && ($2=="closed")) || ((track=="closed") && ($2=="open")) ) {
		print "<tr style=\"border-top: 4px solid\">"
  }
	else {
		print "<tr>"
  }
	# print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td><td>" $12 "</td><td>" $3 "</td><td>" $4 "</td><td><b>" $5 "</b></td><td>" $13 "</td><td>" $6 "</td><td>" $7 "</td><td><b>" $8 "</b></td><td>" $14 "</td><td>" $9 "</td><td>" $10 "</td><td><b>" $11 "</b></td><td>" $15 "</td>"
	print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td><td>" $12 "</td><td>" $9 "</td><td>" $10 "</td><td><b>" $11 "</b></td><td>" $13 "</td><td>" $3 "</td><td>" $4 "</td><td><b>" $5 "</b></td><td>" $14 "</td><td>" $6 "</td><td>" $7 "</td><td><b>" $8 "</b></td><td>" $15 "</td>"
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

