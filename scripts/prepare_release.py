#!/usr/bin/env python3
"""
ElohimOS Release Preparation Helper

Validates version, generates changelog, and creates GitHub release draft.

Usage:
    python3 scripts/prepare_release.py --version v1.0.0 --from-tag v1.0.0-rc1
"""

import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import sys

def get_current_version() -> str:
    """Read VERSION file"""
    version_file = Path("docs/VERSION")
    if version_file.exists():
        return version_file.read_text().strip()
    return None

def set_version(version: str):
    """Write VERSION file"""
    version_file = Path("docs/VERSION")
    version_file.parent.mkdir(exist_ok=True)
    version_file.write_text(version.lstrip('v') + '\n')
    print(f"✓ Updated {version_file} → {version}")

def run_changelog_generator(version: str, from_tag: str):
    """Run generate_changelog.py"""
    cmd = [
        "python3", "scripts/generate_changelog.py",
        "--version", version,
        "--from-tag", from_tag,
        "--to-tag", "HEAD"
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running changelog generator: {result.stderr}")
        return False

    print(result.stdout)
    return True

def fill_release_template(version: str, from_tag: str) -> str:
    """Fill release template with actual values"""
    template_path = Path(".github/release_template.md")

    if not template_path.exists():
        print(f"Error: Release template not found at {template_path}")
        return None

    template = template_path.read_text()

    # Generate values
    tag = version
    date = datetime.now().strftime("%Y-%m-%d")
    version_slug = version.replace('.', '').replace('-', '')
    changelog_anchor = f"changelog/CHANGELOG.md#{version_slug}---{date}"

    # Replace placeholders
    filled = template.replace("{{VERSION}}", version)
    filled = filled.replace("{{TAG}}", tag)
    filled = filled.replace("{{DATE}}", date)
    filled = filled.replace("{{FROM_TAG}}", from_tag)
    filled = filled.replace("{{CHANGELOG_ANCHOR}}", changelog_anchor)

    return filled

def main():
    parser = argparse.ArgumentParser(description="Prepare release draft")
    parser.add_argument("--version", required=True, help="Version to release (e.g., v1.0.0)")
    parser.add_argument("--from-tag", required=True, help="Previous tag for changelog (e.g., v1.0.0-rc1)")
    parser.add_argument("--skip-version-check", action="store_true", help="Skip VERSION file validation")

    args = parser.parse_args()

    print("="*80)
    print(f"ElohimOS Release Preparation — {args.version}")
    print("="*80 + "\n")

    # Step 1: Validate/update VERSION file
    current_version = get_current_version()

    if current_version:
        print(f"Current VERSION: {current_version}")

        if current_version != args.version.lstrip('v') and not args.skip_version_check:
            print(f"⚠ VERSION file mismatch: {current_version} != {args.version}")
            response = input("Update VERSION file? [y/N]: ")

            if response.lower() == 'y':
                set_version(args.version)
            else:
                print("Aborted. Run with --skip-version-check to bypass.")
                return 1
    else:
        print("No VERSION file found. Creating...")
        set_version(args.version)

    print()

    # Step 2: Generate changelog
    print("Step 1: Generating changelog...")
    if not run_changelog_generator(args.version, args.from_tag):
        print("Failed to generate changelog")
        return 1

    print()

    # Step 3: Fill release template
    print("Step 2: Generating release draft...")
    draft_body = fill_release_template(args.version, args.from_tag)

    if not draft_body:
        return 1

    # Step 4: Write draft to dist/
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    draft_file = dist_dir / f"release_draft_{args.version}.md"
    draft_file.write_text(draft_body)

    print(f"✓ Created release draft: {draft_file}")
    print()

    # Step 5: Print draft
    print("="*80)
    print("RELEASE DRAFT PREVIEW")
    print("="*80)
    print(draft_body[:1500])  # Print first 1500 chars
    print("\n... (truncated)")
    print(f"\nFull draft saved to: {draft_file}")
    print("="*80)
    print()

    # Step 6: Next steps
    print("Next Steps:")
    print(f"  1. Review: cat {draft_file}")
    print(f"  2. Verify: cat changelog/CHANGELOG.md")
    print(f"  3. Tag: git tag {args.version} && git push origin {args.version}")
    print(f"  4. Create GitHub release using draft body from {draft_file}")
    print()

    return 0

if __name__ == "__main__":
    exit(main())
