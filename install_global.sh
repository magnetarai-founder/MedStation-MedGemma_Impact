#!/bin/bash

# Install Neutron Star as a global command

echo "Installing Neutron Star globally..."

# Get the current directory (absolute path)
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a wrapper script
cat > /tmp/neutron << 'EOF'
#!/bin/bash
NEUTRON_DIR="REPLACE_WITH_PATH"
cd "$NEUTRON_DIR" && ./run
EOF

# Replace the placeholder with actual path
sed -i '' "s|REPLACE_WITH_PATH|$CURRENT_DIR|g" /tmp/neutron

# Make it executable
chmod +x /tmp/neutron

# Move to /usr/local/bin (might need sudo)
if [ -w "/usr/local/bin" ]; then
    mv /tmp/neutron /usr/local/bin/neutron
    echo "✅ Installed! You can now type 'neutron' from anywhere"
else
    echo "Need sudo permission to install globally..."
    sudo mv /tmp/neutron /usr/local/bin/neutron
    echo "✅ Installed! You can now type 'neutron' from anywhere"
fi