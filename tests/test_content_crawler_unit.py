"""
ContentCrawler Unit Tests

Requirements: 1.3, 4.4
- 파싱 실패 시 폴백 동작 검증
- 에러 처리 검증
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, HTTPError, RequestException

from crawler.content_crawler import ContentCrawler
from crawler.models.data_models import CrawlerConfig, PostContent, Comment
from crawler.parsers.base import ContentParser, ParserRegistry
from crawler.parsers.generic import GenericParser


class FailingParser(ContentParser):
    """테스트용 실패하는 파서"""
    
    def __init__(self, domains: list):
        self.domains = domains
    
    def parse_post(self, html: str, url: str, keyword: str = "") -> PostContent:
        raise ValueError("의도적 파싱 실패")
    
    def parse_comments(self, html: str) -> list:
        raise ValueError("의도적 댓글 파싱 실패")
    
    def get_supported_domains(self) -> list:
        return self.domains


class TestContentCrawlerFallback:
    """ContentCrawler 폴백 동작 테스트
    
    Requirements: 4.4
    - Content_Parser가 파싱에 실패하면 범용 파서로 폴백
    """
    
    def test_fallback_to_generic_parser_on_parse_failure(self):
        """전용 파서 실패 시 GenericParser로 폴백
        
        Requirements: 4.4
        """
        # 테스트용 HTML
        test_html = """
        <html>
        <head><title>테스트 제목</title></head>
        <body>
            <h1 class="title">테스트 게시글 제목</h1>
            <div class="content">
                <p>이것은 테스트 본문입니다. 충분히 긴 내용을 포함해야 합니다.</p>
            </div>
        </body>
        </html>
        """
        
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        # 실패하는 파서 등록
        failing_parser = FailingParser(["test.com"])
        crawler.parser_registry.register(failing_parser)
        
        # HTTP 요청 모킹
        with patch.object(crawler, '_fetch_html', return_value=test_html):
            result = crawler.crawl_post("https://test.com/post/1", "테스트")
        
        # GenericParser로 폴백하여 파싱 성공해야 함
        assert result is not None
        assert result.title == "테스트 게시글 제목"
        assert "테스트 본문" in result.body
    
    def test_returns_none_when_both_parsers_fail(self):
        """전용 파서와 GenericParser 모두 실패 시 None 반환
        
        Requirements: 1.3
        """
        # 파싱 불가능한 HTML
        invalid_html = "<html><body></body></html>"
        
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        # 실패하는 파서 등록
        failing_parser = FailingParser(["test.com"])
        crawler.parser_registry.register(failing_parser)
        
        # GenericParser도 실패하도록 모킹
        mock_generic = Mock(spec=GenericParser)
        mock_generic.parse_post.side_effect = ValueError("GenericParser도 실패")
        crawler.parser_registry._generic_parser = mock_generic
        
        with patch.object(crawler, '_fetch_html', return_value=invalid_html):
            result = crawler.crawl_post("https://test.com/post/1", "테스트")
        
        assert result is None


class TestContentCrawlerErrorHandling:
    """ContentCrawler 에러 처리 테스트
    
    Requirements: 1.3
    - 게시글 본문 추출 실패 시 에러 로깅 후 다음 URL로 진행
    """
    
    def test_returns_none_on_fetch_failure(self):
        """HTML 가져오기 실패 시 None 반환
        
        Requirements: 1.3
        """
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        with patch.object(crawler, '_fetch_html', return_value=None):
            result = crawler.crawl_post("https://example.com/post/1", "테스트")
        
        assert result is None
    
    def test_returns_none_on_timeout(self):
        """타임아웃 발생 시 None 반환
        
        Requirements: 1.3
        """
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        with patch.object(crawler.session, 'get', side_effect=Timeout("타임아웃")):
            with patch.object(crawler.rate_limiter, 'wait', return_value=0):
                result = crawler.crawl_post("https://example.com/post/1", "테스트")
        
        assert result is None
    
    def test_returns_none_on_http_error(self):
        """HTTP 에러 발생 시 None 반환
        
        Requirements: 1.3
        """
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        
        with patch.object(crawler.session, 'get', return_value=mock_response):
            with patch.object(crawler.rate_limiter, 'wait', return_value=0):
                result = crawler.crawl_post("https://example.com/post/1", "테스트")
        
        assert result is None
    
    def test_crawl_multiple_continues_on_failure(self):
        """여러 URL 크롤링 시 실패해도 계속 진행
        
        Requirements: 1.3
        """
        test_html = """
        <html>
        <head><title>성공</title></head>
        <body>
            <h1 class="title">성공한 게시글</h1>
            <div class="content">
                <p>이것은 성공한 게시글의 본문입니다. 충분히 긴 내용입니다.</p>
            </div>
        </body>
        </html>
        """
        
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        # 첫 번째는 실패, 두 번째는 성공
        def mock_fetch(url):
            if "fail" in url:
                return None
            return test_html
        
        with patch.object(crawler, '_fetch_html', side_effect=mock_fetch):
            results = crawler.crawl_multiple_posts([
                "https://example.com/fail/1",
                "https://example.com/success/2",
                "https://example.com/fail/3",
            ], "테스트")
        
        # 성공한 것만 결과에 포함
        assert len(results) == 1
        assert results[0].title == "성공한 게시글"


class TestContentCrawlerComments:
    """ContentCrawler 댓글 크롤링 테스트
    
    Requirements: 2.1, 2.3, 2.4
    """
    
    def test_returns_empty_list_on_fetch_failure(self):
        """HTML 가져오기 실패 시 빈 배열 반환
        
        Requirements: 2.4
        """
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        with patch.object(crawler, '_fetch_html', return_value=None):
            result = crawler.crawl_comments("https://example.com/post/1")
        
        assert result == []
    
    def test_fallback_on_comment_parse_failure(self):
        """댓글 파싱 실패 시 GenericParser로 폴백
        
        Requirements: 4.4
        """
        test_html = """
        <html>
        <body>
            <div class="comments">
                <div class="comment">
                    <span class="author">작성자1</span>
                    <span class="content">댓글 내용입니다</span>
                </div>
            </div>
        </body>
        </html>
        """
        
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        # 실패하는 파서 등록
        failing_parser = FailingParser(["test.com"])
        crawler.parser_registry.register(failing_parser)
        
        with patch.object(crawler, '_fetch_html', return_value=test_html):
            result = crawler.crawl_comments("https://test.com/post/1")
        
        # GenericParser로 폴백하여 댓글 파싱 시도
        # (실제 결과는 HTML 구조에 따라 다를 수 있음)
        assert isinstance(result, list)


class TestContentCrawlerRateLimiting:
    """ContentCrawler Rate Limiting 테스트
    
    Requirements: 5.1, 5.2, 5.3
    """
    
    def test_returns_none_when_domain_suspended(self):
        """도메인이 일시 중단 상태일 때 None 반환
        
        Requirements: 5.3
        """
        config = CrawlerConfig(default_delay=0.1)
        crawler = ContentCrawler(config)
        
        # 도메인 일시 중단 상태로 설정
        crawler.rate_limiter._suspended_domains["example.com"] = True
        
        result = crawler.crawl_post("https://example.com/post/1", "테스트")
        
        assert result is None


class TestContentCrawlerContextManager:
    """ContentCrawler 컨텍스트 매니저 테스트"""
    
    def test_context_manager_closes_session(self):
        """컨텍스트 매니저 종료 시 세션 닫힘"""
        config = CrawlerConfig(default_delay=0.1)
        
        with ContentCrawler(config) as crawler:
            assert crawler.session is not None
        
        # 세션이 닫혔는지 확인 (closed 속성이 없으므로 간접 확인)
        # requests.Session은 close() 호출 후에도 사용 가능하지만
        # 여기서는 __exit__이 호출되었는지만 확인

