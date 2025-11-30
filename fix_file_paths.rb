#!/usr/bin/env ruby
require 'xcodeproj'

project_path = 'apps/native/MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

puts "Fixing duplicate file paths in Xcode project..."

# Find and fix ContextService.swift
context_ref = project.files.find { |f| f.path&.include?('ContextService.swift') }
if context_ref
  puts "\nContextService.swift:"
  puts "  Old path: #{context_ref.path}"
  puts "  Old real_path: #{context_ref.real_path}"

  # Change from "Shared/Services/ContextService.swift" to "ContextService.swift"
  context_ref.path = 'ContextService.swift'

  puts "  New path: #{context_ref.path}"
  puts "  New real_path: #{context_ref.real_path}"
end

# Find and fix ModelMemoryTracker.swift
tracker_ref = project.files.find { |f| f.path&.include?('ModelMemoryTracker.swift') }
if tracker_ref
  puts "\nModelMemoryTracker.swift:"
  puts "  Old path: #{tracker_ref.path}"
  puts "  Old real_path: #{tracker_ref.real_path}"

  # Change from "Shared/Services/ModelMemoryTracker.swift" to "ModelMemoryTracker.swift"
  tracker_ref.path = 'ModelMemoryTracker.swift'

  puts "  New path: #{tracker_ref.path}"
  puts "  New real_path: #{tracker_ref.real_path}"
end

# Save the project
project.save
puts "\n✅ Project saved successfully!"
