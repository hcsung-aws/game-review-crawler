"""
Property-Based Tests for Post-Comment Relationship Integrity

**Feature: community-crawler-enhancement, Property 10: Post-Comment Relationship Integrity**
**Validates: Requirements 6.1**

For any 저장된 PostContent에 대해, 해당 게시글의 comments 필드에 있는 모든 Comment는 
해당 게시글에 속한 것이어야 한다.
"""

import pytest
import os
import tempfile
import shutil
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from typing import List

from crawler.models.data_models import Comment, PostContent, CrawlerConfig
from crawler.exporters.data_store import DataStore


# Custom strategies for generating test data
@st.composite
def comment_strategy(draw):
    """Comment 객체 생성 전략"""
    author = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    content = draw(st.text(min_size=0, max_size=500))
    created_at = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    like_count = draw(st.integers(min_value=0, max_value=1000000))
    
    return Comment(
        author=author,
        content=content,
        created_at=created_at,
        like_count=like_count
    )


@st.composite
def post_content_strategy(draw, unique_id: str = ""):
    """PostContent 객체 생성 전략"""
    # UUID를 사용하여 고유한 URL 생성
    import uuid
    base_url = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    url = f"https://example.com/{base_url}/{uuid.uuid4()}"
    title = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    body = draw(st.text(min_size=0, max_size=2000))
    site = draw(st.sampled_from(["inven.co.kr", "ruliweb.com", "dcinside.com", "gamemeca.com"]))
    keyword = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    author = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip())))
    created_at = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    view_count = draw(st.integers(min_value=0, max_value=10000000))
    like_count = draw(st.integers(min_value=0, max_value=1000000))
    comments = draw(st.lists(comment_strategy(), min_size=0, max_size=10))
    
    return PostContent(
        url=url,
        title=title,
        body=body,
        site=site,
        keyword=keyword,
        author=author,
        created_at=created_at,
        view_count=view_count,
        like_count=like_count,
        comments=comments
    )


class TestPostCommentRelationshipIntegrity:
    """
    **Feature: community-crawler-enhancement, Property 10: Post-Comment Relationship Integrity**
    **Validates: Requirements 6.1**
    
    For any 저장된 PostContent에 대해, 해당 게시글의 comments 필드에 있는 모든 Comment는 
    해당 게시글에 속한 것이어야 한다.
    """
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """테스트 전후 임시 디렉토리 설정 및 정리"""
        self.temp_dir = tempfile.mkdtemp()
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_datastore_preserves_post_comment_relationship(self, posts: List[PostContent]):
        """
        DataStore에 저장된 게시글의 댓글은 해당 게시글에 속한 것이어야 한다.
        
        Property: For any 저장된 PostContent에 대해, 해당 게시글의 comments 필드에 있는 
        모든 Comment는 해당 게시글에 속한 것이어야 한다.
        """
        config = CrawlerConfig(output_dir=self.temp_dir)
        store = DataStore(config)
        
        # 게시글 추가
        for post in posts:
            store.add_post(post)
        
        # 저장된 게시글 검증
        stored_posts = store.get_posts()
        
        assert len(stored_posts) == len(posts)
        
        for original, stored in zip(posts, stored_posts):
            # 게시글 기본 정보 일치 확인
            assert stored.url == original.url
            assert stored.title == original.title
            
            # 댓글 수 일치 확인
            assert len(stored.comments) == len(original.comments)
            
            # 각 댓글이 원본과 동일한지 확인 (관계 무결성)
            for orig_comment, stored_comment in zip(original.comments, stored.comments):
                assert stored_comment.author == orig_comment.author
                assert stored_comment.content == orig_comment.content
                assert stored_comment.created_at == orig_comment.created_at
                assert stored_comment.like_count == orig_comment.like_count
    
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=3))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_save_and_load_preserves_post_comment_relationship(self, posts: List[PostContent]):
        """
        파일로 저장 후 로드해도 게시글-댓글 관계가 유지되어야 한다.
        
        Property: 저장 및 로드 후에도 각 게시글의 comments 필드에 있는 
        모든 Comment는 해당 게시글에 속한 것이어야 한다.
        """
        config = CrawlerConfig(output_dir=self.temp_dir)
        store = DataStore(config)
        
        # 게시글 추가
        for post in posts:
            store.add_post(post)
        
        # 날짜별 저장
        saved_files = store.save_by_date("test_posts")
        
        # 새 DataStore에서 로드
        new_store = DataStore(config)
        for filepath in saved_files.values():
            new_store.load_and_add(filepath)
        
        # 로드된 게시글 검증
        loaded_posts = new_store.get_posts()
        
        # 원본 게시글과 로드된 게시글 매칭 (URL 기준)
        original_by_url = {p.url: p for p in posts}
        
        for loaded in loaded_posts:
            assert loaded.url in original_by_url
            original = original_by_url[loaded.url]
            
            # 댓글 수 일치 확인
            assert len(loaded.comments) == len(original.comments)
            
            # 각 댓글이 원본과 동일한지 확인 (관계 무결성)
            for orig_comment, loaded_comment in zip(original.comments, loaded.comments):
                assert loaded_comment.author == orig_comment.author
                assert loaded_comment.content == orig_comment.content
                assert loaded_comment.created_at == orig_comment.created_at
                assert loaded_comment.like_count == orig_comment.like_count
    
    @given(post=post_content_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comments_belong_to_single_post(self, post: PostContent):
        """
        각 댓글은 정확히 하나의 게시글에만 속해야 한다.
        
        Property: 게시글의 comments 필드에 있는 모든 Comment는 
        해당 게시글에만 속하고 다른 게시글에는 속하지 않아야 한다.
        """
        config = CrawlerConfig(output_dir=self.temp_dir)
        store = DataStore(config)
        
        # 게시글 추가
        store.add_post(post)
        
        # 저장된 게시글 가져오기
        stored_posts = store.get_posts()
        assert len(stored_posts) == 1
        
        stored_post = stored_posts[0]
        
        # 댓글이 해당 게시글에만 속하는지 확인
        # (이 테스트에서는 단일 게시글이므로 댓글이 다른 곳에 속할 수 없음)
        assert len(stored_post.comments) == len(post.comments)
        
        # 댓글 내용이 원본과 일치하는지 확인
        for i, comment in enumerate(stored_post.comments):
            original_comment = post.comments[i]
            assert comment.author == original_comment.author
            assert comment.content == original_comment.content
