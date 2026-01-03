"""
Exporter 클래스 구현

Requirements: 6.2
- JSON 및 CSV 형식 내보내기 지원
"""

import os
import json
import csv
from abc import ABC, abstractmethod
from typing import List, Optional

from crawler.models.data_models import PostContent


class BaseExporter(ABC):
    """내보내기 기본 클래스"""
    
    @abstractmethod
    def export(self, posts: List[PostContent], filepath: str) -> str:
        """게시글 목록을 파일로 내보내기
        
        Args:
            posts: 내보낼 게시글 목록
            filepath: 저장할 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        pass
    
    @abstractmethod
    def get_extension(self) -> str:
        """파일 확장자 반환"""
        pass


class JSONExporter(BaseExporter):
    """JSON 형식 내보내기
    
    Requirements: 6.2
    - JSON 형식 지원
    """
    
    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """JSONExporter 초기화
        
        Args:
            indent: JSON 들여쓰기 크기
            ensure_ascii: ASCII 인코딩 강제 여부
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def export(self, posts: List[PostContent], filepath: str) -> str:
        """게시글 목록을 JSON 파일로 내보내기
        
        Args:
            posts: 내보낼 게시글 목록
            filepath: 저장할 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        # 확장자 확인 및 추가
        if not filepath.endswith(".json"):
            filepath = f"{filepath}.json"
        
        # 디렉토리 생성
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # JSON 데이터 생성
        data = [post.to_dict() for post in posts]
        
        # 파일 저장
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=self.ensure_ascii, indent=self.indent)
        
        return filepath
    
    def get_extension(self) -> str:
        """파일 확장자 반환"""
        return ".json"


class CSVExporter(BaseExporter):
    """CSV 형식 내보내기
    
    Requirements: 6.2
    - CSV 형식 지원
    - 게시글과 댓글을 별도 파일로 저장
    """
    
    def __init__(self, include_comments: bool = True):
        """CSVExporter 초기화
        
        Args:
            include_comments: 댓글 파일 생성 여부
        """
        self.include_comments = include_comments
    
    def export(self, posts: List[PostContent], filepath: str) -> str:
        """게시글 목록을 CSV 파일로 내보내기
        
        게시글은 메인 파일에, 댓글은 별도 파일에 저장한다.
        
        Args:
            posts: 내보낼 게시글 목록
            filepath: 저장할 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        # 확장자 확인 및 추가
        if not filepath.endswith(".csv"):
            filepath = f"{filepath}.csv"
        
        # 디렉토리 생성
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # 게시글 CSV 저장
        self._export_posts(posts, filepath)
        
        # 댓글 CSV 저장 (옵션)
        if self.include_comments:
            comments_filepath = filepath.replace(".csv", "_comments.csv")
            self._export_comments(posts, comments_filepath)
        
        return filepath
    
    def _export_posts(self, posts: List[PostContent], filepath: str) -> None:
        """게시글을 CSV로 저장
        
        Args:
            posts: 게시글 목록
            filepath: 저장할 파일 경로
        """
        fieldnames = [
            "url", "title", "body", "site", "keyword", 
            "author", "created_at", "view_count", "like_count", "comment_count"
        ]
        
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for post in posts:
                row = {
                    "url": post.url,
                    "title": post.title,
                    "body": post.body,
                    "site": post.site,
                    "keyword": post.keyword,
                    "author": post.author or "",
                    "created_at": post.created_at.isoformat() if post.created_at else "",
                    "view_count": post.view_count,
                    "like_count": post.like_count,
                    "comment_count": len(post.comments)
                }
                writer.writerow(row)
    
    def _export_comments(self, posts: List[PostContent], filepath: str) -> None:
        """댓글을 CSV로 저장
        
        Args:
            posts: 게시글 목록 (댓글 포함)
            filepath: 저장할 파일 경로
        """
        fieldnames = ["post_url", "author", "content", "created_at", "like_count"]
        
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for post in posts:
                for comment in post.comments:
                    row = {
                        "post_url": post.url,
                        "author": comment.author,
                        "content": comment.content,
                        "created_at": comment.created_at.isoformat() if comment.created_at else "",
                        "like_count": comment.like_count
                    }
                    writer.writerow(row)
    
    def get_extension(self) -> str:
        """파일 확장자 반환"""
        return ".csv"


class ExporterFactory:
    """Exporter 팩토리 클래스"""
    
    _exporters = {
        "json": JSONExporter,
        "csv": CSVExporter
    }
    
    @classmethod
    def create(cls, format_type: str, **kwargs) -> BaseExporter:
        """형식에 맞는 Exporter 생성
        
        Args:
            format_type: 내보내기 형식 ("json" 또는 "csv")
            **kwargs: Exporter 초기화 인자
            
        Returns:
            생성된 Exporter 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 형식인 경우
        """
        format_type = format_type.lower()
        if format_type not in cls._exporters:
            raise ValueError(f"Unsupported format: {format_type}. Supported: {list(cls._exporters.keys())}")
        
        return cls._exporters[format_type](**kwargs)
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """지원하는 형식 목록 반환"""
        return list(cls._exporters.keys())
