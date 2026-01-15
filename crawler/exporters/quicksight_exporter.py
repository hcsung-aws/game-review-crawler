"""
게임별 QuickSight 데이터 내보내기

Requirements: 6.1, 6.2, 6.3, 6.4
- 게임별 디렉토리 구조 생성
- posts.csv, comments.csv, sentiment.csv, issues.csv 내보내기
- UTF-8 인코딩, ISO 8601 날짜 형식
- quicksight_data/{game_id}/ 경로 구조
"""

import os
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from crawler.models.data_models import PostContent
from crawler.models.analysis_models import (
    SentimentResult,
    DetectedIssue,
    GameAnalysisResult
)


class GameQuickSightExporter:
    """게임별 QuickSight 데이터 내보내기
    
    Requirements: 6.1, 6.2, 6.3, 6.4
    - 게임별로 별도 디렉토리에 CSV 파일 생성
    - posts.csv, comments.csv, sentiment.csv, issues.csv 파일 생성
    - QuickSight 호환 형식 (UTF-8, ISO 8601 날짜)
    """
    
    def __init__(self, base_output_dir: str = "quicksight_data"):
        """GameQuickSightExporter 초기화
        
        Args:
            base_output_dir: 기본 출력 디렉토리
        """
        self.base_output_dir = base_output_dir
    
    def get_game_export_path(self, game_id: str) -> str:
        """게임별 내보내기 경로 반환
        
        Requirements: 6.4
        - quicksight_data/{game_id}/ 형식의 디렉토리 구조
        
        Args:
            game_id: 게임 ID
            
        Returns:
            게임별 내보내기 경로
        """
        return os.path.join(self.base_output_dir, game_id)
    
    def export_game_data(
        self,
        game_id: str,
        posts: List[PostContent],
        analysis: Optional[GameAnalysisResult] = None,
        posts_with_sentiment: Optional[List[Tuple[PostContent, SentimentResult]]] = None,
        issues: Optional[List[DetectedIssue]] = None
    ) -> Dict[str, str]:
        """게임별 QuickSight 데이터 내보내기
        
        Requirements: 6.1, 6.2
        - 게임별로 별도 디렉토리에 CSV 파일 생성
        - posts.csv, comments.csv, sentiment.csv, issues.csv 파일 생성
        
        Args:
            game_id: 게임 ID
            posts: 게시글 목록
            analysis: 게임 분석 결과 (선택)
            posts_with_sentiment: 감성 분석 결과가 포함된 게시글 목록 (선택)
            issues: 이슈 목록 (선택)
            
        Returns:
            생성된 파일 경로 딕셔너리
            {"posts": "path", "comments": "path", "sentiment": "path", "issues": "path"}
        """
        # 게임별 디렉토리 생성
        export_path = self.get_game_export_path(game_id)
        os.makedirs(export_path, exist_ok=True)
        
        result = {}
        
        # posts.csv 내보내기
        posts_path = self._export_posts_csv(game_id, posts)
        result["posts"] = posts_path
        
        # comments.csv 내보내기
        comments_path = self._export_comments_csv(game_id, posts)
        result["comments"] = comments_path
        
        # sentiment.csv 내보내기
        if posts_with_sentiment:
            sentiment_path = self._export_sentiment_csv(game_id, posts_with_sentiment)
        elif analysis:
            # analysis에서 감성 데이터 추출하여 내보내기
            sentiment_path = self._export_sentiment_from_analysis(game_id, posts, analysis)
        else:
            # 빈 sentiment.csv 생성
            sentiment_path = self._export_empty_sentiment_csv(game_id)
        result["sentiment"] = sentiment_path
        
        # issues.csv 내보내기
        if issues:
            issues_path = self._export_issues_csv(game_id, issues)
        elif analysis:
            issues_path = self._export_issues_csv(game_id, analysis.issues)
        else:
            # 빈 issues.csv 생성
            issues_path = self._export_empty_issues_csv(game_id)
        result["issues"] = issues_path
        
        return result

    def _export_posts_csv(self, game_id: str, posts: List[PostContent]) -> str:
        """게시글 CSV 내보내기
        
        Requirements: 6.2, 6.3
        - posts.csv 파일 생성
        - UTF-8 인코딩, ISO 8601 날짜 형식
        
        Args:
            game_id: 게임 ID
            posts: 게시글 목록
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "posts.csv")
        
        fieldnames = [
            "post_id", "url", "title", "body", "site", "keyword",
            "author", "created_at", "view_count", "like_count", "comment_count",
            "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, post in enumerate(posts):
                row = {
                    "post_id": f"{game_id}_{idx}",
                    "url": post.url,
                    "title": post.title,
                    "body": post.body[:1000] if post.body else "",  # 본문 길이 제한
                    "site": post.site,
                    "keyword": post.keyword,
                    "author": post.author or "",
                    "created_at": self._format_date(post.created_at),
                    "view_count": post.view_count,
                    "like_count": post.like_count,
                    "comment_count": len(post.comments),
                    "game_id": game_id
                }
                writer.writerow(row)
        
        return filepath
    
    def _export_comments_csv(self, game_id: str, posts: List[PostContent]) -> str:
        """댓글 CSV 내보내기
        
        Requirements: 6.2, 6.3
        - comments.csv 파일 생성
        - UTF-8 인코딩, ISO 8601 날짜 형식
        
        Args:
            game_id: 게임 ID
            posts: 게시글 목록 (댓글 포함)
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "comments.csv")
        
        fieldnames = [
            "comment_id", "post_url", "author", "content",
            "created_at", "like_count", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            comment_idx = 0
            for post in posts:
                for comment in post.comments:
                    row = {
                        "comment_id": f"{game_id}_c{comment_idx}",
                        "post_url": post.url,
                        "author": comment.author,
                        "content": comment.content[:500] if comment.content else "",  # 내용 길이 제한
                        "created_at": self._format_date(comment.created_at),
                        "like_count": comment.like_count,
                        "game_id": game_id
                    }
                    writer.writerow(row)
                    comment_idx += 1
        
        return filepath
    
    def _export_sentiment_csv(
        self,
        game_id: str,
        posts_with_sentiment: List[Tuple[PostContent, SentimentResult]]
    ) -> str:
        """감성 분석 결과 CSV 내보내기
        
        Requirements: 6.2, 6.3
        - sentiment.csv 파일 생성
        - UTF-8 인코딩, ISO 8601 날짜 형식
        
        Args:
            game_id: 게임 ID
            posts_with_sentiment: 감성 분석 결과가 포함된 게시글 목록
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "sentiment.csv")
        
        fieldnames = [
            "sentiment_id", "post_url", "title", "sentiment_score",
            "sentiment_label", "confidence", "created_at", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, (post, sentiment) in enumerate(posts_with_sentiment):
                row = {
                    "sentiment_id": f"{game_id}_s{idx}",
                    "post_url": post.url,
                    "title": post.title,
                    "sentiment_score": round(sentiment.score, 4),
                    "sentiment_label": sentiment.label.value,
                    "confidence": round(sentiment.confidence, 4),
                    "created_at": self._format_date(post.created_at),
                    "game_id": game_id
                }
                writer.writerow(row)
        
        return filepath

    def _export_sentiment_from_analysis(
        self,
        game_id: str,
        posts: List[PostContent],
        analysis: GameAnalysisResult
    ) -> str:
        """분석 결과에서 감성 데이터 추출하여 CSV 내보내기
        
        Args:
            game_id: 게임 ID
            posts: 게시글 목록
            analysis: 게임 분석 결과
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "sentiment.csv")
        
        fieldnames = [
            "sentiment_id", "post_url", "title", "sentiment_score",
            "sentiment_label", "confidence", "created_at", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # 분석 결과의 평균 감성 점수를 기반으로 레이블 결정
            avg_score = analysis.sentiment_avg
            if avg_score > 0.1:
                default_label = "positive"
            elif avg_score < -0.1:
                default_label = "negative"
            else:
                default_label = "neutral"
            
            for idx, post in enumerate(posts):
                row = {
                    "sentiment_id": f"{game_id}_s{idx}",
                    "post_url": post.url,
                    "title": post.title,
                    "sentiment_score": round(avg_score, 4),
                    "sentiment_label": default_label,
                    "confidence": 0.5,  # 개별 분석이 아니므로 낮은 신뢰도
                    "created_at": self._format_date(post.created_at),
                    "game_id": game_id
                }
                writer.writerow(row)
        
        return filepath
    
    def _export_empty_sentiment_csv(self, game_id: str) -> str:
        """빈 감성 분석 CSV 파일 생성
        
        Args:
            game_id: 게임 ID
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "sentiment.csv")
        
        fieldnames = [
            "sentiment_id", "post_url", "title", "sentiment_score",
            "sentiment_label", "confidence", "created_at", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        return filepath
    
    def _export_issues_csv(self, game_id: str, issues: List[DetectedIssue]) -> str:
        """이슈 목록 CSV 내보내기
        
        Requirements: 6.2, 6.3
        - issues.csv 파일 생성
        - UTF-8 인코딩, ISO 8601 날짜 형식
        
        Args:
            game_id: 게임 ID
            issues: 이슈 목록
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "issues.csv")
        
        fieldnames = [
            "issue_id", "title", "keywords", "priority_score",
            "is_hot", "is_bug", "severity", "post_count",
            "total_views", "total_comments", "sentiment_avg",
            "first_seen", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for issue in issues:
                row = {
                    "issue_id": issue.issue_id,
                    "title": issue.title,
                    "keywords": "|".join(issue.cluster.keywords),  # 파이프로 구분
                    "priority_score": round(issue.priority_score, 4),
                    "is_hot": "true" if issue.is_hot else "false",
                    "is_bug": "true" if issue.is_bug else "false",
                    "severity": issue.severity.value,
                    "post_count": issue.cluster.post_count,
                    "total_views": issue.cluster.total_views,
                    "total_comments": issue.cluster.total_comments,
                    "sentiment_avg": round(issue.sentiment_avg, 4),
                    "first_seen": self._format_date(issue.first_seen),
                    "game_id": game_id
                }
                writer.writerow(row)
        
        return filepath
    
    def _export_empty_issues_csv(self, game_id: str) -> str:
        """빈 이슈 CSV 파일 생성
        
        Args:
            game_id: 게임 ID
            
        Returns:
            생성된 파일 경로
        """
        export_path = self.get_game_export_path(game_id)
        filepath = os.path.join(export_path, "issues.csv")
        
        fieldnames = [
            "issue_id", "title", "keywords", "priority_score",
            "is_hot", "is_bug", "severity", "post_count",
            "total_views", "total_comments", "sentiment_avg",
            "first_seen", "game_id"
        ]
        
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        return filepath
    
    def _format_date(self, dt: Optional[datetime]) -> str:
        """날짜를 ISO 8601 형식으로 포맷
        
        Requirements: 6.3
        - ISO 8601 형식 (YYYY-MM-DD)
        
        Args:
            dt: datetime 객체
            
        Returns:
            ISO 8601 형식 문자열 또는 빈 문자열
        """
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d")
