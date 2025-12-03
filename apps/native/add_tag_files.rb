#!/usr/bin/env ruby
require 'xcodeproj'

project_path = 'MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Get the main target
target = project.targets.find { |t| t.name == 'MagnetarStudio' }

# Find Shared group
shared_group = project.main_group.groups.find { |g| g.display_name == 'Shared' }

# Ensure subgroups exist
models_group = shared_group.groups.find { |g| g.display_name == 'Models' }
services_group = shared_group.groups.find { |g| g.display_name == 'Services' }
views_group = shared_group.groups.find { |g| g.display_name == 'Views' }

# Add ModelTag.swift to Models group
model_tag_path = 'Shared/Models/ModelTag.swift'
if File.exist?(model_tag_path)
  file_ref = models_group.new_file(model_tag_path)
  target.add_file_references([file_ref])
  puts "Added ModelTag.swift"
end

# Add ModelTagService.swift to Services group
service_path = 'Shared/Services/ModelTagService.swift'
if File.exist?(service_path)
  file_ref = services_group.new_file(service_path)
  target.add_file_references([file_ref])
  puts "Added ModelTagService.swift"
end

# Add ModelTagEditorSheet.swift to Views group
editor_path = 'Shared/Views/ModelTagEditorSheet.swift'
if File.exist?(editor_path)
  file_ref = views_group.new_file(editor_path)
  target.add_file_references([file_ref])
  puts "Added ModelTagEditorSheet.swift"
end

project.save

puts "✅ Added tag system files to Xcode project"
