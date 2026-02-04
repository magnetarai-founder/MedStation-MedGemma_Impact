#!/usr/bin/env python3
"""
Test suite for multi-language analyzers.

Demonstrates usage and validates functionality across all supported languages.
"""

from pathlib import Path
from .analyzers import (
    Language,
    TypeScriptAnalyzer,
    GoAnalyzer,
    RustAnalyzer,
    JavaAnalyzer,
    UnifiedAnalyzer,
    detect_language,
    detect_language_from_content,
    get_unified_analyzer,
)


def test_typescript_analyzer():
    """Test TypeScript analyzer."""
    print("\n=== Testing TypeScript Analyzer ===")

    ts_code = """
    import { Component } from 'react';
    import type { User } from './types';

    /**
     * User profile component
     */
    export interface UserProps {
        name: string;
        age: number;
    }

    export class UserProfile extends Component<UserProps> {
        async fetchUser(id: string): Promise<User> {
            const response = await fetch(`/api/users/${id}`);
            return response.json();
        }

        render() {
            return <div>{this.props.name}</div>;
        }
    }

    export async function getUserById(id: string): Promise<User> {
        const user = await fetchUser(id);
        return user;
    }

    const greet = (name: string): string => {
        return `Hello, ${name}`;
    };
    """

    analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)
    entities = analyzer.extract_entities(ts_code, "UserProfile.tsx")
    dependencies = analyzer.find_dependencies(ts_code, "UserProfile.tsx")

    print(f"Found {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.entity_type}: {entity.name} @ line {entity.line_number}")
        if entity.extends:
            print(f"    extends: {entity.extends}")
        if entity.methods:
            print(f"    methods: {entity.methods}")

    print(f"\nFound {len(dependencies)} dependencies:")
    for dep in dependencies:
        print(f"  - {dep.module} (symbols: {dep.symbols})")


def test_go_analyzer():
    """Test Go analyzer."""
    print("\n=== Testing Go Analyzer ===")

    go_code = """
    package main

    import (
        "fmt"
        "github.com/gin-gonic/gin"
    )

    // User represents a user in the system
    type User struct {
        ID       int
        Name     string
        Email    string
        IsActive bool
    }

    // UserService handles user operations
    type UserService interface {
        GetUser(id int) (*User, error)
        CreateUser(user *User) error
        DeleteUser(id int) error
    }

    // GetUserByID retrieves a user by ID
    func (u *User) GetUserByID(id int) (*User, error) {
        user := &User{ID: id}
        err := fetchUserFromDB(user)
        return user, err
    }

    func main() {
        router := gin.Default()
        router.Run(":8080")
    }
    """

    analyzer = GoAnalyzer()
    entities = analyzer.extract_entities(go_code, "main.go")
    dependencies = analyzer.find_dependencies(go_code, "main.go")
    call_graph = analyzer.get_call_graph(go_code, "main.go")

    print(f"Found {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.entity_type}: {entity.name} @ line {entity.line_number}")
        if entity.attributes:
            print(f"    fields: {entity.attributes}")
        if entity.methods:
            print(f"    methods: {entity.methods}")

    print(f"\nFound {len(dependencies)} dependencies:")
    for dep in dependencies:
        print(f"  - {dep.module}")

    print(f"\nCall graph ({len(call_graph)} functions):")
    for func_name, node in call_graph.items():
        if node.calls:
            print(f"  - {func_name} calls: {node.calls}")


def test_rust_analyzer():
    """Test Rust analyzer."""
    print("\n=== Testing Rust Analyzer ===")

    rust_code = """
    use std::collections::HashMap;
    use serde::{Serialize, Deserialize};

    /// User data structure
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct User {
        pub id: u64,
        pub name: String,
        email: String,
    }

    /// Database trait for user operations
    pub trait UserRepository {
        fn find_user(&self, id: u64) -> Option<User>;
        fn save_user(&mut self, user: User) -> Result<(), String>;
    }

    impl User {
        pub fn new(id: u64, name: String, email: String) -> Self {
            Self { id, name, email }
        }

        pub async fn fetch_from_api(&self) -> Result<User, reqwest::Error> {
            let url = format!("https://api.example.com/users/{}", self.id);
            let response = reqwest::get(&url).await?;
            response.json().await
        }
    }

    pub fn create_user(name: &str, email: &str) -> User {
        User::new(0, name.to_string(), email.to_string())
    }
    """

    analyzer = RustAnalyzer()
    entities = analyzer.extract_entities(rust_code, "user.rs")
    dependencies = analyzer.find_dependencies(rust_code, "user.rs")

    print(f"Found {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.entity_type}: {entity.name} @ line {entity.line_number}")
        if entity.decorators:
            print(f"    attributes: {entity.decorators}")
        if entity.methods:
            print(f"    methods: {entity.methods}")
        if entity.implements:
            print(f"    implements: {entity.implements}")

    print(f"\nFound {len(dependencies)} dependencies:")
    for dep in dependencies:
        symbols = f" ({dep.symbols})" if dep.symbols else ""
        print(f"  - {dep.module}{symbols}")


def test_java_analyzer():
    """Test Java analyzer."""
    print("\n=== Testing Java Analyzer ===")

    java_code = """
    package com.example.users;

    import java.util.List;
    import java.util.Optional;
    import javax.persistence.*;

    /**
     * User entity class
     */
    @Entity
    @Table(name = "users")
    public class User {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;

        private String name;
        private String email;

        public User() {}

        public User(String name, String email) {
            this.name = name;
            this.email = email;
        }

        public Long getId() {
            return id;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }
    }

    @Repository
    public interface UserRepository extends JpaRepository<User, Long> {
        Optional<User> findByEmail(String email);
        List<User> findByNameContaining(String name);
    }

    @Service
    public class UserService {
        private final UserRepository repository;

        public UserService(UserRepository repository) {
            this.repository = repository;
        }

        public User createUser(String name, String email) {
            User user = new User(name, email);
            return repository.save(user);
        }
    }
    """

    analyzer = JavaAnalyzer()
    entities = analyzer.extract_entities(java_code, "User.java")
    dependencies = analyzer.find_dependencies(java_code, "User.java")

    print(f"Found {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.entity_type}: {entity.name} @ line {entity.line_number}")
        if entity.annotations:
            print(f"    annotations: {entity.annotations}")
        if entity.methods:
            print(f"    methods: {entity.methods}")
        if entity.extends:
            print(f"    extends: {entity.extends}")

    print(f"\nFound {len(dependencies)} dependencies:")
    for dep in dependencies:
        print(f"  - {dep.module}")


def test_language_detection():
    """Test language detection."""
    print("\n=== Testing Language Detection ===")

    test_cases = [
        ("file.ts", Language.TYPESCRIPT),
        ("file.tsx", Language.TSX),
        ("file.js", Language.JAVASCRIPT),
        ("file.go", Language.GO),
        ("file.rs", Language.RUST),
        ("file.java", Language.JAVA),
        ("file.py", Language.PYTHON),
    ]

    for filename, expected in test_cases:
        detected = Language.from_extension(Path(filename).suffix)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {filename} -> {detected.value} (expected: {expected.value})")

    print("\nContent-based detection:")

    content_tests = [
        ("package main\n\nfunc main() {}", Language.GO),
        ("use std::io;\n\nfn main() {}", Language.RUST),
        ("interface User {\n  name: string;\n}", Language.TYPESCRIPT),
        ("def hello():\n    pass", Language.PYTHON),
    ]

    for content, expected in content_tests:
        detected = detect_language_from_content(content)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} {expected.value}: {detected.value}")


def test_unified_analyzer():
    """Test unified analyzer."""
    print("\n=== Testing Unified Analyzer ===")

    unified = get_unified_analyzer()

    # Create temporary test files
    test_files = {
        "test.ts": """
        export class Calculator {
            add(a: number, b: number): number {
                return a + b;
            }
        }
        """,
        "test.go": """
        package main

        type Calculator struct {}

        func (c *Calculator) Add(a, b int) int {
            return a + b
        }
        """,
    }

    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        for filename, content in test_files.items():
            file_path = Path(tmpdir) / filename
            file_path.write_text(content)

            result = unified.parse_file(file_path)
            print(f"\n{filename} ({result.language.value}):")
            print(f"  Entities: {len(result.entities)}")
            for entity in result.entities:
                print(f"    - {entity.entity_type}: {entity.name}")

            if result.errors:
                print(f"  Errors: {result.errors}")


def test_cross_language_features():
    """Test cross-language features."""
    print("\n=== Testing Cross-Language Features ===")

    # Test CodeEntity uniformity
    from .analyzers import CodeEntity

    entities = [
        CodeEntity(
            name="User",
            entity_type="class",
            language=Language.TYPESCRIPT,
            file_path="user.ts",
            line_number=10,
            methods=["getName", "setName"],
        ),
        CodeEntity(
            name="User",
            entity_type="struct",
            language=Language.GO,
            file_path="user.go",
            line_number=5,
            attributes=["Name", "Email"],
        ),
        CodeEntity(
            name="User",
            entity_type="struct",
            language=Language.RUST,
            file_path="user.rs",
            line_number=8,
            decorators=["#[derive(Debug)]"],
        ),
    ]

    print("Unified CodeEntity format across languages:")
    for entity in entities:
        data = entity.to_dict()
        print(f"\n  {data['language']} - {data['type']} {data['name']}:")
        print(f"    file: {data['file']}:{data['line']}")
        if data.get("methods"):
            print(f"    methods: {data['methods']}")
        if data.get("attributes"):
            print(f"    attributes: {data['attributes']}")
        if data.get("decorators"):
            print(f"    decorators: {data['decorators']}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Multi-Language Code Analyzer Test Suite")
    print("=" * 70)

    try:
        test_typescript_analyzer()
        test_go_analyzer()
        test_rust_analyzer()
        test_java_analyzer()
        test_language_detection()
        test_unified_analyzer()
        test_cross_language_features()

        print("\n" + "=" * 70)
        print("✓ All tests completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
