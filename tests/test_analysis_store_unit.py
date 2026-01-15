"""
Unit Tests for AnalysisDataStore

Requirements: 1.1
- 분석 결과 저장 및 로드
- 저장 후 로드 시 동일한 데이터 반환 검증
"""

import pytest
import os
import shutil
import tempfile
from datetime import datetime

from crawler.exporters.analysis_store import AnalysisDataStore
from crawler.models.analysis_models import (
    GameAnalysisResult,
    DetectedIssue,
    KeywordCluster,
    TrendData,
    TrendPoint,
    SentimentLabel,
    IssueSeverity
)


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성 및 정리"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def analysis_store(temp_dir):
    """AnalysisDataStore 인스턴스 생성"""
    return AnalysisDataStore(base_dir=temp_dir)


@pytest.fixture
def sample_analysis_result():
    """샘플 분석 결과 생성"""
    cluster = KeywordCluster(
        cluster_id="cluster-001",
        keywords=["버그", "오류", "에러"],
        representative="버그",
        post_count=10,
        total_views=5000,
        total_comments=150
    )
    
    issue = DetectedIssue(
        issue_id="issue-001",
        title="버그 관련 이슈",
        cluster=cluster,
        priority_score=0.85,
        is_hot=True,
        is_bug=True,
        severity=IssueSeverity.HIGH,
        related_posts=["https://example.com/post/1", "https://example.com/post/2"],
        first_seen=datetime(2024, 1, 15, 10, 30, 0),
        sentiment_avg=-0.5
    )
    
    trend_point = TrendPoint(
        date=datetime(2024, 1, 15),
        value=-0.3,
        count=25
    )
    
    trend_data = TrendData(
        metric_name="sentiment",
        period="daily",
        data_points=[trend_point]
    )
    
    return GameAnalysisResult(
        game_id="test-game",
        analyzed_at=datetime(2024, 1, 15, 12, 0, 0),
        total_posts=100,
        total_comments=500,
        sentiment_distribution={"positive": 30, "negative": 40, "neutral": 30},
        sentiment_avg=-0.1,
        issues=[issue],
        hot_issues=[issue],
        bug_issues=[issue],
        sentiment_trend=trend_data
    )


class TestAnalysisDataStoreSaveLoad:
    """AnalysisDataStore 저장/로드 테스트"""
    
    def test_save_and_load_analysis(self, analysis_store, sample_analysis_result):
        """저장 후 로드 시 동일한 데이터 반환 검증 (Requirements: 1.1)"""
        game_id = "test-game"
        
        # 저장
        filepath = analysis_store.save_analysis(game_id, sample_analysis_result)
        assert os.path.exists(filepath)
        
        # 로드
        loaded = analysis_store.load_analysis(filepath)
        assert loaded is not None
        
        # 기본 필드 검증
        assert loaded.game_id == sample_analysis_result.game_id
        assert loaded.analyzed_at == sample_analysis_result.analyzed_at
        assert loaded.total_posts == sample_analysis_result.total_posts
        assert loaded.total_comments == sample_analysis_result.total_comments
        assert loaded.sentiment_avg == sample_analysis_result.sentiment_avg
        assert loaded.sentiment_distribution == sample_analysis_result.sentiment_distribution
    
    def test_save_and_load_issues(self, analysis_store, sample_analysis_result):
        """이슈 데이터 저장/로드 검증"""
        game_id = "test-game"
        
        filepath = analysis_store.save_analysis(game_id, sample_analysis_result)
        loaded = analysis_store.load_analysis(filepath)
        
        # 이슈 검증
        assert len(loaded.issues) == len(sample_analysis_result.issues)
        assert len(loaded.hot_issues) == len(sample_analysis_result.hot_issues)
        assert len(loaded.bug_issues) == len(sample_analysis_result.bug_issues)
        
        original_issue = sample_analysis_result.issues[0]
        loaded_issue = loaded.issues[0]
        
        assert loaded_issue.issue_id == original_issue.issue_id
        assert loaded_issue.title == original_issue.title
        assert loaded_issue.priority_score == original_issue.priority_score
        assert loaded_issue.is_hot == original_issue.is_hot
        assert loaded_issue.is_bug == original_issue.is_bug
        assert loaded_issue.severity == original_issue.severity
    
    def test_save_and_load_trend_data(self, analysis_store, sample_analysis_result):
        """트렌드 데이터 저장/로드 검증"""
        game_id = "test-game"
        
        filepath = analysis_store.save_analysis(game_id, sample_analysis_result)
        loaded = analysis_store.load_analysis(filepath)
        
        # 트렌드 검증
        assert loaded.sentiment_trend is not None
        assert loaded.sentiment_trend.metric_name == sample_analysis_result.sentiment_trend.metric_name
        assert loaded.sentiment_trend.period == sample_analysis_result.sentiment_trend.period
        assert len(loaded.sentiment_trend.data_points) == len(sample_analysis_result.sentiment_trend.data_points)
    
    def test_load_nonexistent_file(self, analysis_store):
        """존재하지 않는 파일 로드 시 None 반환"""
        result = analysis_store.load_analysis("/nonexistent/path/file.json")
        assert result is None


class TestAnalysisDataStoreLatest:
    """최신 분석 결과 조회 테스트"""
    
    def test_get_latest_analysis(self, analysis_store, sample_analysis_result):
        """최신 분석 결과 조회 (Requirements: 1.1)"""
        game_id = "test-game"
        
        # 첫 번째 분석 저장
        analysis_store.save_analysis(game_id, sample_analysis_result)
        
        # 두 번째 분석 저장 (더 최신)
        newer_result = GameAnalysisResult(
            game_id=game_id,
            analyzed_at=datetime(2024, 1, 16, 12, 0, 0),  # 하루 뒤
            total_posts=150,
            total_comments=700,
            sentiment_distribution={"positive": 50, "negative": 30, "neutral": 20},
            sentiment_avg=0.2,
            issues=[],
            hot_issues=[],
            bug_issues=[]
        )
        analysis_store.save_analysis(game_id, newer_result)
        
        # 최신 결과 조회
        latest = analysis_store.get_latest_analysis(game_id)
        assert latest is not None
        assert latest.analyzed_at == newer_result.analyzed_at
        assert latest.total_posts == 150
    
    def test_get_latest_analysis_no_data(self, analysis_store):
        """데이터가 없는 게임의 최신 분석 조회"""
        result = analysis_store.get_latest_analysis("nonexistent-game")
        assert result is None


class TestAnalysisDataStoreList:
    """분석 결과 목록 조회 테스트"""
    
    def test_list_analyses(self, analysis_store, sample_analysis_result):
        """분석 결과 파일 목록 조회"""
        game_id = "test-game"
        
        # 여러 분석 저장
        analysis_store.save_analysis(game_id, sample_analysis_result)
        
        newer_result = GameAnalysisResult(
            game_id=game_id,
            analyzed_at=datetime(2024, 1, 16, 12, 0, 0),
            total_posts=150,
            total_comments=700,
            sentiment_distribution={"positive": 50, "negative": 30, "neutral": 20},
            sentiment_avg=0.2,
            issues=[],
            hot_issues=[],
            bug_issues=[]
        )
        analysis_store.save_analysis(game_id, newer_result)
        
        # 목록 조회
        files = analysis_store.list_analyses(game_id)
        assert len(files) == 2
        assert all(os.path.exists(f) for f in files)
    
    def test_list_analyses_empty(self, analysis_store):
        """데이터가 없는 게임의 목록 조회"""
        files = analysis_store.list_analyses("nonexistent-game")
        assert files == []
    
    def test_get_all_game_ids(self, analysis_store, sample_analysis_result):
        """모든 게임 ID 목록 조회"""
        # 여러 게임 저장
        analysis_store.save_analysis("game-a", sample_analysis_result)
        
        result_b = GameAnalysisResult(
            game_id="game-b",
            analyzed_at=datetime(2024, 1, 15, 12, 0, 0),
            total_posts=50,
            total_comments=200,
            sentiment_distribution={"positive": 20, "negative": 20, "neutral": 10},
            sentiment_avg=0.0,
            issues=[],
            hot_issues=[],
            bug_issues=[]
        )
        analysis_store.save_analysis("game-b", result_b)
        
        # 게임 ID 목록 조회
        game_ids = analysis_store.get_all_game_ids()
        assert "game-a" in game_ids
        assert "game-b" in game_ids


class TestAnalysisDataStoreDelete:
    """분석 결과 삭제 테스트"""
    
    def test_delete_analysis(self, analysis_store, sample_analysis_result):
        """분석 결과 파일 삭제"""
        game_id = "test-game"
        
        filepath = analysis_store.save_analysis(game_id, sample_analysis_result)
        assert os.path.exists(filepath)
        
        result = analysis_store.delete_analysis(filepath)
        assert result is True
        assert not os.path.exists(filepath)
    
    def test_delete_nonexistent_file(self, analysis_store):
        """존재하지 않는 파일 삭제"""
        result = analysis_store.delete_analysis("/nonexistent/path/file.json")
        assert result is False
    
    def test_delete_game_analyses(self, analysis_store, sample_analysis_result):
        """게임의 모든 분석 결과 삭제"""
        game_id = "test-game"
        
        # 여러 분석 저장
        analysis_store.save_analysis(game_id, sample_analysis_result)
        
        newer_result = GameAnalysisResult(
            game_id=game_id,
            analyzed_at=datetime(2024, 1, 16, 12, 0, 0),
            total_posts=150,
            total_comments=700,
            sentiment_distribution={"positive": 50, "negative": 30, "neutral": 20},
            sentiment_avg=0.2,
            issues=[],
            hot_issues=[],
            bug_issues=[]
        )
        analysis_store.save_analysis(game_id, newer_result)
        
        # 모두 삭제
        deleted_count = analysis_store.delete_game_analyses(game_id)
        assert deleted_count == 2
        
        # 확인
        files = analysis_store.list_analyses(game_id)
        assert len(files) == 0


class TestAnalysisDataStoreSummary:
    """분석 요약 정보 테스트"""
    
    def test_get_analysis_summary(self, analysis_store, sample_analysis_result):
        """분석 요약 정보 조회"""
        game_id = "test-game"
        
        analysis_store.save_analysis(game_id, sample_analysis_result)
        
        summary = analysis_store.get_analysis_summary(game_id)
        assert summary is not None
        assert summary["game_id"] == game_id
        assert summary["total_analyses"] == 1
        assert summary["total_posts"] == sample_analysis_result.total_posts
        assert summary["total_comments"] == sample_analysis_result.total_comments
        assert summary["sentiment_avg"] == sample_analysis_result.sentiment_avg
        assert summary["issue_count"] == len(sample_analysis_result.issues)
        assert summary["hot_issue_count"] == len(sample_analysis_result.hot_issues)
        assert summary["bug_issue_count"] == len(sample_analysis_result.bug_issues)
    
    def test_get_analysis_summary_no_data(self, analysis_store):
        """데이터가 없는 게임의 요약 조회"""
        summary = analysis_store.get_analysis_summary("nonexistent-game")
        assert summary is None
