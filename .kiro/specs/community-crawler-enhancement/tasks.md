# Implementation Plan

- [x] 1. 프로젝트 구조 및 데이터 모델 설정






  - [x] 1.1 프로젝트 디렉토리 구조 생성

    - `crawler/` 디렉토리 하위에 `models/`, `parsers/`, `utils/`, `exporters/` 생성
    - `tests/` 디렉토리 생성
    - _Requirements: 4.2_

  - [x] 1.2 데이터 모델 클래스 구현

    - `CrawlerConfig`, `SearchResult`, `PostContent`, `Comment` dataclass 구현
    - 필수 필드 및 기본값 정의
    - _Requirements: 1.2, 2.2, 6.1_

  - [x] 1.3 Property test: 직렬화 Round-Trip

    - **Property 1: Serialization Round-Trip**
    - **Validates: Requirements 1.4, 6.4**

  - [x] 1.4 Unit test: 데이터 모델 유효성 검증

    - PostContent, Comment 객체 생성 및 필드 검증 테스트
    - _Requirements: 1.2, 2.2_

- [x] 2. RelevanceFilter 구현



  - [x] 2.1 RelevanceFilter 클래스 구현


    - `calculate_score()` 메서드: 키워드 출현 빈도 및 위치 기반 점수 계산
    - `filter()` 메서드: threshold 기반 필터링
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.2 Property test: 관련성 점수 범위 및 필터링

    - **Property 3: Relevance Score Range and Filtering**
    - **Validates: Requirements 3.1, 3.2**
  - [x] 2.3 Property test: 키워드 빈도와 점수 관계


    - **Property 4: Keyword Frequency Affects Score**
    - **Validates: Requirements 3.3**

  - [x] 2.4 URL 중복 제거 유틸리티 구현

    - 중복 URL 필터링 함수 구현
    - _Requirements: 3.4_


  - [x] 2.5 Property test: URL 중복 제거

    - **Property 5: URL Deduplication**
    - **Validates: Requirements 3.4**

- [x] 3. Checkpoint - 모든 테스트 통과 확인





  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. RateLimiter 구현




  - [x] 4.1 RateLimiter 클래스 구현

    - `wait()` 메서드: 도메인별 대기 시간 적용
    - `handle_rate_limit()` 메서드: 지수 백오프 처리
    - 도메인별 개별 설정 지원
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.2 Property test: Rate Limiter 최소 지연

    - **Property 7: Rate Limiter Minimum Delay**
    - **Validates: Requirements 5.1**

  - [x] 4.3 Property test: 지수 백오프
    - **Property 8: Exponential Backoff on Rate Limit**
    - **Validates: Requirements 5.2**
  - [x] 4.4 Property test: 도메인별 Rate Limit 설정
    - **Property 9: Domain-Specific Rate Limit Settings**
    - **Validates: Requirements 5.4**

- [x] 5. ParserRegistry 및 기본 파서 구현
  - [x] 5.1 ContentParser 추상 클래스 및 ParserRegistry 구현
    - `ContentParser` ABC 정의
    - `ParserRegistry.register()`, `get_parser()` 메서드 구현
    - _Requirements: 4.1, 4.2_
  - [x] 5.2 GenericParser 구현
    - BeautifulSoup 기반 범용 HTML 파싱
    - 제목, 본문, 날짜 추출 로직
    - _Requirements: 4.3_
  - [x] 5.3 Property test: 도메인별 파서 선택
    - **Property 6: Parser Selection by Domain**
    - **Validates: Requirements 4.1, 4.3**
  - [x] 5.4 Property test: 파싱 결과 필수 필드 포함
    - **Property 2: Parsed Content Contains Required Fields**
    - **Validates: Requirements 1.2, 2.2**

- [x] 6. Checkpoint - 모든 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. 사이트별 파서 구현
  - [x] 7.1 InvenParser 구현
    - inven.co.kr 게시글 및 댓글 파싱
    - _Requirements: 4.1, 1.1, 2.1_
  - [x] 7.2 RuliwebParser 구현
    - ruliweb.com 게시글 및 댓글 파싱
    - _Requirements: 4.1, 1.1, 2.1_
  - [x] 7.3 DCInsideParser 구현
    - dcinside.com 게시글 및 댓글 파싱
    - _Requirements: 4.1, 1.1, 2.1_
  - [x] 7.4 Unit test: 각 사이트별 파서 동작 검증
    - 샘플 HTML에 대한 파싱 결과 검증
    - _Requirements: 4.1_

- [x] 8. ContentCrawler 구현
  - [x] 8.1 ContentCrawler 클래스 구현
    - `crawl_post()` 메서드: 게시글 본문 추출
    - `crawl_comments()` 메서드: 댓글 추출 (최대 3페이지)
    - RateLimiter 및 ParserRegistry 통합
    - _Requirements: 1.1, 1.3, 2.1, 2.3, 4.4_
  - [x] 8.2 Unit test: ContentCrawler 에러 처리
    - 파싱 실패 시 폴백 동작 검증
    - _Requirements: 1.3, 4.4_

- [-] 9. SearchEngineManager 및 어댑터 구현
  - [x] 9.1 SearchEngineManager 클래스 구현
    - 다중 어댑터 관리 및 failover 로직
    - SearchCache 통합
    - _Requirements: 7.1, 7.2_
  - [x] 9.2 DuckDuckGoAdapter 구현
    - 기존 DuckDuckGo API 통합
    - _Requirements: 7.1_
  - [x] 9.3 GoogleCSEAdapter 구현
    - Google Custom Search Engine API 통합
    - API 키 설정 지원
    - _Requirements: 7.1_
  - [x] 9.4 DirectCrawlAdapter 구현
    - 커뮤니티 사이트 게시판 목록 직접 크롤링
    - _Requirements: 7.1, 7.5_
  - [x] 9.5 SearchCache 구현
    - 검색 결과 캐싱 및 TTL 관리
    - _Requirements: 7.3, 7.4_
  - [x] 9.6 Property test: Search Adapter Failover
    - **Property 11: Search Adapter Failover**
    - **Validates: Requirements 7.2**
  - [x] 9.7 Property test: Search Cache Consistency
    - **Property 12: Search Cache Consistency**
    - **Validates: Requirements 7.3, 7.4**
  - [x] 9.8 Jitter 기능 RateLimiter에 추가
    - `_add_jitter()` 메서드 구현
    - 랜덤 지연 범위 설정 지원
    - _Requirements: 8.1, 8.2_
  - [x] 9.9 Property test: Jitter Range Compliance
    - **Property 13: Jitter Range Compliance**
    - **Validates: Requirements 8.1, 8.2**
  - [x] 9.10 Unit test: SearchEngineManager 검색 및 필터링
    - 검색 결과 필터링 동작 검증
    - _Requirements: 3.1, 3.2_

- [x] 10. DataStore 및 Exporter 구현
  - [x] 10.1 DataStore 클래스 구현
    - 게시글 추가 및 관리
    - 날짜별 파일 분할 로직
    - _Requirements: 6.1, 6.3_
  - [x] 10.2 JSONExporter 및 CSVExporter 구현
    - JSON 및 CSV 형식 내보내기
    - _Requirements: 6.2_
  - [x] 10.3 Property test: 게시글-댓글 관계 무결성
    - **Property 10: Post-Comment Relationship Integrity**
    - **Validates: Requirements 6.1**
  - [x] 10.4 Unit test: 내보내기 형식 검증
    - JSON, CSV 파일 생성 및 구조 검증
    - _Requirements: 6.2_

- [x] 11. Checkpoint - 모든 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. CrawlerOrchestrator 및 통합
  - [x] 12.1 CrawlerOrchestrator 클래스 구현
    - 전체 크롤링 프로세스 조율
    - SearchEngine, ContentCrawler, DataStore 통합
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 6.1_
  - [x] 12.2 기존 search_review.py와 통합
    - Bedrock 키워드 생성 기능 연동
    - 기존 인터페이스 유지하면서 새 기능 적용
    - _Requirements: 1.1_
  - [x] 12.3 Integration test: 전체 크롤링 흐름
    - 검색 → 크롤링 → 저장 end-to-end 테스트
    - _Requirements: 1.1, 1.2, 2.1, 6.1_

- [x] 13. Final Checkpoint - 모든 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.
