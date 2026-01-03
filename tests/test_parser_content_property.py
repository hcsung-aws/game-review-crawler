"""
Property-Based Tests for Parser Content

**Feature: community-crawler-enhancement, Property 2: Parsed Content Contains Required Fields**
**Validates: Requirements 1.2, 2.2**

For any 유효한 HTML 입력에 대해, 파싱된 PostContent는 title, body, site, url 필드를 
반드시 포함해야 하며, 파싱된 Comment는 author, content 필드를 반드시 포함해야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import List

from crawler.parsers.generic import GenericParser
from crawler.models.data_models import PostContent, Comment


# Strategies for generating test HTML
@st.composite
def html_title_strategy(draw):
    """HTML 제목 생성 전략"""
    # printable 문자만 사용하여 제어 문자 문제 방지
    title_text = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Zs')),
        min_size=1, 
        max_size=100
    ).filter(lambda x: x.strip()))
    tag_type = draw(st.sampled_from([
        '<h1>{}</h1>',
        '<h1 class="title">{}</h1>',
        '<h1 class="post-title">{}</h1>',
        '<title>{}</title>',
        '<div class="title"><h1>{}</h1></div>'
    ]))
    return tag_type.format(title_text), title_text


@st.composite
def html_body_strategy(draw):
    """HTML 본문 생성 전략"""
    # 최소 50자 이상의 본문 (GenericParser의 최소 길이 체크)
    # printable 문자만 사용하여 제어 문자 문제 방지
    body_text = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Zs')),
        min_size=60, 
        max_size=500
    ).filter(lambda x: len(x.strip()) >= 60))
    tag_type = draw(st.sampled_from([
        '<article class="content">{}</article>',
        '<div class="post-content">{}</div>',
        '<div class="entry-content">{}</div>',
        '<article>{}</article>',
        '<main>{}</main>'
    ]))
    return tag_type.format(body_text), body_text


@st.composite
def html_comment_strategy(draw):
    """HTML 댓글 생성 전략"""
    # printable 문자만 사용하되, HTML 특수문자(<, >, &, ", ')는 제외
    # BeautifulSoup이 이들을 HTML 태그나 엔티티로 해석할 수 있기 때문
    safe_chars = st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Zs'),
        blacklist_characters='<>&"\''
    )
    author = draw(st.text(alphabet=safe_chars, min_size=1, max_size=30).filter(lambda x: x.strip()))
    content = draw(st.text(alphabet=safe_chars, min_size=1, max_size=200).filter(lambda x: x.strip()))
    
    comment_html = f'''
    <div class="comment">
        <span class="author">{author}</span>
        <div class="content">{content}</div>
    </div>
    '''
    return comment_html, author, content


@st.composite
def valid_html_strategy(draw):
    """유효한 HTML 문서 생성 전략"""
    title_html, title_text = draw(html_title_strategy())
    body_html, body_text = draw(html_body_strategy())
    
    # 댓글 생성 (0~3개)
    num_comments = draw(st.integers(min_value=0, max_value=3))
    comments_data = [draw(html_comment_strategy()) for _ in range(num_comments)]
    
    comments_html = ""
    if comments_data:
        comments_html = '<div class="comments">' + ''.join([c[0] for c in comments_data]) + '</div>'
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body>
        {title_html}
        {body_html}
        {comments_html}
    </body>
    </html>
    '''
    
    return html, title_text, body_text, comments_data


@st.composite
def url_strategy(draw):
    """유효한 URL 생성 전략"""
    domain = draw(st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
        min_size=3,
        max_size=15
    ).filter(lambda x: x and x[0].isalpha()))
    
    tld = draw(st.sampled_from([".com", ".co.kr", ".net", ".org"]))
    path = draw(st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789/-_"),
        min_size=1,
        max_size=30
    ))
    
    return f"https://{domain}{tld}/{path}"


# printable 문자 전략 (keyword 등에 사용)
printable_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Zs')),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())


class TestParsedContentRequiredFields:
    """
    **Feature: community-crawler-enhancement, Property 2: Parsed Content Contains Required Fields**
    **Validates: Requirements 1.2, 2.2**
    
    For any 유효한 HTML 입력에 대해, 파싱된 PostContent는 title, body, site, url 필드를 
    반드시 포함해야 하며, 파싱된 Comment는 author, content 필드를 반드시 포함해야 한다.
    """
    
    @given(
        html_data=valid_html_strategy(),
        url=url_strategy(),
        keyword=printable_text_strategy
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_content_has_required_fields(self, html_data, url: str, keyword: str):
        """파싱된 PostContent가 필수 필드를 포함해야 함"""
        html, expected_title, expected_body, comments_data = html_data
        
        parser = GenericParser()
        result = parser.parse_post(html, url, keyword)
        
        # Assert: 필수 필드가 존재하고 비어있지 않아야 함
        assert result.url is not None and result.url != ""
        assert result.title is not None and result.title != ""
        assert result.body is not None and result.body != ""
        assert result.site is not None and result.site != ""
        
        # Assert: URL과 keyword가 올바르게 설정됨
        assert result.url == url
        assert result.keyword == keyword
    
    @given(
        html_data=valid_html_strategy(),
        url=url_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_content_title_extracted_correctly(self, html_data, url: str):
        """파싱된 제목이 추출되어야 함 (HTML 특수문자 제외)"""
        html, expected_title, expected_body, comments_data = html_data
        
        # HTML 특수문자가 포함된 경우 스킵 (BeautifulSoup이 태그로 해석할 수 있음)
        assume('<' not in expected_title and '>' not in expected_title)
        
        parser = GenericParser()
        result = parser.parse_post(html, url)
        
        # Assert: 제목이 추출되어야 함
        assert result.title is not None
        assert len(result.title) > 0
        # 제목에 원본 텍스트가 포함되어야 함 (HTML 태그 제거 후)
        assert expected_title.strip() in result.title or result.title in expected_title.strip()
    
    @given(
        html_data=valid_html_strategy(),
        url=url_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_content_body_extracted(self, html_data, url: str):
        """파싱된 본문이 추출되어야 함"""
        html, expected_title, expected_body, comments_data = html_data
        
        parser = GenericParser()
        result = parser.parse_post(html, url)
        
        # Assert: 본문이 추출되어야 함
        assert result.body is not None
        assert len(result.body) > 0
    
    @given(
        html_data=valid_html_strategy(),
        url=url_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_site_extracted_from_url(self, html_data, url: str):
        """site 필드가 URL에서 올바르게 추출되어야 함"""
        html, _, _, _ = html_data
        
        parser = GenericParser()
        result = parser.parse_post(html, url)
        
        # Assert: site가 URL의 도메인과 일치해야 함
        from urllib.parse import urlparse
        expected_site = urlparse(url).netloc
        assert result.site == expected_site
    
    @given(html_data=valid_html_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comments_have_required_fields(self, html_data):
        """파싱된 Comment가 필수 필드를 포함해야 함"""
        html, _, _, comments_data = html_data
        
        # 댓글이 있는 경우만 테스트
        assume(len(comments_data) > 0)
        
        parser = GenericParser()
        comments = parser.parse_comments(html)
        
        # Assert: 파싱된 댓글 수가 원본과 일치
        assert len(comments) == len(comments_data)
        
        # Assert: 각 댓글이 필수 필드를 포함
        for comment in comments:
            assert comment.author is not None and comment.author != ""
            assert comment.content is not None and comment.content != ""
    
    @given(html_data=valid_html_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comment_author_extracted_correctly(self, html_data):
        """댓글 작성자가 올바르게 추출되어야 함"""
        html, _, _, comments_data = html_data
        
        # 댓글이 있는 경우만 테스트
        assume(len(comments_data) > 0)
        
        parser = GenericParser()
        comments = parser.parse_comments(html)
        
        # Assert: 각 댓글의 작성자가 원본과 일치
        for i, comment in enumerate(comments):
            expected_author = comments_data[i][1].strip()
            assert comment.author == expected_author
    
    @given(html_data=valid_html_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comment_content_extracted_correctly(self, html_data):
        """댓글 내용이 올바르게 추출되어야 함"""
        html, _, _, comments_data = html_data
        
        # 댓글이 있는 경우만 테스트
        assume(len(comments_data) > 0)
        
        parser = GenericParser()
        comments = parser.parse_comments(html)
        
        # Assert: 각 댓글의 내용이 원본과 일치
        for i, comment in enumerate(comments):
            expected_content = comments_data[i][2].strip()
            assert comment.content == expected_content
    
    @given(url=url_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_empty_html_returns_empty_fields(self, url: str):
        """빈 HTML에 대해 빈 필드가 반환되어야 함"""
        html = "<html><body></body></html>"
        
        parser = GenericParser()
        result = parser.parse_post(html, url)
        
        # Assert: URL과 site는 설정되어야 함
        assert result.url == url
        assert result.site is not None
        
        # Assert: 제목과 본문은 빈 문자열일 수 있음
        assert result.title is not None
        assert result.body is not None
    
    @given(url=url_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_no_comments_returns_empty_list(self, url: str):
        """댓글이 없는 HTML에 대해 빈 리스트가 반환되어야 함"""
        html = """
        <html>
        <body>
            <h1>Test Title</h1>
            <article class="content">This is a test body content that is long enough to pass the minimum length check for the parser.</article>
        </body>
        </html>
        """
        
        parser = GenericParser()
        result = parser.parse_post(html, url)
        
        # Assert: 댓글이 빈 리스트여야 함
        assert result.comments is not None
        assert isinstance(result.comments, list)
        assert len(result.comments) == 0
