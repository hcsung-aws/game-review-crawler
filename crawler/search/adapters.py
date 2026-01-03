"""
Search Adapter 구현

Requirements: 7.1, 7.5
- SearchAdapter: 검색 어댑터 추상 클래스
- DuckDuckGoAdapter: DuckDuckGo 검색 API 어댑터
- GoogleCSEAdapter: Google Custom Search Engine 어댑터
- DirectCrawlAdapter: 커뮤니티 사이트 직접 크롤링 어댑터
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from crawler.models.data_models import SearchResult, CrawlerConfig


logger = logging.getLogger(__name__)


class SearchAdapter(ABC):
    """검색 어댑터 추상 클래스
    
    Requirements: 7.1
    - 다양한 검색 엔진을 통일된 인터페이스로 제공
    """
    
    @abstractmethod
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        """검색 수행
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """어댑터 사용 가능 여부
        
        Returns:
            사용 가능 여부
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """어댑터 이름
        
        Returns:
            어댑터 식별 이름
        """
        pass


class DuckDuckGoAdapter(SearchAdapter):
    """DuckDuckGo 검색 API 어댑터
    
    Requirements: 7.1
    - 기존 DuckDuckGo API 통합
    - duckduckgo_search 라이브러리 사용
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """DuckDuckGoAdapter 초기화
        
        Args:
            config: 크롤러 설정
        """
        self._config = config or CrawlerConfig()
        self._available = True
        self._last_error: Optional[str] = None
        self._throttled_until: float = 0
    
    @property
    def name(self) -> str:
        return "DuckDuckGo"
    
    def is_available(self) -> bool:
        """어댑터 사용 가능 여부
        
        스로틀링 상태이거나 이전 오류가 있으면 사용 불가
        """
        if time.time() < self._throttled_until:
            return False
        return self._available
    
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        """DuckDuckGo 검색 수행
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
            
        Raises:
            RuntimeError: 검색 실패 시
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error("duckduckgo_search 라이브러리가 설치되지 않았습니다.")
            self._available = False
            raise RuntimeError("duckduckgo_search 라이브러리가 필요합니다.")
        
        # 쿼리 구성: 키워드 AND 연산 + site 필터
        keyword_query = " AND ".join(keywords)
        query = f"{keyword_query} site:{site}"
        
        logger.info(f"DuckDuckGo 검색: {query}")
        
        results: List[SearchResult] = []
        
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                
                if not raw_results:
                    logger.warning(f"검색 결과 없음: {query}")
                    return results
                
                for item in raw_results:
                    url = item.get("href", "")
                    title = item.get("title", "")
                    snippet = item.get("body", "")
                    
                    # 관련성 점수는 나중에 RelevanceFilter에서 계산
                    result = SearchResult(
                        url=url,
                        title=title,
                        snippet=snippet,
                        relevance_score=0.0  # 초기값, 나중에 계산
                    )
                    results.append(result)
                
                logger.info(f"DuckDuckGo 검색 완료: {len(results)}개 결과")
                self._available = True
                self._last_error = None
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"DuckDuckGo 검색 실패: {error_msg}")
            self._last_error = error_msg
            
            # 스로틀링 감지 (RateLimitException 등)
            if "rate" in error_msg.lower() or "429" in error_msg:
                # 5분간 스로틀링 상태로 설정
                self._throttled_until = time.time() + 300
                logger.warning("DuckDuckGo 스로틀링 감지, 5분간 비활성화")
            
            raise RuntimeError(f"DuckDuckGo 검색 실패: {error_msg}")
        
        return results
    
    def reset_throttle(self) -> None:
        """스로틀링 상태 초기화"""
        self._throttled_until = 0
        self._available = True
        self._last_error = None


class GoogleCSEAdapter(SearchAdapter):
    """Google Custom Search Engine 어댑터
    
    Requirements: 7.1
    - Google Custom Search Engine API 통합
    - API 키 설정 지원
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """GoogleCSEAdapter 초기화
        
        Args:
            config: 크롤러 설정 (google_api_key, google_cse_id 필요)
        """
        self._config = config or CrawlerConfig()
        self._api_key = self._config.google_api_key
        self._cse_id = self._config.google_cse_id
        self._last_error: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "GoogleCSE"
    
    def is_available(self) -> bool:
        """API 키와 CSE ID가 설정되어 있어야 사용 가능"""
        return bool(self._api_key and self._cse_id)
    
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        """Google CSE 검색 수행
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
            
        Raises:
            RuntimeError: API 키 미설정 또는 검색 실패 시
        """
        if not self.is_available():
            raise RuntimeError("Google CSE API 키 또는 CSE ID가 설정되지 않았습니다.")
        
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests 라이브러리가 필요합니다.")
        
        # 쿼리 구성
        keyword_query = " ".join(keywords)
        query = f"{keyword_query} site:{site}"
        
        logger.info(f"Google CSE 검색: {query}")
        
        results: List[SearchResult] = []
        
        try:
            # Google CSE API 호출
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self._api_key,
                "cx": self._cse_id,
                "q": query,
                "num": min(max_results, 10)  # Google CSE는 최대 10개
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            for item in items:
                result = SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    relevance_score=0.0
                )
                results.append(result)
            
            logger.info(f"Google CSE 검색 완료: {len(results)}개 결과")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Google CSE 검색 실패: {error_msg}")
            self._last_error = error_msg
            raise RuntimeError(f"Google CSE 검색 실패: {error_msg}")
        
        return results


class DirectCrawlAdapter(SearchAdapter):
    """커뮤니티 사이트 직접 크롤링 어댑터
    
    Requirements: 7.1, 7.5
    - 커뮤니티 사이트의 게시판 목록 페이지를 직접 크롤링
    - 검색 API 의존도 감소
    """
    
    # 사이트별 게시판 URL 패턴
    BOARD_URLS = {
        "inven.co.kr": "https://www.inven.co.kr/board/webzine/2097",
        "ruliweb.com": "https://bbs.ruliweb.com/community/board/300143",
        "dcinside.com": "https://gall.dcinside.com/mgallery/board/lists/?id=aoegame",
    }
    
    def __init__(self, config: Optional[CrawlerConfig] = None, parser_registry=None):
        """DirectCrawlAdapter 초기화
        
        Args:
            config: 크롤러 설정
            parser_registry: 파서 레지스트리 (사이트별 파싱용)
        """
        self._config = config or CrawlerConfig()
        self._parser_registry = parser_registry
        self._last_error: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "DirectCrawl"
    
    def is_available(self) -> bool:
        """항상 사용 가능 (외부 API 의존 없음)"""
        return True
    
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        """사이트 게시판 직접 크롤링
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
            
        Raises:
            RuntimeError: 크롤링 실패 시
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            raise RuntimeError("requests, beautifulsoup4 라이브러리가 필요합니다.")
        
        board_url = self.BOARD_URLS.get(site)
        if not board_url:
            logger.warning(f"지원하지 않는 사이트: {site}")
            return []
        
        logger.info(f"직접 크롤링: {board_url}")
        
        results: List[SearchResult] = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(board_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 사이트별 게시글 목록 파싱
            posts = self._parse_board_list(soup, site, board_url)
            
            # 키워드 필터링
            keyword_lower = [kw.lower() for kw in keywords]
            for post in posts:
                title_lower = post["title"].lower()
                # 키워드 중 하나라도 포함되면 결과에 추가
                if any(kw in title_lower for kw in keyword_lower):
                    result = SearchResult(
                        url=post["url"],
                        title=post["title"],
                        snippet="",  # 직접 크롤링은 snippet 없음
                        relevance_score=0.0
                    )
                    results.append(result)
                    
                    if len(results) >= max_results:
                        break
            
            logger.info(f"직접 크롤링 완료: {len(results)}개 결과")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"직접 크롤링 실패: {error_msg}")
            self._last_error = error_msg
            raise RuntimeError(f"직접 크롤링 실패: {error_msg}")
        
        return results
    
    def _parse_board_list(self, soup, site: str, base_url: str) -> List[dict]:
        """게시판 목록 파싱
        
        Args:
            soup: BeautifulSoup 객체
            site: 사이트 도메인
            base_url: 기본 URL
            
        Returns:
            게시글 정보 목록 [{url, title}, ...]
        """
        posts = []
        
        if "inven.co.kr" in site:
            # 인벤 게시판 파싱
            for item in soup.select("tr.ls-table-body"):
                title_elem = item.select_one("td.tit a")
                if title_elem:
                    href = title_elem.get("href", "")
                    if not href.startswith("http"):
                        href = f"https://www.inven.co.kr{href}"
                    posts.append({
                        "url": href,
                        "title": title_elem.get_text(strip=True)
                    })
                    
        elif "ruliweb.com" in site:
            # 루리웹 게시판 파싱
            for item in soup.select("tr.table_body"):
                title_elem = item.select_one("td.subject a.deco")
                if title_elem:
                    href = title_elem.get("href", "")
                    if not href.startswith("http"):
                        href = f"https://bbs.ruliweb.com{href}"
                    posts.append({
                        "url": href,
                        "title": title_elem.get_text(strip=True)
                    })
                    
        elif "dcinside.com" in site:
            # 디시인사이드 게시판 파싱
            for item in soup.select("tr.ub-content"):
                title_elem = item.select_one("td.gall_tit a")
                if title_elem:
                    href = title_elem.get("href", "")
                    if not href.startswith("http"):
                        href = f"https://gall.dcinside.com{href}"
                    posts.append({
                        "url": href,
                        "title": title_elem.get_text(strip=True)
                    })
        
        return posts
