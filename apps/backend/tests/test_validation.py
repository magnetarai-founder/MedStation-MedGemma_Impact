"""
Module: test_validation.py
Purpose: Test input validation, SQL injection prevention, and security validation

Coverage:
- SQL identifier validation (injection prevention)
- SafeSQLBuilder validation
- Quote identifier escaping
- Whitelist validation
- Error response format validation
- Pydantic model validation

Priority: 3.2 (Edge Cases & Error Handling)
Expected Coverage Gain: +2%
"""

import os
import sys
import pytest
from pathlib import Path

# Ensure test environment
os.environ["MEDSTATION_ENV"] = "test"

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.security.sql_safety import (
    validate_identifier,
    quote_identifier,
    validate_and_quote,
    SafeSQLBuilder,
    build_update_sql,
    SQLInjectionError,
    IDENTIFIER_PATTERN,
    MAX_IDENTIFIER_LENGTH,
)


class TestSQLIdentifierValidation:
    """Test SQL identifier validation for injection prevention"""

    def test_valid_identifier_passes(self):
        """Test that valid identifiers pass validation"""
        assert validate_identifier("users") == "users"
        assert validate_identifier("user_id") == "user_id"
        assert validate_identifier("_private") == "_private"
        assert validate_identifier("User123") == "User123"

    def test_empty_identifier_raises_error(self):
        """Test that empty identifier raises SQLInjectionError"""
        with pytest.raises(SQLInjectionError) as exc:
            validate_identifier("")
        assert "Empty" in str(exc.value)

    def test_identifier_too_long_raises_error(self):
        """Test that identifier exceeding max length raises error"""
        long_name = "a" * (MAX_IDENTIFIER_LENGTH + 1)
        with pytest.raises(SQLInjectionError) as exc:
            validate_identifier(long_name)
        assert "exceeds maximum length" in str(exc.value)

    def test_identifier_at_max_length_passes(self):
        """Test that identifier at exactly max length passes"""
        max_name = "a" * MAX_IDENTIFIER_LENGTH
        assert validate_identifier(max_name) == max_name

    def test_sql_injection_attempt_blocked(self):
        """Test that SQL injection patterns are blocked"""
        with pytest.raises(SQLInjectionError):
            validate_identifier("users; DROP TABLE users;--")

    def test_identifier_with_spaces_blocked(self):
        """Test that identifiers with spaces are blocked"""
        with pytest.raises(SQLInjectionError):
            validate_identifier("user name")

    def test_identifier_starting_with_number_blocked(self):
        """Test that identifiers starting with number are blocked"""
        with pytest.raises(SQLInjectionError):
            validate_identifier("123users")

    def test_sql_keywords_blocked(self):
        """Test that SQL keywords are blocked as identifiers"""
        keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
                    "UNION", "JOIN", "EXEC", "GRANT"]
        for keyword in keywords:
            with pytest.raises(SQLInjectionError) as exc:
                validate_identifier(keyword)
            assert "reserved SQL keyword" in str(exc.value)

    def test_sql_keywords_case_insensitive(self):
        """Test that SQL keyword detection is case insensitive"""
        with pytest.raises(SQLInjectionError):
            validate_identifier("select")
        with pytest.raises(SQLInjectionError):
            validate_identifier("SELECT")
        with pytest.raises(SQLInjectionError):
            validate_identifier("SeLeCt")


class TestWhitelistValidation:
    """Test whitelist-based identifier validation"""

    def test_whitelist_allows_valid_value(self):
        """Test that whitelisted values are allowed"""
        result = validate_identifier("users", allowed=["users", "sessions"])
        assert result == "users"

    def test_whitelist_blocks_invalid_value(self):
        """Test that non-whitelisted values are blocked"""
        with pytest.raises(SQLInjectionError) as exc:
            validate_identifier("hackers", allowed=["users", "sessions"])
        assert "Must be one of" in str(exc.value)

    def test_whitelist_error_shows_allowed_values(self):
        """Test that error message shows allowed values"""
        with pytest.raises(SQLInjectionError) as exc:
            validate_identifier("bad", allowed=["users", "sessions"])
        assert "users" in str(exc.value)
        assert "sessions" in str(exc.value)

    def test_whitelist_truncates_long_list(self):
        """Test that long whitelist is truncated in error message"""
        long_list = [f"table_{i}" for i in range(20)]
        with pytest.raises(SQLInjectionError) as exc:
            validate_identifier("invalid", allowed=long_list)
        assert "..." in str(exc.value)


class TestQuoteIdentifier:
    """Test identifier quoting for SQL safety"""

    def test_simple_identifier_quoted(self):
        """Test that simple identifiers are quoted"""
        result = quote_identifier("users")
        assert result == '"users"'

    def test_identifier_with_embedded_quote_escaped(self):
        """Test that embedded quotes are escaped by doubling"""
        result = quote_identifier('user"name')
        assert result == '"user""name"'

    def test_multiple_quotes_escaped(self):
        """Test that multiple embedded quotes are escaped"""
        result = quote_identifier('a"b"c')
        assert result == '"a""b""c"'

    def test_validate_and_quote_combined(self):
        """Test validate_and_quote combines both operations"""
        result = validate_and_quote("users", allowed=["users"])
        assert result == '"users"'

    def test_validate_and_quote_fails_on_invalid(self):
        """Test validate_and_quote raises on invalid identifier"""
        with pytest.raises(SQLInjectionError):
            validate_and_quote("invalid", allowed=["users"])


class TestSafeSQLBuilder:
    """Test SafeSQLBuilder for safe query construction"""

    def test_simple_select_all(self):
        """Test simple SELECT * query"""
        builder = SafeSQLBuilder("users")
        sql = builder.build()
        assert sql == 'SELECT * FROM "users"'

    def test_select_specific_columns(self):
        """Test SELECT with specific columns"""
        builder = SafeSQLBuilder("users", allowed_columns=["id", "name"])
        sql = builder.select(["id", "name"]).build()
        assert '"id"' in sql
        assert '"name"' in sql
        assert 'FROM "users"' in sql

    def test_select_with_where(self):
        """Test SELECT with WHERE clause"""
        builder = SafeSQLBuilder("users")
        sql = builder.select(["id"]).where("id = ?").build()
        assert "WHERE id = ?" in sql

    def test_select_with_order_by_asc(self):
        """Test SELECT with ORDER BY ASC"""
        builder = SafeSQLBuilder("users", allowed_columns=["name"])
        sql = builder.select(["name"]).order_by("name").build()
        assert 'ORDER BY "name" ASC' in sql

    def test_select_with_order_by_desc(self):
        """Test SELECT with ORDER BY DESC"""
        builder = SafeSQLBuilder("users", allowed_columns=["created_at"])
        sql = builder.select(["created_at"]).order_by("created_at", desc=True).build()
        assert 'ORDER BY "created_at" DESC' in sql

    def test_select_with_limit(self):
        """Test SELECT with LIMIT"""
        builder = SafeSQLBuilder("users")
        sql = builder.limit(10).build()
        assert "LIMIT 10" in sql

    def test_select_with_offset(self):
        """Test SELECT with OFFSET"""
        builder = SafeSQLBuilder("users")
        sql = builder.offset(20).build()
        assert "OFFSET 20" in sql

    def test_select_with_all_clauses(self):
        """Test SELECT with all clauses combined"""
        builder = SafeSQLBuilder("users", allowed_columns=["id", "name"])
        sql = (builder
               .select(["id", "name"])
               .where("active = ?")
               .order_by("name")
               .limit(10)
               .offset(5)
               .build())
        assert '"id"' in sql
        assert '"name"' in sql
        assert 'FROM "users"' in sql
        assert "WHERE active = ?" in sql
        assert 'ORDER BY "name" ASC' in sql
        assert "LIMIT 10" in sql
        assert "OFFSET 5" in sql

    def test_invalid_column_blocked(self):
        """Test that invalid column names are blocked"""
        builder = SafeSQLBuilder("users", allowed_columns=["id", "name"])
        with pytest.raises(SQLInjectionError):
            builder.select(["password"])

    def test_invalid_table_blocked(self):
        """Test that invalid table names are blocked"""
        with pytest.raises(SQLInjectionError):
            SafeSQLBuilder("secrets", allowed_tables=["users", "sessions"])

    def test_negative_limit_blocked(self):
        """Test that negative LIMIT raises ValueError"""
        builder = SafeSQLBuilder("users")
        with pytest.raises(ValueError) as exc:
            builder.limit(-1)
        assert "non-negative" in str(exc.value)

    def test_negative_offset_blocked(self):
        """Test that negative OFFSET raises ValueError"""
        builder = SafeSQLBuilder("users")
        with pytest.raises(ValueError) as exc:
            builder.offset(-1)
        assert "non-negative" in str(exc.value)


class TestBuildUpdateSQL:
    """Test safe UPDATE statement builder"""

    def test_simple_update(self):
        """Test simple UPDATE statement"""
        sql = build_update_sql("users", ["name", "email"])
        assert 'UPDATE "users"' in sql
        assert '"name" = ?' in sql
        assert '"email" = ?' in sql
        assert "WHERE id = ?" in sql

    def test_update_with_custom_where(self):
        """Test UPDATE with custom WHERE clause"""
        sql = build_update_sql("users", ["status"], where_clause="user_id = ? AND active = ?")
        assert "WHERE user_id = ? AND active = ?" in sql

    def test_update_with_whitelist(self):
        """Test UPDATE with column whitelist"""
        sql = build_update_sql(
            "users",
            ["name"],
            allowed_tables=["users"],
            allowed_columns=["name", "email"]
        )
        assert '"name" = ?' in sql

    def test_update_invalid_table_blocked(self):
        """Test that invalid table in UPDATE is blocked"""
        with pytest.raises(SQLInjectionError):
            build_update_sql("secrets", ["name"], allowed_tables=["users"])

    def test_update_invalid_column_blocked(self):
        """Test that invalid column in UPDATE is blocked"""
        with pytest.raises(SQLInjectionError):
            build_update_sql("users", ["password"], allowed_columns=["name"])


class TestIdentifierPattern:
    """Test the identifier regex pattern"""

    def test_pattern_allows_valid_identifiers(self):
        """Test pattern allows valid SQL identifiers"""
        valid = ["users", "user_id", "_private", "User123", "a", "_"]
        for ident in valid:
            assert IDENTIFIER_PATTERN.match(ident) is not None

    def test_pattern_blocks_invalid_identifiers(self):
        """Test pattern blocks invalid identifiers"""
        invalid = ["123abc", "user-id", "user.id", "user id", "", "user@id"]
        for ident in invalid:
            assert IDENTIFIER_PATTERN.match(ident) is None


class TestErrorResponseValidation:
    """Test error response format consistency"""

    def test_error_code_module_exists(self):
        """Test that error codes module is importable"""
        from api.error_codes import ErrorCode
        assert ErrorCode is not None

    def test_error_responses_return_correct_structure(self):
        """Test that error response helpers return correct structure"""
        from api.error_responses import bad_request, unauthorized, forbidden
        from api.error_codes import ErrorCode

        # bad_request should raise HTTPException
        try:
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED)
        except Exception as e:
            assert hasattr(e, 'status_code')
            assert e.status_code == 400

    def test_unauthorized_error(self):
        """Test unauthorized error response"""
        from api.error_responses import unauthorized
        from api.error_codes import ErrorCode

        try:
            raise unauthorized(ErrorCode.AUTH_INVALID_CREDENTIALS)
        except Exception as e:
            assert e.status_code == 401

    def test_forbidden_error(self):
        """Test forbidden error response"""
        from api.error_responses import forbidden
        from api.error_codes import ErrorCode

        try:
            raise forbidden(ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS)
        except Exception as e:
            assert e.status_code == 403


class TestPydanticModelValidation:
    """Test Pydantic model validation"""

    def test_register_request_username_too_short(self):
        """Test RegisterRequest rejects username < 3 chars"""
        from api.auth_routes import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", password="password123!", device_id="device1")

    def test_register_request_username_too_long(self):
        """Test RegisterRequest rejects username > 50 chars"""
        from api.auth_routes import RegisterRequest
        from pydantic import ValidationError

        long_username = "a" * 51
        with pytest.raises(ValidationError):
            RegisterRequest(username=long_username, password="password123!", device_id="device1")

    def test_register_request_password_too_short(self):
        """Test RegisterRequest rejects password < 8 chars"""
        from api.auth_routes import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(username="validuser", password="short", device_id="device1")

    def test_register_request_valid(self):
        """Test RegisterRequest accepts valid input"""
        from api.auth_routes import RegisterRequest

        req = RegisterRequest(
            username="validuser",
            password="ValidPassword123!",
            device_id="device123"
        )
        assert req.username == "validuser"
        assert req.password == "ValidPassword123!"

    def test_login_request_allows_any_length(self):
        """Test LoginRequest has no length constraints"""
        from api.auth_routes import LoginRequest

        # Should not raise
        req = LoginRequest(username="x", password="y")
        assert req.username == "x"

    def test_refresh_request_requires_token(self):
        """Test RefreshRequest requires refresh_token field"""
        from api.auth_routes import RefreshRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RefreshRequest()  # Missing required field
