#!/bin/bash

rsync -rlptC --del --stats --progress -i ../parseme-st-guidelines/1.0/ carlos.ramisch@webequipe.lidil.univ-mrs.fr:/var/www/equipes/parsemefr/guidelines-hypertext/
