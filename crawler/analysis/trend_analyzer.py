"""
트렌드 분석 모듈

Requirements: 4.1, 4.3, 4.4
- 감성 점수 시계열 분석
- 이슈 언급 빈도 추이 분석
- 부정적 감성 급증 탐지
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from crawler.models.analysis_models import TrendPoint, TrendData, DetectedIssue, SentimentResult
from crawler.models.data_models import PostContent
from crawler.analysis.sentiment import SentimentAnalyzer


class TrendAnalyzer:
    """트렌드 분석기"""
    
    def __init__(self, sentiment_analyzer: Optional[SentimentAnalyzer] = None):
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
    
    def _get_date_key(self, dt: datetime, period: str) -> datetime:
        if period == "weekly":
            days_since_monday = dt.weekday()
            week_start = dt - timedelta(days=days_since_monday)
            return datetime(week_start.year, week_start.month, week_start.day)
        else:
            return datetime(dt.year, dt.month, dt.day)
    
    def _filter_by_date_range(
        self, 
        posts: List[PostContent],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PostContent]:
        filtered = []
        for post in posts:
            if post.created_at is None:
                continue
            post_date = post.created_at
            if start_date is not None:
                start_normalized = datetime(start_date.year, start_date.month, start_date.day)
                if post_date < start_normalized:
                    continue
            if end_date is not None:
                end_normalized = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
                if post_date > end_normalized:
                    continue
            filtered.append(post)
        return filtered
    
    def analyze_sentiment_trend(
        self, 
        posts: List[PostContent],
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TrendData:
        filtered_posts = self._filter_by_date_range(posts, start_date, end_date)
        date_scores: Dict[datetime, List[float]] = defaultdict(list)
        for post in filtered_posts:
            if post.created_at is None:
                continue
            date_key = self._get_date_key(post.created_at, period)
            sentiment_result = self.sentiment_analyzer.analyze_post(post)
            date_scores[date_key].append(sentiment_result.score)
        data_points = []
        for date_key in sorted(date_scores.keys()):
            scores = date_scores[date_key]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            data_points.append(TrendPoint(date=date_key, value=avg_score, count=len(scores)))
        return TrendData(metric_name="sentiment", period=period, data_points=data_points)
    
    def analyze_issue_trend(
        self, 
        posts: List[PostContent],
        issue: DetectedIssue,
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TrendData:
        filtered_posts = self._filter_by_date_range(posts, start_date, end_date)
        keywords = issue.cluster.keywords if issue.cluster else []
        if not keywords:
            keywords = [issue.title]
        date_mentions: Dict[datetime, int] = defaultdict(int)
        for post in filtered_posts:
            if post.created_at is None:
                continue
            text = f"{post.title} {post.body}".lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    date_key = self._get_date_key(post.created_at, period)
                    date_mentions[date_key] += 1
                    break
        data_points = []
        for date_key in sorted(date_mentions.keys()):
            count = date_mentions[date_key]
            data_points.append(TrendPoint(date=date_key, value=float(count), count=count))
        return TrendData(metric_name=f"issue_{issue.issue_id}", period=period, data_points=data_points)
    
    def analyze_keyword_trend(
        self,
        posts: List[PostContent],
        keyword: str,
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TrendData:
        filtered_posts = self._filter_by_date_range(posts, start_date, end_date)
        date_mentions: Dict[datetime, int] = defaultdict(int)
        keyword_lower = keyword.lower()
        for post in filtered_posts:
            if post.created_at is None:
                continue
            text = f"{post.title} {post.body}".lower()
            if keyword_lower in text:
                date_key = self._get_date_key(post.created_at, period)
                date_mentions[date_key] += 1
        data_points = []
        for date_key in sorted(date_mentions.keys()):
            count = date_mentions[date_key]
            data_points.append(TrendPoint(date=date_key, value=float(count), count=count))
        return TrendData(metric_name=f"keyword_{keyword}", period=period, data_points=data_points)
    
    def detect_sentiment_spike(self, trend: TrendData, threshold: float = -0.3) -> List[TrendPoint]:
        spikes = []
        for point in trend.data_points:
            if point.value < threshold:
                spikes.append(point)
        return spikes
    
    def detect_sentiment_change(
        self,
        trend: TrendData,
        change_threshold: float = 0.3
    ) -> List[Tuple[TrendPoint, TrendPoint, float]]:
        changes = []
        data_points = trend.data_points
        for i in range(1, len(data_points)):
            prev_point = data_points[i - 1]
            curr_point = data_points[i]
            change = curr_point.value - prev_point.value
            if abs(change) >= change_threshold:
                changes.append((prev_point, curr_point, change))
        return changes
    
    def get_trend_summary(self, trend: TrendData) -> Dict:
        if not trend.data_points:
            return {
                "metric_name": trend.metric_name,
                "period": trend.period,
                "total_points": 0,
                "avg_value": 0.0,
                "min_value": 0.0,
                "max_value": 0.0,
                "total_count": 0,
                "start_date": None,
                "end_date": None
            }
        values = [p.value for p in trend.data_points]
        counts = [p.count for p in trend.data_points]
        return {
            "metric_name": trend.metric_name,
            "period": trend.period,
            "total_points": len(trend.data_points),
            "avg_value": sum(values) / len(values),
            "min_value": min(values),
            "max_value": max(values),
            "total_count": sum(counts),
            "start_date": trend.data_points[0].date.isoformat(),
            "end_date": trend.data_points[-1].date.isoformat()
        }
    
    def compare_periods(
        self,
        posts: List[PostContent],
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> Dict:
        period1_posts = self._filter_by_date_range(posts, period1_start, period1_end)
        period2_posts = self._filter_by_date_range(posts, period2_start, period2_end)
        period1_avg = self.sentiment_analyzer.get_average_sentiment(period1_posts)
        period2_avg = self.sentiment_analyzer.get_average_sentiment(period2_posts)
        return {
            "period1": {
                "start": period1_start.isoformat(),
                "end": period1_end.isoformat(),
                "post_count": len(period1_posts),
                "avg_sentiment": period1_avg
            },
            "period2": {
                "start": period2_start.isoformat(),
                "end": period2_end.isoformat(),
                "post_count": len(period2_posts),
                "avg_sentiment": period2_avg
            },
            "change": period2_avg - period1_avg
        }
