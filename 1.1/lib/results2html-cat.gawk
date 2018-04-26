#This script formats the PARSEME shared task evaluation results per category into HTML tables for display.
#Parameters:
#	ARGV[1] = language code
# The input file is in a space-separated CSV format with the following fields:
#            System Track " \
#            P-iav-mwe R-iav-mwe F-iav-mwe P-iav-token R-iav-token F-iav-token" \
#            P-irv-mwe R-irv-mwe F-irv-mwe P-irv-token R-irv-token F-ireflv-token" \
#            P-lvc-cause-mwe R-lvc-cause-mwe F-lvc-cause-mwe P-lvc-cause-token R-lvc-cause-token F-lvc-cause-token" \
#            F-lvc-full-mwe P-lvc-full-token R-lvc-full-token F-lvc-full-token" \
#            P-mvc-mwe R-mvc-mwe F-mvc-mwe P-mvc-token R-mvc-token F-mvc-token" \
#            P-vid-mwe R-vid-mwe F-vid-mwe P-vid-token R-vid-token F-vid-token" \
#            P-vpc-full-mwe R-vpc-full-mwe F-vpc-full-mwe P-vpc-full-token R-vpc-full-token F-vpc-full-token" \
#            P-vpc-semi-mwe R-vpc-semi-mwe F-vpc-semi-mwe P-vpc-semi-token R-vpc-semi-token F-vpc-semi-token" \
# In ARGV[1]=IT, then the file shoudl also contain "P-ls-icv-token R-ls-icv-token F-ls-icv-token"
# The output is an HTML table for the given language.

BEGIN {
NB_CATS=8

print "<!----------------------->"
print "<h1>" ARGV[1] "</h1>"
LANG = ARGV[1]
delete ARGV[1]

print "<table>"
print "<tbody>"
print "<tr>"
print "<th rowspan=\"3\">System</th><th rowspan=\"3\">Track</th><th colspan=\"6\">IAV</th><th colspan=\"6\">IRV</th>"
print "<th colspan=\"6\">LVC.cause</th><th colspan=\"6\">LVC.full</th><th colspan=\"6\">MVC</th>"
print "<th colspan=\"6\">VID</th><th colspan=\"6\">VPC.full</th><th colspan=\"6\">VPC.semi</th>"
if (LANG == "IT") #Italian has a languge-specific category
	print "<th colspan=\"6\">LS.ICV</th>"
print "</tr>"

print "<tr>"
for (i=1; i<=NB_CATS; i++)
	print "<th colspan=\"3\">Per-MWE results</th><th colspan=\"3\">Per-token results</th>"
if (LANG == "IT")
	print "<th colspan=\"3\">Per-MWE results</th><th colspan=\"3\">Per-token results</th>"
print "</tr>"

print "<tr>"
for (i=1; i<=NB_CATS; i++)
	print "<th>Precision</th><th>Recall</th><th>F-measure</th><th>Precision</th><th>Recall</th><th>F-measure</th>"
if (LANG == "IT")
	print "<th>Precision</th><th>Recall</th><th>F-measure</th><th>Precision</th><th>Recall</th><th>F-measure</th>"
print "<tr>"

track=""
}

{
if (NR!=1) {
	print "<tr>"
	print "<td style=\"text-align:left\">" $1 "</td><td style=\"text-align:left\">" $2 "</td>"
	for (i = 3; i <= NF; i++)
		print "<td>" $i "</td>"
	print "<tr>"
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



