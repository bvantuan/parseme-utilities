#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"


# Simply makes a pretty table summarizing stats for all languages train/dev set
# change line 18 below to (train|dev|test) if you also want test data stats


cat 1.1/*/*/*-stats.md | 
grep -v "=" | 
sed -e 's@## File: [A-Z][A-Z]/@@g' -e 's/.cupt//g'\
    -e 's/Language: //g' -e 's/^\*.*: //g' |   
awk '/(train|dev)/{ # (train|data|dev) #<= CHANGEME IF NEEDED!
  head=$0; 
  getline; sent=$1; tsent+=sent; 
  getline; tok=$1; ttok += tok; 
  getline; vmwe=$1;tvmwe+=vmwe; 
  vid = 0; irv=0; lvcfull=0; vpcfull=0; vpcsemi=0; lvccause=0; iav=0; mvc=0; lsicv=0;
  do{
    getline; 
    if($2 == "`VID`:"){    vid = $3; tvid += vid;    }
    else if($2 == "`IRV`:"){   irv = $3; tirv += irv;    }
    else if($2 == "`LVC.full`:"){   lvcfull = $3; tlvcfull += lvcfull;    }
    else if($2 == "`LVC.cause`:"){   lvccause = $3; tlvccause += lvccause;    }
    else if($2 == "`VPC.full`:"){   vpcfull = $3; tvpcfull += vpcfull;    }        
    else if($2 == "`VPC.semi`:"){   vpcsemi = $3; tvpcsemi += vpcsemi;    }            
    else if($2 == "`IAV`:"){   iav = $3; tiav += iav;    }                
    else if($2 == "`MVC`:"){   mvc = $3; tmvc += mvc;    }                
    else if($2 == "`LS.ICV`:"){   lsicv = $3; tlsicv += lsicv;    }                    
  }while(NF > 1);  
  if(prevlang != lang){
    print rowsep;
  }
  prevlang = lang;

  print bline lang "-" head, sent, tok, vmwe, vid, irv, lvcfull, lvccause, vpcfull, vpcsemi, iav, mvc, lsicv eline;
}
/^[A-Z][A-Z]$/{
  lang=$0;  
  if(NR==1){
    if(outformat == "html"){
      print "<table style=\"text-align:right\">\n<tbody>";          
      bline = "<tr><td style=\"font-weight:bold\">";
      OFS = "</td><td style=\"font-weight:bold\">";
      eline = "</td></tr>";
      rowsep = "<tr><td colspan="13"><hr/></td></tr>";    
    }
    else if(outformat == "latex"){
      bline = "\\hline\n";      eline = " \\\\";    OFS = " & ";
      print("\\begin{tabular}{lrrrrrrrr}");
      rowsep = "\\hline";
    }
    else{
      bline = "";      eline = "";      OFS = "\t";
      rowsep = "---------------------------------------------------------"
    }    
    print bline "Language","Sentences","Tokens","VMWE", "VID", "IRV", "LVC.full", "LVC.cause", "VPC.full", "VPC.semi", "IAV", "MVC", "LS.ICV" eline;    
    if(outformat == "html"){  
      bline = "<tr><td style=\"text-align:left\">";
      OFS = "</td><td>";
    }
  }
  

  
}
END{ 
  print rowsep
  print bline "Total",tsent,ttok,tvmwe,tvid,tirv,tlvcfull,tlvccause,tvpcfull, tvpcsemi, tiav, tmvc, tlsicv eline;
  if(outformat == "html"){ 
    print("</tbody>\n</table>");
  }
  else if(outformat == "latex"){
    print("\\hline\n\\end{tabular}");
  }
}' outformat=$1
