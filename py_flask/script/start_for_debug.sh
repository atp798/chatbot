#!/bin/bash
pwd
dir=`pwd`
ps aux|grep $dir|awk '{print $2}'| xargs kill -9
#source script/export_api_token.sh
touch nohup.out
nohup python run.py $dir 2>&1 &
tail -f nohup.out