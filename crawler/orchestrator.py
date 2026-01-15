"""
CrawlerOrchestrator - 크롤링 프로세스 조율자

Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 6.1
- 전체 크롤링 프로세스 조율
- SearchEngineManager, ContentCrawler, DataStore 통합
- 검색 → 크롤링 → 저장 워크플로우 관리
- 게임별 데이터 저장 경로 지원
- 크롤링 후 자동 분석 옵션 지원
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from crawler.models.data_models import (
    CrawlerConfig, 
    SearchResult, 
    PostContent
)
from crawler.models.game_profile import GameProfile, GameProfileManager
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
    game_id: Optional[str] = None  # 게임 ID (게임별 크롤링 시)
    analysis_result: Optional[Any] = None  # 분석 결과 (자동 분석 시)
    
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
        result = {
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
            "posts_count": len(self.posts),
            "game_id": self.game_id
        }
        if self.analysis_result:
            result["analysis_performed"] = True
        return result


class CrawlerOrchestrator:
    """크롤링 프로세스 조율자
    
    전체 크롤링 워크플로우를 관리하고 조율한다.
    
    Requirements:
    - 1.1: 검색 결과 URL에 접속하여 Post_Content 추출, 게임별 데이터 저장 경로 지원
    - 1.2: 제목, 본문, 작성일, 조회수, 추천수 구조화
    - 2.1: 게시글 파싱 시 Comment_Data 함께 추출
    - 3.1: 검색 결과에 대해 Relevance_Score 계산
    - 4.1: Target_Site에 맞는 Content_Parser 선택
    - 5.1: Rate_Limiter를 통해 최소 3초 간격 유지
    - 6.1: 게시글과 댓글을 관계형 구조로 저장
    """
    
    def __init__(
        self, 
        config: Optional[CrawlerConfig] = None,
        profile_manager: Optional[GameProfileManager] = None
    ):
        """CrawlerOrchestrator 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
            profile_manager: 게임 프로필 관리자. None이면 새로 생성
        """
        self.config = config or CrawlerConfig()
        
        # 게임 프로필 관리자
        self.profile_manager = profile_manager or GameProfileManager()
        
        # 컴포넌트 초기화
        self.search_engine = SearchEngineManager(self.config)
        self.content_crawler = ContentCrawler(self.config)
        self.data_store = DataStore(self.config)
        
        # GameAnalyzer는 필요 시 lazy 초기화
        self._game_analyzer = None
        
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
    
    def _get_game_analyzer(self):
        """GameAnalyzer 인스턴스 반환 (lazy 초기화)
        
        Returns:
            GameAnalyzer 인스턴스
        """
        if self._game_analyzer is None:
            from crawler.analysis.game_analyzer import GameAnalyzer
            self._game_analyzer = GameAnalyzer(
                profile_manager=self.profile_manager
            )
        return self._game_analyzer
    
    def crawl(
        self, 
        keywords: List[str], 
        sites: List[str],
        max_results_per_site: int = 10,
        save_results: bool = True,
        output_format: str = "json",
        game_id: Optional[str] = None,
        auto_analyze: bool = False
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
            game_id: 게임 ID (게임별 저장 경로 사용 시)
            auto_analyze: 크롤링 후 자동 분석 수행 여부
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        result = CrawlResult(
            keywords_used=keywords.copy(),
            sites_crawled=sites.copy(),
            started_at=datetime.now(),
            game_id=game_id
        )
        
        logger.info(f"크롤링 시작: keywords={keywords}, sites={sites}, game_id={game_id}")
        
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
            
            # 4. 결과 저장 (게임별 경로 지원)
            if save_results and result.posts:
                self._save_results(result.posts, output_format, game_id)
            
            # 5. 자동 분석 수행
            if auto_analyze and result.posts and game_id:
                logger.info(f"자동 분석 수행 중: game_id={game_id}")
                analyzer = self._get_game_analyzer()
                analysis_result = analyzer.analyze(
                    game_id=game_id,
                    posts=result.posts,
                    save_result=True
                )
                result.analysis_result = analysis_result
                logger.info(f"자동 분석 완료: 이슈 {len(analysis_result.issues)}개 탐지")
            
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
        output_format: str,
        game_id: Optional[str] = None
    ) -> str:
        """결과 저장
        
        Requirements: 1.1
        - 게임별로 별도의 데이터 디렉토리에 결과를 저장
        
        Args:
            posts: 저장할 게시글 목록
            output_format: 출력 형식
            game_id: 게임 ID (게임별 저장 경로 사용 시)
            
        Returns:
            저장된 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawl_results_{timestamp}"
        
        # 게임별 저장 경로 결정
        if game_id:
            output_dir = self.profile_manager.get_data_path(game_id)
            # 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = self.config.output_dir
        
        filepath = f"{output_dir}/{filename}"
        
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
    
    def crawl_game(
        self,
        profile: GameProfile,
        max_results_per_site: int = 10,
        save_results: bool = True,
        output_format: str = "json",
        auto_analyze: bool = True
    ) -> CrawlResult:
        """게임 프로필 기반 크롤링
        
        Requirements: 1.1
        - 게임 프로필의 키워드와 대상 사이트를 사용하여 크롤링
        - 게임별 데이터 저장 경로 적용
        
        Args:
            profile: 게임 프로필
            max_results_per_site: 사이트당 최대 검색 결과 수
            save_results: 결과 저장 여부
            output_format: 출력 형식
            auto_analyze: 크롤링 후 자동 분석 수행 여부
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        # 프로필 등록 (아직 등록되지 않은 경우)
        if not self.profile_manager.get_profile(profile.game_id):
            self.profile_manager.register_game(profile)
        
        # 디렉토리 생성
        self.profile_manager.ensure_directories(profile.game_id)
        
        logger.info(f"게임 '{profile.game_name}' 크롤링 시작")
        
        return self.crawl(
            keywords=profile.keywords,
            sites=profile.target_sites,
            max_results_per_site=max_results_per_site,
            save_results=save_results,
            output_format=output_format,
            game_id=profile.game_id,
            auto_analyze=auto_analyze
        )
    
    def crawl_game_by_id(
        self,
        game_id: str,
        max_results_per_site: int = 10,
        save_results: bool = True,
        output_format: str = "json",
        auto_analyze: bool = True
    ) -> Optional[CrawlResult]:
        """게임 ID로 크롤링
        
        Requirements: 1.1
        - 등록된 게임 프로필을 사용하여 크롤링
        
        Args:
            game_id: 게임 ID
            max_results_per_site: 사이트당 최대 검색 결과 수
            save_results: 결과 저장 여부
            output_format: 출력 형식
            auto_analyze: 크롤링 후 자동 분석 수행 여부
            
        Returns:
            CrawlResult: 크롤링 결과 또는 None (프로필이 없는 경우)
        """
        profile = self.profile_manager.get_profile(game_id)
        
        if not profile:
            logger.error(f"게임 프로필을 찾을 수 없습니다: {game_id}")
            return None
        
        return self.crawl_game(
            profile=profile,
            max_results_per_site=max_results_per_site,
            save_results=save_results,
            output_format=output_format,
            auto_analyze=auto_analyze
        )
    
    def register_game(self, profile: GameProfile) -> None:
        """게임 프로필 등록
        
        Args:
            profile: 등록할 게임 프로필
        """
        self.profile_manager.register_game(profile)
        self.profile_manager.ensure_directories(profile.game_id)
        logger.info(f"게임 프로필 등록 완료: {profile.game_name} ({profile.game_id})")
    
    def get_game_profile(self, game_id: str) -> Optional[GameProfile]:
        """게임 프로필 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            게임 프로필 또는 None
        """
        return self.profile_manager.get_profile(game_id)
    
    def list_games(self) -> List[GameProfile]:
        """등록된 게임 목록 조회
        
        Returns:
            게임 프로필 목록
        """
        return self.profile_manager.list_games()
    
    def get_game_analyzer(self):
        """GameAnalyzer 인스턴스 반환
        
        Returns:
            GameAnalyzer 인스턴스
        """
        return self._get_game_analyzer()
    
    def analyze_game(
        self,
        game_id: str,
        posts: Optional[List[PostContent]] = None
    ) -> Optional[Any]:
        """게임 데이터 분석
        
        Requirements: 2.1, 3.1, 4.1
        - 게임 데이터에 대해 감성 분석, 이슈 탐지, 트렌드 분석 수행
        
        Args:
            game_id: 게임 ID
            posts: 분석할 게시글 목록 (None이면 저장된 데이터 사용)
            
        Returns:
            GameAnalysisResult 또는 None
        """
        if posts is None:
            posts = self.data_store.get_posts()
        
        if not posts:
            logger.warning(f"분석할 데이터가 없습니다: {game_id}")
            return None
        
        analyzer = self._get_game_analyzer()
        return analyzer.analyze(game_id=game_id, posts=posts, save_result=True)
    
    def close(self) -> None:
        """리소스 정리"""
        self.content_crawler.close()
        logger.info("CrawlerOrchestrator 종료")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
