#!/usr/bin/env ruby
require 'xcodeproj'

project_path = 'MagnetarStudio.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Find the Shared group
shared_group = project.main_group['Shared']
views_group = shared_group['Views']
components_group = shared_group['Components']

# Add ModelManagerWindow.swift
model_manager_file = views_group.new_file('Shared/Views/ModelManagerWindow.swift')

# Add SmartModelPicker.swift
smart_picker_file = components_group.new_file('Shared/Components/SmartModelPicker.swift')

# Add files to target
target = project.targets.find { |t| t.name == 'MagnetarStudio' }
if target
  target.add_file_references([model_manager_file, smart_picker_file])
  puts "✅ Added files to MagnetarStudio target"
else
  puts "❌ Could not find MagnetarStudio target"
  exit 1
end

project.save

puts "✅ Added ModelManagerWindow.swift and SmartModelPicker.swift to Xcode project"
