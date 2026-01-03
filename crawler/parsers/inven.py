"""
InvenParser - 인벤(inven.co.kr) 전용 파서

Requirements: 4.1, 1.1, 2.1
- inven.co.kr 게시글 및 댓글 파싱
- 제목, 본문, 작성일, 조회수, 추천수 추출
- 댓글 작성자, 내용, 작성일, 추천수 추출
"""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from crawler.parsers.base import ContentParser
from crawler.models.data_models import PostContent, Comment


class InvenParser(ContentParser):
    """인벤(inven.co.kr) 전용 파서
    
    Requirements: 4.1, 1.1, 2.1
    - 인벤 게시판 HTML 구조에 맞춤 파싱
    - 게시글 본문 및 댓글 추출
    """
    
    SUPPORTED_DOMAINS = [
        "inven.co.kr",
        "www.inven.co.kr",
        "m.inven.co.kr"
    ]
    
    def parse_post(self, html: str, url: str, keyword: str = "") -> PostContent:
        """게시글 파싱
        
        Args:
            html: HTML 문자열
            url: 게시글 URL
            keyword: 검색 키워드
            
        Returns:
            PostContent: 파싱된 게시글 데이터
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # 제목 추출
        title = self._extract_title(soup)
        
        # 본문 추출
        body = self._extract_body(soup)
        
        # 작성자 추출
        author = self._extract_author(soup)
        
        # 날짜 추출
        created_at = self._extract_date(soup)
        
        # 조회수 추출
        view_count = self._extract_view_count(soup)
        
        # 추천수 추출
        like_count = self._extract_like_count(soup)
        
        # 댓글 추출
        comments = self.parse_comments(html)
        
        return PostContent(
            url=url,
            title=title,
            body=body,
            site="inven.co.kr",
            keyword=keyword,
            author=author,
            created_at=created_at,
            view_count=view_count,
            like_count=like_count,
            comments=comments
        )
    
    def parse_comments(self, html: str) -> List[Comment]:
        """댓글 파싱
        
        Args:
            html: HTML 문자열
            
        Returns:
            List[Comment]: 파싱된 댓글 목록
        """
        soup = BeautifulSoup(html, 'lxml')
        comments = []
        
        # 인벤 댓글 영역 선택자들
        comment_selectors = [
            '.comment-list .comment-item',
            '.commentList .comment',
            '.reply-list li',
            '#comment-list .comment',
            '.cmtList li'
        ]
        
        comment_items = []
        for selector in comment_selectors:
            comment_items = soup.select(selector)
            if comment_items:
                break
        
        for item in comment_items:
            comment = self._parse_comment_item(item)
            if comment:
                comments.append(comment)
        
        return comments
    
    def get_supported_domains(self) -> List[str]:
        """지원하는 도메인 목록 반환"""
        return self.SUPPORTED_DOMAINS
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """제목 추출"""
        # 인벤 제목 선택자들
        title_selectors = [
            '.articleTitle',
            '.article-head .title',
            '.contentBody .title',
            'h1.title',
            '.view-title',
            '#content .title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        # 폴백: h1 태그
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return ""
    
    def _extract_body(self, soup: BeautifulSoup) -> str:
        """본문 추출"""
        # 스크립트, 스타일 태그 제거
        for tag in soup.find_all(['script', 'style']):
            tag.decompose()
        
        # 인벤 본문 선택자들
        body_selectors = [
            '.articleContent',
            '.article-body',
            '.contentBody .content',
            '#content .content',
            '.view-content',
            '.postContent'
        ]
        
        for selector in body_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 10:
                    return self._clean_text(text)
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """작성자 추출"""
        author_selectors = [
            '.articleWriter',
            '.article-head .writer',
            '.nickname',
            '.author',
            '.user-name'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """날짜 추출"""
        date_selectors = [
            '.articleDate',
            '.article-head .date',
            '.regdate',
            '.date',
            'time'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                # datetime 속성 확인
                if element.has_attr('datetime'):
                    try:
                        return datetime.fromisoformat(element['datetime'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                
                text = element.get_text(strip=True)
                parsed = self._parse_date_string(text)
                if parsed:
                    return parsed
        
        return None
    
    def _parse_date_string(self, text: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        # 인벤 날짜 형식들
        patterns = [
            (r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})\s*(\d{1,2}):(\d{2})', '%Y-%m-%d %H:%M'),
            (r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})', '%Y-%m-%d'),
            (r'(\d{2})[.-](\d{1,2})[.-](\d{1,2})', '%y-%m-%d'),
        ]
        
        for pattern, _ in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) >= 5:
                        year = int(groups[0])
                        if year < 100:
                            year += 2000
                        return datetime(year, int(groups[1]), int(groups[2]), 
                                       int(groups[3]), int(groups[4]))
                    elif len(groups) >= 3:
                        year = int(groups[0])
                        if year < 100:
                            year += 2000
                        return datetime(year, int(groups[1]), int(groups[2]))
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_view_count(self, soup: BeautifulSoup) -> int:
        """조회수 추출"""
        view_selectors = [
            '.articleHit',
            '.hit',
            '.view-count',
            '.read'
        ]
        
        for selector in view_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                numbers = re.findall(r'[\d,]+', text)
                if numbers:
                    return int(numbers[0].replace(',', ''))
        
        # 텍스트에서 조회수 패턴 찾기
        text = soup.get_text()
        match = re.search(r'조회[:\s]*([0-9,]+)', text)
        if match:
            return int(match.group(1).replace(',', ''))
        
        return 0
    
    def _extract_like_count(self, soup: BeautifulSoup) -> int:
        """추천수 추출"""
        like_selectors = [
            '.articleLike',
            '.recommend',
            '.like-count',
            '.vote-up'
        ]
        
        for selector in like_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                numbers = re.findall(r'[\d,]+', text)
                if numbers:
                    return int(numbers[0].replace(',', ''))
        
        # 텍스트에서 추천 패턴 찾기
        text = soup.get_text()
        match = re.search(r'추천[:\s]*([0-9,]+)', text)
        if match:
            return int(match.group(1).replace(',', ''))
        
        return 0
    
    def _parse_comment_item(self, item) -> Optional[Comment]:
        """개별 댓글 아이템 파싱"""
        # 작성자 추출
        author = ""
        author_selectors = ['.nickname', '.writer', '.author', '.name', '.user']
        for selector in author_selectors:
            author_elem = item.select_one(selector)
            if author_elem:
                author = author_elem.get_text(strip=True)
                break
        
        if not author:
            author = "익명"
        
        # 내용 추출
        content = ""
        content_selectors = ['.content', '.text', '.comment-text', '.body', '.reply-content']
        for selector in content_selectors:
            content_elem = item.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                break
        
        if not content:
            # 전체 텍스트에서 추출 (작성자, 날짜 등 제외)
            for tag in item.find_all(['span', 'div'], class_=re.compile(r'(nick|author|date|time|like)')):
                tag.decompose()
            content = item.get_text(strip=True)
        
        if not content:
            return None
        
        # 날짜 추출
        created_at = None
        date_selectors = ['.date', '.time', 'time', '.regdate']
        for selector in date_selectors:
            date_elem = item.select_one(selector)
            if date_elem:
                if date_elem.has_attr('datetime'):
                    try:
                        created_at = datetime.fromisoformat(date_elem['datetime'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                else:
                    created_at = self._parse_date_string(date_elem.get_text(strip=True))
                break
        
        # 추천수 추출
        like_count = 0
        like_selectors = ['.like', '.recommend', '.vote', '.good']
        for selector in like_selectors:
            like_elem = item.select_one(selector)
            if like_elem:
                numbers = re.findall(r'\d+', like_elem.get_text(strip=True))
                if numbers:
                    like_count = int(numbers[0])
                break
        
        return Comment(
            author=author,
            content=content,
            created_at=created_at,
            like_count=like_count
        )
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
