"""
CrawlerOrchestrator - 크롤링 프로세스 조율자

Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 6.1
- 전체 크롤링 프로세스 조율
- SearchEngineManager, ContentCrawler, DataStore 통합
- 검색 → 크롤링 → 저장 워크플로우 관리
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from crawler.models.data_models import (
    CrawlerConfig, 
    SearchResult, 
    PostContent
)
from crawler.search.manager import SearchEngineManager
from crawler.search.adapters import DuckDuckGoAdapter, GoogleCSEAdapter, DirectCrawlAdapter
from crawler.content_crawler import ContentCrawler
from crawler.exporters.data_store import DataStore
from crawler.exporters.exporters import JSONExporter, CSVExporter, ExporterFactory
from crawler.utils.url_deduplicator import deduplicate_urls


logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """크롤링 결과 데이터 모델
    
    크롤링 작업의 결과를 담는 컨테이너.
    """
    posts: List[PostContent] = field(default_factory=list)
    total_searched: int = 0
    total_crawled: int = 0
    total_failed: int = 0
    keywords_used: List[str] = field(default_factory=list)
    sites_crawled: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """크롤링 소요 시간 (초)"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """크롤링 성공률"""
        if self.total_searched == 0:
            return 0.0
        return self.total_crawled / self.total_searched
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "total_searched": self.total_searched,
            "total_crawled": self.total_crawled,
            "total_failed": self.total_failed,
            "success_rate": self.success_rate,
            "keywords_used": self.keywords_used,
            "sites_crawled": self.sites_crawled,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "posts_count": len(self.posts)
        }


class CrawlerOrchestrator:
    """크롤링 프로세스 조율자
    
    전체 크롤링 워크플로우를 관리하고 조율한다.
    
    Requirements:
    - 1.1: 검색 결과 URL에 접속하여 Post_Content 추출
    - 1.2: 제목, 본문, 작성일, 조회수, 추천수 구조화
    - 2.1: 게시글 파싱 시 Comment_Data 함께 추출
    - 3.1: 검색 결과에 대해 Relevance_Score 계산
    - 4.1: Target_Site에 맞는 Content_Parser 선택
    - 5.1: Rate_Limiter를 통해 최소 3초 간격 유지
    - 6.1: 게시글과 댓글을 관계형 구조로 저장
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """CrawlerOrchestrator 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
        """
        self.config = config or CrawlerConfig()
        
        # 컴포넌트 초기화
        self.search_engine = SearchEngineManager(self.config)
        self.content_crawler = ContentCrawler(self.config)
        self.data_store = DataStore(self.config)
        
        # 기본 검색 어댑터 등록
        self._register_default_adapters()
        
        logger.info("CrawlerOrchestrator 초기화 완료")
    
    def _register_default_adapters(self) -> None:
        """기본 검색 어댑터 등록
        
        Requirements: 7.1
        - DuckDuckGo, Google CSE, 직접 크롤링 어댑터 등록
        """
        # DuckDuckGo 어댑터 (기본)
        self.search_engine.register_adapter(DuckDuckGoAdapter())
        
        # Google CSE 어댑터 (API 키가 있는 경우)
        if self.config.google_api_key and self.config.google_cse_id:
            google_adapter = GoogleCSEAdapter(
                api_key=self.config.google_api_key,
                cse_id=self.config.google_cse_id
            )
            self.search_engine.register_adapter(google_adapter)
        
        # 직접 크롤링 어댑터
        direct_adapter = DirectCrawlAdapter(
            parser_registry=self.content_crawler.parser_registry
        )
        self.search_engine.register_adapter(direct_adapter)
    
    def crawl(
        self, 
        keywords: List[str], 
        sites: List[str],
        max_results_per_site: int = 10,
        save_results: bool = True,
        output_format: str = "json"
    ) -> CrawlResult:
        """크롤링 수행
        
        키워드와 사이트 목록을 받아 전체 크롤링 프로세스를 수행한다.
        
        Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 6.1
        
        Args:
            keywords: 검색 키워드 목록
            sites: 대상 사이트 도메인 목록
            max_results_per_site: 사이트당 최대 검색 결과 수
            save_results: 결과 저장 여부
            output_format: 출력 형식 ("json" 또는 "csv")
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        result = CrawlResult(
            keywords_used=keywords.copy(),
            sites_crawled=sites.copy(),
            started_at=datetime.now()
        )
        
        logger.info(f"크롤링 시작: keywords={keywords}, sites={sites}")
        
        try:
            # 1. 검색 수행
            all_search_results = self._search_all_sites(
                keywords, sites, max_results_per_site
            )
            result.total_searched = len(all_search_results)
            logger.info(f"검색 완료: {result.total_searched}개 결과")
            
            # 2. URL 중복 제거
            unique_urls = deduplicate_urls([r.url for r in all_search_results])
            logger.info(f"중복 제거 후: {len(unique_urls)}개 URL")
            
            # URL과 SearchResult 매핑
            url_to_result = {r.url: r for r in all_search_results}
            
            # 3. 콘텐츠 크롤링
            for url in unique_urls:
                search_result = url_to_result.get(url)
                keyword = keywords[0] if keywords else ""
                
                try:
                    post = self.content_crawler.crawl_post(url, keyword)
                    
                    if post:
                        self.data_store.add_post(post)
                        result.posts.append(post)
                        result.total_crawled += 1
                        logger.debug(f"크롤링 성공: {url}")
                    else:
                        result.total_failed += 1
                        result.errors.append(f"크롤링 실패: {url}")
                        
                except Exception as e:
                    result.total_failed += 1
                    error_msg = f"크롤링 에러: {url} - {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
            
            # 4. 결과 저장
            if save_results and result.posts:
                self._save_results(result.posts, output_format)
            
        except Exception as e:
            error_msg = f"크롤링 프로세스 에러: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        
        result.finished_at = datetime.now()
        
        logger.info(
            f"크롤링 완료: {result.total_crawled}/{result.total_searched} 성공, "
            f"소요시간: {result.duration_seconds:.1f}초"
        )
        
        return result
    
    def _search_all_sites(
        self, 
        keywords: List[str], 
        sites: List[str],
        max_results_per_site: int
    ) -> List[SearchResult]:
        """모든 사이트에서 검색 수행
        
        Args:
            keywords: 검색 키워드 목록
            sites: 대상 사이트 목록
            max_results_per_site: 사이트당 최대 결과 수
            
        Returns:
            검색 결과 목록
        """
        all_results: List[SearchResult] = []
        
        for site in sites:
            try:
                results = self.search_engine.search(
                    keywords=keywords,
                    site=site,
                    max_results=max_results_per_site
                )
                all_results.extend(results)
                logger.info(f"사이트 '{site}' 검색 완료: {len(results)}개 결과")
                
            except Exception as e:
                logger.warning(f"사이트 '{site}' 검색 실패: {e}")
        
        return all_results
    
    def _save_results(
        self, 
        posts: List[PostContent], 
        output_format: str
    ) -> str:
        """결과 저장
        
        Args:
            posts: 저장할 게시글 목록
            output_format: 출력 형식
            
        Returns:
            저장된 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawl_results_{timestamp}"
        filepath = f"{self.config.output_dir}/{filename}"
        
        exporter = ExporterFactory.create(output_format)
        saved_path = exporter.export(posts, filepath)
        
        logger.info(f"결과 저장 완료: {saved_path}")
        return saved_path
    
    def search_only(
        self, 
        keywords: List[str], 
        sites: List[str],
        max_results_per_site: int = 10
    ) -> List[SearchResult]:
        """검색만 수행 (크롤링 없이)
        
        Args:
            keywords: 검색 키워드 목록
            sites: 대상 사이트 목록
            max_results_per_site: 사이트당 최대 결과 수
            
        Returns:
            검색 결과 목록
        """
        return self._search_all_sites(keywords, sites, max_results_per_site)
    
    def crawl_urls(
        self, 
        urls: List[str], 
        keyword: str = "",
        save_results: bool = True,
        output_format: str = "json"
    ) -> CrawlResult:
        """URL 목록 직접 크롤링
        
        검색 없이 URL 목록을 직접 크롤링한다.
        
        Args:
            urls: 크롤링할 URL 목록
            keyword: 검색 키워드
            save_results: 결과 저장 여부
            output_format: 출력 형식
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        result = CrawlResult(
            keywords_used=[keyword] if keyword else [],
            started_at=datetime.now()
        )
        
        # URL 중복 제거
        unique_urls = deduplicate_urls(urls)
        result.total_searched = len(unique_urls)
        
        logger.info(f"URL 직접 크롤링 시작: {len(unique_urls)}개 URL")
        
        for url in unique_urls:
            try:
                post = self.content_crawler.crawl_post(url, keyword)
                
                if post:
                    self.data_store.add_post(post)
                    result.posts.append(post)
                    result.total_crawled += 1
                    
                    # 사이트 목록 업데이트
                    if post.site and post.site not in result.sites_crawled:
                        result.sites_crawled.append(post.site)
                else:
                    result.total_failed += 1
                    result.errors.append(f"크롤링 실패: {url}")
                    
            except Exception as e:
                result.total_failed += 1
                result.errors.append(f"크롤링 에러: {url} - {str(e)}")
        
        # 결과 저장
        if save_results and result.posts:
            self._save_results(result.posts, output_format)
        
        result.finished_at = datetime.now()
        
        logger.info(
            f"URL 크롤링 완료: {result.total_crawled}/{result.total_searched} 성공"
        )
        
        return result
    
    def get_data_store(self) -> DataStore:
        """DataStore 인스턴스 반환"""
        return self.data_store
    
    def get_search_engine(self) -> SearchEngineManager:
        """SearchEngineManager 인스턴스 반환"""
        return self.search_engine
    
    def get_content_crawler(self) -> ContentCrawler:
        """ContentCrawler 인스턴스 반환"""
        return self.content_crawler
    
    def clear_data(self) -> None:
        """저장된 데이터 초기화"""
        self.data_store.clear()
        logger.info("데이터 저장소 초기화 완료")
    
    def clear_cache(self) -> int:
        """검색 캐시 초기화
        
        Returns:
            삭제된 캐시 항목 수
        """
        count = self.search_engine.clear_cache()
        logger.info(f"검색 캐시 초기화 완료: {count}개 항목 삭제")
        return count
    
    def export_results(
        self, 
        output_format: str = "json",
        filename: Optional[str] = None
    ) -> str:
        """현재 저장된 결과 내보내기
        
        Args:
            output_format: 출력 형식 ("json" 또는 "csv")
            filename: 파일명 (없으면 자동 생성)
            
        Returns:
            저장된 파일 경로
        """
        posts = self.data_store.get_posts()
        
        if not posts:
            logger.warning("내보낼 데이터가 없습니다.")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}"
        
        filepath = f"{self.config.output_dir}/{filename}"
        exporter = ExporterFactory.create(output_format)
        saved_path = exporter.export(posts, filepath)
        
        logger.info(f"내보내기 완료: {saved_path}")
        return saved_path
    
    def close(self) -> None:
        """리소스 정리"""
        self.content_crawler.close()
        logger.info("CrawlerOrchestrator 종료")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
