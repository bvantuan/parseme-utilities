#!/bin/bash

rsync -rlptC --del --stats --progress -i ../parseme-st-guidelines/ carlos.ramisch@webequipe.lidil.univ-mrs.fr:/var/www/equipes/parsemefr/parseme-st-guidelines/1.1
