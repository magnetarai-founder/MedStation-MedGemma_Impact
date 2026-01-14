"""
Redshift SQL Processor Constants

Shared constants and pre-compiled regex patterns.
"""

import re

# SQL reserved words that need special handling
RESERVED_WORDS = frozenset({
    "select",
    "from",
    "where",
    "group",
    "order",
    "by",
    "limit",
    "offset",
    "join",
    "left",
    "right",
    "full",
    "inner",
    "outer",
    "on",
    "using",
    "as",
    "case",
    "when",
    "then",
    "else",
    "end",
    "not",
    "and",
    "or",
    "like",
    "ilike",
    "in",
    "is",
    "null",
    "table",
    "column",
    "columns",
    "view",
    "with",
    "recursive",
    "union",
    "all",
    "distinct",
    "having",
    "top",
})

# Pre-compiled regex patterns for better performance
REGEX_PATTERNS = {
    "null_numeric": re.compile(r"null::numeric\b", re.IGNORECASE),
    "null_decimal": re.compile(r"null::decimal\((\d+),(\d+)\)", re.IGNORECASE),
    "null_int": re.compile(r"null::int\b", re.IGNORECASE),
    "null_text": re.compile(r"null::text\b", re.IGNORECASE),
    "null_varchar": re.compile(r"null::varchar\b", re.IGNORECASE),
    "regex_op": re.compile(r"(\w+)\s*~\s*'([^']+)'", re.IGNORECASE),
    "not_regex_op": re.compile(r"(\w+)\s*!~\s*'([^']+)'", re.IGNORECASE),
    "from_clause": re.compile(r"\bFROM\s+(\w+)", re.IGNORECASE),
    "double_colon_cast": re.compile(r"::(\w+)\b", re.IGNORECASE),
    "table_name": re.compile(r"\b{table_name}\b", re.IGNORECASE),
}

# Column name patterns for type inference
IDENTIFIER_PATTERNS = [
    "BARCODE",
    "UPC",
    "EAN",
    "GTIN",
    "SKU",
    "MERCHANT_SKU",
    "PRODUCT_CODE",
    "ITEM_CODE",
    "ASIN",
    "ISBN",
]

NUMERIC_PATTERNS = [
    "PRICE",
    "COST",
    "SALES",
    "REVENUE",
    "AMOUNT",
    "VALUE",
    "QUANTITY",
    "QTY",
    "COUNT",
    "WEIGHT",
    "SIZE",
    "VOLUME",
    "PERCENT",
    "RATE",
    "MARGIN",
    "DISCOUNT",
    "TAX",
    "TOTAL",
]
