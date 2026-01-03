"""
ContentCrawler - 콘텐츠 크롤러

Requirements: 1.1, 1.3, 2.1, 2.3, 4.4
- 게시글 본문 및 메타데이터 추출
- 댓글 추출 (최대 3페이지)
- RateLimiter 및 ParserRegistry 통합
- 에러 처리 및 폴백 로직
"""

import logging
import random
from typing import List, Optional
from urllib.parse import urlparse, urljoin

import requests
from requests.exceptions import RequestException, Timeout, HTTPError

from crawler.models.data_models import CrawlerConfig, PostContent, Comment
from crawler.utils.rate_limiter import RateLimiter
from crawler.parsers.base import ParserRegistry, ContentParser
from crawler.parsers.generic import GenericParser
from crawler.parsers.inven import InvenParser
from crawler.parsers.ruliweb import RuliwebParser
from crawler.parsers.dcinside import DCInsideParser


logger = logging.getLogger(__name__)


# 실제 브라우저와 유사한 User-Agent 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class ContentCrawler:
    """콘텐츠 크롤러
    
    Requirements:
    - 1.1: 검색 결과 URL에 접속하여 Post_Content 추출
    - 1.3: 게시글 본문 추출 실패 시 에러 로깅 후 다음 URL로 진행
    - 2.1: 게시글 파싱 시 Comment_Data 함께 추출
    - 2.3: 댓글 페이지네이션 시 최대 3페이지까지 수집
    - 4.4: Content_Parser 파싱 실패 시 범용 파서로 폴백
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """ContentCrawler 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
        """
        if config is None:
            config = CrawlerConfig()
        
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.parser_registry = ParserRegistry()
        
        # 기본 파서 등록
        self._register_default_parsers()
        
        # HTTP 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",  # br(Brotli) 제외 - 일부 환경에서 디코딩 문제 발생
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # 타임아웃 설정
        self.connect_timeout = 10  # 연결 타임아웃 (초)
        self.read_timeout = 30     # 읽기 타임아웃 (초)
    
    def _register_default_parsers(self) -> None:
        """기본 파서 등록
        
        Requirements: 4.1, 4.2
        - 사이트별 맞춤 파서 등록
        - GenericParser를 폴백으로 설정
        """
        # 사이트별 파서 등록
        self.parser_registry.register(InvenParser())
        self.parser_registry.register(RuliwebParser())
        self.parser_registry.register(DCInsideParser())
        
        # 범용 파서를 폴백으로 설정
        self.parser_registry.set_generic_parser(GenericParser())
    
    def _get_random_user_agent(self) -> str:
        """랜덤 User-Agent 반환
        
        Requirements: 8.3
        - 실제 브라우저와 유사한 User-Agent 사용
        """
        return random.choice(USER_AGENTS)
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        parsed = urlparse(url)
        return parsed.netloc
    
    def _fetch_html(self, url: str) -> Optional[str]:
        """URL에서 HTML 가져오기
        
        Requirements: 5.1, 5.2, 5.3
        - Rate limiting 적용
        - HTTP 429 응답 시 지수 백오프
        - 재시도 횟수 초과 시 None 반환
        
        Args:
            url: 대상 URL
            
        Returns:
            HTML 문자열 또는 None (실패 시)
        """
        domain = self._extract_domain(url)
        
        # Rate limiting 적용
        wait_result = self.rate_limiter.wait(domain)
        if wait_result < 0:
            logger.warning(f"도메인 '{domain}'이 일시 중단 상태입니다. URL: {url}")
            return None
        
        # User-Agent 설정
        headers = {"User-Agent": self._get_random_user_agent()}
        
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            
            # HTTP 429 처리
            if response.status_code == 429:
                logger.warning(f"Rate limit 발생: {url}")
                can_retry, _ = self.rate_limiter.handle_rate_limit(domain)
                
                if can_retry:
                    # 재시도
                    return self._fetch_html(url)
                else:
                    logger.error(f"재시도 횟수 초과로 크롤링 중단: {url}")
                    return None
            
            response.raise_for_status()
            
            # 성공 시 재시도 카운터 리셋
            self.rate_limiter.reset_retry_count(domain)
            
            # 인코딩 처리: Content-Type 헤더의 charset을 우선 사용
            # requests가 Content-Type에서 charset을 자동으로 설정하므로 그대로 사용
            # apparent_encoding이 None이고 encoding도 없는 경우에만 utf-8 사용
            if not response.encoding:
                if response.apparent_encoding:
                    response.encoding = response.apparent_encoding
                else:
                    response.encoding = 'utf-8'
            
            return response.text
            
        except Timeout:
            logger.error(f"타임아웃 발생: {url}")
            return None
        except HTTPError as e:
            logger.error(f"HTTP 에러 발생: {url} - {e}")
            return None
        except RequestException as e:
            logger.error(f"요청 에러 발생: {url} - {e}")
            return None
    
    def crawl_post(self, url: str, keyword: str = "") -> Optional[PostContent]:
        """게시글 본문 및 메타데이터 추출
        
        Requirements: 1.1, 1.3, 4.4
        - URL에 접속하여 Post_Content 추출
        - 추출 실패 시 에러 로깅 후 None 반환
        - 전용 파서 실패 시 GenericParser로 폴백
        
        Args:
            url: 게시글 URL
            keyword: 검색 키워드
            
        Returns:
            PostContent 또는 None (실패 시)
        """
        logger.info(f"게시글 크롤링 시작: {url}")
        
        # HTML 가져오기
        html = self._fetch_html(url)
        if not html:
            logger.error(f"HTML 가져오기 실패: {url}")
            return None
        
        # 파서 선택
        parser = self.parser_registry.get_parser(url)
        if parser is None:
            logger.error(f"파서를 찾을 수 없음: {url}")
            return None
        
        # 파싱 시도
        try:
            post = parser.parse_post(html, url, keyword)
            
            # 필수 필드 검증
            if not post.title and not post.body:
                raise ValueError("제목과 본문이 모두 비어있음")
            
            logger.info(f"게시글 파싱 성공: {post.title[:50] if post.title else '(제목 없음)'}...")
            return post
            
        except Exception as e:
            logger.warning(f"전용 파서 실패, GenericParser로 폴백 시도: {url} - {e}")
            
            # Requirements 4.4: 폴백 처리
            generic_parser = self.parser_registry._generic_parser
            if generic_parser and parser != generic_parser:
                try:
                    post = generic_parser.parse_post(html, url, keyword)
                    
                    if not post.title and not post.body:
                        raise ValueError("제목과 본문이 모두 비어있음")
                    
                    logger.info(f"GenericParser로 파싱 성공: {post.title[:50] if post.title else '(제목 없음)'}...")
                    return post
                    
                except Exception as fallback_error:
                    logger.error(f"GenericParser도 실패: {url} - {fallback_error}")
            
            return None
    
    def crawl_comments(self, url: str, max_pages: int = None) -> List[Comment]:
        """댓글 추출
        
        Requirements: 2.1, 2.3, 2.4
        - 게시글의 댓글 추출
        - 페이지네이션 시 최대 max_pages 페이지까지 수집
        - 댓글이 없으면 빈 배열 반환
        
        Args:
            url: 게시글 URL
            max_pages: 최대 페이지 수 (기본값: config.max_comment_pages)
            
        Returns:
            Comment 목록 (실패 시 빈 배열)
        """
        if max_pages is None:
            max_pages = self.config.max_comment_pages
        
        logger.info(f"댓글 크롤링 시작: {url} (최대 {max_pages} 페이지)")
        
        all_comments: List[Comment] = []
        
        # 첫 페이지 HTML 가져오기
        html = self._fetch_html(url)
        if not html:
            logger.warning(f"댓글 HTML 가져오기 실패: {url}")
            return all_comments
        
        # 파서 선택
        parser = self.parser_registry.get_parser(url)
        if parser is None:
            logger.warning(f"댓글 파서를 찾을 수 없음: {url}")
            return all_comments
        
        # 첫 페이지 댓글 파싱
        try:
            comments = parser.parse_comments(html)
            all_comments.extend(comments)
            logger.debug(f"1페이지 댓글 {len(comments)}개 추출")
        except Exception as e:
            logger.warning(f"댓글 파싱 실패: {url} - {e}")
            
            # 폴백 시도
            generic_parser = self.parser_registry._generic_parser
            if generic_parser and parser != generic_parser:
                try:
                    comments = generic_parser.parse_comments(html)
                    all_comments.extend(comments)
                except Exception as fallback_error:
                    logger.error(f"GenericParser 댓글 파싱도 실패: {fallback_error}")
        
        # 추가 페이지 크롤링 (사이트별 페이지네이션 로직 필요)
        # 현재는 첫 페이지만 처리 (사이트별 페이지네이션 URL 패턴이 다름)
        # TODO: 사이트별 댓글 페이지네이션 구현
        
        logger.info(f"총 {len(all_comments)}개 댓글 추출 완료")
        return all_comments
    
    def crawl_post_with_comments(self, url: str, keyword: str = "") -> Optional[PostContent]:
        """게시글과 댓글을 함께 크롤링
        
        Requirements: 1.1, 2.1
        - 게시글 본문과 댓글을 한 번에 추출
        - 댓글은 게시글 HTML에서 추출 (추가 요청 없음)
        
        Args:
            url: 게시글 URL
            keyword: 검색 키워드
            
        Returns:
            PostContent (댓글 포함) 또는 None (실패 시)
        """
        # crawl_post가 이미 댓글을 포함하여 파싱함
        return self.crawl_post(url, keyword)
    
    def crawl_multiple_posts(
        self, 
        urls: List[str], 
        keyword: str = ""
    ) -> List[PostContent]:
        """여러 게시글 크롤링
        
        Requirements: 1.1, 1.3
        - 여러 URL에 대해 순차적으로 크롤링
        - 실패한 URL은 건너뛰고 계속 진행
        
        Args:
            urls: 게시글 URL 목록
            keyword: 검색 키워드
            
        Returns:
            성공적으로 크롤링된 PostContent 목록
        """
        results: List[PostContent] = []
        
        for i, url in enumerate(urls):
            logger.info(f"크롤링 진행: {i + 1}/{len(urls)}")
            
            post = self.crawl_post(url, keyword)
            if post:
                results.append(post)
            else:
                logger.warning(f"크롤링 실패, 다음 URL로 진행: {url}")
        
        logger.info(f"크롤링 완료: {len(results)}/{len(urls)} 성공")
        return results
    
    def close(self) -> None:
        """세션 종료"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

