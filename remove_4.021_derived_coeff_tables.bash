#!/bin/bash

for db; do

    echo $db
    if ! sqlite3 "$db" 'drop table coeffbest; drop table coeffdirection; drop table coeffnorm; drop table coeffsecondary; vacuum;'; then    
        echo 1>&2 "*** could not remove derived coeff tables {coeffbest,coeffdirection,coeffnorm,coeffsecondary} from $db"
    fi

done

