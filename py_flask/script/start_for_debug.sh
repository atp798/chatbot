#!/bin/bash

pwd
#source script/export_api_token.sh
nohup python run.py 2>&1 & 
tail -f nohup.out
