/**
 * Example TypeScript test file for demonstrating auto-healing capabilities.
 *
 * This file intentionally contains various types of failures that the auto-healer can fix:
 * - Missing imports
 * - Assertion mismatches
 * - Mock configuration issues
 * - Type errors
 */

// MISSING IMPORT - Auto-healer will detect and suggest fix
// import { User } from '../models/User';

interface UserData {
  id: number;
  name: string;
  email: string;
  status: string; // New field added
  createdAt: Date;
}

/**
 * Calculate total of numbers
 * Behavior changed: now adds 1 to the sum
 */
function calculateTotal(items: number[]): number {
  return items.reduce((sum, item) => sum + item, 0) + 1;
}

/**
 * Get user data by ID
 * API changed: now returns status field
 */
function getUserData(userId: number): UserData {
  return {
    id: userId,
    name: 'John Doe',
    email: 'john@example.com',
    status: 'active', // New field
    createdAt: new Date('2024-01-01')
  };
}

/**
 * UserService class
 */
class UserService {
  createUser(name: string, email: string): UserData {
    return {
      id: 123,
      name,
      email,
      status: 'active',
      createdAt: new Date()
    };
  }

  async fetchUserFromAPI(userId: number): Promise<UserData> {
    // Simulated API call
    return getUserData(userId);
  }
}

// Test 1: Assertion mismatch (expected value needs updating)
describe('calculateTotal', () => {
  it('should calculate total of basic numbers', () => {
    const result = calculateTotal([1, 2, 3]);
    expect(result).toBe(6); // Should be 7 after code change
  });

  it('should handle zeros correctly', () => {
    const result = calculateTotal([0, 0, 0]);
    expect(result).toBe(0); // Should be 1 after code change
  });

  it('should handle empty array', () => {
    const result = calculateTotal([]);
    expect(result).toBe(0); // Should be 1 after code change
  });

  it('should handle negative numbers', () => {
    const result = calculateTotal([-1, 1]);
    expect(result).toBe(0); // Should be 1 after code change
  });
});

// Test 2: Object property assertions with API changes
describe('getUserData', () => {
  it('should return user with correct name', () => {
    const user = getUserData(1);
    expect(user.name).toBe('John Doe');
  });

  it('should return user with email', () => {
    const user = getUserData(1);
    expect(user.email).toBe('john@example.com');
  });

  it('should have correct ID type', () => {
    const user = getUserData(1);
    expect(typeof user.id).toBe('number');
    expect(user.id).toBeGreaterThan(0);
  });

  // This test doesn't check for 'status' - will fail if we validate object shape
  it('should return complete user object', () => {
    const user = getUserData(1);
    expect(user).toHaveProperty('id');
    expect(user).toHaveProperty('name');
    expect(user).toHaveProperty('email');
    // Missing: expect(user).toHaveProperty('status');
  });
});

// Test 3: Mock configuration issues
describe('UserService', () => {
  let service: UserService;

  beforeEach(() => {
    service = new UserService();
  });

  it('should create user with correct name', () => {
    const user = service.createUser('Alice', 'alice@example.com');
    expect(user.name).toBe('Alice');
  });

  it('should create user with status', () => {
    const user = service.createUser('Bob', 'bob@example.com');
    expect(user.status).toBe('pending'); // Wrong! Should be 'active'
  });

  it('should set created timestamp', () => {
    const user = service.createUser('Charlie', 'charlie@example.com');
    expect(user.createdAt).toBeInstanceOf(Date);
  });

  // Mock test that needs updating
  it('should fetch user from API', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      id: 1,
      name: 'Mocked User',
      email: 'mock@example.com'
      // Missing 'status' and 'createdAt' fields
    });

    // @ts-ignore - for testing purposes
    service.fetchUserFromAPI = mockFetch;

    const user = await service.fetchUserFromAPI(1);
    expect(user.name).toBe('Mocked User');
  });
});

// Test 4: Type expectations that changed
describe('Type validations', () => {
  it('should return correct types for user data', () => {
    const user = getUserData(1);

    expect(typeof user.id).toBe('number');
    expect(typeof user.name).toBe('string');
    expect(typeof user.email).toBe('string');
    expect(typeof user.createdAt).toBe('string'); // Wrong! It's a Date now
  });

  it('should validate user ID range', () => {
    const user = getUserData(1);
    expect(user.id).toBeGreaterThanOrEqual(1);
    expect(user.id).toBeLessThanOrEqual(1000); // May fail if ID out of range
  });
});

// Test 5: Array operations with wrong expectations
describe('Array operations', () => {
  it('should calculate total for multiple values', () => {
    const values = [10, 20, 30];
    const result = calculateTotal(values);

    expect(result).toBeGreaterThan(0); // Pass
    expect(result).toBe(60); // Fail - should be 61
    expect(result).toBeLessThan(100); // Pass
  });

  it('should handle single value', () => {
    expect(calculateTotal([5])).toBe(5); // Should be 6
  });

  it('should handle large numbers', () => {
    expect(calculateTotal([100, 200, 300])).toBe(600); // Should be 601
  });
});

// Test 6: Parameterized tests with Jest
describe.each([
  [[1, 2, 3], 6],  // Wrong - should be 7
  [[10, 20], 30],  // Wrong - should be 31
  [[100], 100],    // Wrong - should be 101
  [[0], 0],        // Wrong - should be 1
])('calculateTotal with different inputs', (items, expected) => {
  it(`should calculate total of ${items} to equal ${expected}`, () => {
    expect(calculateTotal(items)).toBe(expected);
  });
});

// Test 7: Async tests with timing issues
describe('Async operations', () => {
  it('should create user asynchronously', async () => {
    const service = new UserService();
    const user = await service.fetchUserFromAPI(1);

    expect(user).toBeDefined();
    expect(user.name).toBe('John Doe');
    expect(user.status).toBe('pending'); // Wrong - should be 'active'
  });

  it('should handle errors gracefully', async () => {
    const service = new UserService();

    // Mock a failing API call
    service.fetchUserFromAPI = jest.fn().mockRejectedValue(
      new Error('API Error')
    );

    await expect(service.fetchUserFromAPI(999)).rejects.toThrow('API Error');
  });
});

// Test 8: Snapshot testing (may need updates)
describe('Snapshot tests', () => {
  it('should match user data snapshot', () => {
    const user = getUserData(1);
    expect(user).toMatchSnapshot();
    // Snapshot will fail if user structure changed
  });

  it('should match calculation results', () => {
    const results = {
      basic: calculateTotal([1, 2, 3]),
      empty: calculateTotal([]),
      negative: calculateTotal([-5, 5])
    };
    expect(results).toMatchSnapshot();
  });
});

// Test 9: Edge cases
describe('Edge cases', () => {
  it('should handle very large arrays', () => {
    const largeArray = Array(1000).fill(1);
    const result = calculateTotal(largeArray);
    expect(result).toBe(1000); // Should be 1001
  });

  it('should handle decimal numbers', () => {
    const result = calculateTotal([1.5, 2.5, 3.5]);
    expect(result).toBe(7.5); // Should be 8.5
  });

  it('should handle negative sums', () => {
    const result = calculateTotal([-10, -20, -30]);
    expect(result).toBe(-60); // Should be -59
  });
});

// Test 10: Object matching
describe('Object matching', () => {
  it('should match user object shape', () => {
    const user = getUserData(1);

    expect(user).toEqual({
      id: 1,
      name: 'John Doe',
      email: 'john@example.com',
      createdAt: expect.any(Date)
      // Missing 'status' field
    });
  });

  it('should have all required properties', () => {
    const user = getUserData(1);

    expect(user).toMatchObject({
      id: expect.any(Number),
      name: expect.any(String),
      email: expect.any(String),
      status: 'pending' // Wrong value
    });
  });
});

// Test 11: Tests that should be skipped
describe.skip('Future features', () => {
  it('should implement feature X', () => {
    expect(true).toBe(false);
  });
});

// Test 12: Tests marked as TODO
describe('TODO tests', () => {
  it.todo('should implement user deletion');
  it.todo('should handle concurrent requests');
  it.todo('should cache user data');
});

export { calculateTotal, getUserData, UserService };
