#!/usr/bin/env python3
"""
Example Usage of Auto-Documentation System

This script demonstrates how to use the DocGenerator to:
1. Generate docstrings for undocumented code
2. Check documentation health
3. Update stale documentation
4. Generate README and API documentation
"""

import asyncio
from pathlib import Path

from api.services.docs import DocGenerator, DocstringStyle, get_doc_generator


async def example_generate_docstring():
    """Example: Generate a docstring for a specific function."""
    print("\n" + "=" * 70)
    print("Example 1: Generate Docstring for a Function")
    print("=" * 70)

    generator = get_doc_generator(workspace_root=Path.cwd())

    # Generate docstring for a function
    try:
        docstring = await generator.generate_docstring(
            file_path="api/services/ollama_client.py",
            entity_name="get_ollama_client",
            style=DocstringStyle.GOOGLE,
        )

        print("\nGenerated Docstring:")
        print("-" * 70)
        print(docstring)
        print("-" * 70)

    except Exception as e:
        print(f"Error: {e}")


async def example_check_sync():
    """Example: Check if documentation is in sync with code."""
    print("\n" + "=" * 70)
    print("Example 2: Check Documentation Sync")
    print("=" * 70)

    generator = get_doc_generator()

    # Check if a function's docstring is up to date
    try:
        is_synced, reason = await generator.check_sync(
            file_path="api/services/ollama_client.py", entity_name="get_ollama_client"
        )

        print(f"\nFunction: get_ollama_client")
        print(f"In Sync: {is_synced}")
        if not is_synced:
            print(f"Reason: {reason}")

    except Exception as e:
        print(f"Error: {e}")


async def example_update_with_preview():
    """Example: Preview docstring update before applying."""
    print("\n" + "=" * 70)
    print("Example 3: Update Docstring with Preview")
    print("=" * 70)

    generator = get_doc_generator()

    try:
        # Preview the change
        diff = await generator.update_docstring(
            file_path="api/services/cache_service.py",
            entity_name="CacheService",
            style=DocstringStyle.GOOGLE,
            preview=True,  # Don't apply, just show diff
        )

        if diff:
            print(f"\nAction: {diff.action}")
            print(f"Entity: {diff.entity_name}")
            print("\nDiff Preview:")
            print("-" * 70)
            for line in diff.diff_lines[:20]:  # Show first 20 lines
                print(line)
            print("-" * 70)

            # To apply the change, call with preview=False:
            # await generator.update_docstring(
            #     file_path="api/services/cache_service.py",
            #     entity_name="CacheService",
            #     preview=False
            # )

    except Exception as e:
        print(f"Error: {e}")


async def example_health_scan():
    """Example: Scan entire workspace for documentation health."""
    print("\n" + "=" * 70)
    print("Example 4: Documentation Health Scan")
    print("=" * 70)

    generator = get_doc_generator()

    # Scan all Python files (excluding tests)
    results = await generator.scan_documentation_health(
        include_patterns=["**/*.py"],
        exclude_patterns=[
            "**/test_*.py",
            "**/tests/**",
            "**/__pycache__/**",
            "**/venv/**",
        ],
    )

    # Show summary
    print(f"\nScanned {len(results)} files\n")

    # Show top 5 files needing attention
    print("Files Needing Attention:")
    print("-" * 70)

    needs_attention = [r for r in results if r.missing or r.stale]
    needs_attention.sort(key=lambda x: x.coverage_percent)

    for status in needs_attention[:5]:
        print(f"\nFile: {status.file_path}")
        print(f"  Coverage: {status.coverage_percent:.1f}%")
        print(f"  Missing docs: {len(status.missing)}")
        print(f"  Stale docs: {len(status.stale)}")

        if status.missing:
            print(f"  Undocumented: {', '.join(status.missing[:3])}")

    # Overall statistics
    total_entities = sum(r.total_entities for r in results)
    total_ok = sum(len(r.ok) for r in results)
    overall_coverage = (total_ok / total_entities * 100) if total_entities > 0 else 0

    print("\n" + "=" * 70)
    print(f"Overall Documentation Coverage: {overall_coverage:.1f}%")
    print(f"Total Entities: {total_entities}")
    print(f"Documented: {total_ok}")
    print(f"Missing: {sum(len(r.missing) for r in results)}")
    print(f"Stale: {sum(len(r.stale) for r in results)}")
    print("=" * 70)


async def example_generate_readme():
    """Example: Generate README.md from codebase."""
    print("\n" + "=" * 70)
    print("Example 5: Generate README")
    print("=" * 70)

    generator = get_doc_generator()

    # Generate README (without writing to file, just return content)
    readme_content = await generator.generate_readme(
        output_path=None,  # Don't write, just return
        include_api_overview=True,
        include_structure=True,
    )

    print("\nGenerated README Preview (first 50 lines):")
    print("-" * 70)
    lines = readme_content.splitlines()
    for line in lines[:50]:
        print(line)
    print("-" * 70)

    # To actually write the README:
    # await generator.generate_readme(
    #     output_path="README.md",
    #     include_api_overview=True,
    #     include_structure=True
    # )


async def example_generate_api_docs():
    """Example: Generate API documentation."""
    print("\n" + "=" * 70)
    print("Example 6: Generate API Documentation")
    print("=" * 70)

    generator = get_doc_generator()

    # Generate API documentation
    try:
        generated_files = await generator.generate_api_docs(
            output_dir="docs/api", format="markdown"
        )

        print(f"\nGenerated {len(generated_files)} API documentation files:")
        for file_path in generated_files:
            print(f"  - {file_path}")

    except Exception as e:
        print(f"Error: {e}")


async def example_batch_update():
    """Example: Batch update all missing docstrings in a file."""
    print("\n" + "=" * 70)
    print("Example 7: Batch Update Missing Docstrings")
    print("=" * 70)

    generator = get_doc_generator()

    file_path = "api/services/cache_service.py"

    try:
        # First, check what needs updating
        status = await generator._check_file_documentation(Path(file_path))

        print(f"\nFile: {status.file_path}")
        print(f"Missing docstrings: {len(status.missing)}")

        if status.missing:
            print(f"\nEntities without docs: {', '.join(status.missing)}")

            # Preview updates for first 3 missing
            for entity_name in status.missing[:3]:
                print(f"\n--- Generating docstring for {entity_name} ---")

                diff = await generator.update_docstring(
                    file_path=file_path, entity_name=entity_name, preview=True
                )

                if diff:
                    print(f"Action: {diff.action}")
                    print("New docstring preview:")
                    print(diff.new_docstring[:200] + "...")  # First 200 chars

            # To apply all updates:
            # for entity_name in status.missing:
            #     await generator.update_docstring(
            #         file_path=file_path,
            #         entity_name=entity_name,
            #         preview=False
            #     )

    except Exception as e:
        print(f"Error: {e}")


async def example_compare_styles():
    """Example: Compare different docstring styles."""
    print("\n" + "=" * 70)
    print("Example 8: Compare Docstring Styles")
    print("=" * 70)

    generator = get_doc_generator()

    file_path = "api/services/ollama_client.py"
    entity_name = "OllamaClient.chat"

    for style in [DocstringStyle.GOOGLE, DocstringStyle.NUMPY, DocstringStyle.SPHINX]:
        print(f"\n--- {style.value.upper()} STYLE ---")
        try:
            docstring = await generator.generate_docstring(
                file_path=file_path, entity_name=entity_name, style=style
            )
            print(docstring[:300] + "...")  # First 300 chars

        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MagnetarCode Auto-Documentation System - Examples")
    print("=" * 70)

    # Run examples
    examples = [
        ("Generate Docstring", example_generate_docstring),
        ("Check Sync", example_check_sync),
        ("Update with Preview", example_update_with_preview),
        ("Health Scan", example_health_scan),
        ("Generate README", example_generate_readme),
        ("Generate API Docs", example_generate_api_docs),
        ("Batch Update", example_batch_update),
        ("Compare Styles", example_compare_styles),
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n" + "=" * 70)
    print("Running Example 1: Generate Docstring")
    print("(Comment out others to run individually)")
    print("=" * 70)

    # Run first example by default
    # Uncomment others as needed
    await example_generate_docstring()
    # await example_check_sync()
    # await example_update_with_preview()
    # await example_health_scan()
    # await example_generate_readme()
    # await example_generate_api_docs()
    # await example_batch_update()
    # await example_compare_styles()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
