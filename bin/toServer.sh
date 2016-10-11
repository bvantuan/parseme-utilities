#!/bin/bash

rsync -rlptC --del --stats --progress -i ../guidelines-hypertext/ carlos.ramisch@webequipe.lidil.univ-mrs.fr:/var/www/equipes/parsemefr/guidelines-hypertext/
