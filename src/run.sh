#!/bin/sh

#ConfigFile=test_configures/test1_config.json5
ConfigFile=test_configures/test2_config.json5

if [ $# -gt 1 ]; then
    ConfigFile=$1
fi

if [ ! -f $ConfigFile ]; then
    echo file $ConfigFile does not exist
    exit
fi

echo python3 sequence.py $ConfigFile
echo ==============================
python3 sequence.py $ConfigFile
