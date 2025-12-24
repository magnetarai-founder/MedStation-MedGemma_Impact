"""
Tests for Trust Network Models

Tests the Pydantic models used in the MagnetarTrust decentralized trust network.
"""

import pytest
from pydantic import ValidationError

from api.trust_models import (
    NodeType,
    TrustLevel,
    DisplayMode,
    TrustNode,
    TrustRelationship,
    RegisterNodeRequest,
    VouchRequest,
    TrustNetworkResponse,
    NodeListResponse,
    TrustRelationshipResponse,
)


class TestNodeTypeEnum:
    """Tests for NodeType enum"""

    def test_node_type_values(self):
        """Test all NodeType values exist"""
        assert NodeType.INDIVIDUAL == "individual"
        assert NodeType.CHURCH == "church"
        assert NodeType.MISSION == "mission"
        assert NodeType.FAMILY == "family"
        assert NodeType.ORGANIZATION == "organization"

    def test_node_type_all_values(self):
        """Test all node types are enumerable"""
        values = [e.value for e in NodeType]
        assert len(values) == 5
        assert "individual" in values
        assert "church" in values


class TestTrustLevelEnum:
    """Tests for TrustLevel enum"""

    def test_trust_level_values(self):
        """Test all TrustLevel values exist"""
        assert TrustLevel.DIRECT == "direct"
        assert TrustLevel.VOUCHED == "vouched"
        assert TrustLevel.NETWORK == "network"

    def test_trust_level_all_values(self):
        """Test all trust levels are enumerable"""
        values = [e.value for e in TrustLevel]
        assert len(values) == 3


class TestDisplayModeEnum:
    """Tests for DisplayMode enum"""

    def test_display_mode_values(self):
        """Test all DisplayMode values exist"""
        assert DisplayMode.PEACETIME == "peacetime"
        assert DisplayMode.UNDERGROUND == "underground"

    def test_display_mode_all_values(self):
        """Test all display modes are enumerable"""
        values = [e.value for e in DisplayMode]
        assert len(values) == 2


class TestTrustNode:
    """Tests for TrustNode model"""

    def test_create_basic_node(self):
        """Test creating a basic trust node"""
        node = TrustNode(
            public_key="pk_test123",
            public_name="John Doe",
            type=NodeType.INDIVIDUAL
        )

        assert node.public_key == "pk_test123"
        assert node.public_name == "John Doe"
        assert node.type == NodeType.INDIVIDUAL
        assert node.display_mode == DisplayMode.PEACETIME  # Default

    def test_node_auto_generates_id(self):
        """Test node auto-generates unique ID"""
        node1 = TrustNode(
            public_key="pk_test1",
            public_name="Node 1",
            type=NodeType.INDIVIDUAL
        )
        node2 = TrustNode(
            public_key="pk_test2",
            public_name="Node 2",
            type=NodeType.INDIVIDUAL
        )

        assert node1.id != node2.id
        assert node1.id.startswith("node_")

    def test_node_with_all_fields(self):
        """Test creating node with all optional fields"""
        node = TrustNode(
            public_key="pk_church",
            public_name="First Baptist Church",
            alias="safe_house_alpha",
            type=NodeType.CHURCH,
            display_mode=DisplayMode.UNDERGROUND,
            bio="A welcoming church community",
            location="Springfield",
            is_hub=True,
            vouched_by="node_abc123"
        )

        assert node.alias == "safe_house_alpha"
        assert node.display_mode == DisplayMode.UNDERGROUND
        assert node.is_hub is True
        assert node.vouched_by == "node_abc123"

    def test_node_timestamps_auto_set(self):
        """Test node timestamps are auto-set"""
        node = TrustNode(
            public_key="pk_test",
            public_name="Test",
            type=NodeType.INDIVIDUAL
        )

        assert node.created_at is not None
        assert node.last_seen is not None

    def test_node_requires_public_key(self):
        """Test node requires public_key"""
        with pytest.raises(ValidationError):
            TrustNode(
                public_name="Test",
                type=NodeType.INDIVIDUAL
            )

    def test_node_requires_type(self):
        """Test node requires type"""
        with pytest.raises(ValidationError):
            TrustNode(
                public_key="pk_test",
                public_name="Test"
            )

    def test_node_types(self):
        """Test creating nodes of each type"""
        for node_type in NodeType:
            node = TrustNode(
                public_key=f"pk_{node_type.value}",
                public_name=f"Test {node_type.value}",
                type=node_type
            )
            assert node.type == node_type


class TestTrustRelationship:
    """Tests for TrustRelationship model"""

    def test_create_basic_relationship(self):
        """Test creating a basic trust relationship"""
        rel = TrustRelationship(
            from_node="node_alice",
            to_node="node_bob",
            level=TrustLevel.DIRECT
        )

        assert rel.from_node == "node_alice"
        assert rel.to_node == "node_bob"
        assert rel.level == TrustLevel.DIRECT

    def test_relationship_auto_generates_id(self):
        """Test relationship auto-generates unique ID"""
        rel1 = TrustRelationship(
            from_node="node_a",
            to_node="node_b",
            level=TrustLevel.DIRECT
        )
        rel2 = TrustRelationship(
            from_node="node_c",
            to_node="node_d",
            level=TrustLevel.VOUCHED
        )

        assert rel1.id != rel2.id
        assert rel1.id.startswith("trust_")

    def test_vouched_relationship(self):
        """Test creating a vouched relationship"""
        rel = TrustRelationship(
            from_node="node_alice",
            to_node="node_carol",
            level=TrustLevel.VOUCHED,
            vouched_by="node_bob",
            note="Bob introduced me to Carol"
        )

        assert rel.level == TrustLevel.VOUCHED
        assert rel.vouched_by == "node_bob"
        assert rel.note == "Bob introduced me to Carol"

    def test_mutual_relationship(self):
        """Test mutual trust flag"""
        rel = TrustRelationship(
            from_node="node_a",
            to_node="node_b",
            level=TrustLevel.DIRECT,
            is_mutual=True
        )

        assert rel.is_mutual is True

    def test_relationship_timestamps(self):
        """Test relationship timestamps are set"""
        rel = TrustRelationship(
            from_node="node_a",
            to_node="node_b",
            level=TrustLevel.DIRECT
        )

        assert rel.established is not None
        assert rel.last_verified is not None

    def test_relationship_trust_levels(self):
        """Test all trust levels work"""
        for level in TrustLevel:
            rel = TrustRelationship(
                from_node="node_a",
                to_node="node_b",
                level=level
            )
            assert rel.level == level


class TestRegisterNodeRequest:
    """Tests for RegisterNodeRequest model"""

    def test_basic_registration(self):
        """Test basic node registration request"""
        req = RegisterNodeRequest(
            public_key="pk_new_user",
            public_name="New User",
            type=NodeType.INDIVIDUAL
        )

        assert req.public_key == "pk_new_user"
        assert req.public_name == "New User"
        assert req.type == NodeType.INDIVIDUAL
        assert req.display_mode == DisplayMode.PEACETIME  # Default

    def test_church_registration(self):
        """Test church registration with all fields"""
        req = RegisterNodeRequest(
            public_key="pk_church",
            public_name="Community Church",
            type=NodeType.CHURCH,
            alias="safe_house_1",
            bio="A community of believers",
            location="Downtown",
            display_mode=DisplayMode.UNDERGROUND
        )

        assert req.type == NodeType.CHURCH
        assert req.alias == "safe_house_1"
        assert req.display_mode == DisplayMode.UNDERGROUND

    def test_registration_requires_key_and_name(self):
        """Test registration requires public_key and public_name"""
        with pytest.raises(ValidationError):
            RegisterNodeRequest(type=NodeType.INDIVIDUAL)


class TestVouchRequest:
    """Tests for VouchRequest model"""

    def test_basic_vouch(self):
        """Test basic vouch request"""
        req = VouchRequest(target_node_id="node_carol")

        assert req.target_node_id == "node_carol"
        assert req.level == TrustLevel.VOUCHED  # Default

    def test_vouch_with_note(self):
        """Test vouch request with note"""
        req = VouchRequest(
            target_node_id="node_carol",
            level=TrustLevel.DIRECT,
            note="I've known Carol for 10 years"
        )

        assert req.level == TrustLevel.DIRECT
        assert req.note == "I've known Carol for 10 years"

    def test_vouch_requires_target(self):
        """Test vouch requires target_node_id"""
        with pytest.raises(ValidationError):
            VouchRequest()


class TestTrustNetworkResponse:
    """Tests for TrustNetworkResponse model"""

    def test_empty_network(self):
        """Test response with empty network"""
        resp = TrustNetworkResponse(
            node_id="node_isolated",
            direct_trusts=[],
            vouched_trusts=[],
            network_trusts=[],
            total_network_size=0
        )

        assert resp.node_id == "node_isolated"
        assert len(resp.direct_trusts) == 0
        assert resp.total_network_size == 0

    def test_network_with_trusts(self):
        """Test response with trust relationships"""
        direct_node = TrustNode(
            public_key="pk_direct",
            public_name="Direct Friend",
            type=NodeType.INDIVIDUAL
        )

        resp = TrustNetworkResponse(
            node_id="node_me",
            direct_trusts=[direct_node],
            vouched_trusts=[],
            network_trusts=[],
            total_network_size=1
        )

        assert len(resp.direct_trusts) == 1
        assert resp.direct_trusts[0].public_name == "Direct Friend"


class TestNodeListResponse:
    """Tests for NodeListResponse model"""

    def test_empty_list(self):
        """Test response with empty node list"""
        resp = NodeListResponse(nodes=[], total=0)

        assert len(resp.nodes) == 0
        assert resp.total == 0

    def test_list_with_nodes(self):
        """Test response with nodes"""
        nodes = [
            TrustNode(
                public_key=f"pk_{i}",
                public_name=f"Node {i}",
                type=NodeType.INDIVIDUAL
            )
            for i in range(3)
        ]

        resp = NodeListResponse(nodes=nodes, total=3)

        assert len(resp.nodes) == 3
        assert resp.total == 3


class TestTrustRelationshipResponse:
    """Tests for TrustRelationshipResponse model"""

    def test_empty_relationships(self):
        """Test response with no relationships"""
        resp = TrustRelationshipResponse(relationships=[], total=0)

        assert len(resp.relationships) == 0
        assert resp.total == 0

    def test_with_relationships(self):
        """Test response with relationships"""
        rels = [
            TrustRelationship(
                from_node="node_a",
                to_node=f"node_{i}",
                level=TrustLevel.DIRECT
            )
            for i in range(3)
        ]

        resp = TrustRelationshipResponse(relationships=rels, total=3)

        assert len(resp.relationships) == 3
        assert resp.total == 3
