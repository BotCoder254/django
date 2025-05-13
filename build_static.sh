#!/bin/bash

# Install project dependencies
pip install -r requirements.txt

# Run collectstatic
python manage.py collectstatic --noinput

# Make the staticfiles directory accessible to Vercel
mkdir -p staticfiles 