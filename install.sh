#!/bin/bash

echo "config = {
    'debug': False,
    'api_key':'oma avain tähän'
}" > config.py

echo "[]" > data.json

pipenv install -r requirements.txt