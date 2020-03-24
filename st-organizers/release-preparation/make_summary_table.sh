#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"

if [ $# -ne 1 ]; then
  echo "This script requires an argument, choose one output format among {txt,html,latex}"
  exit -1
fi

# Simply makes a pretty table summarizing stats for all languages train/dev set
# change line 18 below to (train|dev|test) if you also want test data stats


for a in preliminary-sharedtask-data/??/; do
#for a in preliminary-sharedtask-data-alt/??/; do	
  if [ -f $a/dev-stats.md ]; then
    cat $a/{train,dev,test}-stats.md
  elif [ -f $a/train-stats.md ]; then
    cat $a/{train,test}-stats.md
  fi
done |
grep -v "=" | 
sed -e 's@## File: [A-Z][A-Z]/@@g' -e 's/.cupt//g'\
    -e 's/Language: //g' -e 's/^\*.*: //g' |
awk 'BEGIN{   prevlang = "XX";}
/(test|train|dev)/{ # (train|test|dev) #<= CHANGEME IF NEEDED!  
  head=$2 "  ";   
  if(prevlang!=lang && prevlang != "XX"){    
    print rowsep;
    if (langsent!=0){
      avglength = int(10*(langtok/langsent))/10;
    }
    else{
      avglength = NR;
    }
    print bline prevlang "-Total" , langsent, langtok, avglength,langvmwe, langvid, langirv, langlvcfull, langlvccause, langvpcfull, langvpcsemi, langiav, langmvc, langlsicv eline;    
    print langsep;    
    langsent=0; langtok=0; langvmwe=0; langvid=0; langlvcfull=0; langlvccause=0; langvpcfull=0; langvpccause=0; langvpcsemi=0; langiav=0; langmvc=0; langlsicv=0; langirv=0;
  }
  getline; sent=$1; tsent+=sent; langsent+=sent;
  getline; tok=$1; ttok += tok; langtok+=tok;
  getline; vmwe=$1;tvmwe+=vmwe; langvmwe+=vmwe;
  vid = 0; irv=0; lvcfull=0; vpcfull=0; vpcsemi=0; lvccause=0; iav=0; mvc=0; lsicv=0;
  do{
    getline; # print "line=", $0; 
    if($2 == "`VID`:"){    vid = $3; tvid += vid; langvid+= vid;   }
    else if($2 == "`IRV`:"){   irv = $3; tirv += irv;  langirv+= irv;   }
    else if($2 == "`LVC.full`:"){   lvcfull = $3; tlvcfull += lvcfull;   langlvcfull+= lvcfull;  }
    else if($2 == "`LVC.cause`:"){   lvccause = $3; tlvccause += lvccause;   langlvccause+= lvccause;  }
    else if($2 == "`VPC.full`:"){   vpcfull = $3; tvpcfull += vpcfull;   langvpcfull+= vpcfull;  }        
    else if($2 == "`VPC.semi`:"){   vpcsemi = $3; tvpcsemi += vpcsemi;  langvpcsemi+= vpcsemi;   }            
    else if($2 == "`IAV`:"){   iav = $3; tiav += iav;  langiav+= iav;   }                
    else if($2 == "`MVC`:"){   mvc = $3; tmvc += mvc;  langmvc+= mvc;   }                
    else if($2 == "`LS.ICV`:"){   lsicv = $3; tlsicv += lsicv;  langlsicv+= lsicv;   } 
  } while ($0 ~ /\*/);

  #Adding the statistics of unseen
  if (head ~ /(dev)|(test)/) {
    unseen_wrt_train = $1;
    getline
    ratio_unseen_wrt_train = sprintf("%.2f", $1);
  }
  if (head ~ /test/) {
    getline;  
    unseen_wrt_train_dev = $1;
    getline;  
    ratio_unseen_wrt_train_dev = sprintf("%.2f", $1);
  }

  if(prevlang != lang){
    #print rowsep;
  }
  prevlang = lang;	

  if (head ~ /train/)
    print bline lang "-" head, sent, tok, int(10*(tok/sent))/10, vmwe, vid, irv, lvcfull, lvccause, vpcfull, vpcsemi, iav, mvc, lsicv, "", "", "", "" eline;
  else
    if (head ~ /dev/)
      print bline lang "-" head, sent, tok, int(10*(tok/sent))/10, vmwe, vid, irv, lvcfull, lvccause, vpcfull, vpcsemi, iav, mvc, lsicv, unseen_wrt_train, ratio_unseen_wrt_train, "", "" eline;
    else
      print bline lang "-" head, sent, tok, int(10*(tok/sent))/10, vmwe, vid, irv, lvcfull, lvccause, vpcfull, vpcsemi, iav, mvc, lsicv, unseen_wrt_train, ratio_unseen_wrt_train, unseen_wrt_train_dev, ratio_unseen_wrt_train_dev eline;
}
/Statistics [A-Z][A-Z]$/{
  lang=$2;  
  if(NR==1){
    if(outformat == "html"){
      print "<table style=\"text-align:right\">\n<tbody>";          
      bline = "<tr><td style=\"font-weight:bold\">";
      OFS = "</td><td style=\"font-weight:bold\">";
      eline = "</td></tr>";
      rowsep = "<tr style=\"height:1px; background-color: #d5d5d5;\"><td colspan=\"18\"></td></tr>";    
      langsep = "<tr style=\"height:2px; background-color: #222222;\"><td colspan=\"18\"></td></tr>";          
    }
    else if(outformat == "latex"){
      bline = "";      eline = " \\\\";    OFS = " & ";
      print("\\begin{tabular}{lrrrrrrrrrrrrrr}");
      rowsep = "\\hline";
      langsep = "\\hline\\hline";
    }
    else{
      bline = "";      eline = "";      OFS = "\t";
      rowsep =  "------------------------------------------------------------------------------------------------------------------"
      langsep = "=================================================================================================================="

    }    
    print langsep; 
#    print bline "Lang-split","Sentences","Tokens","Avg. length","VMWE", "VID", "IRV", "LVC.full", "LVC.cause", "VPC.full", "VPC.semi", "IAV", "MVC", "LS.ICV" eline;   
    print bline "Lang-split","Sentences","Tokens","Avg. length","VMWE", "VID", "IRV", "LVC.full", "LVC.cause", "VPC.full", "VPC.semi", "IAV", "MVC", "LS.ICV", "Unseen wrt train", "Ratio unseen wrt train", "Unseen wrt train+dev", "Ratio unseen wrt train+dev", eline;   
    print langsep; 
    if(outformat == "html"){  
      bline = "<tr><td style=\"text-align:left\">";
      OFS = "</td><td>";
    }
  }  
}
END{ 
  print rowsep;
  print bline prevlang "-Total" , langsent, langtok, int(10*(langtok/langsent))/10, langvmwe, langvid, langirv, langlvcfull, langlvccause, langvpcfull, langvpcsemi, langiav, langmvc, langlsicv eline;    
  print langsep;
  print bline "Total    ",tsent,ttok,int(10*(ttok/tsent))/10,tvmwe,tvid,tirv,tlvcfull,tlvccause,tvpcfull, tvpcsemi, tiav, tmvc, tlsicv eline;
  print langsep;  
  if(outformat == "html"){ 
    print("</tbody>\n</table>");
  }
  else if(outformat == "latex"){
    print("\\hline\n\\end{tabular}");
  }
}' outformat=$1






