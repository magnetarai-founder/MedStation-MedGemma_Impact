#!/usr/bin/env python3
"""
Vault Seed Data Service
Populates decoy vault with realistic documents for plausible deniability

Security: Decoy vault must look convincing to be effective
"""

import logging
import uuid
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

# Database path
from config_paths import get_config_paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


class DecoyVaultSeeder:
    """
    Seed decoy vault with realistic documents

    Goal: Make decoy vault indistinguishable from real vault
    """

    def __init__(self):
        self.db_path = VAULT_DB_PATH

    def seed_decoy_vault(self, user_id: str) -> Dict[str, Any]:
        """
        Populate decoy vault with realistic documents

        Args:
            user_id: User ID to seed decoy vault for

        Returns:
            Summary of seeded documents
        """
        logger.info(f"🌱 Seeding decoy vault for user {user_id}")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if decoy vault already seeded
        cursor.execute("""
            SELECT COUNT(*) FROM vault_documents
            WHERE user_id = ? AND vault_type = 'decoy'
        """, (user_id,))

        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.info(f"Decoy vault already seeded ({existing_count} documents)")
            conn.close()
            return {
                "status": "already_seeded",
                "document_count": existing_count,
                "message": "Decoy vault already contains documents"
            }

        # Seed decoy documents
        seeded_docs = []

        for doc_data in DECOY_DOCUMENTS:
            doc_id = str(uuid.uuid4())
            created_at = self._generate_realistic_timestamp()

            # Create minimal encrypted metadata (just filename)
            metadata = {
                "filename": doc_data["name"],
                "type": doc_data["type"],
                "size": len(doc_data["content"]),
            }

            # In real implementation, this would be encrypted client-side
            # For seeding, we'll store plaintext and let client encrypt on first access
            encrypted_blob = base64.b64encode(doc_data["content"].encode('utf-8')).decode('utf-8')
            encrypted_metadata = base64.b64encode(str(metadata).encode('utf-8')).decode('utf-8')

            cursor.execute("""
                INSERT INTO vault_documents
                (id, user_id, vault_type, encrypted_blob, encrypted_metadata, created_at, updated_at, size_bytes)
                VALUES (?, ?, 'decoy', ?, ?, ?, ?, ?)
            """, (
                doc_id,
                user_id,
                encrypted_blob,
                encrypted_metadata,
                created_at,
                created_at,
                len(doc_data["content"])
            ))

            seeded_docs.append({
                "id": doc_id,
                "name": doc_data["name"],
                "type": doc_data["type"]
            })

        conn.commit()
        conn.close()

        logger.info(f"✅ Seeded {len(seeded_docs)} decoy documents")

        return {
            "status": "success",
            "document_count": len(seeded_docs),
            "documents": seeded_docs,
            "message": f"Decoy vault seeded with {len(seeded_docs)} realistic documents"
        }

    def _generate_realistic_timestamp(self) -> str:
        """Generate realistic timestamp (random date in past 6 months)"""
        days_ago = uuid.uuid4().int % 180  # 0-180 days ago
        timestamp = datetime.now(UTC) - timedelta(days=days_ago)
        return timestamp.isoformat()

    def clear_decoy_vault(self, user_id: str) -> Dict[str, Any]:
        """
        Clear all decoy vault documents (for testing)

        Args:
            user_id: User ID to clear decoy vault for

        Returns:
            Summary of cleared documents
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM vault_documents
            WHERE user_id = ? AND vault_type = 'decoy'
        """, (user_id,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"🗑️ Cleared {deleted_count} decoy documents for user {user_id}")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Cleared {deleted_count} decoy vault documents"
        }


# Realistic decoy documents
DECOY_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "name": "Personal Budget 2025.txt",
        "type": "text",
        "content": """# Personal Budget 2025

## Monthly Income
- Salary: $4,500
- Freelance: $800
Total: $5,300

## Monthly Expenses
- Rent: $1,400
- Utilities: $180
- Groceries: $450
- Transportation: $220
- Insurance: $200
- Internet: $60
- Phone: $50
- Entertainment: $150
- Savings: $500
- Emergency Fund: $300
Total: $3,510

## Savings Goals
- Emergency Fund: $10,000 (current: $6,200)
- Vacation Fund: $3,000 (current: $1,400)
- New Laptop: $2,000 (current: $800)

Notes:
- Increase savings by 10% if freelance work picks up
- Review insurance rates in March
- Consider reducing entertainment budget
"""
    },

    {
        "name": "WiFi Passwords.txt",
        "type": "text",
        "content": """# WiFi Network Passwords

## Home Network
Network: HomeNetwork-5G
Password: SecureHome2024!

## Office
Network: CompanyGuest
Password: GuestWiFi123

## Parents' House
Network: Mom&DadWiFi
Password: FamilyNetwork2023

## Coffee Shop (Saved)
Network: BrewCoffee-Guest
Password: coffee2024

## Gym
Network: FitnessClub-Members
Password: StayHealthy!
"""
    },

    {
        "name": "Shopping List.txt",
        "type": "text",
        "content": """# Weekly Shopping List

## Groceries
- [ ] Milk (2 gallons)
- [ ] Bread
- [ ] Eggs (dozen)
- [ ] Chicken breast
- [ ] Broccoli
- [ ] Carrots
- [ ] Apples
- [ ] Bananas
- [ ] Pasta
- [ ] Tomato sauce
- [ ] Coffee
- [ ] Greek yogurt

## Household
- [ ] Paper towels
- [ ] Laundry detergent
- [ ] Dish soap
- [ ] Trash bags
- [ ] Light bulbs

## Pharmacy
- [ ] Toothpaste
- [ ] Vitamins
- [ ] Allergy medication

Total Budget: ~$120
"""
    },

    {
        "name": "Travel Plans - Summer.txt",
        "type": "text",
        "content": """# Summer Vacation Plans 2025

## Destination: Pacific Northwest

### Dates
June 15-25 (10 days)

### Itinerary
**Seattle (3 days)**
- Pike Place Market
- Space Needle
- Museum of Pop Culture
- Ferry to Bainbridge Island

**Portland (2 days)**
- Powell's Books
- Food trucks
- Japanese Gardens
- Columbia River Gorge day trip

**Crater Lake (2 days)**
- Camping at Rim Village
- Hike around rim
- Boat tour

**Oregon Coast (3 days)**
- Cannon Beach
- Haystack Rock
- Seaside
- Astoria

### Budget
- Flights: $450
- Rental car: $400
- Hotels/camping: $800
- Food: $500
- Activities: $250
Total: ~$2,400

### Packing List
- Hiking boots
- Rain jacket
- Camera
- Camping gear
- Sunscreen
"""
    },

    {
        "name": "Book Recommendations.txt",
        "type": "text",
        "content": """# Books to Read

## Currently Reading
- "The Midnight Library" by Matt Haig
  Progress: 45%
  Rating so far: 4/5

## To Read
**Fiction**
- "Project Hail Mary" by Andy Weir
- "The Seven Husbands of Evelyn Hugo" by Taylor Jenkins Reid
- "Circe" by Madeline Miller

**Non-Fiction**
- "Atomic Habits" by James Clear
- "The Body Keeps the Score" by Bessel van der Kolk
- "Sapiens" by Yuval Noah Harari

**Classics**
- "1984" by George Orwell (re-read)
- "To Kill a Mockingbird" by Harper Lee

## Finished (2025)
✓ "Where the Crawdads Sing" - 5/5
✓ "Educated" - 4/5
✓ "The Silent Patient" - 3.5/5

Notes:
- Join book club meeting 2nd Tuesday of month
- Library card expires in June - renew
"""
    },

    {
        "name": "Recipe - Mom's Lasagna.txt",
        "type": "text",
        "content": """# Mom's Famous Lasagna

Serves: 8-10
Prep time: 30 min
Cook time: 1 hour

## Ingredients

**Meat Sauce:**
- 1 lb ground beef
- 1 lb Italian sausage
- 1 onion, diced
- 4 cloves garlic, minced
- 2 cans (28 oz) crushed tomatoes
- 1 can (6 oz) tomato paste
- 2 tsp dried basil
- 1 tsp fennel seeds
- Salt and pepper to taste

**Cheese Layer:**
- 15 oz ricotta cheese
- 1 egg
- 1/2 cup parmesan, grated
- 1/4 cup fresh parsley
- 3 cups mozzarella, shredded

**Other:**
- 12 lasagna noodles
- Olive oil

## Instructions

1. Cook noodles according to package, drain
2. Brown meat with onions and garlic
3. Add tomatoes, paste, and spices. Simmer 30 min
4. Mix ricotta, egg, parmesan, and parsley
5. Layer in 9x13 pan:
   - Sauce
   - Noodles
   - Ricotta mixture
   - Mozzarella
   - Repeat
6. Top with remaining mozzarella
7. Bake at 375°F for 45 min, covered
8. Uncover, bake 15 min more until bubbly
9. Let rest 15 min before serving

**Mom's tip:** Make day ahead for better flavor!
"""
    },

    {
        "name": "Workout Routine.txt",
        "type": "text",
        "content": """# Weekly Workout Plan

## Monday - Chest & Triceps
- Bench press: 4x8
- Incline dumbbell press: 3x10
- Cable flyes: 3x12
- Tricep dips: 3x12
- Tricep pushdowns: 3x15

## Tuesday - Cardio
- 30 min treadmill (interval training)
- 15 min rowing machine

## Wednesday - Back & Biceps
- Deadlifts: 4x6
- Pull-ups: 3x8
- Barbell rows: 3x10
- Lat pulldowns: 3x12
- Bicep curls: 3x12
- Hammer curls: 3x12

## Thursday - Rest or Yoga

## Friday - Legs
- Squats: 4x8
- Leg press: 3x10
- Lunges: 3x12 each leg
- Leg curls: 3x12
- Calf raises: 3x15

## Saturday - Shoulders & Abs
- Military press: 4x8
- Lateral raises: 3x12
- Front raises: 3x12
- Planks: 3x60sec
- Russian twists: 3x20
- Leg raises: 3x15

## Sunday - Rest

**Notes:**
- Warm up 10 min before each session
- Stretch after workout
- Track weight progression
- Current weight: 175 lbs
- Goal weight: 185 lbs
"""
    },

    {
        "name": "Car Maintenance Log.txt",
        "type": "text",
        "content": """# 2019 Honda Civic - Maintenance Log

## Vehicle Info
VIN: 1HGBH41JXMN109186
License: ABC-1234
Purchase Date: March 2021
Current Mileage: 45,230 miles

## Maintenance History

### Oil Changes
- 3/15/2025 @ 45,000 mi - Jiffy Lube ($45)
- 12/10/2024 @ 42,000 mi - Honda Dealer ($65)
- 9/5/2024 @ 39,000 mi - Jiffy Lube ($45)

### Tire Rotation
- 1/20/2025 @ 44,000 mi - Costco (Free)
- 7/15/2024 @ 38,000 mi - Costco (Free)

### Other Service
- 2/1/2025 - Air filter replacement ($30)
- 10/12/2024 - Battery replacement ($140) - Interstate
- 6/20/2024 - Brake pads front ($220)

## Upcoming Maintenance
- [ ] Oil change due @ 48,000 mi (June 2025)
- [ ] Tire rotation @ 50,000 mi
- [ ] Transmission fluid @ 60,000 mi

## Insurance
Provider: State Farm
Policy #: 1234-5678-90
Renewal: August 2025
Monthly: $120

## Notes
- Check tire pressure monthly
- Windshield has small chip (driver side) - monitor for spreading
- New tires needed around 60,000 miles
"""
    },

    {
        "name": "Meeting Notes - Q1 Review.txt",
        "type": "text",
        "content": """# Q1 2025 Team Meeting Notes

Date: March 28, 2025
Attendees: Sarah, Mike, Jennifer, Tom, Me

## Key Points

### Q1 Performance
- Revenue: $420K (target was $400K) ✓
- Customer acquisition: 45 new clients (target 40) ✓
- Customer retention: 94% (target 95%) ⚠
- Project completion: 92% on-time (target 90%) ✓

### Wins
- Launched new product line successfully
- Secured 3-year contract with MegaCorp
- Team morale survey: 8.2/10 (up from 7.8)
- Zero critical security incidents

### Challenges
- Lost 2 major clients to competitor
- Hiring delays (3 positions open >60 days)
- Office space getting cramped
- IT infrastructure needs upgrade

### Q2 Goals
1. Increase retention to 96%
2. Fill all open positions
3. Launch marketing campaign
4. Upgrade to new CRM system
5. Plan team building event

## Action Items
- [ ] Me: Research CRM options by April 15
- [ ] Sarah: Schedule interviews for open roles
- [ ] Mike: Draft marketing campaign proposal
- [ ] Jennifer: Get quotes for office expansion
- [ ] Tom: Plan team building event (June)

## Next Meeting
April 25, 2025 @ 10:00 AM
"""
    },

    {
        "name": "Password Reset Links.txt",
        "type": "text",
        "content": """# Common Password Reset Links

## Banking
- Chase: https://www.chase.com/forgot-password
- Bank of America: https://www.bankofamerica.com/reset
- Capital One: https://www.capitalone.com/password-reset

## Email
- Gmail: https://accounts.google.com/signin/recovery
- Outlook: https://account.live.com/password/reset

## Shopping
- Amazon: https://www.amazon.com/ap/forgotpassword
- eBay: https://signin.ebay.com/ws/eBayISAPI.dll?ForgotPassword

## Utilities
- Electric company: https://myaccount.powercompany.com/forgot
- Water: https://www.waterutility.com/reset-password

## Streaming
- Netflix: https://www.netflix.com/password
- Spotify: https://accounts.spotify.com/en/password-reset
- HBO Max: https://www.hbomax.com/password-reset

## Social Media
- Facebook: https://www.facebook.com/login/identify
- Twitter: https://twitter.com/i/flow/password_reset
- LinkedIn: https://www.linkedin.com/checkpoint/rp/request-password-reset

**Note:** Always verify URL before entering credentials!
Bookmark this page for easy access.
"""
    }
]


def get_seeder() -> DecoyVaultSeeder:
    """Get global seeder instance"""
    return DecoyVaultSeeder()


if __name__ == "__main__":
    # Test seeding
    seeder = DecoyVaultSeeder()
    result = seeder.seed_decoy_vault("test_user_123")
    print(result)
