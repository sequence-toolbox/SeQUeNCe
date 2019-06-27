#!/bin/sh

ConfigFile=config.json

if [ $# -gt 1 ]; then
    ConfigFile=$1
fi

if [ ! -f $ConfigFile ]; then
    echo file $ConfigFile does not exist
    exit
fi

echo python3 sequence.py $ConfigFile
python3 sequence.py $ConfigFile
