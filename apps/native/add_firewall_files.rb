#!/usr/bin/env ruby

require 'xcodeproj'

# Path to your Xcode project
project_path = '/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Get the main target
target = project.targets.first

# Files to add
files_to_add = [
  {
    path: 'Shared/Services/SecurityManager.swift',
    group: 'Shared/Services'
  },
  {
    path: 'Shared/Networking/NetworkFirewallProtocol.swift',
    group: 'Shared/Networking'
  },
  {
    path: 'Shared/Views/NetworkApprovalModal.swift',
    group: 'Shared/Views'
  },
  {
    path: 'Shared/Modifiers/NetworkFirewallModifier.swift',
    group: 'Shared/Modifiers'
  }
]

files_to_add.each do |file_info|
  file_path = file_info[:path]
  group_path = file_info[:group]

  # Find or create the group
  group = project
  group_path.split('/').each do |part|
    group = group[part] || group.new_group(part)
  end

  # Check if file already exists in the group
  existing_file = group.files.find { |f| f.path == file_path.split('/').last }

  if existing_file
    puts "⚠️  #{file_path} already exists, removing first..."
    existing_file.remove_from_project
  end

  # Get just the filename
  filename = File.basename(file_path)

  # Add the file to the group with correct path
  file_ref = group.new_file("../#{file_path}")

  # Add the file to the target's sources build phase
  target.add_file_references([file_ref])

  puts "✅ Added #{file_path} to #{group_path}"
end

# Save the project
project.save

puts "\n🎉 All files added successfully!"
puts "Now run: xcodebuild -project MagnetarStudio.xcodeproj -scheme MagnetarStudio build"
