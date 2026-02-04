#!/usr/bin/env python3
"""
Documentation Generator CLI

Command-line interface for the auto-documentation system.

Usage:
    python cli.py scan                     # Scan documentation health
    python cli.py generate <file> <entity> # Generate docstring
    python cli.py update <file> <entity>   # Update docstring
    python cli.py readme                   # Generate README
    python cli.py api-docs                 # Generate API docs
    python cli.py batch-update             # Update all missing docstrings
"""

import argparse
import asyncio
import sys
from pathlib import Path

from api.services.docs import DocGenerator, DocstringStyle, get_doc_generator


async def cmd_scan(args):
    """Scan workspace for documentation health."""
    generator = get_doc_generator(workspace_root=Path.cwd())

    print("Scanning documentation health...")
    results = await generator.scan_documentation_health()

    # Show summary
    print(f"\n{'=' * 80}")
    print(f"Documentation Health Report - {len(results)} files scanned")
    print(f"{'=' * 80}\n")

    # Calculate overall stats
    total_entities = sum(r.total_entities for r in results)
    total_ok = sum(len(r.ok) for r in results)
    total_missing = sum(len(r.missing) for r in results)
    total_stale = sum(len(r.stale) for r in results)
    overall_coverage = (total_ok / total_entities * 100) if total_entities > 0 else 0

    print(f"Overall Coverage: {overall_coverage:.1f}%")
    print(f"Total Entities: {total_entities}")
    print(f"✓ Documented: {total_ok}")
    print(f"✗ Missing: {total_missing}")
    print(f"⚠ Stale: {total_stale}\n")

    # Show files needing attention
    needs_attention = [r for r in results if r.missing or r.stale]
    needs_attention.sort(key=lambda x: x.coverage_percent)

    if needs_attention:
        print(f"\nFiles Needing Attention ({len(needs_attention)}):")
        print("-" * 80)

        for i, status in enumerate(needs_attention[:args.limit], 1):
            print(f"\n{i}. {status.file_path}")
            print(f"   Coverage: {status.coverage_percent:.1f}%")

            if status.missing:
                print(f"   Missing ({len(status.missing)}): {', '.join(status.missing[:5])}")
                if len(status.missing) > 5:
                    print(f"   ... and {len(status.missing) - 5} more")

            if status.stale:
                print(f"   Stale ({len(status.stale)}): {', '.join(status.stale[:3])}")
                if len(status.stale) > 3:
                    print(f"   ... and {len(status.stale) - 3} more")
    else:
        print("\n✓ All documentation is up to date!")

    print(f"\n{'=' * 80}\n")


async def cmd_generate(args):
    """Generate docstring for a specific entity."""
    generator = get_doc_generator()

    print(f"Generating docstring for {args.entity} in {args.file}...")

    try:
        docstring = await generator.generate_docstring(
            file_path=args.file, entity_name=args.entity, style=args.style
        )

        print(f"\n{'=' * 80}")
        print(f"Generated Docstring ({args.style.value} style)")
        print(f"{'=' * 80}\n")
        print(docstring)
        print(f"\n{'=' * 80}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_update(args):
    """Update docstring for a specific entity."""
    generator = get_doc_generator()

    print(f"Updating docstring for {args.entity} in {args.file}...")

    try:
        # Always preview first
        diff = await generator.update_docstring(
            file_path=args.file, entity_name=args.entity, style=args.style, preview=True
        )

        if not diff:
            print("No changes needed.")
            return

        print(f"\n{'=' * 80}")
        print(f"Docstring Update Preview - Action: {diff.action}")
        print(f"{'=' * 80}\n")

        if diff.old_docstring:
            print("Old Docstring:")
            print("-" * 80)
            print(diff.old_docstring)
            print("-" * 80)

        print("\nNew Docstring:")
        print("-" * 80)
        print(diff.new_docstring)
        print("-" * 80)

        # Ask for confirmation unless --yes flag
        if not args.yes:
            response = input("\nApply this change? [y/N]: ")
            if response.lower() != "y":
                print("Cancelled.")
                return

        # Apply the change
        await generator.update_docstring(
            file_path=args.file, entity_name=args.entity, style=args.style, preview=False
        )

        print(f"\n✓ Updated {args.entity} in {args.file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_readme(args):
    """Generate README.md."""
    generator = get_doc_generator()

    print(f"Generating README at {args.output}...")

    try:
        await generator.generate_readme(
            output_path=args.output,
            include_api_overview=not args.no_api,
            include_structure=not args.no_structure,
        )

        print(f"✓ Generated README at {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_api_docs(args):
    """Generate API documentation."""
    generator = get_doc_generator()

    print(f"Generating API documentation in {args.output_dir}...")

    try:
        files = await generator.generate_api_docs(output_dir=args.output_dir, format=args.format)

        print(f"\n✓ Generated {len(files)} API documentation files:")
        for file_path in files:
            print(f"  - {file_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_batch_update(args):
    """Batch update all missing docstrings."""
    generator = get_doc_generator()

    print("Scanning for missing documentation...")
    results = await generator.scan_documentation_health()

    # Collect all missing docstrings
    to_update = []
    for status in results:
        for entity_name in status.missing:
            to_update.append((status.file_path, entity_name))

    if not to_update:
        print("✓ No missing docstrings found!")
        return

    print(f"\nFound {len(to_update)} entities without docstrings.")

    if not args.yes:
        response = input(f"Update all {len(to_update)} entities? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return

    # Update each one
    print("\nUpdating docstrings...")
    success = 0
    failed = 0

    for i, (file_path, entity_name) in enumerate(to_update, 1):
        try:
            print(f"[{i}/{len(to_update)}] {file_path}::{entity_name}...", end=" ")
            await generator.update_docstring(
                file_path=file_path, entity_name=entity_name, style=args.style, preview=False
            )
            print("✓")
            success += 1

        except Exception as e:
            print(f"✗ ({e})")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"Batch Update Complete")
    print(f"{'=' * 80}")
    print(f"✓ Success: {success}")
    print(f"✗ Failed: {failed}")
    print(f"{'=' * 80}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-Documentation System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan documentation health")
    scan_parser.add_argument(
        "--limit", type=int, default=10, help="Max files to show (default: 10)"
    )

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate docstring for entity")
    gen_parser.add_argument("file", help="Python file path")
    gen_parser.add_argument("entity", help="Entity name (function/class/method)")
    gen_parser.add_argument(
        "--style",
        type=DocstringStyle,
        default=DocstringStyle.GOOGLE,
        choices=list(DocstringStyle),
        help="Docstring style (default: google)",
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update docstring for entity")
    update_parser.add_argument("file", help="Python file path")
    update_parser.add_argument("entity", help="Entity name (function/class/method)")
    update_parser.add_argument(
        "--style",
        type=DocstringStyle,
        default=DocstringStyle.GOOGLE,
        choices=list(DocstringStyle),
        help="Docstring style (default: google)",
    )
    update_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )

    # README command
    readme_parser = subparsers.add_parser("readme", help="Generate README.md")
    readme_parser.add_argument(
        "--output", default="README.md", help="Output path (default: README.md)"
    )
    readme_parser.add_argument("--no-api", action="store_true", help="Skip API overview")
    readme_parser.add_argument("--no-structure", action="store_true", help="Skip project structure")

    # API docs command
    api_parser = subparsers.add_parser("api-docs", help="Generate API documentation")
    api_parser.add_argument(
        "--output-dir", default="docs/api", help="Output directory (default: docs/api)"
    )
    api_parser.add_argument(
        "--format",
        choices=["markdown", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    # Batch update command
    batch_parser = subparsers.add_parser("batch-update", help="Update all missing docstrings")
    batch_parser.add_argument(
        "--style",
        type=DocstringStyle,
        default=DocstringStyle.GOOGLE,
        choices=list(DocstringStyle),
        help="Docstring style (default: google)",
    )
    batch_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Map commands to handlers
    commands = {
        "scan": cmd_scan,
        "generate": cmd_generate,
        "update": cmd_update,
        "readme": cmd_readme,
        "api-docs": cmd_api_docs,
        "batch-update": cmd_batch_update,
    }

    # Run command
    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
