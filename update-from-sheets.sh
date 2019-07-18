#!/bin/bash

# Verify if last command was correct
correct(){
    if [[ $1 != 0 ]]; then
        echo "ERROR: $2"
        exit $1
    fi
}

# Print first lines
printHeaderComment() {
	echo "# Managed by google sheets."
	echo "# WARN do not update this file manually!"
	echo "# It should be updated using update-from-sheets.sh script that is located on this repository base folder."
}

echo "Updating config"
{
	printHeaderComment
	echo
	wget -qO- "https://docs.google.com/spreadsheets/d/1e4mmEdcIFR5kuFUGa1X2NaaK3qy0nu06m3oD3zDjp7w/export?format=csv&gid=1521923406&range=A5:A5" | tr -d '"'
        echo
} > config.py
correct $? "Error updating config."

echo "To view the changes use:"
echo "  git diff config.py"
