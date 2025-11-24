#!/bin/bash
#
# MagnetarStudio Launch Script
# Launches the app with OS activity logging disabled for clean console output
#

echo "🚀 Launching MagnetarStudio..."

# Set environment variable to suppress verbose system logging
export OS_ACTIVITY_MODE=disable

# Launch the app
open /Users/indiedevhipps/Library/Developer/Xcode/DerivedData/MagnetarStudio-aqipwmnpaojwwlgsputrbahvgron/Build/Products/Debug/MagnetarStudio.app

echo "✅ MagnetarStudio launched with clean logging"
echo ""
echo "Login credentials:"
echo "  Username: elohim_founder"
echo "  Password: ElohimOS_2024_Founder"
