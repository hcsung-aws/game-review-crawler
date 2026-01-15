"""
CrawlerOrchestrator Integration Tests

Requirements: 1.1, 1.2, 2.1, 6.1
- 검색 → 크롤링 → 저장 end-to-end 테스트
"""

import os
import json
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from crawler import (
    CrawlerOrchestrator,
    CrawlerConfig,
    CrawlResult,
    PostContent,
    Comment,
    SearchResult
)
from crawler.search.adapters import SearchAdapter


class MockSearchAdapter(SearchAdapter):
    """테스트용 Mock 검색 어댑터"""
    
    def __init__(self, name: str = "MockAdapter", results: list = None):
        self._name = name
        self._results = results or []
        self._available = True
        self._search_count = 0
    
    @property
    def name(self) -> str:
        return self._name
    
    def is_available(self) -> bool:
        return self._available
    
    def search(self, keywords: list, site: str, max_results: int) -> list:
        self._search_count += 1
        return self._results[:max_results]
    
    def set_available(self, available: bool):
        self._available = available
    
    def set_results(self, results: list):
        self._results = results


class TestCrawlerOrchestratorInit:
    """CrawlerOrchestrator 초기화 테스트"""
    
    def test_init_with_default_config(self):
        """기본 설정으로 초기화"""
        orchestrator = CrawlerOrchestrator()
        
        assert orchestrator.config is not None
        assert orchestrator.search_engine is not None
        assert orchestrator.content_crawler is not None
        assert orchestrator.data_store is not None
        
        orchestrator.close()
    
    def test_init_with_custom_config(self):
        """커스텀 설정으로 초기화"""
        config = CrawlerConfig(
            output_dir="test_output",
            default_delay=1.0,
            relevance_threshold=0.7
        )
        
        orchestrator = CrawlerOrchestrator(config)
        
        assert orchestrator.config.output_dir == "test_output"
        assert orchestrator.config.default_delay == 1.0
        assert orchestrator.config.relevance_threshold == 0.7
        
        orchestrator.close()
    
    def test_default_adapters_registered(self):
        """기본 어댑터가 등록되는지 확인"""
        orchestrator = CrawlerOrchestrator()
        
        adapters = orchestrator.search_engine.get_adapters()
        # DuckDuckGo와 DirectCrawl 어댑터가 기본 등록됨
        assert len(adapters) >= 2
        
        adapter_names = [a.name for a in adapters]
        assert "DuckDuckGo" in adapter_names
        assert "DirectCrawl" in adapter_names
        
        orchestrator.close()


class TestCrawlResultDataClass:
    """CrawlResult 데이터 클래스 테스트"""
    
    def test_crawl_result_defaults(self):
        """기본값 테스트"""
        result = CrawlResult()
        
        assert result.posts == []
        assert result.total_searched == 0
        assert result.total_crawled == 0
        assert result.total_failed == 0
        assert result.keywords_used == []
        assert result.sites_crawled == []
        assert result.errors == []
    
    def test_crawl_result_duration(self):
        """소요 시간 계산 테스트"""
        result = CrawlResult(
            started_at=datetime(2024, 1, 1, 10, 0, 0),
            finished_at=datetime(2024, 1, 1, 10, 0, 30)
        )
        
        assert result.duration_seconds == 30.0
    
    def test_crawl_result_success_rate(self):
        """성공률 계산 테스트"""
        result = CrawlResult(
            total_searched=10,
            total_crawled=7,
            total_failed=3
        )
        
        assert result.success_rate == 0.7
    
    def test_crawl_result_success_rate_zero_searched(self):
        """검색 결과 0일 때 성공률"""
        result = CrawlResult(total_searched=0)
        
        assert result.success_rate == 0.0
    
    def test_crawl_result_to_dict(self):
        """딕셔너리 변환 테스트"""
        result = CrawlResult(
            total_searched=10,
            total_crawled=7,
            keywords_used=["test"],
            sites_crawled=["example.com"]
        )
        
        data = result.to_dict()
        
        assert data["total_searched"] == 10
        assert data["total_crawled"] == 7
        assert data["keywords_used"] == ["test"]
        assert data["sites_crawled"] == ["example.com"]


class TestCrawlerOrchestratorSearchOnly:
    """검색만 수행하는 기능 테스트"""
    
    def test_search_only_with_mock_adapter(self):
        """Mock 어댑터로 검색만 수행"""
        orchestrator = CrawlerOrchestrator()
        
        # Mock 어댑터 설정
        mock_results = [
            SearchResult(
                url="https://example.com/post1",
                title="Test Post 1",
                snippet="Test snippet 1",
                relevance_score=0.8
            ),
            SearchResult(
                url="https://example.com/post2",
                title="Test Post 2",
                snippet="Test snippet 2",
                relevance_score=0.6
            )
        ]
        
        mock_adapter = MockSearchAdapter("TestAdapter", mock_results)
        
        # 기존 어댑터 제거하고 Mock 어댑터만 사용
        orchestrator.search_engine._adapters = [mock_adapter]
        
        # 검색 수행
        results = orchestrator.search_only(
            keywords=["test"],
            sites=["example.com"],
            max_results_per_site=10
        )
        
        assert len(results) == 2
        assert results[0].url == "https://example.com/post1"
        
        orchestrator.close()


class TestCrawlerOrchestratorCrawlUrls:
    """URL 직접 크롤링 테스트"""
    
    def test_crawl_urls_with_mock_content(self):
        """Mock 콘텐츠로 URL 크롤링"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # ContentCrawler의 crawl_post를 Mock
            mock_post = PostContent(
                url="https://example.com/post1",
                title="Test Title",
                body="Test body content",
                site="example.com",
                keyword="test",
                author="TestAuthor",
                created_at=datetime.now(),
                view_count=100,
                like_count=10,
                comments=[
                    Comment(author="User1", content="Comment 1"),
                    Comment(author="User2", content="Comment 2")
                ]
            )
            
            with patch.object(
                orchestrator.content_crawler, 
                'crawl_post', 
                return_value=mock_post
            ):
                result = orchestrator.crawl_urls(
                    urls=["https://example.com/post1"],
                    keyword="test",
                    save_results=False
                )
            
            assert result.total_searched == 1
            assert result.total_crawled == 1
            assert result.total_failed == 0
            assert len(result.posts) == 1
            assert result.posts[0].title == "Test Title"
            assert len(result.posts[0].comments) == 2
            
            orchestrator.close()
    
    def test_crawl_urls_with_failures(self):
        """크롤링 실패 처리 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # crawl_post가 None을 반환하도록 Mock
            with patch.object(
                orchestrator.content_crawler, 
                'crawl_post', 
                return_value=None
            ):
                result = orchestrator.crawl_urls(
                    urls=["https://example.com/post1", "https://example.com/post2"],
                    keyword="test",
                    save_results=False
                )
            
            assert result.total_searched == 2
            assert result.total_crawled == 0
            assert result.total_failed == 2
            assert len(result.errors) == 2
            
            orchestrator.close()


class TestCrawlerOrchestratorDataManagement:
    """데이터 관리 기능 테스트"""
    
    def test_clear_data(self):
        """데이터 초기화 테스트"""
        orchestrator = CrawlerOrchestrator()
        
        # 데이터 추가
        post = PostContent(
            url="https://example.com/post1",
            title="Test",
            body="Body",
            site="example.com",
            keyword="test"
        )
        orchestrator.data_store.add_post(post)
        
        assert orchestrator.data_store.count() == 1
        
        # 데이터 초기화
        orchestrator.clear_data()
        
        assert orchestrator.data_store.count() == 0
        
        orchestrator.close()
    
    def test_clear_cache(self):
        """캐시 초기화 테스트"""
        orchestrator = CrawlerOrchestrator()
        
        # 캐시에 데이터 추가
        orchestrator.search_engine._cache.set(
            ["test"], 
            "example.com", 
            [SearchResult(url="test", title="test", snippet="test")]
        )
        
        # 캐시 초기화
        count = orchestrator.clear_cache()
        
        assert count >= 0
        
        orchestrator.close()


class TestCrawlerOrchestratorExport:
    """내보내기 기능 테스트"""
    
    def test_export_json(self):
        """JSON 내보내기 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # 데이터 추가
            post = PostContent(
                url="https://example.com/post1",
                title="Test Title",
                body="Test Body",
                site="example.com",
                keyword="test"
            )
            orchestrator.data_store.add_post(post)
            
            # JSON 내보내기
            filepath = orchestrator.export_results(
                output_format="json",
                filename="test_export"
            )
            
            assert filepath.endswith(".json")
            assert os.path.exists(filepath)
            
            # 파일 내용 확인
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            assert len(data) == 1
            assert data[0]["title"] == "Test Title"
            
            orchestrator.close()
    
    def test_export_csv(self):
        """CSV 내보내기 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # 데이터 추가
            post = PostContent(
                url="https://example.com/post1",
                title="Test Title",
                body="Test Body",
                site="example.com",
                keyword="test"
            )
            orchestrator.data_store.add_post(post)
            
            # CSV 내보내기
            filepath = orchestrator.export_results(
                output_format="csv",
                filename="test_export"
            )
            
            assert filepath.endswith(".csv")
            assert os.path.exists(filepath)
            
            orchestrator.close()
    
    def test_export_empty_data(self):
        """빈 데이터 내보내기 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # 빈 데이터로 내보내기 시도
            filepath = orchestrator.export_results(output_format="json")
            
            assert filepath == ""
            
            orchestrator.close()


class TestCrawlerOrchestratorContextManager:
    """Context Manager 테스트"""
    
    def test_context_manager(self):
        """with 문 사용 테스트"""
        with CrawlerOrchestrator() as orchestrator:
            assert orchestrator is not None
            assert orchestrator.search_engine is not None
        
        # close가 호출되었는지 확인 (세션이 닫혔는지)
        # 직접 확인하기 어려우므로 예외 없이 종료되면 성공


class TestIntegrationWorkflow:
    """통합 워크플로우 테스트"""
    
    def test_full_workflow_with_mocks(self):
        """전체 워크플로우 테스트 (Mock 사용)
        
        Requirements: 1.1, 1.2, 2.1, 6.1
        - 검색 → 크롤링 → 저장 end-to-end 테스트
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # Mock 검색 결과
            mock_search_results = [
                SearchResult(
                    url="https://inven.co.kr/post1",
                    title="몬스터헌터 리뷰",
                    snippet="게임 리뷰 내용",
                    relevance_score=0.9
                )
            ]
            
            # Mock 크롤링 결과
            mock_post = PostContent(
                url="https://inven.co.kr/post1",
                title="몬스터헌터 리뷰",
                body="상세한 게임 리뷰 본문입니다.",
                site="inven.co.kr",
                keyword="몬스터헌터",
                author="게이머",
                created_at=datetime.now(),
                view_count=1000,
                like_count=50,
                comments=[
                    Comment(author="유저1", content="좋은 리뷰네요"),
                    Comment(author="유저2", content="동의합니다")
                ]
            )
            
            # Mock 어댑터 설정
            mock_adapter = MockSearchAdapter("TestAdapter", mock_search_results)
            orchestrator.search_engine._adapters = [mock_adapter]
            
            # ContentCrawler Mock
            with patch.object(
                orchestrator.content_crawler,
                'crawl_post',
                return_value=mock_post
            ):
                result = orchestrator.crawl(
                    keywords=["몬스터헌터", "리뷰"],
                    sites=["inven.co.kr"],
                    max_results_per_site=10,
                    save_results=True,
                    output_format="json"
                )
            
            # 결과 검증
            assert result.total_searched == 1
            assert result.total_crawled == 1
            assert result.total_failed == 0
            assert len(result.posts) == 1
            
            # 게시글 검증
            post = result.posts[0]
            assert post.title == "몬스터헌터 리뷰"
            assert post.site == "inven.co.kr"
            assert len(post.comments) == 2
            
            # 저장된 파일 확인
            files = os.listdir(tmpdir)
            json_files = [f for f in files if f.endswith(".json")]
            assert len(json_files) >= 1
            
            orchestrator.close()
    
    def test_workflow_with_url_deduplication(self):
        """URL 중복 제거 테스트
        
        Requirements: 3.4
        - 중복 URL이 발견되면 한 번만 처리
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir, relevance_threshold=0.0)
            orchestrator = CrawlerOrchestrator(config)
            
            # 중복 URL이 포함된 검색 결과
            mock_search_results = [
                SearchResult(url="https://example.com/post1", title="Post 1", snippet="test keyword", relevance_score=0.9),
                SearchResult(url="https://example.com/post1", title="Post 1 Dup", snippet="test keyword", relevance_score=0.8),
                SearchResult(url="https://example.com/post2", title="Post 2", snippet="test keyword", relevance_score=0.7)
            ]
            
            mock_adapter = MockSearchAdapter("TestAdapter", mock_search_results)
            orchestrator.search_engine._adapters = [mock_adapter]
            
            crawl_count = 0
            
            def mock_crawl_post(url, keyword):
                nonlocal crawl_count
                crawl_count += 1
                return PostContent(
                    url=url,
                    title=f"Title for {url}",
                    body="Body",
                    site="example.com",
                    keyword=keyword
                )
            
            with patch.object(
                orchestrator.content_crawler,
                'crawl_post',
                side_effect=mock_crawl_post
            ):
                result = orchestrator.crawl(
                    keywords=["test"],
                    sites=["example.com"],
                    save_results=False
                )
            
            # 중복 제거로 2개만 크롤링되어야 함
            assert crawl_count == 2
            assert result.total_crawled == 2
            
            orchestrator.close()


class TestGameAnalyzerIntegration:
    """GameAnalyzer 통합 테스트
    
    Requirements: 1.1, 2.1, 3.1, 4.1, 5.1
    - 크롤링 → 분석 → 저장 → 대시보드 표시 end-to-end 테스트
    """
    
    def test_game_analyzer_initialization(self):
        """GameAnalyzer 초기화 테스트"""
        from crawler.analysis.game_analyzer import GameAnalyzer
        
        analyzer = GameAnalyzer()
        
        assert analyzer.sentiment_analyzer is not None
        assert analyzer.issue_detector is not None
        assert analyzer.trend_analyzer is not None
        assert analyzer.alert_manager is not None
        assert analyzer.analysis_store is not None
        assert analyzer.profile_manager is not None
    
    def test_game_analyzer_analyze_posts(self):
        """게시글 분석 테스트
        
        Requirements: 2.1, 3.1, 4.1
        - 감성 분석, 이슈 탐지, 트렌드 분석 수행
        """
        from crawler.analysis.game_analyzer import GameAnalyzer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from crawler.exporters.analysis_store import AnalysisDataStore
            
            analyzer = GameAnalyzer(
                analysis_store=AnalysisDataStore(base_dir=tmpdir)
            )
            
            # 테스트 게시글 생성
            posts = [
                PostContent(
                    url="https://example.com/post1",
                    title="게임 버그 발생",
                    body="게임에서 심각한 버그가 발생했습니다. 오류가 계속 나요.",
                    site="example.com",
                    keyword="게임",
                    created_at=datetime(2024, 1, 1, 10, 0, 0),
                    view_count=1000,
                    like_count=10,
                    comments=[
                        Comment(author="유저1", content="저도 같은 문제 있어요"),
                        Comment(author="유저2", content="빨리 수정해주세요")
                    ]
                ),
                PostContent(
                    url="https://example.com/post2",
                    title="게임 재미있어요",
                    body="정말 재미있는 게임입니다. 추천합니다!",
                    site="example.com",
                    keyword="게임",
                    created_at=datetime(2024, 1, 2, 10, 0, 0),
                    view_count=500,
                    like_count=50,
                    comments=[
                        Comment(author="유저3", content="동의합니다!")
                    ]
                ),
                PostContent(
                    url="https://example.com/post3",
                    title="업데이트 후기",
                    body="업데이트 후 렉이 심해졌어요. 튕김 현상도 있습니다.",
                    site="example.com",
                    keyword="게임",
                    created_at=datetime(2024, 1, 3, 10, 0, 0),
                    view_count=800,
                    like_count=5,
                    comments=[]
                )
            ]
            
            # 분석 수행
            result = analyzer.analyze(
                game_id="test-game",
                posts=posts,
                save_result=True
            )
            
            # 결과 검증
            assert result.game_id == "test-game"
            assert result.total_posts == 3
            assert result.total_comments == 3
            
            # 감성 분포 검증
            assert "positive" in result.sentiment_distribution
            assert "negative" in result.sentiment_distribution
            assert "neutral" in result.sentiment_distribution
            
            # 이슈 탐지 검증
            assert isinstance(result.issues, list)
            
            # 버그 이슈 검증 (버그, 오류, 렉, 튕김 키워드 포함)
            assert isinstance(result.bug_issues, list)
            
            # 트렌드 검증
            assert result.sentiment_trend is not None
            assert result.sentiment_trend.metric_name == "sentiment"
    
    def test_orchestrator_with_auto_analyze(self):
        """CrawlerOrchestrator 자동 분석 테스트
        
        Requirements: 1.1, 2.1, 3.1, 4.1
        - 크롤링 후 자동 분석 수행
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # Mock 게시글
            mock_posts = [
                PostContent(
                    url="https://example.com/post1",
                    title="게임 리뷰",
                    body="재미있는 게임입니다.",
                    site="example.com",
                    keyword="게임",
                    created_at=datetime.now(),
                    view_count=100,
                    like_count=10,
                    comments=[]
                )
            ]
            
            # Mock 검색 결과
            mock_search_results = [
                SearchResult(
                    url="https://example.com/post1",
                    title="게임 리뷰",
                    snippet="재미있는 게임",
                    relevance_score=0.9
                )
            ]
            
            mock_adapter = MockSearchAdapter("TestAdapter", mock_search_results)
            orchestrator.search_engine._adapters = [mock_adapter]
            
            with patch.object(
                orchestrator.content_crawler,
                'crawl_post',
                return_value=mock_posts[0]
            ):
                result = orchestrator.crawl(
                    keywords=["게임"],
                    sites=["example.com"],
                    max_results_per_site=10,
                    save_results=True,
                    game_id="test-game",
                    auto_analyze=True
                )
            
            # 크롤링 결과 검증
            assert result.total_crawled == 1
            assert result.game_id == "test-game"
            
            # 자동 분석 결과 검증
            assert result.analysis_result is not None
            assert result.analysis_result.game_id == "test-game"
            assert result.analysis_result.total_posts == 1
            
            orchestrator.close()
    
    def test_orchestrator_crawl_game_profile(self):
        """게임 프로필 기반 크롤링 테스트
        
        Requirements: 1.1
        - 게임 프로필의 키워드와 대상 사이트를 사용하여 크롤링
        """
        from crawler.models.game_profile import GameProfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlerConfig(output_dir=tmpdir)
            orchestrator = CrawlerOrchestrator(config)
            
            # 게임 프로필 생성
            profile = GameProfile(
                game_id="monster-hunter",
                game_name="몬스터헌터",
                keywords=["몬스터헌터", "몬헌"],
                target_sites=["inven.co.kr", "ruliweb.com"],
                data_dir=os.path.join(tmpdir, "data/monster-hunter"),
                quicksight_dir=os.path.join(tmpdir, "quicksight_data/monster-hunter")
            )
            
            # Mock 검색 결과
            mock_search_results = [
                SearchResult(
                    url="https://inven.co.kr/post1",
                    title="몬스터헌터 공략",
                    snippet="몬헌 공략",
                    relevance_score=0.9
                )
            ]
            
            mock_post = PostContent(
                url="https://inven.co.kr/post1",
                title="몬스터헌터 공략",
                body="몬헌 공략 내용",
                site="inven.co.kr",
                keyword="몬스터헌터",
                created_at=datetime.now(),
                view_count=500,
                like_count=20,
                comments=[]
            )
            
            mock_adapter = MockSearchAdapter("TestAdapter", mock_search_results)
            orchestrator.search_engine._adapters = [mock_adapter]
            
            with patch.object(
                orchestrator.content_crawler,
                'crawl_post',
                return_value=mock_post
            ):
                result = orchestrator.crawl_game(
                    profile=profile,
                    max_results_per_site=10,
                    save_results=True,
                    auto_analyze=False
                )
            
            # 결과 검증
            assert result.game_id == "monster-hunter"
            assert result.total_crawled == 1
            assert "몬스터헌터" in result.keywords_used or "몬헌" in result.keywords_used
            
            # 게임별 디렉토리 생성 확인
            assert os.path.exists(os.path.join(tmpdir, "data/monster-hunter"))
            
            orchestrator.close()
    
    def test_full_analysis_pipeline(self):
        """전체 분석 파이프라인 테스트
        
        Requirements: 1.1, 2.1, 3.1, 4.1, 5.1
        - 크롤링 → 분석 → 저장 → 조회 end-to-end 테스트
        """
        from crawler.analysis.game_analyzer import GameAnalyzer
        from crawler.exporters.analysis_store import AnalysisDataStore
        from crawler.models.game_profile import GameProfile, GameProfileManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 컴포넌트 초기화
            profile_manager = GameProfileManager(
                base_data_dir=os.path.join(tmpdir, "data"),
                base_quicksight_dir=os.path.join(tmpdir, "quicksight_data")
            )
            
            analysis_store = AnalysisDataStore(
                base_dir=os.path.join(tmpdir, "analysis_data")
            )
            
            analyzer = GameAnalyzer(
                analysis_store=analysis_store,
                profile_manager=profile_manager
            )
            
            # 게임 프로필 등록
            profile = GameProfile(
                game_id="test-game",
                game_name="테스트 게임",
                keywords=["테스트"],
                target_sites=["example.com"]
            )
            profile_manager.register_game(profile)
            
            # 테스트 게시글 생성
            posts = [
                PostContent(
                    url="https://example.com/post1",
                    title="버그 신고",
                    body="심각한 버그가 있습니다. 오류 발생.",
                    site="example.com",
                    keyword="테스트",
                    created_at=datetime(2024, 1, 1),
                    view_count=1000,
                    like_count=5,
                    comments=[
                        Comment(author="유저1", content="저도 같은 문제")
                    ]
                ),
                PostContent(
                    url="https://example.com/post2",
                    title="좋은 게임",
                    body="정말 재미있어요! 추천합니다.",
                    site="example.com",
                    keyword="테스트",
                    created_at=datetime(2024, 1, 2),
                    view_count=500,
                    like_count=50,
                    comments=[]
                )
            ]
            
            # 1. 분석 수행
            result = analyzer.analyze(
                game_id="test-game",
                posts=posts,
                save_result=True
            )
            
            # 2. 분석 결과 검증
            assert result.game_id == "test-game"
            assert result.total_posts == 2
            assert result.total_comments == 1
            
            # 3. 저장된 결과 조회
            loaded_result = analysis_store.get_latest_analysis("test-game")
            assert loaded_result is not None
            assert loaded_result.game_id == "test-game"
            assert loaded_result.total_posts == 2
            
            # 4. 분석 요약 조회
            summary = analyzer.get_analysis_summary("test-game")
            assert summary is not None
            assert summary["game_id"] == "test-game"
            assert summary["total_posts"] == 2
    
    def test_sentiment_only_analysis(self):
        """감성 분석만 수행 테스트
        
        Requirements: 2.1
        """
        from crawler.analysis.game_analyzer import GameAnalyzer
        
        analyzer = GameAnalyzer()
        
        posts = [
            PostContent(
                url="https://example.com/post1",
                title="좋아요",
                body="정말 좋습니다. 재미있어요!",
                site="example.com",
                keyword="test",
                view_count=100,
                like_count=10,
                comments=[]
            ),
            PostContent(
                url="https://example.com/post2",
                title="별로",
                body="실망입니다. 불만족스러워요.",
                site="example.com",
                keyword="test",
                view_count=50,
                like_count=2,
                comments=[]
            )
        ]
        
        result = analyzer.analyze_sentiment_only(posts)
        
        assert "distribution" in result
        assert "average_score" in result
        assert "negative_post_count" in result
        assert result["total_posts"] == 2
    
    def test_issues_only_detection(self):
        """이슈 탐지만 수행 테스트
        
        Requirements: 3.1
        """
        from crawler.analysis.game_analyzer import GameAnalyzer
        
        analyzer = GameAnalyzer()
        
        posts = [
            PostContent(
                url="https://example.com/post1",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다.",
                site="example.com",
                keyword="test",
                view_count=1000,
                like_count=10,
                comments=[]
            ),
            PostContent(
                url="https://example.com/post2",
                title="버그 또 발생",
                body="또 버그가 발생했어요. 오류입니다.",
                site="example.com",
                keyword="test",
                view_count=800,
                like_count=5,
                comments=[]
            )
        ]
        
        result = analyzer.detect_issues_only(posts)
        
        assert "issues" in result
        assert "hot_issues" in result
        assert "bug_issues" in result
        assert "total_issues" in result
    
    def test_trend_only_analysis(self):
        """트렌드 분석만 수행 테스트
        
        Requirements: 4.1
        """
        from crawler.analysis.game_analyzer import GameAnalyzer
        
        analyzer = GameAnalyzer()
        
        posts = [
            PostContent(
                url="https://example.com/post1",
                title="Day 1",
                body="좋아요",
                site="example.com",
                keyword="test",
                created_at=datetime(2024, 1, 1),
                view_count=100,
                like_count=10,
                comments=[]
            ),
            PostContent(
                url="https://example.com/post2",
                title="Day 2",
                body="별로예요",
                site="example.com",
                keyword="test",
                created_at=datetime(2024, 1, 2),
                view_count=50,
                like_count=2,
                comments=[]
            )
        ]
        
        result = analyzer.analyze_trend_only(posts, period="daily")
        
        assert result.metric_name == "sentiment"
        assert result.period == "daily"
        assert len(result.data_points) == 2
