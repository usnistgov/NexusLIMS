#!/bin/bash

# add/replace if variable is non empty
# $1 = variable to replace/remove
# $2 = new value to set
function update_conf() {
    local query
    if [ "$1" == "" ]; then return 0; fi

    # First remove existing configuration info
    if [ -e /code/basic_extractor_config.py ]; then
        if [ "$2" != "" ]; then
            query="$1"
	    mv /code/basic_extractor_config.py /code/basic_extractor_config.py.old
            grep -v "^$query" /code/basic_extractor_config.py.old > /code/basic_extractor_config.py
            rm /code/basic_extractor_config.py.old
	fi
    fi

    # Then, update config info
    if [ "$2" != "" ]; then
        echo "$1=\"$2\"" >> /code/basic_extractor_config.py
    fi
}

# Set configuration information 
update_conf   "rabbitmqURL" "$RABBITMQ_URL"

# Start clowder
cd /code
python basic_extractor.py
