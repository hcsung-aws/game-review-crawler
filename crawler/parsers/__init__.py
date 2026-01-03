# Parsers Package
"""사이트별 콘텐츠 파서

Requirements: 4.1, 4.2, 4.3
- ContentParser: 파서 추상 클래스
- ParserRegistry: 파서 레지스트리
- GenericParser: 범용 HTML 파서
- InvenParser: 인벤 전용 파서
- RuliwebParser: 루리웹 전용 파서
- DCInsideParser: 디시인사이드 전용 파서
"""

from crawler.parsers.base import ContentParser, ParserRegistry
from crawler.parsers.generic import GenericParser
from crawler.parsers.inven import InvenParser
from crawler.parsers.ruliweb import RuliwebParser
from crawler.parsers.dcinside import DCInsideParser

__all__ = [
    "ContentParser",
    "ParserRegistry",
    "GenericParser",
    "InvenParser",
    "RuliwebParser",
    "DCInsideParser",
]
