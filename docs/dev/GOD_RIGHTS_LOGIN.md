# God Rights (Founder) Login

## Overview

ElohimOS has a hardcoded "backdoor" admin account for founder/field support access. This account always exists and cannot be locked out, allowing the ElohimOS team to help users troubleshoot issues.

## Development Credentials

**Username:** `elohim_founder`
**Password:** `ElohimOS_2024_Founder`

## Production Setup

In production, set these environment variables:

```bash
ELOHIM_GOD_USERNAME="elohim_founder"  # Optional, defaults to this
ELOHIM_GOD_PASSWORD="your-secure-password-here"  # REQUIRED
```

**IMPORTANT:** The default password (`ElohimOS_2024_Founder`) only works in development mode. Production REQUIRES setting `ELOHIM_GOD_PASSWORD`.

## How It Works

1. When a user logs in with `elohim_founder` username, auth_middleware checks if it matches `GOD_RIGHTS_USERNAME`
2. If yes, validates password against `GOD_RIGHTS_PASSWORD` (bypasses user database)
3. Creates JWT token with `role: "god_rights"` and `user_id: "god_rights"`
4. This account has full access to all system features, including:
   - Support Dashboard (coming soon)
   - User account management
   - Password resets
   - Account unlocking
   - Role elevation

## Use Cases

- **Field Support:** When your team is helping users set up ElohimOS and encounters issues
- **Account Recovery:** When a user gets locked out and needs help
- **Team Management:** Setting up super_admins and delegating support access
- **Troubleshooting:** Diagnosing issues in user accounts
- **Emergency Access:** Critical situations requiring immediate access

## Security Notes

- This account cannot be disabled through normal means
- Failed login attempts are logged
- Access should be restricted to trusted ElohimOS team members only
- Consider rotating the password periodically
- In production, use a strong, unique password stored securely

## Future Enhancements

- [ ] Support Dashboard for managing all users on a device
- [ ] Audit logging of God Rights actions
- [ ] Role delegation to super_admins
- [ ] Limited support mode for super_admins
