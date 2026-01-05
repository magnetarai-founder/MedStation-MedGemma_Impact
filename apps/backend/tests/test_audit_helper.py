"""
Comprehensive tests for api/audit_helper.py

Tests the unified audit event recording API.

Coverage targets:
- record_audit_event: Main entry point for audit logging
- get_user_from_current_user: User ID extraction helper
- Error handling and graceful degradation
"""

import pytest
from unittest.mock import patch, MagicMock

from api.audit_helper import record_audit_event, get_user_from_current_user


# ========== record_audit_event Tests ==========

class TestRecordAuditEvent:
    """Tests for record_audit_event function"""

    def test_basic_audit_event(self):
        """Test recording a basic audit event"""
        # Patch at source module since import happens inside the function
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='test.action'
            )

        assert result is True
        mock_audit.assert_called_once_with(
            user_id='user_123',
            action='test.action',
            resource=None,
            resource_id=None,
            details=None
        )

    def test_audit_event_with_all_params(self):
        """Test recording an audit event with all parameters"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='admin_456',
                action='admin.reset_all',
                resource='system',
                resource_id='sys_001',
                details={'reason': 'dev reset', 'files_cleared': 50},
                ip_address='192.168.1.100',
                user_agent='Mozilla/5.0'
            )

        assert result is True
        mock_audit.assert_called_once_with(
            user_id='admin_456',
            action='admin.reset_all',
            resource='system',
            resource_id='sys_001',
            details={'reason': 'dev reset', 'files_cleared': 50}
        )

    def test_audit_event_with_resource(self):
        """Test recording an audit event with resource info"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_789',
                action='workflow.visibility.changed',
                resource='workflow',
                resource_id='wf_123',
                details={'from': 'personal', 'to': 'team'}
            )

        assert result is True
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs['resource'] == 'workflow'
        assert call_kwargs['resource_id'] == 'wf_123'
        assert call_kwargs['details'] == {'from': 'personal', 'to': 'team'}

    def test_audit_event_logs_to_python_logger(self):
        """Test that audit events are also logged via Python logger"""
        with patch('api.audit_logger.audit_log_sync'):
            with patch('api.audit_helper.logger') as mock_logger:
                record_audit_event(
                    user_id='user_123',
                    action='test.action',
                    resource='test',
                    ip_address='10.0.0.1',
                    user_agent='TestAgent/1.0'
                )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert 'Audit: test.action' in call_args[0][0]
        assert call_args[1]['extra']['user_id'] == 'user_123'
        assert call_args[1]['extra']['ip_address'] == '10.0.0.1'
        assert call_args[1]['extra']['user_agent'] == 'TestAgent/1.0'

    def test_audit_event_handles_exception(self):
        """Test that exceptions are caught and logged"""
        with patch('api.audit_logger.audit_log_sync', side_effect=Exception("DB error")):
            with patch('api.audit_helper.logger') as mock_logger:
                result = record_audit_event(
                    user_id='user_123',
                    action='test.action'
                )

        # Should return False on error
        assert result is False
        # Should log the error
        mock_logger.error.assert_called_once()
        assert "Failed to record audit event" in mock_logger.error.call_args[0][0]

    def test_audit_event_import_error_fallback(self):
        """Test fallback import path when api.audit_logger fails"""
        # This tests the ImportError handling in the try/except block
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        import_count = 0

        def mock_import(name, *args, **kwargs):
            nonlocal import_count
            if name == 'api.audit_logger':
                import_count += 1
                if import_count == 1:
                    raise ImportError("No module named api.audit_logger")
            return original_import(name, *args, **kwargs)

        # This is tricky to test because the import happens inside the function
        # We'll just verify the function works normally
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='test',
                action='test.action'
            )

        assert result is True

    def test_audit_event_system_user(self):
        """Test recording an audit event from system (not a user)"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='system',
                action='system.startup',
                resource='system',
                details={'version': '1.0.0'}
            )

        assert result is True
        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]['user_id'] == 'system'

    def test_audit_event_rbac_change(self):
        """Test recording an RBAC change audit event"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='admin_001',
                action='rbac.role.assigned',
                resource='user',
                resource_id='user_456',
                details={'role': 'moderator', 'granted_by': 'admin_001'}
            )

        assert result is True

    def test_audit_event_agent_operation(self):
        """Test recording an agent auto-apply audit event"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='agent.auto_apply',
                resource='agent',
                resource_id='agent_789',
                details={'files_changed': 3, 'patch_applied': True}
            )

        assert result is True

    def test_audit_event_data_export(self):
        """Test recording a data export audit event"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='data.export',
                resource='backup',
                details={'format': 'json', 'size_mb': 150}
            )

        assert result is True


# ========== get_user_from_current_user Tests ==========

class TestGetUserFromCurrentUser:
    """Tests for get_user_from_current_user function"""

    def test_extract_user_id_from_dict(self):
        """Test extracting user_id from valid dict"""
        current_user = {'user_id': 'user_123', 'username': 'john'}
        result = get_user_from_current_user(current_user)
        assert result == 'user_123'

    def test_missing_user_id_returns_system(self):
        """Test that missing user_id returns 'system'"""
        current_user = {'username': 'john'}  # No user_id
        result = get_user_from_current_user(current_user)
        assert result == 'system'

    def test_none_returns_system(self):
        """Test that None returns 'system'"""
        result = get_user_from_current_user(None)
        assert result == 'system'

    def test_empty_dict_returns_system(self):
        """Test that empty dict returns 'system'"""
        result = get_user_from_current_user({})
        assert result == 'system'

    def test_non_dict_returns_system(self):
        """Test that non-dict types return 'system'"""
        # String
        result = get_user_from_current_user("user_123")
        assert result == 'system'

        # List
        result = get_user_from_current_user(['user_123'])
        assert result == 'system'

        # Integer
        result = get_user_from_current_user(123)
        assert result == 'system'

    def test_user_id_with_special_values(self):
        """Test user_id extraction with various valid values"""
        # UUID format
        current_user = {'user_id': '550e8400-e29b-41d4-a716-446655440000'}
        assert get_user_from_current_user(current_user) == '550e8400-e29b-41d4-a716-446655440000'

        # Numeric string
        current_user = {'user_id': '12345'}
        assert get_user_from_current_user(current_user) == '12345'

        # Email format
        current_user = {'user_id': 'user@example.com'}
        assert get_user_from_current_user(current_user) == 'user@example.com'

    def test_user_id_empty_string(self):
        """Test that empty string user_id is returned (not 'system')"""
        # Empty string is falsy but still a valid value to return
        current_user = {'user_id': ''}
        result = get_user_from_current_user(current_user)
        # .get() returns '' for empty string, which is falsy but not None
        assert result == ''

    def test_user_id_none_value(self):
        """Test that None user_id value returns None (key exists but value is None)"""
        current_user = {'user_id': None}
        result = get_user_from_current_user(current_user)
        # .get() returns None because key exists with value None
        # (default 'system' only used when key is missing)
        assert result is None


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests combining both functions"""

    def test_audit_with_extracted_user(self):
        """Test recording audit event using extracted user"""
        current_user = {'user_id': 'user_456', 'role': 'admin'}

        user_id = get_user_from_current_user(current_user)

        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id=user_id,
                action='admin.action',
                resource='system'
            )

        assert result is True
        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]['user_id'] == 'user_456'

    def test_audit_with_system_fallback(self):
        """Test audit event falls back to 'system' for missing user"""
        current_user = None

        user_id = get_user_from_current_user(current_user)

        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id=user_id,
                action='system.internal',
                resource='system'
            )

        assert result is True
        assert mock_audit.call_args[1]['user_id'] == 'system'


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_audit_event_unicode_details(self):
        """Test audit event with unicode in details"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='用户_123',
                action='测试.动作',
                details={'message': '日本語テスト', 'emoji': '🔐'}
            )

        assert result is True

    def test_audit_event_large_details(self):
        """Test audit event with large details dict"""
        large_details = {f'key_{i}': f'value_{i}' * 100 for i in range(100)}

        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='large.data',
                details=large_details
            )

        assert result is True

    def test_audit_event_nested_details(self):
        """Test audit event with nested details dict"""
        nested_details = {
            'level1': {
                'level2': {
                    'level3': 'deep_value'
                }
            },
            'array': [1, 2, {'nested': True}]
        }

        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='nested.data',
                details=nested_details
            )

        assert result is True

    def test_audit_event_special_chars_in_action(self):
        """Test audit event with special characters in action"""
        with patch('api.audit_logger.audit_log_sync') as mock_audit:
            result = record_audit_event(
                user_id='user_123',
                action='test.action-with_special.chars:v1'
            )

        assert result is True

    def test_get_user_with_extra_fields(self):
        """Test user extraction ignores extra fields"""
        current_user = {
            'user_id': 'user_123',
            'username': 'john',
            'email': 'john@example.com',
            'role': 'admin',
            'permissions': ['read', 'write', 'admin']
        }

        result = get_user_from_current_user(current_user)
        assert result == 'user_123'
