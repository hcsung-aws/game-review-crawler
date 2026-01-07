"""
Property-Based Tests for Game Profile

**Feature: game-analytics-dashboard, Property 1: Game Data Path Consistency**
**Validates: Requirements 1.1, 1.5, 6.4**

For any 게임 ID에 대해, 데이터 저장 경로는 `data/{game_id}/` 형식이어야 하고,
QuickSight 내보내기 경로는 `quicksight_data/{game_id}/` 형식이어야 한다.

**Feature: game-analytics-dashboard, Property 3: GameProfile Required Fields**
**Validates: Requirements 1.4**

For any GameProfile 객체는 game_id, game_name, keywords, target_sites 필드를 
반드시 포함해야 하며, game_id는 비어있지 않아야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from crawler.models.game_profile import GameProfile, GameProfileManager


# Custom strategies for generating test data
@st.composite
def game_id_strategy(draw):
    """유효한 game_id 생성 전략 (kebab-case)"""
    # kebab-case 형식의 game_id 생성
    parts = draw(st.lists(
        st.text(
            alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789'),
            min_size=1,
            max_size=10
        ),
        min_size=1,
        max_size=3
    ))
    return '-'.join(parts)


@st.composite
def game_profile_strategy(draw):
    """유효한 GameProfile 객체 생성 전략"""
    game_id = draw(game_id_strategy())
    game_name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    keywords = draw(st.lists(
        st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        min_size=1,
        max_size=5
    ))
    target_sites = draw(st.lists(
        st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        min_size=1,
        max_size=5
    ))
    
    return GameProfile(
        game_id=game_id,
        game_name=game_name,
        keywords=keywords,
        target_sites=target_sites
    )


class TestGameDataPathConsistency:
    """
    **Feature: game-analytics-dashboard, Property 1: Game Data Path Consistency**
    **Validates: Requirements 1.1, 1.5, 6.4**
    
    For any 게임 ID에 대해, 데이터 저장 경로는 `data/{game_id}/` 형식이어야 하고,
    QuickSight 내보내기 경로는 `quicksight_data/{game_id}/` 형식이어야 한다.
    """
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_data_path_format(self, profile: GameProfile):
        """데이터 경로가 data/{game_id} 형식인지 검증"""
        expected_data_path = f"data/{profile.game_id}"
        assert profile.data_dir == expected_data_path, \
            f"Expected data_dir to be '{expected_data_path}', got '{profile.data_dir}'"
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_quicksight_path_format(self, profile: GameProfile):
        """QuickSight 경로가 quicksight_data/{game_id} 형식인지 검증"""
        expected_quicksight_path = f"quicksight_data/{profile.game_id}"
        assert profile.quicksight_dir == expected_quicksight_path, \
            f"Expected quicksight_dir to be '{expected_quicksight_path}', got '{profile.quicksight_dir}'"
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_manager_data_path_consistency(self, profile: GameProfile):
        """GameProfileManager를 통한 데이터 경로 일관성 검증"""
        manager = GameProfileManager()
        manager.register_game(profile)
        
        data_path = manager.get_data_path(profile.game_id)
        expected_path = f"data/{profile.game_id}"
        
        assert data_path == expected_path, \
            f"Expected data path '{expected_path}', got '{data_path}'"
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_manager_quicksight_path_consistency(self, profile: GameProfile):
        """GameProfileManager를 통한 QuickSight 경로 일관성 검증"""
        manager = GameProfileManager()
        manager.register_game(profile)
        
        quicksight_path = manager.get_quicksight_path(profile.game_id)
        expected_path = f"quicksight_data/{profile.game_id}"
        
        assert quicksight_path == expected_path, \
            f"Expected quicksight path '{expected_path}', got '{quicksight_path}'"
    
    @given(game_id=game_id_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_unregistered_game_path_format(self, game_id: str):
        """등록되지 않은 게임에 대한 경로도 일관된 형식 유지"""
        manager = GameProfileManager()
        
        data_path = manager.get_data_path(game_id)
        quicksight_path = manager.get_quicksight_path(game_id)
        
        assert data_path == f"data/{game_id}", \
            f"Expected data path 'data/{game_id}', got '{data_path}'"
        assert quicksight_path == f"quicksight_data/{game_id}", \
            f"Expected quicksight path 'quicksight_data/{game_id}', got '{quicksight_path}'"



class TestGameProfileRequiredFields:
    """
    **Feature: game-analytics-dashboard, Property 3: GameProfile Required Fields**
    **Validates: Requirements 1.4**
    
    For any GameProfile 객체는 game_id, game_name, keywords, target_sites 필드를 
    반드시 포함해야 하며, game_id는 비어있지 않아야 한다.
    """
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_required_fields_present(self, profile: GameProfile):
        """필수 필드가 모두 존재하는지 검증"""
        # game_id 필수
        assert hasattr(profile, 'game_id'), "game_id field must exist"
        assert profile.game_id is not None, "game_id must not be None"
        assert profile.game_id.strip(), "game_id must not be empty"
        
        # game_name 필수
        assert hasattr(profile, 'game_name'), "game_name field must exist"
        assert profile.game_name is not None, "game_name must not be None"
        assert profile.game_name.strip(), "game_name must not be empty"
        
        # keywords 필수
        assert hasattr(profile, 'keywords'), "keywords field must exist"
        assert profile.keywords is not None, "keywords must not be None"
        assert len(profile.keywords) > 0, "keywords must not be empty"
        
        # target_sites 필수
        assert hasattr(profile, 'target_sites'), "target_sites field must exist"
        assert profile.target_sites is not None, "target_sites must not be None"
        assert len(profile.target_sites) > 0, "target_sites must not be empty"
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_to_dict_contains_required_fields(self, profile: GameProfile):
        """to_dict() 결과에 필수 필드가 포함되는지 검증"""
        profile_dict = profile.to_dict()
        
        required_fields = ['game_id', 'game_name', 'keywords', 'target_sites']
        for field in required_fields:
            assert field in profile_dict, f"to_dict() must contain '{field}'"
    
    @given(profile=game_profile_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_round_trip_preserves_required_fields(self, profile: GameProfile):
        """직렬화/역직렬화 후에도 필수 필드가 유지되는지 검증"""
        profile_dict = profile.to_dict()
        restored = GameProfile.from_dict(profile_dict)
        
        assert restored.game_id == profile.game_id
        assert restored.game_name == profile.game_name
        assert restored.keywords == profile.keywords
        assert restored.target_sites == profile.target_sites
    
    def test_empty_game_id_raises_error(self):
        """빈 game_id로 생성 시 에러 발생 검증"""
        with pytest.raises(ValueError, match="game_id must not be empty"):
            GameProfile(
                game_id="",
                game_name="Test Game",
                keywords=["test"],
                target_sites=["site1"]
            )
    
    def test_whitespace_game_id_raises_error(self):
        """공백만 있는 game_id로 생성 시 에러 발생 검증"""
        with pytest.raises(ValueError, match="game_id must not be empty"):
            GameProfile(
                game_id="   ",
                game_name="Test Game",
                keywords=["test"],
                target_sites=["site1"]
            )
    
    def test_empty_game_name_raises_error(self):
        """빈 game_name으로 생성 시 에러 발생 검증"""
        with pytest.raises(ValueError, match="game_name must not be empty"):
            GameProfile(
                game_id="test-game",
                game_name="",
                keywords=["test"],
                target_sites=["site1"]
            )
    
    def test_empty_keywords_raises_error(self):
        """빈 keywords로 생성 시 에러 발생 검증"""
        with pytest.raises(ValueError, match="keywords must not be empty"):
            GameProfile(
                game_id="test-game",
                game_name="Test Game",
                keywords=[],
                target_sites=["site1"]
            )
    
    def test_empty_target_sites_raises_error(self):
        """빈 target_sites로 생성 시 에러 발생 검증"""
        with pytest.raises(ValueError, match="target_sites must not be empty"):
            GameProfile(
                game_id="test-game",
                game_name="Test Game",
                keywords=["test"],
                target_sites=[]
            )
