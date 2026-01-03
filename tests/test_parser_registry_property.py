"""
Property-Based Tests for ParserRegistry

**Feature: community-crawler-enhancement, Property 6: Parser Selection by Domain**
**Validates: Requirements 4.1, 4.3**

For any URL에 대해, 해당 도메인에 등록된 파서가 있으면 그 파서가 선택되고, 
없으면 GenericParser가 선택되어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import List

from crawler.parsers.base import ContentParser, ParserRegistry
from crawler.parsers.generic import GenericParser
from crawler.models.data_models import PostContent, Comment


class MockParser(ContentParser):
    """테스트용 Mock 파서"""
    
    def __init__(self, domains: List[str], name: str = "MockParser"):
        self._domains = domains
        self._name = name
    
    def parse_post(self, html: str, url: str, keyword: str = "") -> PostContent:
        return PostContent(
            url=url,
            title=f"Parsed by {self._name}",
            body="Mock body",
            site=self._domains[0] if self._domains else "unknown",
            keyword=keyword
        )
    
    def parse_comments(self, html: str) -> List[Comment]:
        return []
    
    def get_supported_domains(self) -> List[str]:
        return self._domains
    
    @property
    def name(self) -> str:
        return self._name


# Strategies for generating test data
@st.composite
def domain_strategy(draw):
    """유효한 도메인 생성 전략"""
    # 도메인 구성요소 생성
    subdomain = draw(st.one_of(
        st.just(""),
        st.sampled_from(["www", "m", "mobile", "api", "blog"])
    ))
    
    name = draw(st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
        min_size=3,
        max_size=15
    ).filter(lambda x: x and x[0].isalpha()))
    
    tld = draw(st.sampled_from([".com", ".co.kr", ".net", ".org", ".io"]))
    
    if subdomain:
        return f"{subdomain}.{name}{tld}"
    return f"{name}{tld}"


@st.composite
def url_strategy(draw, domain: str = None):
    """유효한 URL 생성 전략"""
    if domain is None:
        domain = draw(domain_strategy())
    
    protocol = draw(st.sampled_from(["http://", "https://"]))
    path = draw(st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789/-_"),
        min_size=0,
        max_size=50
    ))
    
    return f"{protocol}{domain}/{path}"


class TestParserSelectionByDomain:
    """
    **Feature: community-crawler-enhancement, Property 6: Parser Selection by Domain**
    **Validates: Requirements 4.1, 4.3**
    
    For any URL에 대해, 해당 도메인에 등록된 파서가 있으면 그 파서가 선택되고,
    없으면 GenericParser가 선택되어야 한다.
    """
    
    @given(domain=domain_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_registered_domain_returns_specific_parser(self, domain: str):
        """등록된 도메인에 대해 해당 파서가 반환되어야 함"""
        # Setup
        registry = ParserRegistry()
        mock_parser = MockParser([domain], f"Parser for {domain}")
        generic_parser = GenericParser()
        
        registry.register(mock_parser)
        registry.set_generic_parser(generic_parser)
        
        # URL 생성
        url = f"https://{domain}/some/path"
        
        # Test
        selected_parser = registry.get_parser(url)
        
        # Assert: 등록된 파서가 선택되어야 함
        assert selected_parser is mock_parser
        assert selected_parser is not generic_parser
    
    @given(
        registered_domain=domain_strategy(),
        unregistered_domain=domain_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_unregistered_domain_returns_generic_parser(self, registered_domain: str, unregistered_domain: str):
        """등록되지 않은 도메인에 대해 GenericParser가 반환되어야 함"""
        # 두 도메인이 다른 경우만 테스트
        assume(registered_domain.lower() != unregistered_domain.lower())
        assume(not unregistered_domain.lower().endswith('.' + registered_domain.lower()))
        assume(not registered_domain.lower().endswith('.' + unregistered_domain.lower()))
        
        # Setup
        registry = ParserRegistry()
        mock_parser = MockParser([registered_domain], f"Parser for {registered_domain}")
        generic_parser = GenericParser()
        
        registry.register(mock_parser)
        registry.set_generic_parser(generic_parser)
        
        # URL 생성 (등록되지 않은 도메인)
        url = f"https://{unregistered_domain}/some/path"
        
        # Test
        selected_parser = registry.get_parser(url)
        
        # Assert: GenericParser가 선택되어야 함
        assert selected_parser is generic_parser
        assert selected_parser is not mock_parser
    
    @given(
        base_domain=domain_strategy(),
        subdomain=st.sampled_from(["m", "www", "mobile", "api"])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_subdomain_matches_base_domain_parser(self, base_domain: str, subdomain: str):
        """서브도메인 URL이 기본 도메인 파서와 매칭되어야 함"""
        # Setup
        registry = ParserRegistry()
        mock_parser = MockParser([base_domain], f"Parser for {base_domain}")
        generic_parser = GenericParser()
        
        registry.register(mock_parser)
        registry.set_generic_parser(generic_parser)
        
        # 서브도메인 URL 생성
        subdomain_url = f"https://{subdomain}.{base_domain}/some/path"
        
        # Test
        selected_parser = registry.get_parser(subdomain_url)
        
        # Assert: 기본 도메인 파서가 선택되어야 함
        assert selected_parser is mock_parser
    
    @given(domains=st.lists(domain_strategy(), min_size=1, max_size=5, unique=True))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_multiple_parsers_select_correct_one(self, domains: List[str]):
        """여러 파서가 등록된 경우 올바른 파서가 선택되어야 함"""
        # Setup
        registry = ParserRegistry()
        generic_parser = GenericParser()
        registry.set_generic_parser(generic_parser)
        
        parsers = {}
        for domain in domains:
            parser = MockParser([domain], f"Parser for {domain}")
            registry.register(parser)
            parsers[domain.lower()] = parser
        
        # Test: 각 도메인에 대해 올바른 파서가 선택되는지 확인
        for domain in domains:
            url = f"https://{domain}/test/path"
            selected_parser = registry.get_parser(url)
            
            # Assert
            assert selected_parser is parsers[domain.lower()]
    
    @given(domain=domain_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_no_generic_parser_returns_none(self, domain: str):
        """GenericParser가 설정되지 않고 도메인이 등록되지 않은 경우 None 반환"""
        # Setup
        registry = ParserRegistry()
        # GenericParser를 설정하지 않음
        
        # URL 생성
        url = f"https://{domain}/some/path"
        
        # Test
        selected_parser = registry.get_parser(url)
        
        # Assert: None이 반환되어야 함
        assert selected_parser is None
    
    @given(domain=domain_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_has_parser_for_registered_domain(self, domain: str):
        """등록된 도메인에 대해 has_parser_for가 True 반환"""
        # Setup
        registry = ParserRegistry()
        mock_parser = MockParser([domain], f"Parser for {domain}")
        registry.register(mock_parser)
        
        # URL 생성
        url = f"https://{domain}/some/path"
        
        # Test & Assert
        assert registry.has_parser_for(url) is True
    
    @given(
        registered_domain=domain_strategy(),
        unregistered_domain=domain_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_has_parser_for_unregistered_domain(self, registered_domain: str, unregistered_domain: str):
        """등록되지 않은 도메인에 대해 has_parser_for가 False 반환"""
        # 두 도메인이 다른 경우만 테스트
        assume(registered_domain.lower() != unregistered_domain.lower())
        assume(not unregistered_domain.lower().endswith('.' + registered_domain.lower()))
        assume(not registered_domain.lower().endswith('.' + unregistered_domain.lower()))
        
        # Setup
        registry = ParserRegistry()
        mock_parser = MockParser([registered_domain], f"Parser for {registered_domain}")
        registry.register(mock_parser)
        
        # URL 생성 (등록되지 않은 도메인)
        url = f"https://{unregistered_domain}/some/path"
        
        # Test & Assert
        assert registry.has_parser_for(url) is False
