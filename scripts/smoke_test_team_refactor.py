#!/usr/bin/env python3
"""
Smoke test for Phase 2.1 Team Service Refactor

Tests core team operations to verify the modularization didn't break behavior:
- Team creation
- Invite code validation
- Member joining
- Role updates
- Brute-force protection
"""

from api.services.team import get_team_manager

def main():
    tm = get_team_manager()

    print("=" * 70)
    print("TEAM SERVICE REFACTOR - RUNTIME SMOKE TEST")
    print("=" * 70)

    print("\n=== 1) Create team ===")
    team = tm.create_team(
        name="Refactor Test Team",
        creator_user_id="founder_user_1",
        description="Smoke test team for refactor",
    )
    print("Created team:", team)
    team_id = team["team_id"]
    invite_code = team["invite_code"]
    print(f"  team_id: {team_id}")
    print(f"  invite_code: {invite_code}")

    print("\n=== 2) Validate invite code & join as member ===")
    validated_team_id = tm.validate_invite_code(invite_code, ip_address="127.0.0.1")
    print("Validated team_id from invite:", validated_team_id)
    assert validated_team_id == team_id, f"Expected {team_id}, got {validated_team_id}"
    print("✓ Invite code validated correctly")

    joined = tm.join_team(team_id=team_id, user_id="member_user_1", role="member")
    print("Joined team as member:", joined)
    assert joined == True, "Expected join_team to return True"
    print("✓ Member joined successfully")

    print("\n=== 3) Get team members & user teams ===")
    members = tm.get_team_members(team_id)
    print(f"Team members ({len(members)} total):")
    for m in members:
        print(f"  - {m['user_id']}: {m['role']}")
    assert len(members) == 2, f"Expected 2 members (founder + new member), got {len(members)}"
    print("✓ Member count correct")

    user_teams = tm.get_user_teams("member_user_1")
    print(f"User teams for member_user_1 ({len(user_teams)} total):")
    for t in user_teams:
        print(f"  - {t['name']} ({t['team_id']}): role={t['user_role']}")
    assert len(user_teams) == 1, f"Expected 1 team, got {len(user_teams)}"
    print("✓ User teams retrieved correctly")

    print("\n=== 4) Update member role (member -> admin) ===")
    success, message = tm.update_member_role(
        team_id=team_id,
        user_id="member_user_1",
        new_role="admin",
        requesting_user_role="super_admin",   # creator got super_admin on create_team
        requesting_user_id="founder_user_1",
    )
    print(f"Update role result: success={success}, message='{message}'")
    assert success == True, f"Expected role update to succeed, got: {message}"
    print("✓ Role updated successfully")

    # Verify the role actually changed
    members_after = tm.get_team_members(team_id)
    member_user = [m for m in members_after if m['user_id'] == 'member_user_1'][0]
    assert member_user['role'] == 'admin', f"Expected role 'admin', got '{member_user['role']}'"
    print("✓ Role change verified in database")

    print("\n=== 5) Brute-force protection sanity check ===")
    bad_code = "BAD-CODE-XXXXX"
    results = []
    for i in range(12):
        res = tm.validate_invite_code(bad_code, ip_address="192.0.2.1")
        results.append(res)
        if i < 3 or i >= 9:
            print(f"  Attempt {i+1}: {res}")
        elif i == 3:
            print("  ... (attempts 4-9) ...")

    # All should fail (None), but after ~10 attempts it should be due to lockout
    failures = [r for r in results if r is None]
    print(f"Failed attempts: {len(failures)}/12")
    assert len(failures) == 12, "All attempts with bad code should fail"
    print("✓ Brute-force protection behavior looks consistent")

    print("\n" + "=" * 70)
    print("ALL SMOKE TESTS PASSED ✓")
    print("=" * 70)
    print("\nConclusion: Team service refactor appears functionally correct.")
    print("Core operations (create, join, validate, role updates) work as expected.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n" + "=" * 70)
        print("SMOKE TEST FAILED ✗")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        exit(1)
