#!/bin/bash
 ps aux|grep run.py|awk '{print $2}'| xargs kill -9
pwd
#source script/export_api_token.sh
touch nohup.out
nohup python3 run.py 2>&1 & 
tail -f nohup.out
