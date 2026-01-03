"""
데이터 모델 정의

Requirements: 1.2, 2.2, 6.1
- PostContent: 게시글 제목, 본문, 작성일, 조회수, 추천수
- Comment: 댓글 작성자, 내용, 작성일, 추천수
- SearchResult: 검색 결과 URL, 제목, snippet, 관련성 점수
- CrawlerConfig: 크롤러 설정
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Tuple
import json


@dataclass
class Comment:
    """댓글 데이터 모델
    
    Requirements: 2.2
    - 댓글 작성자, 내용, 작성일, 추천수 포함
    """
    author: str
    content: str
    created_at: Optional[datetime] = None
    like_count: int = 0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "like_count": self.like_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Comment":
        """딕셔너리에서 객체 생성"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        return cls(
            author=data["author"],
            content=data["content"],
            created_at=created_at,
            like_count=data.get("like_count", 0)
        )


@dataclass
class PostContent:
    """게시글 콘텐츠 데이터 모델
    
    Requirements: 1.2, 6.1
    - 제목, 본문, 작성일, 조회수, 추천수 구조화
    - 게시글과 댓글을 관계형 구조로 저장
    """
    url: str
    title: str
    body: str
    site: str
    keyword: str
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    view_count: int = 0
    like_count: int = 0
    comments: List[Comment] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "url": self.url,
            "title": self.title,
            "body": self.body,
            "site": self.site,
            "keyword": self.keyword,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comments": [c.to_dict() for c in self.comments]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PostContent":
        """딕셔너리에서 객체 생성"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        comments = [Comment.from_dict(c) for c in data.get("comments", [])]
        return cls(
            url=data["url"],
            title=data["title"],
            body=data["body"],
            site=data["site"],
            keyword=data["keyword"],
            author=data.get("author"),
            created_at=created_at,
            view_count=data.get("view_count", 0),
            like_count=data.get("like_count", 0),
            comments=comments
        )
    
    def to_json(self) -> str:
        """JSON 문자열로 직렬화"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "PostContent":
        """JSON 문자열에서 역직렬화"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class SearchResult:
    """검색 결과 데이터 모델
    
    Requirements: 3.1
    - URL, 제목, snippet, 관련성 점수 포함
    """
    url: str
    title: str
    snippet: str
    relevance_score: float = 0.0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        """딕셔너리에서 객체 생성"""
        return cls(
            url=data["url"],
            title=data["title"],
            snippet=data["snippet"],
            relevance_score=data.get("relevance_score", 0.0)
        )


@dataclass
class CrawlerConfig:
    """크롤러 설정 데이터 모델
    
    Requirements: 5.1, 5.4, 7.3, 8.1
    - 기본 지연 시간, 최대 재시도 횟수
    - 관련성 임계값, 최대 댓글 페이지 수
    - 캐시 TTL, Jitter 범위
    - Google API 설정
    """
    output_dir: str = "data"
    default_delay: float = 3.0
    max_retries: int = 3
    relevance_threshold: float = 0.5
    max_comment_pages: int = 3
    cache_ttl: int = 3600
    jitter_range: Tuple[float, float] = (0.5, 2.0)
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "output_dir": self.output_dir,
            "default_delay": self.default_delay,
            "max_retries": self.max_retries,
            "relevance_threshold": self.relevance_threshold,
            "max_comment_pages": self.max_comment_pages,
            "cache_ttl": self.cache_ttl,
            "jitter_range": list(self.jitter_range),
            "google_api_key": self.google_api_key,
            "google_cse_id": self.google_cse_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CrawlerConfig":
        """딕셔너리에서 객체 생성"""
        jitter_range = tuple(data.get("jitter_range", (0.5, 2.0)))
        return cls(
            output_dir=data.get("output_dir", "data"),
            default_delay=data.get("default_delay", 3.0),
            max_retries=data.get("max_retries", 3),
            relevance_threshold=data.get("relevance_threshold", 0.5),
            max_comment_pages=data.get("max_comment_pages", 3),
            cache_ttl=data.get("cache_ttl", 3600),
            jitter_range=jitter_range,
            google_api_key=data.get("google_api_key"),
            google_cse_id=data.get("google_cse_id")
        )
