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

# Files to add with their group paths
files_to_add = [
  # Phase 1: Foundation
  { path: 'Shared/Models/AppContext.swift', group: 'Shared/Models' },
  { path: 'Shared/Models/ContextBundle.swift', group: 'Shared/Models' },
  { path: 'Shared/Models/ModelRoutingDecision.swift', group: 'Shared/Models' },

  # Phase 3: Vault Security
  { path: 'Shared/Services/VaultPermissionManager.swift', group: 'Shared/Services' },
  { path: 'macOS/Dialogs/FileAccessPermissionModal.swift', group: 'macOS/Dialogs' },
  { path: 'macOS/Panels/VaultAdminPanel.swift', group: 'macOS/Panels' },

  # Phase 4: Apple FM Integration
  { path: 'Shared/Services/AppleFMOrchestrator.swift', group: 'Shared/Services' },
  { path: 'Shared/Services/ResourceMonitor.swift', group: 'Shared/Services' },
  { path: 'Shared/Services/OrchestratorInitializer.swift', group: 'Shared/Services' }
]

# Helper function to find or create group
def find_or_create_group(project, path)
  components = path.split('/')
  current_group = project.main_group

  components.each do |component|
    next_group = current_group.groups.find { |g| g.display_name == component }

    if next_group.nil?
      # Create the group if it doesn't exist
      next_group = current_group.new_group(component)
      puts "  📁 Created group: #{component}"
    end

    current_group = next_group
  end

  current_group
end

puts "🔧 Adding files to Xcode project..."
puts ""

files_to_add.each do |file_info|
  file_path = "/Users/indiedevhipps/Documents/MagnetarStudio/apps/native/#{file_info[:path]}"

  # Check if file exists
  unless File.exist?(file_path)
    puts "⚠️  File not found: #{file_info[:path]}"
    next
  end

  # Find or create the group
  group = find_or_create_group(project, file_info[:group])

  # Check if file is already in project
  existing_file = group.files.find { |f| f.path == File.basename(file_path) }

  if existing_file
    puts "⏭️  Already exists: #{file_info[:path]}"
    next
  end

  # Add file reference to group
  file_ref = group.new_file(file_path)

  # Add to build phase (compile sources)
  target.source_build_phase.add_file_reference(file_ref)

  puts "✅ Added: #{file_info[:path]}"
end

puts ""
puts "💾 Saving project..."
project.save

puts "✅ Done! All files added to Xcode project."
puts ""
puts "Next steps:"
puts "1. Open Xcode and verify files appear in Project Navigator"
puts "2. Build the project (⌘B) to verify all errors are resolved"
