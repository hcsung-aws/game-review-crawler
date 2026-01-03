"""
ContentParser 추상 클래스 및 ParserRegistry 구현

Requirements: 4.1, 4.2
- ContentParser ABC: 사이트별 파서의 기본 인터페이스
- ParserRegistry: 도메인별 파서 등록 및 조회
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from urllib.parse import urlparse

from crawler.models.data_models import PostContent, Comment


class ContentParser(ABC):
    """콘텐츠 파서 추상 클래스
    
    Requirements: 4.1
    - 각 사이트별 맞춤 파서의 기본 인터페이스 정의
    - parse_post: 게시글 파싱
    - parse_comments: 댓글 파싱
    """
    
    @abstractmethod
    def parse_post(self, html: str, url: str, keyword: str = "") -> PostContent:
        """게시글 파싱
        
        Args:
            html: HTML 문자열
            url: 게시글 URL
            keyword: 검색 키워드
            
        Returns:
            PostContent: 파싱된 게시글 데이터
        """
        pass
    
    @abstractmethod
    def parse_comments(self, html: str) -> List[Comment]:
        """댓글 파싱
        
        Args:
            html: HTML 문자열
            
        Returns:
            List[Comment]: 파싱된 댓글 목록
        """
        pass
    
    @abstractmethod
    def get_supported_domains(self) -> List[str]:
        """지원하는 도메인 목록 반환
        
        Returns:
            List[str]: 지원 도메인 목록
        """
        pass


class ParserRegistry:
    """파서 레지스트리
    
    Requirements: 4.1, 4.2
    - 도메인별 파서 등록 및 관리
    - 플러그인 방식으로 파서 등록 가능
    - 등록되지 않은 도메인은 GenericParser 사용
    """
    
    def __init__(self):
        self._parsers: Dict[str, ContentParser] = {}
        self._generic_parser: Optional[ContentParser] = None
    
    def register(self, parser: ContentParser) -> None:
        """파서 등록
        
        Requirements: 4.2
        - 플러그인 방식으로 파서 등록
        
        Args:
            parser: 등록할 파서 인스턴스
        """
        for domain in parser.get_supported_domains():
            self._parsers[domain.lower()] = parser
    
    def set_generic_parser(self, parser: ContentParser) -> None:
        """범용 파서 설정
        
        Requirements: 4.3
        - 등록되지 않은 사이트용 기본 파서
        
        Args:
            parser: GenericParser 인스턴스
        """
        self._generic_parser = parser
    
    def get_parser(self, url: str) -> Optional[ContentParser]:
        """URL에 맞는 파서 반환
        
        Requirements: 4.1, 4.3
        - 도메인에 등록된 파서가 있으면 해당 파서 반환
        - 없으면 GenericParser 반환
        
        Args:
            url: 대상 URL
            
        Returns:
            ContentParser: 해당 도메인의 파서 또는 GenericParser
        """
        domain = self._extract_domain(url)
        
        # 정확한 도메인 매칭
        if domain in self._parsers:
            return self._parsers[domain]
        
        # 서브도메인 포함 매칭 (예: m.inven.co.kr -> inven.co.kr)
        for registered_domain, parser in self._parsers.items():
            if domain.endswith('.' + registered_domain) or domain == registered_domain:
                return parser
        
        # 등록된 파서가 없으면 GenericParser 반환
        return self._generic_parser
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출
        
        Args:
            url: 대상 URL
            
        Returns:
            str: 소문자 도메인
        """
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        return domain.lower()
    
    def get_registered_domains(self) -> List[str]:
        """등록된 도메인 목록 반환
        
        Returns:
            List[str]: 등록된 도메인 목록
        """
        return list(self._parsers.keys())
    
    def has_parser_for(self, url: str) -> bool:
        """해당 URL에 대한 전용 파서 존재 여부
        
        Args:
            url: 대상 URL
            
        Returns:
            bool: 전용 파서 존재 여부 (GenericParser 제외)
        """
        domain = self._extract_domain(url)
        
        if domain in self._parsers:
            return True
        
        for registered_domain in self._parsers.keys():
            if domain.endswith('.' + registered_domain):
                return True
        
        return False
