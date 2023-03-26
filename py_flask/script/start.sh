#!/bin/bash

pwd
#source script/export_api_token.sh
gunicorn -w 10 -b 127.0.0.1:9081 -k gevent -t 10 -D run:app_entry