"""
Unit Tests for Data Models

Requirements: 1.2, 2.2
- PostContent 객체 생성 및 필드 검증
- Comment 객체 생성 및 필드 검증
"""

import pytest
from datetime import datetime
from crawler.models.data_models import Comment, PostContent, SearchResult, CrawlerConfig


class TestComment:
    """Comment 데이터 모델 유닛 테스트"""
    
    def test_comment_creation_with_required_fields(self):
        """필수 필드만으로 Comment 생성"""
        comment = Comment(author="테스터", content="테스트 댓글입니다")
        
        assert comment.author == "테스터"
        assert comment.content == "테스트 댓글입니다"
        assert comment.created_at is None
        assert comment.like_count == 0
    
    def test_comment_creation_with_all_fields(self):
        """모든 필드로 Comment 생성"""
        created = datetime(2024, 1, 15, 10, 30, 0)
        comment = Comment(
            author="작성자",
            content="전체 필드 테스트",
            created_at=created,
            like_count=42
        )
        
        assert comment.author == "작성자"
        assert comment.content == "전체 필드 테스트"
        assert comment.created_at == created
        assert comment.like_count == 42


class TestPostContent:
    """PostContent 데이터 모델 유닛 테스트"""
    
    def test_post_creation_with_required_fields(self):
        """필수 필드만으로 PostContent 생성"""
        post = PostContent(
            url="https://example.com/post/1",
            title="테스트 게시글",
            body="게시글 본문입니다",
            site="example.com",
            keyword="테스트"
        )
        
        assert post.url == "https://example.com/post/1"
        assert post.title == "테스트 게시글"
        assert post.body == "게시글 본문입니다"
        assert post.site == "example.com"
        assert post.keyword == "테스트"
        assert post.author is None
        assert post.created_at is None
        assert post.view_count == 0
        assert post.like_count == 0
        assert post.comments == []
    
    def test_post_creation_with_all_fields(self):
        """모든 필드로 PostContent 생성"""
        created = datetime(2024, 1, 15, 10, 30, 0)
        comments = [
            Comment(author="댓글러1", content="첫 번째 댓글"),
            Comment(author="댓글러2", content="두 번째 댓글")
        ]
        
        post = PostContent(
            url="https://example.com/post/1",
            title="전체 필드 테스트",
            body="게시글 본문",
            site="example.com",
            keyword="테스트",
            author="게시자",
            created_at=created,
            view_count=1000,
            like_count=50,
            comments=comments
        )
        
        assert post.author == "게시자"
        assert post.created_at == created
        assert post.view_count == 1000
        assert post.like_count == 50
        assert len(post.comments) == 2
        assert post.comments[0].author == "댓글러1"
    
    def test_post_with_empty_comments(self):
        """댓글이 없는 게시글 (Requirements 2.4)"""
        post = PostContent(
            url="https://example.com/post/2",
            title="댓글 없는 게시글",
            body="본문",
            site="example.com",
            keyword="테스트"
        )
        
        assert post.comments == []
        assert isinstance(post.comments, list)


class TestSearchResult:
    """SearchResult 데이터 모델 유닛 테스트"""
    
    def test_search_result_creation(self):
        """SearchResult 생성 테스트"""
        result = SearchResult(
            url="https://example.com/search/1",
            title="검색 결과",
            snippet="검색 결과 요약",
            relevance_score=0.85
        )
        
        assert result.url == "https://example.com/search/1"
        assert result.title == "검색 결과"
        assert result.snippet == "검색 결과 요약"
        assert result.relevance_score == 0.85
    
    def test_search_result_default_score(self):
        """기본 관련성 점수 테스트"""
        result = SearchResult(
            url="https://example.com",
            title="제목",
            snippet="요약"
        )
        
        assert result.relevance_score == 0.0


class TestCrawlerConfig:
    """CrawlerConfig 데이터 모델 유닛 테스트"""
    
    def test_config_default_values(self):
        """기본값 테스트"""
        config = CrawlerConfig()
        
        assert config.output_dir == "data"
        assert config.default_delay == 3.0
        assert config.max_retries == 3
        assert config.relevance_threshold == 0.5
        assert config.max_comment_pages == 3
        assert config.cache_ttl == 3600
        assert config.jitter_range == (0.5, 2.0)
        assert config.google_api_key is None
        assert config.google_cse_id is None
    
    def test_config_custom_values(self):
        """사용자 정의 값 테스트"""
        config = CrawlerConfig(
            output_dir="custom_data",
            default_delay=5.0,
            max_retries=5,
            relevance_threshold=0.7,
            jitter_range=(1.0, 3.0),
            google_api_key="test_key",
            google_cse_id="test_cse"
        )
        
        assert config.output_dir == "custom_data"
        assert config.default_delay == 5.0
        assert config.max_retries == 5
        assert config.relevance_threshold == 0.7
        assert config.jitter_range == (1.0, 3.0)
        assert config.google_api_key == "test_key"
        assert config.google_cse_id == "test_cse"
