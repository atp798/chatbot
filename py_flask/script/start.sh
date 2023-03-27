#!/bin/bash

pwd
#source script/export_api_token.sh
gunicorn --worker-connections=100 --workers=1 -b 127.0.0.1:9081 -k gevent -t 10 -D run:app_entry
