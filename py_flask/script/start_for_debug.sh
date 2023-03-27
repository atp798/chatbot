#!/bin/bash
 ps aux|grep run.py|awk '{print $2}'| xargs kill -9
pwd
#source script/export_api_token.sh
nohup python run.py 2>&1 & 
tail -f nohup.out
