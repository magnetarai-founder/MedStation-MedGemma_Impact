#!/usr/bin/env python3
"""
CodexEngine (minimal): deterministic patch application and rollback.
For now, uses the system 'patch' command to apply unified diffs transactionally.
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
import fcntl
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import difflib
from .codex_deterministic_ops import DeterministicOps
from .codex_codemods import CodemodOperations


class CodexEngine:
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path.cwd()
        self._patch_log_dir = self.repo_root / ".ai_agent"
        self._patch_log_dir.mkdir(exist_ok=True)

    def apply_unified_diff(self, diff_text: str, patch_id: str) -> Tuple[bool, str]:
        if not diff_text.strip():
            return False, "Empty diff"

        # SECURITY: Pre-scan diff for path traversal attacks
        is_safe, safety_msg = self._validate_diff_paths(diff_text)
        if not is_safe:
            return False, f"Security: {safety_msg}"

        # CONCURRENCY: Acquire file lock to prevent concurrent applies
        lock_file = self.repo_root / ".ai_agent" / "apply.lock"
        lock_file.parent.mkdir(exist_ok=True)
        lock_fd = None

        try:
            lock_fd = open(lock_file, 'w')
            # Try to acquire exclusive lock (non-blocking)
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False, "Another patch is being applied. Please wait and try again."

            # Write diff to temp file for patch command
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".diff")
            tmp.write(diff_text.encode())
            tmp.close()

            # Prepare backup dir
            backup_dir = self._patch_log_dir / patch_id
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        # Backup target files mentioned in diff (best-effort)
        targets = self._extract_targets(diff_text)
        for t in targets:
            tp = (self.repo_root / t).resolve()
            if tp.exists() and tp.is_file():
                try:
                    bd = backup_dir / t
                    bd.parent.mkdir(parents=True, exist_ok=True)
                    bd.write_text(tp.read_text())
                except Exception:
                    continue

        # Detect patch strip level (-p0 vs -p1)
        # Check if headers have a/ b/ prefixes (typical git diff format)
        patch_level = self._detect_patch_level(diff_text)

        try:
            # Try system patch if available
            if shutil.which('patch'):
                # Try with detected patch level
                dry = subprocess.run(
                    f"patch -p{patch_level} --dry-run < '{tmp.name}'",
                    shell=True,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if dry.returncode != 0:
                    # If detected level fails, try the opposite
                    alternate_level = 1 if patch_level == 0 else 0
                    dry = subprocess.run(
                        f"patch -p{alternate_level} --dry-run < '{tmp.name}'",
                        shell=True,
                        cwd=self.repo_root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if dry.returncode != 0:
                        raise RuntimeError(dry.stderr.strip() or dry.stdout.strip())
                    patch_level = alternate_level

                applied = subprocess.run(
                    f"patch -p{patch_level} < '{tmp.name}'",
                    shell=True,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if applied.returncode != 0:
                    raise RuntimeError(applied.stderr.strip() or applied.stdout.strip())
            else:
                raise RuntimeError('patch command not available')
        except Exception as e:
            # Create parent dirs for added files before retry
            try:
                for f in self._extract_targets(diff_text):
                    if '/dev/null' in f:
                        continue
                    p = self.repo_root / f
                    p.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            # Fallback 1: per-file application using system patch
            ok, msg = self._apply_per_file(diff_text)
            if not ok:
                # Fallback 2: minimal Python applier for simple single-hunk replacements
                ok2, msg2 = self._apply_simple_diff(diff_text)
                if not ok2:
                    os.unlink(tmp.name)
                    return False, f"Apply failed: {e}; per-file: {msg}; fallback: {msg2}"
            os.unlink(tmp.name)

            # Save patch to log for potential rollback
            patch_file = self._patch_log_dir / f"{patch_id}.diff"
            patch_file.write_text(diff_text)
            return True, "Applied"

        finally:
            # CONCURRENCY: Release lock
            if lock_fd:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                except Exception:
                    pass

    def rollback(self, patch_id: str) -> Tuple[bool, str]:
        # Prefer exact backup restore if available
        backup_dir = self._patch_log_dir / patch_id
        if backup_dir.exists():
            restored_any = False
            for bd in backup_dir.rglob('*'):
                if bd.is_file():
                    rel = bd.relative_to(backup_dir)
                    dest = (self.repo_root / rel).resolve()
                    try:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(bd.read_text())
                        restored_any = True
                    except Exception:
                        continue
            return (True, "Rolled back from backups") if restored_any else (False, "No backups to restore")

        # Fallback to reverse diff
        patch_file = self._patch_log_dir / f"{patch_id}.diff"
        if not patch_file.exists():
            return False, "Patch not found"
        diff = patch_file.read_text()
        reversed_diff = self._reverse_unified_diff(diff)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".diff")
        tmp.write(reversed_diff.encode())
        tmp.close()
        applied = subprocess.run(
            f"patch -p0 < '{tmp.name}'",
            shell=True,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        os.unlink(tmp.name)
        if applied.returncode != 0:
            return False, f"Rollback failed: {applied.stderr.strip() or applied.stdout.strip()}"
        return True, "Rolled back"

    def _detect_patch_level(self, diff: str) -> int:
        """
        Detect whether diff uses -p0 or -p1 format by checking path prefixes.

        Returns:
            0 for -p0 (no prefix), 1 for -p1 (a/ b/ prefix)
        """
        for ln in diff.splitlines():
            if ln.startswith('--- ') or ln.startswith('+++ '):
                path = ln.split(' ', 1)[1].strip()
                if '\t' in path:
                    path = path.split('\t', 1)[0]

                # Check for a/ or b/ prefix (git format)
                if path.startswith('a/') or path.startswith('b/'):
                    return 1

                # If no prefix and not /dev/null, assume -p0
                if path != '/dev/null':
                    return 0

        # Default to -p1 for git-style diffs
        return 1

    def _validate_diff_paths(self, diff: str) -> Tuple[bool, str]:
        """
        Validate diff paths to prevent path traversal attacks

        Security checks:
        - Rejects absolute paths (starting with /)
        - Rejects parent directory traversal (../)
        - Rejects paths outside repo_root after resolution
        - Allows /dev/null (standard for new/deleted files)

        Returns:
            (is_safe, error_message)
        """
        for ln in diff.splitlines():
            if not (ln.startswith('--- ') or ln.startswith('+++ ')):
                continue

            # Extract path from diff header
            path = ln.split(' ', 1)[1].strip()
            if '\t' in path:
                path = path.split('\t', 1)[0]

            # Strip a/ b/ prefixes if present
            if path.startswith('a/') or path.startswith('b/'):
                path = path[2:]

            # Allow /dev/null (standard for new/deleted files)
            if path == '/dev/null':
                continue

            # REJECT: Absolute paths
            if path.startswith('/'):
                return False, f"Absolute path not allowed: {path}"

            # REJECT: Parent directory traversal
            if '../' in path or path.startswith('..'):
                return False, f"Path traversal not allowed: {path}"

            # REJECT: Paths that resolve outside repo_root
            try:
                resolved = (self.repo_root / path).resolve()
                if not resolved.is_relative_to(self.repo_root.resolve()):
                    return False, f"Path escapes repo root: {path}"
            except (ValueError, RuntimeError):
                return False, f"Invalid path: {path}"

        return True, ""

    def _reverse_unified_diff(self, diff: str) -> str:
        lines = []
        for ln in diff.splitlines():
            if ln.startswith('--- '):
                lines.append('+++ ' + ln[4:])
            elif ln.startswith('+++ '):
                lines.append('--- ' + ln[4:])
            elif ln.startswith('+') and not ln.startswith('+++'):
                lines.append('-' + ln[1:])
            elif ln.startswith('-') and not ln.startswith('---'):
                lines.append('+' + ln[1:])
            else:
                lines.append(ln)
        return "\n".join(lines) + "\n"

    def _apply_simple_diff(self, diff: str) -> Tuple[bool, str]:
        """Very simple unified diff applier for single-file, single-hunk replacements.
        Handles basic line replacements used in stress tests.
        """
        lines = diff.splitlines()
        old = None
        new = None
        target = None
        minus = []
        plus = []
        for ln in lines:
            if ln.startswith('--- '):
                old = ln.split(' ', 1)[1].strip()
                if old.startswith('a/'):
                    old = old[2:]
            elif ln.startswith('+++ '):
                new = ln.split(' ', 1)[1].strip()
                if new.startswith('b/'):
                    new = new[2:]
            elif ln.startswith('@@'):
                continue
            elif ln.startswith('-') and not ln.startswith('---'):
                minus.append(ln[1:])
            elif ln.startswith('+') and not ln.startswith('+++'):
                plus.append(ln[1:])
        target = new or old
        if not target:
            return False, 'no target file in diff'
        path = (self.repo_root / target).resolve()
        if not path.exists():
            return False, f'target not found: {path}'
        try:
            text = path.read_text()
            old_block = "\n".join(minus)
            new_block = "\n".join(plus)
            # Ensure we replace whole lines
            if old_block and (old_block in text):
                text2 = text.replace(old_block, new_block)
            else:
                # Try with trailing newline variants
                text2 = text
                if old_block + "\n" in text:
                    text2 = text.replace(old_block + "\n", new_block + "\n")
            if text2 == text:
                return False, 'simple replacer found no changes'
            path.write_text(text2)
            return True, 'simple apply ok'
        except Exception as e:
            return False, str(e)

    def _extract_targets(self, diff: str) -> list:
        targets = []
        for ln in diff.splitlines():
            if ln.startswith('+++ '):
                f = ln.split(' ', 1)[1].strip()
                # strip timestamp if present
                if '\t' in f:
                    f = f.split('\t', 1)[0]
                if f.startswith('b/'):
                    f = f[2:]
                targets.append(f)
            elif ln.startswith('--- '):
                f = ln.split(' ', 1)[1].strip()
                if '\t' in f:
                    f = f.split('\t', 1)[0]
                if f.startswith('a/'):
                    f = f[2:]
                targets.append(f)
        # Unique and relative
        uniq = []
        seen = set()
        for t in targets:
            if t not in seen:
                uniq.append(t)
                seen.add(t)
        return uniq

    def _split_unified_diff(self, diff: str) -> list:
        """Split a multi-file unified diff into a list of per-file diffs."""
        files = []
        current = []
        for ln in diff.splitlines():
            if ln.startswith('diff --git') or ln.startswith('--- '):
                if current:
                    files.append('\n'.join(current) + '\n')
                    current = []
            current.append(ln)
        if current:
            files.append('\n'.join(current) + '\n')
        # Filter out empty shards
        return [d for d in files if '--- ' in d and '+++ ' in d]

    def _apply_per_file(self, diff_text: str) -> Tuple[bool, str]:
        """Attempt to apply a multi-file diff per-file, improving resilience."""
        shards = self._split_unified_diff(diff_text)
        if not shards:
            return False, 'no per-file shards found'
        # Try applying each shard independently
        for i, shard in enumerate(shards):
            # Detect add/delete operations and handle directly to avoid quoting issues
            lines = shard.splitlines()
            header_old = next((ln for ln in lines if ln.startswith('--- ')), None)
            header_new = next((ln for ln in lines if ln.startswith('+++ ')), None)
            old_path = header_old.split(' ', 1)[1].strip() if header_old else ''
            new_path = header_new.split(' ', 1)[1].strip() if header_new else ''
            if '\t' in old_path:
                old_path = old_path.split('\t', 1)[0]
            if '\t' in new_path:
                new_path = new_path.split('\t', 1)[0]

            # Add new file
            if old_path == '/dev/null' and new_path and new_path != '/dev/null':
                target = (self.repo_root / new_path).resolve()
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    content_lines = []
                    in_hunk = False
                    for ln in lines:
                        if ln.startswith('@@ '):
                            in_hunk = True
                            continue
                        if not in_hunk:
                            continue
                        if ln.startswith('+') and not ln.startswith('+++'):
                            content_lines.append(ln[1:] + ('\n' if not ln.endswith('\n') else ''))
                        elif ln.startswith(' ') or ln.startswith('-'):
                            # For pure add from /dev/null, context/minus lines should not appear, ignore
                            continue
                    target.write_text(''.join(content_lines))
                    continue
                except Exception as e:
                    return False, f'shard {i} add-file failed: {e}'

            # Delete file
            if new_path == '/dev/null' and old_path and old_path != '/dev/null':
                target = (self.repo_root / old_path).resolve()
                try:
                    if target.exists():
                        target.unlink()
                    continue
                except Exception as e:
                    return False, f'shard {i} delete-file failed: {e}'

            # Write temp shard
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".shard{i}.diff")
            tmp.write(shard.encode())
            tmp.close()
            try:
                if shutil.which('patch'):
                    dry = subprocess.run(
                        f"patch -p0 --dry-run < '{tmp.name}'",
                        shell=True,
                        cwd=self.repo_root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if dry.returncode != 0:
                        # Try simple applier on this shard
                        ok, msg = self._apply_simple_diff(shard)
                        if not ok:
                            os.unlink(tmp.name)
                            return False, f"shard {i} dry-run failed: {dry.stderr or dry.stdout}; simple: {msg}"
                    else:
                        applied = subprocess.run(
                            f"patch -p0 < '{tmp.name}'",
                            shell=True,
                            cwd=self.repo_root,
                            capture_output=True,
                            text=True,
                            timeout=20,
                        )
                        if applied.returncode != 0:
                            # Try simple applier on this shard
                            ok, msg = self._apply_simple_diff(shard)
                            if not ok:
                                os.unlink(tmp.name)
                                return False, f"shard {i} apply failed: {applied.stderr or applied.stdout}; simple: {msg}"
                else:
                    ok, msg = self._apply_simple_diff(shard)
                    if not ok:
                        os.unlink(tmp.name)
                        return False, f"no patch cmd and simple failed for shard {i}: {msg}"
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
        return True, 'per-file apply ok'

    # --- Added search and codemod helpers ---
    def search_code(self, pattern: str, globs: List[str] = None, max_results: int = 200) -> List[Tuple[str,int,str]]:
        """Search code for a regex pattern; returns list of (path, line_no, line)."""
        globs = globs or ['**/*.py', '**/*.js', '**/*.ts']
        results = []
        # If ripgrep is available, use it
        if shutil.which('rg'):
            # Convert glob patterns to ripgrep glob syntax
            rg_globs = []
            for g in globs:
                if g.startswith('**/'):
                    # **/*.py -> -g '*.py'
                    rg_globs.extend(['-g', g[3:]])
                else:
                    # *.py -> -g '*.py'
                    rg_globs.extend(['-g', g])
            
            cmd = ['rg', '-n', '--no-heading', '-e', pattern] + rg_globs
            try:
                p = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
                if p.returncode in (0, 1):  # 1 = no matches
                    for line in p.stdout.strip().splitlines():
                        if not line:
                            continue
                        try:
                            path, lno, content = line.split(':', 2)
                            results.append((path, int(lno), content))
                        except ValueError:
                            continue
                        if len(results) >= max_results:
                            return results[:max_results]
            except Exception:
                pass  # Fall through to Python implementation
            if results:
                return results[:max_results]
        # Fallback: simple Python scan
        import re as _re
        rx = _re.compile(pattern)
        for g in globs:
            for p in self.repo_root.rglob(g.replace('**/','')):
                if not p.is_file():
                    continue
                try:
                    text = p.read_text(errors='ignore')
                except Exception:
                    continue
                for idx, ln in enumerate(text.splitlines(), 1):
                    if rx.search(ln):
                        results.append((str(p.relative_to(self.repo_root)), idx, ln))
                        if len(results) >= max_results:
                            return results
        return results

    def generate_rename_diff(self, old: str, new: str, globs: List[str] = None) -> str:
        """Generate a unified diff for renaming a symbol across files."""
        globs = globs or ['**/*.py']
        import re as _re
        rx = _re.compile(rf"\b{_re.escape(old)}\b")
        diffs = []
        for g in globs:
            for p in self.repo_root.rglob(g.replace('**/','')):
                if not p.is_file():
                    continue
                try:
                    before = p.read_text()
                except Exception:
                    continue
                after = rx.sub(new, before)
                if after != before:
                    rel = str(p.relative_to(self.repo_root))
                    ud = self._unified_text_diff(rel, rel, before, after)
                    diffs.append(ud)
        return '\n'.join(diffs)
    
    # --- Deterministic Operations ---
    
    def add_import(self, file_path: str, import_stmt: str) -> Tuple[bool, str]:
        """Add an import statement to a Python file"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.add_import(path, import_stmt)
    
    def remove_import(self, file_path: str, module_name: str) -> Tuple[bool, str]:
        """Remove an import statement from a Python file"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.remove_import(path, module_name)
    
    def rename_function(self, file_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a function in a Python file"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.rename_function(path, old_name, new_name)
    
    def rename_class(self, file_path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a class in a Python file"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.rename_class(path, old_name, new_name)
    
    def add_function_parameter(self, file_path: str, func_name: str, param_name: str,
                              default_value: Optional[str] = None,
                              after_param: Optional[str] = None) -> Tuple[bool, str]:
        """Add a parameter to a function"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.add_function_parameter(path, func_name, param_name, default_value, after_param)
    
    def extract_to_function(self, file_path: str, start_line: int, end_line: int,
                           func_name: str, params: List[str] = None) -> Tuple[bool, str]:
        """Extract lines of code into a new function"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.extract_to_function(path, start_line, end_line, func_name, params)
    
    def update_json_file(self, file_path: str, updates: Dict[str, Any],
                        create_if_missing: bool = True) -> Tuple[bool, str]:
        """Update JSON file with new values"""
        path = self.repo_root / file_path
        return DeterministicOps.update_json_file(path, updates, create_if_missing)
    
    def add_type_hints(self, file_path: str, func_name: str,
                      param_types: Dict[str, str],
                      return_type: Optional[str] = None) -> Tuple[bool, str]:
        """Add type hints to a function"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return DeterministicOps.add_type_hints(path, func_name, param_types, return_type)
    
    def move_function(self, source_file: str, target_file: str,
                     func_name: str, update_imports: bool = True) -> Tuple[bool, str]:
        """Move a function from one file to another"""
        source = self.repo_root / source_file
        target = self.repo_root / target_file
        if not source.exists():
            return False, f"Source file {source_file} not found"
        return DeterministicOps.move_function(source, target, func_name, update_imports)

    # -------- Advanced codemods (diff generators) --------

    def _rel_module_from_path(self, file_path: str) -> str:
        p = (self.repo_root / file_path).resolve()
        rel = p.relative_to(self.repo_root)
        mod = str(rel.with_suffix('')).replace('/', '.').replace('\\', '.')
        return mod

    def _unified_text_diff(self, old_path: str, new_path: str, before: str, after: str) -> str:
        a = before.splitlines(keepends=True)
        b = after.splitlines(keepends=True)
        # Handle add/delete sentinel correctly for patch
        # Add a tab and timestamp to guard spaces in filenames
        ts = '\t1970-01-01 00:00:00 +0000'
        fromfile = old_path if old_path == '/dev/null' else f"{old_path}{ts}"
        tofile = new_path if new_path == '/dev/null' else f"{new_path}{ts}"
        ud = difflib.unified_diff(a, b, fromfile=fromfile, tofile=tofile)
        return ''.join(ud)

    def _unified_add_file(self, new_path: str, content: str) -> str:
        before = ''
        after = content
        # Proper add-file headers: --- /dev/null, +++ new_path
        return self._unified_text_diff('/dev/null', new_path, before, after)

    def _unified_delete_file(self, old_path: str, content: str) -> str:
        before = content
        after = ''
        # Proper delete-file headers: --- old_path, +++ /dev/null
        return self._unified_text_diff(old_path, '/dev/null', before, after)

    def generate_move_module_diff(self, old_path: str, new_path: str, update_imports: bool = True,
                                  include_globs: list | None = None,
                                  exclude_globs: list | None = None,
                                  files_list: list | None = None) -> str:
        old_abs = (self.repo_root / old_path).resolve()
        if not old_abs.exists():
            return ''
        try:
            before = old_abs.read_text()
        except Exception:
            return ''

        # Create add-new and delete-old diffs
        add_diff = self._unified_add_file(new_path, before)
        del_diff = self._unified_delete_file(old_path, before)

        diffs = [del_diff, add_diff]

        if update_imports:
            # Produce repo-wide import update diff
            upd = CodemodOperations.update_imports_for_moved_module(
                self.repo_root, old_path, new_path,
                include_globs=include_globs, exclude_globs=exclude_globs, files_list=files_list
            )
            if upd.strip():
                diffs.append(upd)

        return '\n'.join(diffs)

    def generate_update_imports_diff(self, old_module_path: str, new_module_path: str,
                                     include_globs: list | None = None,
                                     exclude_globs: list | None = None,
                                     files_list: list | None = None) -> str:
        return CodemodOperations.update_imports_for_moved_module(
            self.repo_root, old_module_path, new_module_path,
            include_globs=include_globs, exclude_globs=exclude_globs, files_list=files_list
        )

    def generate_extract_class_diff(self, source_file: str, class_name: str, target_file: str) -> str:
        src_p = (self.repo_root / source_file).resolve()
        tgt_p = (self.repo_root / target_file).resolve()
        if not src_p.exists():
            return ''
        try:
            src_text = src_p.read_text()
        except Exception:
            return ''

        # Parse AST to locate class
        try:
            import ast
            tree = ast.parse(src_text)
        except Exception:
            return ''

        node = None
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and n.name == class_name:
                node = n
                break
        if not node or not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
            return ''

        lines = src_text.splitlines(keepends=True)
        class_block = ''.join(lines[node.lineno-1:node.end_lineno])

        # Build new target content (append class)
        try:
            tgt_before = tgt_p.read_text() if tgt_p.exists() else ''
        except Exception:
            tgt_before = ''
        tgt_lines = tgt_before.splitlines(keepends=True)
        if tgt_lines and tgt_lines[-1] and not tgt_lines[-1].endswith('\n'):
            tgt_lines[-1] = tgt_lines[-1] + '\n'
        if tgt_lines and tgt_lines[-1].strip():
            tgt_lines.append('\n')
        tgt_lines.append(class_block if class_block.endswith('\n') else class_block + '\n')
        tgt_after = ''.join(tgt_lines)

        # Update source: remove class and add import
        src_after_lines = lines[:node.lineno-1] + lines[node.end_lineno:]
        # Compute module of target for absolute import
        target_module = self._rel_module_from_path(target_file)
        import_stmt = f"from {target_module} import {class_name}\n"
        # Insert import after existing imports/docstring
        try:
            import ast
            tree2 = ast.parse(''.join(src_after_lines))
            insert_at = 0
            if tree2.body and isinstance(tree2.body[0], ast.Expr) and isinstance(tree2.body[0].value, ast.Constant) and isinstance(tree2.body[0].value.value, str):
                insert_at = tree2.body[0].end_lineno
            for n in tree2.body:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    insert_at = max(insert_at, n.end_lineno)
                else:
                    break
            src_after_lines.insert(insert_at, import_stmt)
        except Exception:
            src_after_lines.insert(0, import_stmt)
        src_after = ''.join(src_after_lines)

        src_diff = self._unified_text_diff(source_file, source_file, src_text, src_after)
        tgt_diff = self._unified_text_diff('/dev/null' if not tgt_before else target_file, target_file, tgt_before if tgt_before else '', tgt_after)
        # Optionally organize imports in the source after inserting new import
        try:
            org_diff = self.generate_organize_imports_diff(source_file)
        except Exception:
            org_diff = ''
        parts = [src_diff, tgt_diff]
        if org_diff.strip():
            parts.append(org_diff)
        return '\n'.join(parts)

    def generate_organize_imports_diff(self, file_path: str) -> str:
        p = (self.repo_root / file_path).resolve()
        if not p.exists():
            return ''
        try:
            content = p.read_text()
        except Exception:
            return ''
        # Reuse CodemodOperations.organize_imports logic without writing
        try:
            import ast
            tree = ast.parse(content)
            imports = {'stdlib': [], 'third_party': [], 'local': []}
            stdlib_modules = {
                'os','sys','re','json','math','random','time','datetime','collections','itertools','functools','pathlib','typing',
                'subprocess','threading','multiprocessing','asyncio','logging','unittest','tempfile','shutil','glob','pickle','csv','sqlite3'
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        import_str = f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else '')
                        (imports['stdlib'] if module in stdlib_modules else imports['third_party']).append(import_str)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    level = node.level
                    names = ', '.join([alias.name if not alias.asname else f"{alias.name} as {alias.asname}" for alias in node.names])
                    if level > 0:
                        import_str = f"from {'.'*level}{module} import {names}"
                        imports['local'].append(import_str)
                    else:
                        base = module.split('.')[0]
                        import_str = f"from {module} import {names}"
                        (imports['stdlib'] if base in stdlib_modules else imports['third_party']).append(import_str)
            for k in imports:
                imports[k] = sorted(list(set(imports[k])))
            import_lines = []
            if imports['stdlib']:
                import_lines.extend(x + '\n' for x in imports['stdlib'])
                import_lines.append('\n')
            if imports['third_party']:
                import_lines.extend(x + '\n' for x in imports['third_party'])
                import_lines.append('\n')
            if imports['local']:
                import_lines.extend(x + '\n' for x in imports['local'])
                import_lines.append('\n')
            if import_lines and import_lines[-1] == '\n':
                import_lines.pop()
            lines = content.splitlines(keepends=True)
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith(('import ', 'from ')):
                    import_end = i
                    break
            new_content = ''.join(import_lines + lines[import_end:])
            if new_content == content:
                return ''
            return self._unified_text_diff(file_path, file_path, content, new_content)
        except Exception:
            return ''
    
    # --- Enhanced Codemods ---
    
    def update_imports_for_moved_module(self, old_module_path: str, new_module_path: str) -> str:
        """Generate diff for updating all imports when a module is moved"""
        return CodemodOperations.update_imports_for_moved_module(
            self.repo_root, old_module_path, new_module_path
        )
    
    def organize_imports(self, file_path: str) -> Tuple[bool, str]:
        """Organize imports in a file: stdlib -> third-party -> local"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return CodemodOperations.organize_imports(path)
    
    def extract_class(self, file_path: str, class_name: str, target_file: str,
                     update_imports: bool = True) -> Tuple[bool, str]:
        """Extract a class to another file"""
        source = self.repo_root / file_path
        target = self.repo_root / target_file
        if not source.exists():
            return False, f"Source file {file_path} not found"
        return CodemodOperations.extract_class(source, class_name, target, update_imports)
    
    def update_relative_imports(self, file_path: str, old_location: str, 
                               new_location: str) -> Tuple[bool, str]:
        """Update relative imports when a file is moved"""
        path = self.repo_root / file_path
        old_path = self.repo_root / old_location
        new_path = self.repo_root / new_location
        if not path.exists():
            return False, f"File {file_path} not found"
        return CodemodOperations.update_relative_imports(path, old_path, new_path)
    
    def add_docstring(self, file_path: str, target: str, docstring: str,
                     target_type: str = "function") -> Tuple[bool, str]:
        """Add or update docstring for a function or class"""
        path = self.repo_root / file_path
        if not path.exists():
            return False, f"File {file_path} not found"
        return CodemodOperations.add_docstring(path, target, docstring, target_type)
    
    def move_module(self, old_path: str, new_path: str, update_imports: bool = True) -> Tuple[bool, str]:
        """Move a module file and optionally update all imports"""
        old_file = self.repo_root / old_path
        new_file = self.repo_root / new_path
        
        if not old_file.exists():
            return False, f"Source file {old_path} not found"
            
        # Create target directory if needed
        new_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Move the file
        try:
            import shutil
            shutil.move(str(old_file), str(new_file))
        except Exception as e:
            return False, f"Failed to move file: {e}"
            
        # Update imports if requested
        if update_imports:
            diff = self.update_imports_for_moved_module(old_path, new_path)
            if diff:
                # Apply the import updates
                ok, msg = self.apply_unified_diff(diff, f"update_imports_{old_path}_to_{new_path}")
                if not ok:
                    # Try to rollback the move
                    try:
                        shutil.move(str(new_file), str(old_file))
                    except:
                        pass
                    return False, f"Failed to update imports: {msg}"
                    
        return True, f"Moved {old_path} to {new_path}"
