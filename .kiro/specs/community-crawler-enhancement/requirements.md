# Requirements Document

## Introduction

본 문서는 기존 웹 크롤러의 커뮤니티 크롤링 기능을 개선하기 위한 요구사항을 정의한다. 현재 크롤러는 DuckDuckGo 검색 API를 통해 검색 결과의 snippet만 수집하고 있어, 실제 게시글 본문, 날짜, 댓글 등 핵심 데이터를 놓치고 있다. 또한 검색 결과의 정확도가 낮아 관련 없는 콘텐츠가 다수 포함되는 문제가 있다.

## Glossary

- **Community_Crawler**: 게임 커뮤니티 사이트에서 리뷰 및 의견 데이터를 수집하는 시스템
- **Target_Site**: 크롤링 대상이 되는 커뮤니티 사이트 (인벤, 루리웹, 디시인사이드, 게임메카 등)
- **Post_Content**: 게시글의 제목, 본문, 작성일, 조회수, 추천수를 포함하는 데이터
- **Comment_Data**: 게시글에 달린 댓글 및 대댓글 데이터
- **Relevance_Score**: 검색 키워드와 콘텐츠의 관련성을 나타내는 점수 (0.0 ~ 1.0)
- **Rate_Limiter**: 대상 사이트에 과부하를 주지 않기 위한 요청 속도 제어 메커니즘
- **Content_Parser**: 각 사이트별 HTML 구조에 맞춰 데이터를 추출하는 모듈
- **Search_Adapter**: 검색 기능을 제공하는 외부 API 또는 직접 크롤링 모듈 (DuckDuckGo, Google CSE, 직접 크롤링)
- **Search_Cache**: 검색 결과를 임시 저장하여 중복 요청을 방지하는 캐시 시스템
- **Failover**: 하나의 검색 엔진이 실패하면 자동으로 다른 검색 엔진으로 전환하는 메커니즘

## Requirements

### Requirement 1

**User Story:** As a 데이터 분석가, I want to 실제 게시글 본문을 수집하고 싶다, so that 검색 snippet이 아닌 완전한 리뷰 데이터를 분석할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 검색 결과 URL을 획득한다 THEN Community_Crawler SHALL 해당 URL에 접속하여 Post_Content를 추출한다
2. WHEN Community_Crawler가 게시글 페이지를 파싱한다 THEN Community_Crawler SHALL 제목, 본문, 작성일, 조회수, 추천수를 구조화된 형태로 저장한다
3. WHEN 게시글 본문 추출에 실패한다 THEN Community_Crawler SHALL 에러를 로깅하고 다음 URL로 진행한다
4. WHEN Post_Content를 저장한다 THEN Community_Crawler SHALL JSON 형식으로 직렬화하여 파일에 기록한다

### Requirement 2

**User Story:** As a 데이터 분석가, I want to 댓글 데이터도 함께 수집하고 싶다, so that 게시글에 대한 커뮤니티 반응을 분석할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 게시글을 파싱한다 THEN Community_Crawler SHALL Comment_Data를 함께 추출한다
2. WHEN Comment_Data를 추출한다 THEN Community_Crawler SHALL 댓글 작성자, 내용, 작성일, 추천수를 포함한다
3. WHEN 댓글이 페이지네이션되어 있다 THEN Community_Crawler SHALL 최대 3페이지까지의 댓글을 수집한다
4. WHEN 댓글이 없는 게시글이다 THEN Community_Crawler SHALL 빈 배열로 Comment_Data를 저장한다

### Requirement 3

**User Story:** As a 데이터 분석가, I want to 검색 결과의 관련성을 필터링하고 싶다, so that 관련 없는 콘텐츠를 제외하고 정확한 데이터만 수집할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 검색 결과를 수신한다 THEN Community_Crawler SHALL 각 결과에 대해 Relevance_Score를 계산한다
2. WHEN Relevance_Score가 0.5 미만이다 THEN Community_Crawler SHALL 해당 결과를 수집 대상에서 제외한다
3. WHEN Relevance_Score를 계산한다 THEN Community_Crawler SHALL 제목과 본문에서 키워드 출현 빈도와 위치를 고려한다
4. WHEN 중복 URL이 발견된다 THEN Community_Crawler SHALL 해당 URL을 한 번만 처리한다

### Requirement 4

**User Story:** As a 시스템 관리자, I want to 각 커뮤니티 사이트별 맞춤 파서를 사용하고 싶다, so that 사이트별 HTML 구조 차이에 대응할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 Target_Site에 접근한다 THEN Community_Crawler SHALL 해당 사이트에 맞는 Content_Parser를 선택한다
2. WHEN 새로운 Target_Site를 추가한다 THEN Community_Crawler SHALL 플러그인 방식으로 Content_Parser를 등록할 수 있다
3. WHEN Content_Parser가 등록되지 않은 사이트이다 THEN Community_Crawler SHALL 범용 HTML 파서를 사용하여 기본 추출을 시도한다
4. WHEN Content_Parser가 파싱에 실패한다 THEN Community_Crawler SHALL 실패 원인을 로깅하고 범용 파서로 폴백한다

### Requirement 5

**User Story:** As a 시스템 관리자, I want to 크롤링 속도를 제어하고 싶다, so that 대상 사이트에 과부하를 주지 않고 차단을 방지할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 동일 도메인에 연속 요청한다 THEN Community_Crawler SHALL Rate_Limiter를 통해 최소 3초 간격을 유지한다
2. WHEN HTTP 429 (Too Many Requests) 응답을 수신한다 THEN Community_Crawler SHALL 지수 백오프 방식으로 재시도한다
3. WHEN 재시도 횟수가 3회를 초과한다 THEN Community_Crawler SHALL 해당 도메인 크롤링을 일시 중단하고 다음 도메인으로 진행한다
4. WHEN Rate_Limiter 설정을 변경한다 THEN Community_Crawler SHALL 도메인별로 개별 설정을 적용할 수 있다

### Requirement 6

**User Story:** As a 데이터 분석가, I want to 수집 결과를 구조화된 형태로 저장하고 싶다, so that 후속 분석 작업에 활용할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 데이터를 저장한다 THEN Community_Crawler SHALL 게시글과 댓글을 관계형 구조로 저장한다
2. WHEN 저장 형식을 지정한다 THEN Community_Crawler SHALL JSON 및 CSV 형식을 지원한다
3. WHEN 대용량 데이터를 저장한다 THEN Community_Crawler SHALL 파일을 날짜별로 분할하여 저장한다
4. WHEN 저장된 데이터를 로드한다 THEN Community_Crawler SHALL 동일한 구조의 객체로 역직렬화한다

### Requirement 7

**User Story:** As a 시스템 관리자, I want to 다중 검색 엔진을 활용하고 싶다, so that 단일 검색 API의 스로틀링 문제를 회피하고 안정적으로 검색할 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 검색을 수행한다 THEN Community_Crawler SHALL Search_Adapter를 통해 DuckDuckGo, Google CSE, 직접 크롤링 중 하나를 사용한다
2. WHEN 현재 Search_Adapter가 스로틀링되거나 실패한다 THEN Community_Crawler SHALL Failover 메커니즘을 통해 다음 Search_Adapter로 자동 전환한다
3. WHEN 동일한 검색 쿼리가 반복된다 THEN Community_Crawler SHALL Search_Cache를 확인하여 캐시된 결과를 반환한다
4. WHEN Search_Cache의 결과가 만료된다 THEN Community_Crawler SHALL 새로운 검색을 수행하고 캐시를 갱신한다
5. WHEN 직접 크롤링 모드를 사용한다 THEN Community_Crawler SHALL Target_Site의 게시판 목록 페이지에서 게시글 URL을 추출한다

### Requirement 8

**User Story:** As a 시스템 관리자, I want to 봇 탐지를 회피하고 싶다, so that 크롤링이 차단되지 않고 지속적으로 수행될 수 있다.

#### Acceptance Criteria

1. WHEN Community_Crawler가 요청을 전송한다 THEN Community_Crawler SHALL 요청 간격에 랜덤 지연(Jitter)을 추가한다
2. WHEN 랜덤 지연을 적용한다 THEN Community_Crawler SHALL 설정된 범위 내에서 무작위 시간을 추가한다
3. WHEN HTTP 요청을 전송한다 THEN Community_Crawler SHALL 실제 브라우저와 유사한 User-Agent 헤더를 사용한다
