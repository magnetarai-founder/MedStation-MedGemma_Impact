#!/usr/bin/env ruby
require 'xcodeproj'

project_path = 'apps/native/MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Find the Shared group
shared_group = project.main_group.groups.find { |g| g.path == 'Shared' || g.name == 'Shared' }
unless shared_group
  puts "Error: Shared group not found"
  exit 1
end

# Find Services group
services_group = shared_group.groups.find { |g| g.path == 'Services' || g.name == 'Services' }
unless services_group
  puts "Error: Services group not found"
  exit 1
end

# Add ModelMemoryTracker.swift
file_path = 'Shared/Services/ModelMemoryTracker.swift'
file_ref = services_group.new_file(file_path)

# Get the target
target = project.targets.find { |t| t.name == 'MagnetarStudio' }
unless target
  puts "Error: MagnetarStudio target not found"
  exit 1
end

# Add to compile sources
target.source_build_phase.add_file_reference(file_ref)

# Save
project.save

puts "✅ Added ModelMemoryTracker.swift to Xcode project"
