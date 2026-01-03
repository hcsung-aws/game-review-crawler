"""
Property-Based Tests for Data Models

**Feature: community-crawler-enhancement, Property 1: Serialization Round-Trip**
**Validates: Requirements 1.4, 6.4**

For any valid PostContent 객체, JSON으로 직렬화한 후 역직렬화하면 원본과 동일한 객체가 되어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone
from typing import List, Optional

from crawler.models.data_models import Comment, PostContent, SearchResult, CrawlerConfig


# Custom strategies for generating test data
@st.composite
def comment_strategy(draw):
    """Comment 객체 생성 전략"""
    author = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    content = draw(st.text(min_size=0, max_size=500))
    # datetime은 JSON 직렬화 가능한 범위로 제한
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
def post_content_strategy(draw):
    """PostContent 객체 생성 전략"""
    url = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    title = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    body = draw(st.text(min_size=0, max_size=2000))
    site = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
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


@st.composite
def search_result_strategy(draw):
    """SearchResult 객체 생성 전략"""
    url = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    title = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    snippet = draw(st.text(min_size=0, max_size=500))
    relevance_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    
    return SearchResult(
        url=url,
        title=title,
        snippet=snippet,
        relevance_score=relevance_score
    )


class TestSerializationRoundTrip:
    """
    **Feature: community-crawler-enhancement, Property 1: Serialization Round-Trip**
    **Validates: Requirements 1.4, 6.4**
    
    For any valid PostContent 객체, JSON으로 직렬화한 후 역직렬화하면 
    원본과 동일한 객체가 되어야 한다.
    """
    
    @given(comment=comment_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comment_round_trip(self, comment: Comment):
        """Comment 객체의 직렬화 round-trip 테스트"""
        # Serialize to dict and back
        serialized = comment.to_dict()
        deserialized = Comment.from_dict(serialized)
        
        assert deserialized.author == comment.author
        assert deserialized.content == comment.content
        assert deserialized.created_at == comment.created_at
        assert deserialized.like_count == comment.like_count
    
    @given(post=post_content_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_content_dict_round_trip(self, post: PostContent):
        """PostContent 객체의 dict 직렬화 round-trip 테스트"""
        # Serialize to dict and back
        serialized = post.to_dict()
        deserialized = PostContent.from_dict(serialized)
        
        assert deserialized.url == post.url
        assert deserialized.title == post.title
        assert deserialized.body == post.body
        assert deserialized.site == post.site
        assert deserialized.keyword == post.keyword
        assert deserialized.author == post.author
        assert deserialized.created_at == post.created_at
        assert deserialized.view_count == post.view_count
        assert deserialized.like_count == post.like_count
        assert len(deserialized.comments) == len(post.comments)
        
        for orig, deser in zip(post.comments, deserialized.comments):
            assert deser.author == orig.author
            assert deser.content == orig.content
            assert deser.created_at == orig.created_at
            assert deser.like_count == orig.like_count
    
    @given(post=post_content_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_content_json_round_trip(self, post: PostContent):
        """PostContent 객체의 JSON 직렬화 round-trip 테스트"""
        # Serialize to JSON and back
        json_str = post.to_json()
        deserialized = PostContent.from_json(json_str)
        
        assert deserialized.url == post.url
        assert deserialized.title == post.title
        assert deserialized.body == post.body
        assert deserialized.site == post.site
        assert deserialized.keyword == post.keyword
        assert deserialized.author == post.author
        assert deserialized.created_at == post.created_at
        assert deserialized.view_count == post.view_count
        assert deserialized.like_count == post.like_count
        assert len(deserialized.comments) == len(post.comments)
    
    @given(result=search_result_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_search_result_round_trip(self, result: SearchResult):
        """SearchResult 객체의 직렬화 round-trip 테스트"""
        # Serialize to dict and back
        serialized = result.to_dict()
        deserialized = SearchResult.from_dict(serialized)
        
        assert deserialized.url == result.url
        assert deserialized.title == result.title
        assert deserialized.snippet == result.snippet
        assert abs(deserialized.relevance_score - result.relevance_score) < 1e-9
