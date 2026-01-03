"""
Unit Tests for Site-Specific Parsers

Requirements: 4.1
- InvenParser, RuliwebParser, DCInsideParser 동작 검증
- 샘플 HTML에 대한 파싱 결과 검증
"""

import pytest
from datetime import datetime

from crawler.parsers.inven import InvenParser
from crawler.parsers.ruliweb import RuliwebParser
from crawler.parsers.dcinside import DCInsideParser
from crawler.parsers.base import ParserRegistry
from crawler.parsers.generic import GenericParser
from crawler.models.data_models import PostContent, Comment


class TestInvenParser:
    """InvenParser 단위 테스트"""
    
    @pytest.fixture
    def parser(self):
        return InvenParser()
    
    @pytest.fixture
    def sample_html(self):
        """인벤 스타일 샘플 HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <div class="articleTitle">테스트 게시글 제목</div>
            <div class="articleWriter">테스트유저</div>
            <div class="articleDate">2024-12-25 14:30</div>
            <div class="articleHit">조회 1,234</div>
            <div class="articleLike">추천 56</div>
            <div class="articleContent">
                이것은 테스트 게시글 본문입니다.
                여러 줄로 작성된 내용이 있습니다.
            </div>
            <div class="comment-list">
                <div class="comment-item">
                    <span class="nickname">댓글작성자1</span>
                    <div class="content">첫 번째 댓글입니다.</div>
                    <span class="date">2024-12-25 15:00</span>
                    <span class="like">3</span>
                </div>
                <div class="comment-item">
                    <span class="nickname">댓글작성자2</span>
                    <div class="content">두 번째 댓글입니다.</div>
                    <span class="date">2024-12-25 15:30</span>
                    <span class="like">1</span>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_supported_domains(self, parser):
        """지원 도메인 확인"""
        domains = parser.get_supported_domains()
        assert "inven.co.kr" in domains
        assert "www.inven.co.kr" in domains
        assert "m.inven.co.kr" in domains
    
    def test_parse_post_title(self, parser, sample_html):
        """제목 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.title == "테스트 게시글 제목"
    
    def test_parse_post_body(self, parser, sample_html):
        """본문 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert "테스트 게시글 본문" in result.body
    
    def test_parse_post_author(self, parser, sample_html):
        """작성자 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.author == "테스트유저"
    
    def test_parse_post_date(self, parser, sample_html):
        """날짜 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.created_at is not None
        assert result.created_at.year == 2024
        assert result.created_at.month == 12
        assert result.created_at.day == 25
    
    def test_parse_post_view_count(self, parser, sample_html):
        """조회수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.view_count == 1234
    
    def test_parse_post_like_count(self, parser, sample_html):
        """추천수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.like_count == 56
    
    def test_parse_post_site(self, parser, sample_html):
        """사이트 필드 테스트"""
        result = parser.parse_post(sample_html, "https://www.inven.co.kr/board/test/1", "테스트")
        assert result.site == "inven.co.kr"
    
    def test_parse_comments(self, parser, sample_html):
        """댓글 파싱 테스트"""
        comments = parser.parse_comments(sample_html)
        assert len(comments) == 2
        assert comments[0].author == "댓글작성자1"
        assert "첫 번째 댓글" in comments[0].content
        assert comments[1].author == "댓글작성자2"
    
    def test_parse_empty_html(self, parser):
        """빈 HTML 파싱 테스트"""
        result = parser.parse_post("<html><body></body></html>", "https://inven.co.kr/test", "")
        assert result.url == "https://inven.co.kr/test"
        assert result.site == "inven.co.kr"
        assert result.title == ""
        assert result.body == ""


class TestRuliwebParser:
    """RuliwebParser 단위 테스트"""
    
    @pytest.fixture
    def parser(self):
        return RuliwebParser()
    
    @pytest.fixture
    def sample_html(self):
        """루리웹 스타일 샘플 HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <div class="board_main">
                <div class="board_main_top">
                    <span class="subject">루리웹 테스트 게시글</span>
                    <span class="nick">루리웹유저</span>
                    <span class="regdate">2024-12-24 10:20:30</span>
                    <span class="hit">5,678</span>
                </div>
                <div class="view_content">
                    루리웹 게시글 본문 내용입니다.
                    테스트를 위한 충분한 길이의 텍스트가 필요합니다.
                </div>
            </div>
            <div class="recommend_btn">
                <span class="like_value">89</span>
            </div>
            <div class="comment_view">
                <div class="comment_element">
                    <span class="nick">루리댓글러1</span>
                    <div class="text">루리웹 첫 번째 댓글</div>
                    <span class="date">2024-12-24 11:00</span>
                    <span class="like">5</span>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_supported_domains(self, parser):
        """지원 도메인 확인"""
        domains = parser.get_supported_domains()
        assert "ruliweb.com" in domains
        assert "www.ruliweb.com" in domains
        assert "bbs.ruliweb.com" in domains
    
    def test_parse_post_title(self, parser, sample_html):
        """제목 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.title == "루리웹 테스트 게시글"
    
    def test_parse_post_body(self, parser, sample_html):
        """본문 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert "루리웹 게시글 본문" in result.body
    
    def test_parse_post_author(self, parser, sample_html):
        """작성자 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.author == "루리웹유저"
    
    def test_parse_post_date(self, parser, sample_html):
        """날짜 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.created_at is not None
        assert result.created_at.year == 2024
        assert result.created_at.month == 12
        assert result.created_at.day == 24
    
    def test_parse_post_view_count(self, parser, sample_html):
        """조회수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.view_count == 5678
    
    def test_parse_post_like_count(self, parser, sample_html):
        """추천수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.like_count == 89
    
    def test_parse_post_site(self, parser, sample_html):
        """사이트 필드 테스트"""
        result = parser.parse_post(sample_html, "https://bbs.ruliweb.com/test/1", "테스트")
        assert result.site == "ruliweb.com"
    
    def test_parse_comments(self, parser, sample_html):
        """댓글 파싱 테스트"""
        comments = parser.parse_comments(sample_html)
        assert len(comments) == 1
        assert comments[0].author == "루리댓글러1"
        assert "루리웹 첫 번째 댓글" in comments[0].content


class TestDCInsideParser:
    """DCInsideParser 단위 테스트"""
    
    @pytest.fixture
    def parser(self):
        return DCInsideParser()
    
    @pytest.fixture
    def sample_html(self):
        """디시인사이드 스타일 샘플 HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <div class="gallview_head">
                <span class="title_subject">[정보] 디시 테스트 게시글</span>
                <span class="nickname" data-nick="디시유저">디시유저</span>
                <span class="gall_date" title="2024-12-23 09:15:45">12.23 09:15</span>
                <span class="gall_count">조회 9,999</span>
            </div>
            <div class="btn_recommend_box">
                <span class="up_num">123</span>
            </div>
            <div class="gallview_contents">
                <div class="inner">
                    <div class="writing_view_box">
                        디시인사이드 게시글 본문입니다.
                        여러 줄의 내용이 포함되어 있습니다.
                    </div>
                </div>
            </div>
            <div class="reply_list">
                <div class="reply_item">
                    <span class="nickname" data-nick="디시댓글러">디시댓글러</span>
                    <div class="reply_content">디시 첫 번째 댓글</div>
                    <span class="date_time">12.23 10:00</span>
                    <span class="reply_num">7</span>
                </div>
                <div class="reply_item">
                    <span class="nickname">익명</span>
                    <div class="reply_content">디시 두 번째 댓글</div>
                    <span class="date_time">12.23 10:30</span>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_supported_domains(self, parser):
        """지원 도메인 확인"""
        domains = parser.get_supported_domains()
        assert "dcinside.com" in domains
        assert "gall.dcinside.com" in domains
        assert "m.dcinside.com" in domains
    
    def test_parse_post_title(self, parser, sample_html):
        """제목 파싱 테스트 (말머리 제거)"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert "디시 테스트 게시글" in result.title
        # 말머리 [정보]가 제거되어야 함
        assert "[정보]" not in result.title
    
    def test_parse_post_body(self, parser, sample_html):
        """본문 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert "디시인사이드 게시글 본문" in result.body
    
    def test_parse_post_author(self, parser, sample_html):
        """작성자 파싱 테스트 (data-nick 속성)"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert result.author == "디시유저"
    
    def test_parse_post_date(self, parser, sample_html):
        """날짜 파싱 테스트 (title 속성에서)"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert result.created_at is not None
        assert result.created_at.year == 2024
        assert result.created_at.month == 12
        assert result.created_at.day == 23
    
    def test_parse_post_view_count(self, parser, sample_html):
        """조회수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert result.view_count == 9999
    
    def test_parse_post_like_count(self, parser, sample_html):
        """추천수 파싱 테스트"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert result.like_count == 123
    
    def test_parse_post_site(self, parser, sample_html):
        """사이트 필드 테스트"""
        result = parser.parse_post(sample_html, "https://gall.dcinside.com/test/1", "테스트")
        assert result.site == "dcinside.com"
    
    def test_parse_comments(self, parser, sample_html):
        """댓글 파싱 테스트"""
        comments = parser.parse_comments(sample_html)
        assert len(comments) == 2
        assert comments[0].author == "디시댓글러"
        assert "디시 첫 번째 댓글" in comments[0].content
        assert comments[0].like_count == 7
    
    def test_parse_deleted_comment_skipped(self, parser):
        """삭제된 댓글 스킵 테스트"""
        html = """
        <div class="reply_list">
            <div class="reply_item">
                <div class="del_reply">삭제된 댓글입니다.</div>
            </div>
            <div class="reply_item">
                <span class="nickname">유저</span>
                <div class="reply_content">정상 댓글</div>
            </div>
        </div>
        """
        comments = parser.parse_comments(html)
        assert len(comments) == 1
        assert comments[0].content == "정상 댓글"


class TestParserRegistryIntegration:
    """ParserRegistry와 사이트별 파서 통합 테스트"""
    
    @pytest.fixture
    def registry(self):
        registry = ParserRegistry()
        registry.register(InvenParser())
        registry.register(RuliwebParser())
        registry.register(DCInsideParser())
        registry.set_generic_parser(GenericParser())
        return registry
    
    def test_inven_parser_selection(self, registry):
        """인벤 URL에 대해 InvenParser 선택"""
        parser = registry.get_parser("https://www.inven.co.kr/board/lostark/1234")
        assert isinstance(parser, InvenParser)
    
    def test_inven_mobile_parser_selection(self, registry):
        """인벤 모바일 URL에 대해 InvenParser 선택"""
        parser = registry.get_parser("https://m.inven.co.kr/board/lostark/1234")
        assert isinstance(parser, InvenParser)
    
    def test_ruliweb_parser_selection(self, registry):
        """루리웹 URL에 대해 RuliwebParser 선택"""
        parser = registry.get_parser("https://bbs.ruliweb.com/game/1234")
        assert isinstance(parser, RuliwebParser)
    
    def test_dcinside_parser_selection(self, registry):
        """디시인사이드 URL에 대해 DCInsideParser 선택"""
        parser = registry.get_parser("https://gall.dcinside.com/mgallery/board/1234")
        assert isinstance(parser, DCInsideParser)
    
    def test_unknown_site_uses_generic(self, registry):
        """알 수 없는 사이트에 대해 GenericParser 선택"""
        parser = registry.get_parser("https://unknown-site.com/post/1234")
        assert isinstance(parser, GenericParser)
    
    def test_has_parser_for_registered_sites(self, registry):
        """등록된 사이트에 대해 has_parser_for가 True 반환"""
        assert registry.has_parser_for("https://www.inven.co.kr/test")
        assert registry.has_parser_for("https://bbs.ruliweb.com/test")
        assert registry.has_parser_for("https://gall.dcinside.com/test")
    
    def test_has_parser_for_unknown_site(self, registry):
        """미등록 사이트에 대해 has_parser_for가 False 반환"""
        assert not registry.has_parser_for("https://unknown.com/test")
    
    def test_registered_domains_list(self, registry):
        """등록된 도메인 목록 확인"""
        domains = registry.get_registered_domains()
        assert "inven.co.kr" in domains
        assert "ruliweb.com" in domains
        assert "dcinside.com" in domains


class TestParserEdgeCases:
    """파서 엣지 케이스 테스트"""
    
    def test_inven_parser_no_comments(self):
        """댓글 없는 인벤 게시글"""
        parser = InvenParser()
        html = """
        <html><body>
            <div class="articleTitle">제목</div>
            <div class="articleContent">본문 내용입니다.</div>
        </body></html>
        """
        result = parser.parse_post(html, "https://inven.co.kr/test", "")
        assert result.comments == []
    
    def test_ruliweb_parser_special_characters(self):
        """특수문자 포함 루리웹 게시글"""
        parser = RuliwebParser()
        html = """
        <html><body>
            <div class="board_main">
                <div class="board_main_top">
                    <span class="subject">[리뷰] 게임 &amp; 리뷰 &lt;특수문자&gt;</span>
                </div>
                <div class="view_content">본문 &amp; 내용</div>
            </div>
        </body></html>
        """
        result = parser.parse_post(html, "https://ruliweb.com/test", "")
        assert "&" in result.title or "게임" in result.title
    
    def test_dcinside_parser_no_view_count(self):
        """조회수 없는 디시 게시글"""
        parser = DCInsideParser()
        html = """
        <html><body>
            <div class="gallview_head">
                <span class="title_subject">제목</span>
            </div>
            <div class="gallview_contents">
                <div class="inner">
                    <div class="writing_view_box">본문</div>
                </div>
            </div>
        </body></html>
        """
        result = parser.parse_post(html, "https://dcinside.com/test", "")
        assert result.view_count == 0
    
    def test_all_parsers_return_postcontent(self):
        """모든 파서가 PostContent 객체 반환"""
        parsers = [InvenParser(), RuliwebParser(), DCInsideParser()]
        html = "<html><body><h1>Test</h1><div>Content</div></body></html>"
        
        for parser in parsers:
            result = parser.parse_post(html, "https://test.com/1", "keyword")
            assert isinstance(result, PostContent)
            assert result.url == "https://test.com/1"
            assert result.keyword == "keyword"
    
    def test_all_parsers_return_comment_list(self):
        """모든 파서가 Comment 리스트 반환"""
        parsers = [InvenParser(), RuliwebParser(), DCInsideParser()]
        html = "<html><body></body></html>"
        
        for parser in parsers:
            result = parser.parse_comments(html)
            assert isinstance(result, list)
