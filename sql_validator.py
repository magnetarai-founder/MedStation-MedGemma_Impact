"""
SQL Validator - Pre-checks SQL syntax before processing
"""

import re
import logging
from typing import List, Tuple, Optional
import sqlparse

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validates SQL queries for syntax and common issues"""

    def __init__(self):
        # Common Redshift/DuckDB functions that are valid
        self.valid_functions = {
            "NVL",
            "NULLIF",
            "COALESCE",
            "CAST",
            "TRIM",
            "LTRIM",
            "RTRIM",
            "UPPER",
            "LOWER",
            "LENGTH",
            "SUBSTRING",
            "SUBSTR",
            "REPLACE",
            "REGEXP_MATCHES",
            "REGEXP_EXTRACT",
            "REGEXP_SUBSTR",
            "REGEXP_REPLACE",
            "CURRENT_DATE",
            "DATE",
            "EXTRACT",
            "DATE_PART",
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "STDDEV",
            "VARIANCE",
            "ROW_NUMBER",
            "RANK",
            "DENSE_RANK",
            "FIRST_VALUE",
            "LAST_VALUE",
            "LAG",
            "LEAD",
            "NTILE",
            "PERCENT_RANK",
            "ROUND",
            "CEIL",
            "FLOOR",
            "ABS",
            "SQRT",
            "POWER",
            "MOD",
            "SPLIT_PART",
            "CONCAT",
            "STRING_AGG",
            "LISTAGG",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "TRY_CAST",
            "TO_CHAR",
            "TO_NUMBER",
            "TO_DATE",
        }

        # Common table names in queries - now empty since we accept any table
        self.expected_tables = set()

    def validate_sql(
        self, sql: str, expected_table: Optional[str] = None, strict: bool = False
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate SQL query syntax and structure

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        if not sql or not sql.strip():
            errors.append("SQL query is empty")
            return False, errors, warnings

        # Basic syntax validation using sqlparse
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                errors.append("Could not parse SQL query")
                return False, errors, warnings
        except Exception as e:
            errors.append(f"SQL parsing error: {str(e)}")
            return False, errors, warnings

        # Check for common syntax issues
        syntax_errors = self._check_syntax_issues(sql)
        errors.extend(syntax_errors)

        # Check for balanced parentheses and quotes
        balance_errors = self._check_balanced_delimiters(sql)
        errors.extend(balance_errors)

        # Check for potentially problematic patterns
        pattern_warnings = self._check_problematic_patterns(sql)
        warnings.extend(pattern_warnings)

        # Extract and validate table references
        table_warnings = self._check_table_references(sql)
        warnings.extend(table_warnings)

        # Check for common typos in function names
        function_warnings = self._check_function_names(sql)
        warnings.extend(function_warnings)

        # Optional stricter checks (kept off by default to preserve permissive behavior)
        if strict:
            strict_errors = self._strict_checks(sql)
            errors.extend(strict_errors)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    # Backward-compatible boolean API used by some stress scripts
    def validate_query(self, sql: str, expected_table: Optional[str] = None) -> bool:  # pragma: no cover - adapter
        is_valid, _errors, _warnings = self.validate_sql(sql, expected_table)
        return is_valid

    def _check_syntax_issues(self, sql: str) -> List[str]:
        """Check for common syntax issues"""
        errors = []

        # Skip comma checking - produces too many false positives
        # Real syntax errors will be caught by the SQL engine

        # Check for SELECT without FROM
        if re.search(r"\bSELECT\b", sql, re.IGNORECASE) and not re.search(r"\bFROM\b", sql, re.IGNORECASE):
            # Allow SELECT without FROM for constant expressions
            if not re.search(r"SELECT\s+\d+|SELECT\s+\'[^\']*\'|SELECT\s+CURRENT_DATE", sql, re.IGNORECASE):
                errors.append("SELECT statement missing FROM clause")

        # Check for unclosed CASE statements
        case_count = len(re.findall(r"\bCASE\b", sql, re.IGNORECASE))
        end_count = len(re.findall(r"\bEND\b", sql, re.IGNORECASE))
        if case_count > end_count:
            errors.append(f"Unclosed CASE statement (found {case_count} CASE but only {end_count} END)")

        # Check for FROM present but missing a table name or subquery
        # Heuristic: FROM not followed by an identifier/quoted identifier or opening parenthesis
        if re.search(r"\bFROM\b", sql, re.IGNORECASE):
            missing_table = re.search(
                r"(?is)\bFROM\s*(?!\(|\"?[A-Za-z_][\w]*\"?)\b(?:WHERE|GROUP|ORDER|LIMIT|HAVING)\b|\bFROM\s*$",
                sql,
            )
            if missing_table:
                errors.append("FROM clause missing table name or subquery")

        return errors

    def _check_balanced_delimiters(self, sql: str) -> List[str]:
        """Check for balanced parentheses, quotes, etc."""
        errors = []

        # Remove string literals and comments to avoid false positives
        sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        sql_clean = re.sub(r"/\\*.*?\\*/", "", sql_clean, flags=re.DOTALL)

        # More sophisticated parentheses counting
        # Remove string literals first to avoid counting parens inside strings
        sql_no_strings = sql_clean
        # Remove single-quoted strings
        sql_no_strings = re.sub(r"'[^']*'", "", sql_no_strings)
        # Remove double-quoted strings
        sql_no_strings = re.sub(r'"[^"]*"', "", sql_no_strings)

        # Count parentheses
        open_parens = sql_no_strings.count("(")
        close_parens = sql_no_strings.count(")")

        # Only report parentheses errors if significantly unbalanced
        # Many valid SQL queries can have complex parentheses patterns that are hard to parse
        if abs(open_parens - close_parens) > 2:
            errors.append(f"Possibly unbalanced parentheses: {open_parens} opening, {close_parens} closing")

        # Skip string literal checking - too complex with various escape sequences
        # The SQL parser will catch real string errors

        return errors

    def _check_problematic_patterns(self, sql: str) -> List[str]:
        """Check for patterns that might cause issues"""
        warnings = []

        # Check for very large LIMIT values
        limit_match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 1000000:
                warnings.append(f"Very large LIMIT value ({limit_val}) may cause performance issues")

        # Skip SELECT * warning - often intentional in data transformation

        # Check for missing aliases in subqueries
        if "(" in sql and ")" in sql:
            # Simple check for subqueries without aliases
            if re.search(r"\)\s*(?:WHERE|GROUP|ORDER|LIMIT|$)", sql, re.IGNORECASE):
                warnings.append("Subqueries should have aliases (e.g., ) AS subquery_name")

        # Check for potential cartesian products (multiple tables without JOIN)
        from_match = re.search(r"\bFROM\s+(\w+)\s*,\s*(\w+)", sql, re.IGNORECASE)
        if from_match:
            warnings.append("Multiple tables in FROM clause without JOIN may create cartesian product")

        return warnings

    def _check_table_references(self, sql: str) -> List[str]:
        """Check table references in the query"""
        warnings = []

        # First check if this appears to be a multi-source query (with CTEs or subqueries)
        # (kept as future hooks; not currently used)

        # Extract table names from FROM and JOIN clauses
        table_pattern = r"(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*(?:\s+(?:AS\s+)?[a-zA-Z_]\w*)?)"
        tables = re.findall(table_pattern, sql, re.IGNORECASE)

        # Since we now accept any table name from loaded Excel files,
        # we'll only check for basic issues like missing tables
        if not tables and re.search(r"\bSELECT\b", sql, re.IGNORECASE):
            # Check if it's a SELECT without FROM (which is sometimes valid)
            if not re.search(r"SELECT\s+\d+|SELECT\s+\'[^\']*\'|SELECT\s+CURRENT_DATE", sql, re.IGNORECASE):
                warnings.append("Query appears to be missing a FROM clause")

        return warnings

    def _check_function_names(self, sql: str) -> List[str]:
        """Check for potential typos in function names"""
        warnings = []

        # SQL keywords that might appear before parentheses but aren't functions
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "WITH",
            "AS",
            "AND",
            "OR",
            "NOT",
            "IN",
            "EXISTS",
            "BETWEEN",
            "LIKE",
            "GROUP",
            "BY",
            "ORDER",
            "HAVING",
            "UNION",
            "ALL",
            "DISTINCT",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "ON",
            "USING",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "OVER",
            "PARTITION",
            "ROWS",
            "RANGE",
            "PRECEDING",
            "FOLLOWING",
            "CURRENT",
            "FOR",
            "UPDATE",
            "INSERT",
            "INTO",
            "VALUES",
            "DELETE",
            "CREATE",
            "TABLE",
            "VIEW",
            "INDEX",
            "TRIGGER",
            "DATABASE",
            "SCHEMA",
        }

        # Find all function-like patterns
        function_pattern = r"\b([a-zA-Z_]\w*)\s*\("
        potential_functions = re.findall(function_pattern, sql)

        for func in potential_functions:
            func_upper = func.upper()

            # Skip if it's a known valid function or SQL keyword
            if func_upper in self.valid_functions or func_upper in sql_keywords:
                continue

            # Check for common typos
            typo_map = {
                "NULLIFF": "NULLIF",
                "COALESE": "COALESCE",
                "COALLESCE": "COALESCE",
                "SUBCTR": "SUBSTR",
                "SUBSTRING": "SUBSTR",  # Suggest shorter form
                "TRIMM": "TRIM",
                "LENGHT": "LENGTH",
                "UPPPER": "UPPER",
                "LOWWER": "LOWER",
                "COUNNT": "COUNT",
                "SUMM": "SUM",
                "MAXX": "MAX",
                "MINN": "MIN",
                "REGEX": "REGEXP_MATCHES",
                "REGEX_SUBSTR": "REGEXP_SUBSTR",
            }

            if func_upper in typo_map:
                warnings.append(f"Possible typo: '{func}' - did you mean '{typo_map[func_upper]}'?")
            elif func_upper not in self.valid_functions:
                # Only warn about truly unknown functions, not SQL syntax
                # Skip warning for short words that are likely SQL syntax
                if len(func_upper) > 2:
                    close_matches = [
                        f
                        for f in self.valid_functions
                        if abs(len(f) - len(func_upper)) <= 2 and sum(c1 != c2 for c1, c2 in zip(f, func_upper)) <= 2
                    ]
                    if close_matches:
                        warnings.append(f"Unknown function '{func}' - did you mean '{close_matches[0]}'?")

        return warnings

    def get_validation_summary(self, sql: str) -> str:
        """Get a formatted summary of validation results"""
        is_valid, errors, warnings = self.validate_sql(sql)

        if is_valid and not warnings:
            return "✓ SQL syntax appears valid"

        summary = []
        if errors:
            summary.append("❌ Errors found:")
            for error in errors:
                summary.append(f"  • {error}")

        if warnings:
            if errors:
                summary.append("")
            summary.append("⚠️  Warnings:")
            for warning in warnings:
                summary.append(f"  • {warning}")

        return "\n".join(summary)

    # --- internal helpers -------------------------------------------------
    def _strict_checks(self, sql: str) -> List[str]:
        """Additional conservative checks for obviously invalid syntax.

        These checks catch common typos that sqlparse may tolerate.
        They are intentionally minimal and off by default.
        """
        errs: List[str] = []
        s = sql.strip()
        # SELECT list trailing comma: SELECT a, FROM t
        m = re.search(r"(?is)\bselect\b(.*?)\bfrom\b", s)
        if m:
            sel = m.group(1)
            if re.search(r",\s*$", sel):
                errs.append("Trailing comma in SELECT list before FROM")
            if re.search(r"^\s*,", sel):
                errs.append("Leading comma in SELECT list")
        # Dangling commas in GROUP BY / ORDER BY
        for kw in ["group by", "order by"]:
            mm = re.search(rf"(?is)\b{kw}\b(.*?)(?:$|\blimit\b|\boffset\b|\border\b|\bgroup\b|\bwhere\b|\bhaving\b)", s)
            if mm:
                seg = mm.group(1)
                if re.search(r",\s*$", seg):
                    errs.append(f"Trailing comma in {kw.upper()} clause")
        return errs
