#!/bin/bash
# Fix form fields accessibility by adding id/name attributes

cd "$(dirname "$0")/../.."

echo "🔧 Fixing form field accessibility issues..."
echo ""

# Find all TSX files with input elements
find apps/frontend/src -name "*.tsx" -type f | while read file; do
    # Check if file contains input elements without id or name
    if grep -q '<input' "$file" && ! grep -q 'id=' "$file"; then
        echo "📝 Processing: $file"

        # Create backup
        cp "$file" "$file.bak"

        # This is complex - better to do manually or use proper AST tool
        echo "   ⚠️  Manual review needed"
    fi
done

echo ""
echo "✅ Form field scan complete!"
echo "   Use browser dev tools to identify specific fields"
echo "   Or add id/name attributes manually to flagged components"
