#!/bin/bash
pwd
dir=`pwd`
ps aux|grep $dir|awk '{print $2}'| xargs kill -9
#source script/export_api_token.sh

if command -v python3 &>/dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

mkdir log 2>&1
touch nohup.out
nohup $PYTHON run.py $dir 2>&1 &
tail -f log/log.info