#This script formats the PARSEME shared task evaluation results into HTML tables for display.
#Parameters:
#	ARGV[1] = language code
# The input file is in a space-separated CSV format with the following fields:
#	System Track P-token R-token F-token P-MWE R-MWE F-MWE P-unseen R-unseen F-unseen Rank-token Rank-MWE Rank-unseen
#	X-token, X-MWE and X-unseen are token-based, MWE-based and Unseen MWE-based P/R/F results
# The output is an HTML table for the given language.

BEGIN {
print "<!----------------------->"
print "<h2 id=\"lang-" ARGV[1] "\">" ARGV[1] "</h2>"
delete ARGV[1]

print "<table>"
print "<tbody>"
print "<tr><th rowspan=\"2\">System</th><th rowspan=\"2\">Track</th><th colspan=\"4\">Unseen MWE-based </th><th colspan=\"4\">Global MWE-based </th><th colspan=\"4\">Global Token-based </th></tr>"

print "<tr><th>P</th><th>R</th><th>F1</th><th>Rank</th><th>P</th><th>R</th><th>F1</th><th>Rank</th><th>P</th><th>R</th><th>F1</th><th>Rank</th></tr>"

track=""
}

{
if (NR!=1) {
	#Separate tracks by a thick line
	if ( ((track=="open") && ($2=="closed")) || ((track=="closed") && ($2=="open")) )
		print "<tr style=\"border-top: 4px solid\">"
	else
		print "<tr>"
	print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td><td>" $3 "</td><td>" $4 "</td><td><b>" $5 "</b></td><td>" $12 "</td><td>" $6 "</td><td>" $7 "</td><td><b>" $8 "</b></td><td>" $13 "</td><td>" $9 "</td><td>" $10 "</td><td><b>" $11 "</b></td><td>" $14 "</td>"
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
