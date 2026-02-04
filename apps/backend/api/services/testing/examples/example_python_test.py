"""
Example test file for demonstrating auto-healing capabilities.

This file intentionally contains various types of failures that the auto-healer can fix:
- Missing imports
- Assertion mismatches
- Mock configuration issues
"""

import pytest
from unittest.mock import Mock, patch

# MISSING IMPORT - Auto-healer will fix this
# from datetime import datetime


def calculate_total(items):
    """Example function for testing."""
    return sum(items) + 1  # Intentionally changed behavior


def get_user_data(user_id):
    """Example function that returns user data."""
    return {
        'id': user_id,
        'name': 'John Doe',
        'email': 'john@example.com',
        'created_at': '2024-01-01'  # Changed format
    }


class UserService:
    """Example service class."""

    def create_user(self, name, email):
        return {
            'id': 123,
            'name': name,
            'email': email,
            'status': 'active',  # New field added
            'created_at': datetime.now()  # Will cause NameError
        }


# Test 1: Assertion mismatch (expected value needs updating)
def test_calculate_total_basic():
    """Test basic calculation - expected value is outdated."""
    result = calculate_total([1, 2, 3])
    assert result == 6  # Should be 7 after code change


# Test 2: Assertion mismatch with more complex values
def test_calculate_total_with_zeros():
    """Test calculation with zeros."""
    result = calculate_total([0, 0, 0])
    assert result == 0  # Should be 1 after code change


# Test 3: Expected dictionary value changed
def test_get_user_data():
    """Test user data retrieval."""
    user = get_user_data(1)
    assert user['name'] == 'John Doe'
    assert user['created_at'] == datetime(2024, 1, 1)  # Wrong type, expects string now


# Test 4: Mock configuration needs updating
@patch('services.external_api.get_user')
def test_user_service_with_mock(mock_get_user):
    """Test with mocked external service."""
    # Mock returns wrong structure (API changed)
    mock_get_user.return_value = {
        'name': 'Jane',
        'email': 'jane@example.com'
        # Missing 'status' field that's now required
    }

    service = UserService()
    user = service.create_user('Jane', 'jane@example.com')

    assert user['name'] == 'Jane'
    assert user['status'] == 'active'


# Test 5: Import error (datetime not imported)
def test_user_creation_with_timestamp():
    """Test user creation with timestamp."""
    service = UserService()
    user = service.create_user('Alice', 'alice@example.com')

    # This will fail because datetime is not imported
    assert isinstance(user['created_at'], datetime)


# Test 6: Type error due to API change
def test_user_id_type():
    """Test that user ID is correct type."""
    user = get_user_data(1)
    assert isinstance(user['id'], int)
    assert user['id'] > 0


# Test 7: Multiple assertions, one wrong
def test_multiple_assertions():
    """Test with multiple assertions."""
    result = calculate_total([10, 20, 30])
    assert result > 0  # This will pass
    assert result == 60  # This will fail (should be 61)
    assert result < 100  # This will pass


# Test 8: Expected behavior with edge cases
def test_edge_cases():
    """Test edge cases."""
    assert calculate_total([]) == 0  # Should be 1
    assert calculate_total([1]) == 1  # Should be 2
    assert calculate_total([-1, 1]) == 0  # Should be 1


# Test 9: Fixture-based test with wrong expectation
@pytest.fixture
def sample_items():
    """Fixture providing sample items."""
    return [5, 10, 15]


def test_with_fixture(sample_items):
    """Test using fixture."""
    result = calculate_total(sample_items)
    assert result == 30  # Should be 31


# Test 10: Parameterized test with mixed results
@pytest.mark.parametrize("items,expected", [
    ([1, 2, 3], 6),  # Wrong, should be 7
    ([10, 20], 30),  # Wrong, should be 31
    ([100], 100),  # Wrong, should be 101
])
def test_calculate_total_parameterized(items, expected):
    """Parameterized test with various inputs."""
    assert calculate_total(items) == expected


# Test 11: Attribute error (accessing non-existent attribute)
def test_user_attributes():
    """Test user attributes."""
    user = get_user_data(1)
    # This will work
    assert hasattr(user, '__getitem__')
    # This might fail if we try to access as object
    # assert user.name == 'John Doe'  # AttributeError if user is dict


# Test 12: Test that should be skipped
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    """Test for future feature."""
    assert False


# Test 13: Expected failure
@pytest.mark.xfail(reason="Known issue")
def test_known_issue():
    """Test with known issue."""
    assert calculate_total([1, 2, 3]) == 6  # We know this fails
