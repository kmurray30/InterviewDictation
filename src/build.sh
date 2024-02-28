#!/bin/bash
# Define
appName="ClickMe"

# Clean
rm ../$appName
rm -rf out

# Build
mkdir out
cd out
pyinstaller --onefile -n $appName --log-level ERROR --add-data=../../.env:. ../main.py

# Move
cp dist/$appName ../../$appName
cd ..