"""
데이터 필터링 유틸리티

Requirements: 1.3, 4.3, 5.4, 5.5
- 게임별 데이터 필터링
- 기간, 사이트 필터링
- 조회수, 댓글수, 감성 점수 정렬
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Any
from enum import Enum


class SortField(Enum):
    """정렬 필드"""
    VIEW_COUNT = "view_count"
    COMMENT_COUNT = "comment_count"
    CREATED_AT = "created_at"
    LIKE_COUNT = "like_count"


class SortOrder(Enum):
    """정렬 순서"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class FilterCriteria:
    """필터 조건
    
    Requirements: 5.5
    - 기간, 사이트, 감성, 이슈 유형으로 필터링 지원
    """
    game_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sites: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    min_view_count: Optional[int] = None
    min_comment_count: Optional[int] = None


class DataFilter:
    """데이터 필터링 클래스
    
    Requirements: 1.3, 4.3, 5.4, 5.5
    - 게임별 데이터 필터링
    - 기간, 사이트 필터링
    - 조회수, 댓글수 정렬
    """
    
    def __init__(self):
        pass
    
    def filter_by_game(self, posts: List[Any], game_keywords: List[str]) -> List[Any]:
        """게임별 데이터 필터링
        
        Requirements: 1.3
        - 특정 게임을 선택하면 해당 게임의 데이터만 필터링하여 표시
        """
        if not game_keywords:
            return posts
        
        result = []
        keywords_lower = [kw.lower() for kw in game_keywords]
        
        for post in posts:
            # keyword 필드가 게임 키워드와 일치하는지 확인
            if post.keyword and post.keyword.lower() in keywords_lower:
                result.append(post)
                continue
            
            # 제목이나 본문에 게임 키워드가 포함되어 있는지 확인
            title_lower = post.title.lower() if post.title else ""
            body_lower = post.body.lower() if post.body else ""
            
            for kw in keywords_lower:
                if kw in title_lower or kw in body_lower:
                    result.append(post)
                    break
        
        return result
    
    def filter_by_date_range(self, posts: List[Any], 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[Any]:
        """기간별 데이터 필터링
        
        Requirements: 4.3
        """
        if start_date is None and end_date is None:
            return posts
        
        result = []
        for post in posts:
            if post.created_at is None:
                continue
            
            if start_date is not None and post.created_at < start_date:
                continue
            
            if end_date is not None and post.created_at > end_date:
                continue
            
            result.append(post)
        
        return result
    
    def filter_by_site(self, posts: List[Any], 
                       sites: List[str]) -> List[Any]:
        """사이트별 데이터 필터링
        
        Requirements: 5.5
        """
        if not sites:
            return posts
        
        sites_lower = [s.lower() for s in sites]
        return [post for post in posts if post.site and post.site.lower() in sites_lower]
    
    def filter_by_keyword(self, posts: List[Any],
                          keywords: List[str]) -> List[Any]:
        """키워드별 데이터 필터링"""
        if not keywords:
            return posts
        
        keywords_lower = [kw.lower() for kw in keywords]
        return [post for post in posts if post.keyword and post.keyword.lower() in keywords_lower]
    
    def filter_by_view_count(self, posts: List[Any],
                             min_count: int) -> List[Any]:
        """최소 조회수 필터링"""
        return [post for post in posts if post.view_count >= min_count]
    
    def filter_by_comment_count(self, posts: List[Any],
                                min_count: int) -> List[Any]:
        """최소 댓글수 필터링"""
        return [post for post in posts if len(post.comments) >= min_count]
    
    def apply_filters(self, posts: List[Any],
                      criteria: FilterCriteria) -> List[Any]:
        """복합 필터 적용
        
        Requirements: 5.5
        """
        result = posts
        
        if criteria.start_date is not None or criteria.end_date is not None:
            result = self.filter_by_date_range(result, criteria.start_date, criteria.end_date)
        
        if criteria.sites:
            result = self.filter_by_site(result, criteria.sites)
        
        if criteria.keywords:
            result = self.filter_by_keyword(result, criteria.keywords)
        
        if criteria.min_view_count is not None:
            result = self.filter_by_view_count(result, criteria.min_view_count)
        
        if criteria.min_comment_count is not None:
            result = self.filter_by_comment_count(result, criteria.min_comment_count)
        
        return result
    
    def sort_posts(self, posts: List[Any],
                   sort_field: SortField,
                   sort_order: SortOrder = SortOrder.DESC) -> List[Any]:
        """게시글 정렬
        
        Requirements: 5.4
        """
        reverse = sort_order == SortOrder.DESC
        
        if sort_field == SortField.VIEW_COUNT:
            return sorted(posts, key=lambda p: p.view_count, reverse=reverse)
        elif sort_field == SortField.COMMENT_COUNT:
            return sorted(posts, key=lambda p: len(p.comments), reverse=reverse)
        elif sort_field == SortField.CREATED_AT:
            return sorted(posts, key=lambda p: p.created_at or datetime.min, reverse=reverse)
        elif sort_field == SortField.LIKE_COUNT:
            return sorted(posts, key=lambda p: p.like_count, reverse=reverse)
        else:
            return posts
    
    def sort_by_sentiment(self, posts_with_sentiment: List[Tuple[Any, Any]],
                          sort_order: SortOrder = SortOrder.DESC) -> List[Tuple[Any, Any]]:
        """감성 점수로 정렬
        
        Requirements: 5.4
        """
        reverse = sort_order == SortOrder.DESC
        return sorted(posts_with_sentiment, key=lambda x: x[1].score, reverse=reverse)
    
    def filter_negative_posts(self, posts_with_sentiment: List[Tuple[Any, Any]],
                              threshold: float = -0.3) -> List[Tuple[Any, Any]]:
        """부정적 게시글 필터링
        
        Requirements: 2.4
        """
        return [item for item in posts_with_sentiment if item[1].score < threshold]
    
    def filter_by_sentiment_label(self, posts_with_sentiment: List[Tuple[Any, Any]],
                                  label: Any) -> List[Tuple[Any, Any]]:
        """감성 레이블로 필터링"""
        return [item for item in posts_with_sentiment if item[1].label == label]
