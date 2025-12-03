#!/usr/bin/env ruby
require 'xcodeproj'

project = Xcodeproj::Project.open('MagnetarStudio.xcodeproj')

# Find and remove duplicate paths
duplicates_removed = 0

project.files.each do |file|
  if file.path&.include?('Shared/Views/Shared') || file.path&.include?('Shared/Components/Shared')
    puts "Removing duplicate: #{file.path}"
    file.remove_from_project
    duplicates_removed += 1
  end
end

if duplicates_removed > 0
  project.save
  puts "✅ Removed #{duplicates_removed} duplicate file references"
else
  puts "✅ No duplicates found"
end
