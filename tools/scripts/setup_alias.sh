#!/bin/bash

# This script adds the 'neutron' alias to your shell

SHELL_RC=""

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "Unsupported shell. Please add alias manually."
    exit 1
fi

# Add alias
echo "" >> "$SHELL_RC"
echo "# Neutron Star alias" >> "$SHELL_RC"
echo "alias neutron='cd \"$HOME/Documents/2-Tech/New NS\" && ./run'" >> "$SHELL_RC"

echo "✅ Added 'neutron' command to $SHELL_RC"
echo ""
echo "To use it, either:"
echo "1. Open a new terminal, or"
echo "2. Run: source $SHELL_RC"
echo ""
echo "Then you can type 'neutron' from anywhere to start Neutron Star!"