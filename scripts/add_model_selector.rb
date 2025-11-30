#!/usr/bin/env ruby

require 'xcodeproj'

# Open the Xcode project
project_path = '/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Find the main target
target = project.targets.find { |t| t.name == 'MagnetarStudio' }

if target.nil?
  puts "❌ Could not find MagnetarStudio target"
  exit 1
end

puts "🔧 Adding ModelSelectorMenu.swift to Xcode project..."

file_path = "/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/macOS/Components/ModelSelectorMenu.swift"

# Check if file exists
unless File.exist?(file_path)
  puts "⚠️  File not found: #{file_path}"
  exit 1
end

# Find the macOS group
macos_group = project.main_group.groups.find { |g| g.display_name == 'macOS' }
if macos_group.nil?
  puts "❌ Could not find macOS group"
  exit 1
end

# Find or create Components group
components_group = macos_group.groups.find { |g| g.display_name == 'Components' }
if components_group.nil?
  components_group = macos_group.new_group('Components')
  puts "  📁 Created group: Components"
end

# Check if file is already in project
existing_file = components_group.files.find { |f| f.path == 'ModelSelectorMenu.swift' }

if existing_file
  puts "⏭️  Already exists: ModelSelectorMenu.swift"
else
  # Add file reference to group
  file_ref = components_group.new_file(file_path)

  # Add to build phase (compile sources)
  target.source_build_phase.add_file_reference(file_ref)

  puts "✅ Added: ModelSelectorMenu.swift"
end

puts ""
puts "💾 Saving project..."
project.save

puts "✅ Done!"
