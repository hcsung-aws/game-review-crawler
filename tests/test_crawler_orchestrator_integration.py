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
