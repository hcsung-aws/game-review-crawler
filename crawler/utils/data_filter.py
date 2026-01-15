"""
Data filtering utility

Requirements: 1.3, 4.3, 5.4, 5.5
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Any
from enum import Enum


class SortField(Enum):
    VIEW_COUNT = "view_count"
    COMMENT_COUNT = "comment_count"
    CREATED_AT = "created_at"
    LIKE_COUNT = "like_count"
    SENTIMENT_SCORE = "sentiment_score"


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class SentimentFilter(Enum):
    ALL = "all"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class IssueTypeFilter(Enum):
    ALL = "all"
    BUG = "bug"
    HOT = "hot"
    NORMAL = "normal"


@dataclass
class FilterCriteria:
    game_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sites: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    min_view_count: Optional[int] = None
    min_comment_count: Optional[int] = None
    sentiment_filter: SentimentFilter = SentimentFilter.ALL
    sentiment_min: Optional[float] = None
    sentiment_max: Optional[float] = None
    issue_type_filter: IssueTypeFilter = IssueTypeFilter.ALL

class DataFilter:
    def __init__(self):
        pass
    
    def filter_by_game(self, posts: List[Any], game_ids: List[str]) -> List[Any]:
        if not game_ids:
            return posts
        game_ids_lower = [g.lower() for g in game_ids]
        result = []
        for post in posts:
            keyword = getattr(post, 'keyword', '') or ''
            title = getattr(post, 'title', '') or ''
            body = getattr(post, 'body', '') or ''
            if keyword.lower() in game_ids_lower:
                result.append(post)
            elif any(g in title.lower() for g in game_ids_lower):
                result.append(post)
            elif any(g in body.lower() for g in game_ids_lower):
                result.append(post)
        return result
    
    def filter_by_date_range(self, posts: List[Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Any]:
        if start_date is None and end_date is None:
            return posts
        result = []
        for post in posts:
            created_at = getattr(post, 'created_at', None)
            if created_at is None:
                continue
            if start_date is not None and created_at < start_date:
                continue
            if end_date is not None and created_at > end_date:
                continue
            result.append(post)
        return result
    
    def filter_by_site(self, posts: List[Any], sites: List[str]) -> List[Any]:
        if not sites:
            return posts
        sites_lower = [s.lower() for s in sites]
        result = []
        for post in posts:
            site = getattr(post, 'site', '') or ''
            if site.lower() in sites_lower:
                result.append(post)
        return result
    
    def filter_by_min_view_count(self, posts: List[Any], min_count: int) -> List[Any]:
        result = []
        for post in posts:
            view_count = getattr(post, 'view_count', 0) or 0
            if view_count >= min_count:
                result.append(post)
        return result
    
    def filter_by_min_comment_count(self, posts: List[Any], min_count: int) -> List[Any]:
        result = []
        for post in posts:
            comments = getattr(post, 'comments', []) or []
            if len(comments) >= min_count:
                result.append(post)
        return result

    def sort_posts(self, posts: List[Any], field: SortField, order: SortOrder = SortOrder.DESC) -> List[Any]:
        if not posts:
            return posts
        reverse = (order == SortOrder.DESC)
        def get_sort_key(post):
            if field == SortField.VIEW_COUNT:
                return getattr(post, 'view_count', 0) or 0
            elif field == SortField.COMMENT_COUNT:
                comments = getattr(post, 'comments', []) or []
                return len(comments)
            elif field == SortField.CREATED_AT:
                return getattr(post, 'created_at', None) or datetime.min
            elif field == SortField.LIKE_COUNT:
                return getattr(post, 'like_count', 0) or 0
            return 0
        return sorted(posts, key=get_sort_key, reverse=reverse)
    
    def apply_filters(self, posts: List[Any], criteria: FilterCriteria) -> List[Any]:
        result = posts
        if criteria.game_id:
            result = self.filter_by_game(result, [criteria.game_id])
        if criteria.start_date or criteria.end_date:
            result = self.filter_by_date_range(result, criteria.start_date, criteria.end_date)
        if criteria.sites:
            result = self.filter_by_site(result, criteria.sites)
        if criteria.keywords:
            result = self.filter_by_game(result, criteria.keywords)
        if criteria.min_view_count is not None:
            result = self.filter_by_min_view_count(result, criteria.min_view_count)
        if criteria.min_comment_count is not None:
            result = self.filter_by_min_comment_count(result, criteria.min_comment_count)
        return result
    
    def filter_negative_posts(self, posts_with_sentiment: List[Tuple[Any, Any]], threshold: float = -0.3) -> List[Tuple[Any, Any]]:
        result = []
        for post, sentiment in posts_with_sentiment:
            score = getattr(sentiment, 'score', 0)
            if score < threshold:
                result.append((post, sentiment))
        return result
    
    def sort_by_sentiment(self, posts_with_sentiment: List[Tuple[Any, Any]], order: SortOrder = SortOrder.DESC) -> List[Tuple[Any, Any]]:
        if not posts_with_sentiment:
            return posts_with_sentiment
        reverse = (order == SortOrder.DESC)
        def get_score(item):
            _, sentiment = item
            return getattr(sentiment, 'score', 0)
        return sorted(posts_with_sentiment, key=get_score, reverse=reverse)

    def filter_by_sentiment(self, posts_with_sentiment: List[Tuple[Any, Any]], sentiment_filter: SentimentFilter = SentimentFilter.ALL, min_score: Optional[float] = None, max_score: Optional[float] = None) -> List[Tuple[Any, Any]]:
        if not posts_with_sentiment:
            return posts_with_sentiment
        result = []
        for post, sentiment in posts_with_sentiment:
            score = getattr(sentiment, 'score', 0.0)
            label = getattr(sentiment, 'label', 'neutral')
            if hasattr(label, 'value'):
                label = label.value
            label = str(label).lower()
            if sentiment_filter != SentimentFilter.ALL:
                if sentiment_filter == SentimentFilter.POSITIVE and label != 'positive':
                    continue
                elif sentiment_filter == SentimentFilter.NEGATIVE and label != 'negative':
                    continue
                elif sentiment_filter == SentimentFilter.NEUTRAL and label != 'neutral':
                    continue
            if min_score is not None and score < min_score:
                continue
            if max_score is not None and score > max_score:
                continue
            result.append((post, sentiment))
        return result
    
    def filter_by_issue_type(self, posts_with_analysis: List[Tuple[Any, Any]], issue_type_filter: IssueTypeFilter = IssueTypeFilter.ALL) -> List[Tuple[Any, Any]]:
        if not posts_with_analysis:
            return posts_with_analysis
        if issue_type_filter == IssueTypeFilter.ALL:
            return posts_with_analysis
        result = []
        for post, analysis in posts_with_analysis:
            issue_type = getattr(analysis, 'issue_type', None)
            is_bug = getattr(analysis, 'is_bug', False)
            is_hot = getattr(analysis, 'is_hot', False)
            if issue_type_filter == IssueTypeFilter.BUG:
                if issue_type == 'bug' or is_bug:
                    result.append((post, analysis))
            elif issue_type_filter == IssueTypeFilter.HOT:
                if issue_type == 'hot' or is_hot:
                    result.append((post, analysis))
            elif issue_type_filter == IssueTypeFilter.NORMAL:
                if issue_type is not None:
                    if issue_type == 'normal':
                        result.append((post, analysis))
                else:
                    if not is_bug and not is_hot:
                        result.append((post, analysis))
        return result

    def apply_filters_with_analysis(self, posts_with_analysis: List[Tuple[Any, Any]], criteria: FilterCriteria) -> List[Tuple[Any, Any]]:
        if not posts_with_analysis:
            return posts_with_analysis
        posts = [post for post, _ in posts_with_analysis]
        analysis_map = {id(post): analysis for post, analysis in posts_with_analysis}
        filtered_posts = self.apply_filters(posts, criteria)
        result = [(post, analysis_map[id(post)]) for post in filtered_posts if id(post) in analysis_map]
        if criteria.sentiment_filter != SentimentFilter.ALL or criteria.sentiment_min is not None or criteria.sentiment_max is not None:
            result = self.filter_by_sentiment(result, criteria.sentiment_filter, criteria.sentiment_min, criteria.sentiment_max)
        if criteria.issue_type_filter != IssueTypeFilter.ALL:
            result = self.filter_by_issue_type(result, criteria.issue_type_filter)
        return result
