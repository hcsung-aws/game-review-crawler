"""
게임 프로필 및 프로필 관리자 정의

Requirements: 1.1, 1.4, 1.5
- GameProfile: 게임별 크롤링 설정 및 경로 관리
- GameProfileManager: 게임 프로필 등록, 조회, 경로 관리
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os


@dataclass
class GameProfile:
    """게임 프로필
    
    Requirements: 1.4
    - game_id: 게임 고유 ID (kebab-case)
    - game_name: 게임 표시명
    - keywords: 검색 키워드 목록
    - target_sites: 대상 사이트 목록
    - data_dir: 데이터 저장 디렉토리
    - quicksight_dir: QuickSight 내보내기 디렉토리
    """
    game_id: str
    game_name: str
    keywords: List[str]
    target_sites: List[str]
    data_dir: str = ""
    quicksight_dir: str = ""
    
    def __post_init__(self):
        # game_id 필수 검증
        if not self.game_id or not self.game_id.strip():
            raise ValueError("game_id must not be empty")
        
        # game_name 필수 검증
        if not self.game_name or not self.game_name.strip():
            raise ValueError("game_name must not be empty")
        
        # keywords 필수 검증
        if not self.keywords:
            raise ValueError("keywords must not be empty")
        
        # target_sites 필수 검증
        if not self.target_sites:
            raise ValueError("target_sites must not be empty")
        
        # 기본 경로 설정 (Requirements: 1.1, 1.5, 6.4)
        if not self.data_dir:
            self.data_dir = f"data/{self.game_id}"
        if not self.quicksight_dir:
            self.quicksight_dir = f"quicksight_data/{self.game_id}"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "game_id": self.game_id,
            "game_name": self.game_name,
            "keywords": self.keywords,
            "target_sites": self.target_sites,
            "data_dir": self.data_dir,
            "quicksight_dir": self.quicksight_dir
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GameProfile":
        """딕셔너리에서 객체 생성"""
        return cls(
            game_id=data["game_id"],
            game_name=data["game_name"],
            keywords=data["keywords"],
            target_sites=data["target_sites"],
            data_dir=data.get("data_dir", ""),
            quicksight_dir=data.get("quicksight_dir", "")
        )


class GameProfileManager:
    """게임 프로필 관리자
    
    Requirements: 1.1, 1.5
    - 게임 프로필 등록, 조회, 경로 관리
    """
    
    def __init__(self, base_data_dir: str = "data", base_quicksight_dir: str = "quicksight_data"):
        """
        Args:
            base_data_dir: 기본 데이터 디렉토리
            base_quicksight_dir: 기본 QuickSight 내보내기 디렉토리
        """
        self.profiles: Dict[str, GameProfile] = {}
        self.base_data_dir = base_data_dir
        self.base_quicksight_dir = base_quicksight_dir
    
    def register_game(self, profile: GameProfile) -> None:
        """게임 프로필 등록
        
        Args:
            profile: 등록할 게임 프로필
        """
        self.profiles[profile.game_id] = profile
    
    def get_profile(self, game_id: str) -> Optional[GameProfile]:
        """게임 프로필 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            게임 프로필 또는 None
        """
        return self.profiles.get(game_id)
    
    def get_data_path(self, game_id: str) -> str:
        """게임별 데이터 경로 반환
        
        Requirements: 1.1
        - 게임별로 별도의 데이터 디렉토리에 결과를 저장
        
        Args:
            game_id: 게임 ID
            
        Returns:
            데이터 경로 (형식: data/{game_id}/)
        """
        profile = self.profiles.get(game_id)
        if profile:
            return profile.data_dir
        return f"{self.base_data_dir}/{game_id}"
    
    def get_quicksight_path(self, game_id: str) -> str:
        """게임별 QuickSight 내보내기 경로 반환
        
        Requirements: 1.5, 6.4
        - 게임별로 별도 경로의 데이터 파일 제공
        - quicksight_data/{game_name}/ 형식의 디렉토리 구조
        
        Args:
            game_id: 게임 ID
            
        Returns:
            QuickSight 경로 (형식: quicksight_data/{game_id}/)
        """
        profile = self.profiles.get(game_id)
        if profile:
            return profile.quicksight_dir
        return f"{self.base_quicksight_dir}/{game_id}"
    
    def list_games(self) -> List[GameProfile]:
        """등록된 모든 게임 목록 반환
        
        Returns:
            게임 프로필 목록
        """
        return list(self.profiles.values())
    
    def remove_game(self, game_id: str) -> bool:
        """게임 프로필 제거
        
        Args:
            game_id: 게임 ID
            
        Returns:
            제거 성공 여부
        """
        if game_id in self.profiles:
            del self.profiles[game_id]
            return True
        return False
    
    def ensure_directories(self, game_id: str) -> None:
        """게임별 디렉토리 생성
        
        Args:
            game_id: 게임 ID
        """
        data_path = self.get_data_path(game_id)
        quicksight_path = self.get_quicksight_path(game_id)
        
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(quicksight_path, exist_ok=True)
