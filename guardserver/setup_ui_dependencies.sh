#!/bin/bash

# Setup the static dependencies for Guard UI

# Create directories
mkdir static/css
mkdir static/js

# Download Bootstrap
curl https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css > static/css/bootstrap.min.css
curl https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js > static/js/bootstrap.min.js

# Download jQuery
curl https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js > static/js/jquery.min.js
