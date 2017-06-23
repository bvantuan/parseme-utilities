#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"


# Simply makes a pretty table summarizing stats for all languages training set

# change to test if you want test data stats


cat */*/stats.md | 
#grep -v '^  *' | 
grep -v "=" | 
sed -e 's/### //g' -e 's/.parsemetsv//g'\
    -e 's/Statistics //g' -e 's/^\*.*: //g' | #  cat
awk '/(test)/{
  head=$1; 
  getline; sent=$1; tsent+=sent; 
  getline; tok=$1; ttok += tok; 
  getline; vmwe=$1;tvmwe+=vmwe; 
  id = 0; ireflv=0; lvc=0; vpc=0; oth=0;
  do{
    getline; 
    if($2 == "`ID`:"){    id = $3; tid += id;    }
    else if($2 == "`IReflV`:"){   ireflv = $3; tireflv += ireflv;    }
    else if($2 == "`LVC`:"){   lvc = $3; tlvc += lvc;    }
    else if($2 == "`OTH`:"){   oth = $3; toth += oth;    }
    else if($2 == "`VPC`:"){   vpc = $3; tvpc += vpc;    }        
  }while(NF > 1);
  print bline lang, sent, tok, vmwe, id, ireflv, lvc, oth, vpc eline;
}
/^[A-Z][A-Z]$/{
  lang=$0;
  if(NR==1){
    if(outformat == "html"){
      print "<table style=\"text-align:right\">\n<tbody>";          
      bline = "<tr><td style=\"font-weight:bold\">";
      OFS = "</td><td style=\"font-weight:bold\">";
      eline = "</td></tr>";
    }
    else if(outformat == "latex"){
      bline = "\\hline\n";      eline = " \\\\";    OFS = " & ";
      print("\\begin{tabular}{lrrrrrrrr}");
    }
    else{
      bline = "";      eline = "";      OFS = "\t";
    }
    print bline "Language","Sentences","Tokens","VMWE", "ID", "IReflV", "LVC", "OTH", "VPC" eline;    
    if(outformat == "html"){  
      bline = "<tr><td style=\"text-align:left\">";
      OFS = "</td><td>";
    }
  }
}
END{ 
  print bline "Total",tsent,ttok,tvmwe,tid,tireflv,tlvc,toth,tvpc eline;
  if(outformat == "html"){ 
    print("</tbody>\n</table>");
  }
  else if(outformat == "latex"){
    print("\\hline\n\\end{tabular}");
  }
}' outformat=$1
