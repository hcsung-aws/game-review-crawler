"""
AnalysisDataStore 클래스 구현

Requirements: 1.1, 6.1
- 분석 결과 저장 및 로드
- 게임별 최신 분석 결과 조회
"""

import os
import json
import glob
from datetime import datetime
from typing import Optional, List, Dict

from crawler.models.analysis_models import GameAnalysisResult


class AnalysisDataStore:
    """분석 결과 저장소 클래스
    
    게임별 분석 결과를 저장하고 관리한다.
    
    Requirements: 1.1, 6.1
    - 분석 결과 저장 및 로드
    - 게임별 최신 분석 결과 조회
    """
    
    def __init__(self, base_dir: str = "analysis_data"):
        """AnalysisDataStore 초기화
        
        Args:
            base_dir: 분석 데이터 저장 기본 디렉토리
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
    
    def _get_game_dir(self, game_id: str) -> str:
        """게임별 디렉토리 경로 반환
        
        Args:
            game_id: 게임 ID
            
        Returns:
            게임별 디렉토리 경로
        """
        return os.path.join(self.base_dir, game_id)
    
    def _get_analysis_filename(self, analyzed_at: datetime) -> str:
        """분석 결과 파일명 생성
        
        Args:
            analyzed_at: 분석 시간
            
        Returns:
            파일명 (analysis_YYYYMMDD_HHMMSS.json)
        """
        timestamp = analyzed_at.strftime("%Y%m%d_%H%M%S")
        return f"analysis_{timestamp}.json"
    
    def save_analysis(self, game_id: str, result: GameAnalysisResult) -> str:
        """분석 결과 저장
        
        Requirements: 1.1, 6.1
        - 게임별로 별도의 데이터 디렉토리에 결과를 저장
        
        Args:
            game_id: 게임 ID
            result: 저장할 분석 결과
            
        Returns:
            저장된 파일 경로
        """
        # 게임별 디렉토리 생성
        game_dir = self._get_game_dir(game_id)
        os.makedirs(game_dir, exist_ok=True)
        
        # 파일명 생성 및 저장
        filename = self._get_analysis_filename(result.analyzed_at)
        filepath = os.path.join(game_dir, filename)
        
        data = result.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def load_analysis(self, filepath: str) -> Optional[GameAnalysisResult]:
        """분석 결과 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            로드된 분석 결과. 파일이 없으면 None
        """
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GameAnalysisResult.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def get_latest_analysis(self, game_id: str) -> Optional[GameAnalysisResult]:
        """최신 분석 결과 조회
        
        Requirements: 1.1
        - 게임별 최신 분석 결과 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            최신 분석 결과. 없으면 None
        """
        game_dir = self._get_game_dir(game_id)
        
        if not os.path.exists(game_dir):
            return None
        
        # 분석 파일 목록 조회 (analysis_*.json 패턴)
        pattern = os.path.join(game_dir, "analysis_*.json")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        # 파일명 기준 정렬 (최신 파일이 마지막)
        files.sort()
        latest_file = files[-1]
        
        return self.load_analysis(latest_file)
    
    def list_analyses(self, game_id: str) -> List[str]:
        """게임별 분석 결과 파일 목록 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            분석 결과 파일 경로 목록 (시간순 정렬)
        """
        game_dir = self._get_game_dir(game_id)
        
        if not os.path.exists(game_dir):
            return []
        
        pattern = os.path.join(game_dir, "analysis_*.json")
        files = glob.glob(pattern)
        files.sort()
        
        return files
    
    def get_all_game_ids(self) -> List[str]:
        """저장된 모든 게임 ID 목록 조회
        
        Returns:
            게임 ID 목록
        """
        if not os.path.exists(self.base_dir):
            return []
        
        game_ids = []
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path):
                # 해당 디렉토리에 분석 파일이 있는지 확인
                pattern = os.path.join(item_path, "analysis_*.json")
                if glob.glob(pattern):
                    game_ids.append(item)
        
        return sorted(game_ids)
    
    def delete_analysis(self, filepath: str) -> bool:
        """분석 결과 파일 삭제
        
        Args:
            filepath: 삭제할 파일 경로
            
        Returns:
            삭제 성공 여부
        """
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def delete_game_analyses(self, game_id: str) -> int:
        """게임의 모든 분석 결과 삭제
        
        Args:
            game_id: 게임 ID
            
        Returns:
            삭제된 파일 수
        """
        files = self.list_analyses(game_id)
        deleted_count = 0
        
        for filepath in files:
            if self.delete_analysis(filepath):
                deleted_count += 1
        
        # 빈 디렉토리 삭제
        game_dir = self._get_game_dir(game_id)
        if os.path.exists(game_dir) and not os.listdir(game_dir):
            os.rmdir(game_dir)
        
        return deleted_count
    
    def get_analysis_summary(self, game_id: str) -> Optional[Dict]:
        """게임별 분석 요약 정보 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            분석 요약 정보 딕셔너리. 없으면 None
        """
        latest = self.get_latest_analysis(game_id)
        if not latest:
            return None
        
        files = self.list_analyses(game_id)
        
        return {
            "game_id": game_id,
            "total_analyses": len(files),
            "latest_analyzed_at": latest.analyzed_at.isoformat(),
            "total_posts": latest.total_posts,
            "total_comments": latest.total_comments,
            "sentiment_avg": latest.sentiment_avg,
            "issue_count": len(latest.issues),
            "hot_issue_count": len(latest.hot_issues),
            "bug_issue_count": len(latest.bug_issues)
        }
