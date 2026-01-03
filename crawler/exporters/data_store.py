"""
DataStore 클래스 구현

Requirements: 6.1, 6.3
- 게시글 추가 및 관리
- 날짜별 파일 분할 로직
- 게시글과 댓글을 관계형 구조로 저장
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

from crawler.models.data_models import PostContent, CrawlerConfig


class DataStore:
    """데이터 저장소 클래스
    
    게시글 데이터를 관리하고 날짜별로 분할하여 저장한다.
    
    Requirements: 6.1, 6.3
    - 게시글과 댓글을 관계형 구조로 저장
    - 대용량 데이터를 날짜별로 분할하여 저장
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """DataStore 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
        """
        self.config = config or CrawlerConfig()
        self.output_dir = self.config.output_dir
        self.posts: List[PostContent] = []
        self._posts_by_date: Dict[str, List[PostContent]] = defaultdict(list)
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_post(self, post: PostContent) -> None:
        """게시글 추가
        
        Requirements: 6.1
        - 게시글과 댓글을 관계형 구조로 저장
        
        Args:
            post: 추가할 게시글
        """
        self.posts.append(post)
        
        # 날짜별 분류
        date_key = self._get_date_key(post)
        self._posts_by_date[date_key].append(post)
    
    def add_posts(self, posts: List[PostContent]) -> None:
        """여러 게시글 추가
        
        Args:
            posts: 추가할 게시글 목록
        """
        for post in posts:
            self.add_post(post)
    
    def get_posts(self) -> List[PostContent]:
        """모든 게시글 반환
        
        Returns:
            저장된 모든 게시글 목록
        """
        return self.posts.copy()
    
    def get_posts_by_date(self, date_key: str) -> List[PostContent]:
        """특정 날짜의 게시글 반환
        
        Args:
            date_key: 날짜 키 (YYYY-MM-DD 형식)
            
        Returns:
            해당 날짜의 게시글 목록
        """
        return self._posts_by_date.get(date_key, []).copy()
    
    def get_date_keys(self) -> List[str]:
        """저장된 모든 날짜 키 반환
        
        Returns:
            날짜 키 목록 (정렬됨)
        """
        return sorted(self._posts_by_date.keys())
    
    def clear(self) -> None:
        """모든 데이터 삭제"""
        self.posts.clear()
        self._posts_by_date.clear()
    
    def _get_date_key(self, post: PostContent) -> str:
        """게시글의 날짜 키 생성
        
        Args:
            post: 게시글
            
        Returns:
            날짜 키 (YYYY-MM-DD 형식). 날짜가 없으면 'unknown'
        """
        if post.created_at:
            return post.created_at.strftime("%Y-%m-%d")
        return "unknown"
    
    def save_by_date(self, base_filename: str = "posts") -> Dict[str, str]:
        """날짜별로 파일 분할하여 저장
        
        Requirements: 6.3
        - 대용량 데이터를 날짜별로 분할하여 저장
        
        Args:
            base_filename: 기본 파일명 (확장자 제외)
            
        Returns:
            날짜별 저장된 파일 경로 딕셔너리
        """
        saved_files = {}
        
        for date_key, posts in self._posts_by_date.items():
            filename = f"{base_filename}_{date_key}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            data = [post.to_dict() for post in posts]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            saved_files[date_key] = filepath
        
        return saved_files
    
    def load_from_file(self, filepath: str) -> List[PostContent]:
        """파일에서 게시글 로드
        
        Requirements: 6.4
        - 저장된 데이터를 동일한 구조의 객체로 역직렬화
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            로드된 게시글 목록
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        posts = [PostContent.from_dict(item) for item in data]
        return posts
    
    def load_and_add(self, filepath: str) -> int:
        """파일에서 게시글을 로드하여 저장소에 추가
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            추가된 게시글 수
        """
        posts = self.load_from_file(filepath)
        self.add_posts(posts)
        return len(posts)
    
    def count(self) -> int:
        """저장된 게시글 수 반환
        
        Returns:
            게시글 수
        """
        return len(self.posts)
    
    def count_comments(self) -> int:
        """저장된 총 댓글 수 반환
        
        Returns:
            총 댓글 수
        """
        return sum(len(post.comments) for post in self.posts)
