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

puts "🔧 Adding HotSlotManager.swift to Xcode project..."

file_path = "/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/Shared/Services/HotSlotManager.swift"

# Check if file exists
unless File.exist?(file_path)
  puts "⚠️  File not found: #{file_path}"
  exit 1
end

# Find the Shared/Services group
shared_group = project.main_group.groups.find { |g| g.display_name == 'Shared' }
services_group = shared_group.groups.find { |g| g.display_name == 'Services' }

if services_group.nil?
  puts "❌ Could not find Shared/Services group"
  exit 1
end

# Check if file is already in project
existing_file = services_group.files.find { |f| f.path == 'HotSlotManager.swift' }

if existing_file
  puts "⏭️  Already exists: HotSlotManager.swift"
else
  # Add file reference to group
  file_ref = services_group.new_file(file_path)

  # Add to build phase (compile sources)
  target.source_build_phase.add_file_reference(file_ref)

  puts "✅ Added: HotSlotManager.swift"
end

puts ""
puts "💾 Saving project..."
project.save

puts "✅ Done!"
