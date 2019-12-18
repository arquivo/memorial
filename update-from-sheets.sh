#!/bin/bash

# Verify if last command was correct
correct(){
    if [[ $1 != 0 ]]; then
        echo "ERROR: $2"
        exit $1
    fi
}

# Print first lines
printHeader() {
	echo "# Managed by google sheets."
	echo "# WARN do not update this file manually!"
	echo "# It should be updated using update-from-sheets.sh script that is located on this repository base folder."
	echo 
	echo "ARCHIVE_CONFIG = {"
}

printFoolder() {
	echo "}"
}

echo "Updating config"
{
	printHeader
	echo
	wget -qO- "https://docs.google.com/spreadsheets/d/1e4mmEdcIFR5kuFUGa1X2NaaK3qy0nu06m3oD3zDjp7w/export?format=csv&gid=0&range=AD2:AD" | sed '/^[[:space:]]*$/d' | tr -d '"'
    printFoolder
    echo
} > config.py
correct $? "Error updating config."

echo "To view the changes use:"
echo "  git diff config.py"
