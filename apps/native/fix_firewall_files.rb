#!/usr/bin/env ruby

require 'xcodeproj'

# Path to your Xcode project
project_path = '/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Get the main target
target = project.targets.first

puts "🧹 Cleaning up existing references..."

# Remove ALL existing references to these files
files_to_remove = [
  'SecurityManager.swift',
  'NetworkFirewallProtocol.swift',
  'NetworkApprovalModal.swift',
  'NetworkFirewallModifier.swift'
]

files_to_remove.each do |filename|
  project.files.each do |file|
    if file.path && file.path.include?(filename)
      puts "  Removing: #{file.path}"
      file.remove_from_project
    end
  end
end

puts "\n✨ Adding files with correct paths..."

# Now add them cleanly
files_to_add = [
  { file: 'Shared/Services/SecurityManager.swift', group_path: ['Shared', 'Services'] },
  { file: 'Shared/Networking/NetworkFirewallProtocol.swift', group_path: ['Shared', 'Networking'] },
  { file: 'Shared/Views/NetworkApprovalModal.swift', group_path: ['Shared', 'Views'] },
  { file: 'Shared/Modifiers/NetworkFirewallModifier.swift', group_path: ['Shared', 'Modifiers'] }
]

files_to_add.each do |file_info|
  # Find the group
  group = project.main_group
  file_info[:group_path].each do |group_name|
    group = group[group_name] || group.new_group(group_name)
  end

  # Add file reference
  file_ref = group.new_reference(file_info[:file])

  # Add to target
  target.add_file_references([file_ref])

  puts "  ✅ Added: #{file_info[:file]}"
end

# Save
project.save

puts "\n🎉 Done! Now rebuild."
