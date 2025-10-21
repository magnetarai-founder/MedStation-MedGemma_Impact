#!/bin/bash
# ElohimOS - Setup script to create 'omni' command globally
# Copyright (c) 2025 MagnetarAI, LLC
# 'omni' represents the omnipresent nature of Elohim

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RUN_SCRIPT="$SCRIPT_DIR/../../elohim"

# Detect shell
if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "Unknown shell: $SHELL"
    echo "Defaulting to .bashrc"
    SHELL_RC="$HOME/.bashrc"
fi

# Create alias
ALIAS_LINE="alias omni='$RUN_SCRIPT'"

# Check if alias already exists
if grep -q "alias omni=" "$SHELL_RC" 2>/dev/null; then
    echo "✓ 'omni' alias already exists in $SHELL_RC"
    echo "Updating to point to: $RUN_SCRIPT"
    # Remove old alias and add new one
    sed -i.bak '/alias omni=/d' "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
else
    echo "Adding 'omni' alias to $SHELL_RC"
    echo "" >> "$SHELL_RC"
    echo "# ElohimOS alias" >> "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use the 'omni' command:"
echo "  1. Reload your shell: source $SHELL_RC"
echo "  2. Or open a new terminal window"
echo "  3. Run: omni"
echo ""
echo "The 'omni' command will start ElohimOS from anywhere!"
echo "(omni = omnipresent, a reflection of Elohim)"

# Offer to reload shell
echo ""
read -p "Reload shell now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Reloading shell configuration..."
    source "$SHELL_RC"
    echo "✓ Done! You can now run 'omni' from anywhere to start ElohimOS"
else
    echo "Remember to run: source $SHELL_RC"
    echo "Or open a new terminal to use 'omni'"
fi
