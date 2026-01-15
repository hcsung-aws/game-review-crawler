# Requirements Document

## Introduction

본 문서는 게임별 커뮤니티 반응 분석 대시보드 개선을 위한 요구사항을 정의한다. 현재 대시보드는 단순한 게시글 목록과 기본 통계만 제공하여, 게임별 분석 구분이 불가능하고 정성적 분석(감성 분석, 이슈 우선순위화)이 부재하다. 본 개선을 통해 게임 운영팀이 커뮤니티 반응을 기반으로 게임 오류 해결 및 개선 방향을 신속하게 파악할 수 있도록 한다.

## Glossary

- **Game_Analytics_Dashboard**: 게임별 커뮤니티 반응을 분석하고 시각화하는 웹 대시보드 시스템
- **Sentiment_Analyzer**: 게시글 및 댓글의 긍정/부정/중립 감성을 분석하는 모듈
- **Sentiment_Score**: 텍스트의 감성을 나타내는 점수 (-1.0 ~ 1.0, 음수: 부정, 양수: 긍정)
- **Issue_Detector**: 커뮤니티에서 반복적으로 언급되는 이슈를 탐지하는 모듈
- **Issue_Priority**: 이슈의 긴급도를 나타내는 점수 (조회수, 댓글수, 반복 언급 빈도 기반)
- **Game_Profile**: 특정 게임에 대한 크롤링 설정 및 분석 결과를 포함하는 데이터 구조
- **Keyword_Cluster**: 유사한 의미를 가진 키워드들의 그룹
- **Trend_Indicator**: 특정 이슈나 감성의 시간에 따른 변화 추이
- **Hot_Issue**: 조회수, 댓글수, 반복 언급 빈도가 높아 긴급 대응이 필요한 이슈
- **QuickSight_Export**: AWS QuickSight 연동을 위한 데이터 내보내기 형식

## Requirements

### Requirement 1: 게임별 데이터 분리 및 관리

**User Story:** As a 게임 운영자, I want to 게임별로 크롤링 데이터를 분리하여 관리하고 싶다, so that 담당 게임의 커뮤니티 반응만 집중적으로 분석할 수 있다.

#### Acceptance Criteria

1. WHEN 크롤링을 수행한다 THEN Game_Analytics_Dashboard SHALL 게임별로 별도의 데이터 디렉토리에 결과를 저장한다
2. WHEN 대시보드에 접속한다 THEN Game_Analytics_Dashboard SHALL 게임 선택 인터페이스를 제공한다
3. WHEN 특정 게임을 선택한다 THEN Game_Analytics_Dashboard SHALL 해당 게임의 데이터만 필터링하여 표시한다
4. WHEN Game_Profile을 생성한다 THEN Game_Analytics_Dashboard SHALL 게임명, 검색 키워드, 대상 사이트 목록을 포함한다
5. WHEN QuickSight에서 데이터에 접근한다 THEN Game_Analytics_Dashboard SHALL 게임별로 별도 경로의 데이터 파일을 제공한다

### Requirement 2: 감성 분석 기능

**User Story:** As a 게임 운영자, I want to 게시글과 댓글의 긍정/부정 감성을 분석하고 싶다, so that 커뮤니티의 전반적인 분위기와 불만 사항을 파악할 수 있다.

#### Acceptance Criteria

1. WHEN 게시글 또는 댓글을 분석한다 THEN Sentiment_Analyzer SHALL Sentiment_Score를 계산한다
2. WHEN Sentiment_Score를 계산한다 THEN Sentiment_Analyzer SHALL -1.0(매우 부정)에서 1.0(매우 긍정) 사이의 값을 반환한다
3. WHEN 감성 분석 결과를 표시한다 THEN Game_Analytics_Dashboard SHALL 긍정/부정/중립 비율을 시각화한다
4. WHEN 부정적 게시글을 필터링한다 THEN Game_Analytics_Dashboard SHALL Sentiment_Score가 -0.3 미만인 게시글을 표시한다
5. WHEN 감성 분석을 수행한다 THEN Sentiment_Analyzer SHALL 한국어 텍스트에 대해 정확한 분석을 제공한다

### Requirement 3: 이슈 탐지 및 우선순위화

**User Story:** As a 게임 운영자, I want to 커뮤니티에서 자주 언급되는 이슈를 자동으로 탐지하고 우선순위를 매기고 싶다, so that 긴급한 문제를 빠르게 파악하고 대응할 수 있다.

#### Acceptance Criteria

1. WHEN 게시글 데이터를 분석한다 THEN Issue_Detector SHALL 반복적으로 언급되는 키워드와 주제를 추출한다
2. WHEN 이슈를 탐지한다 THEN Issue_Detector SHALL Keyword_Cluster를 생성하여 유사 이슈를 그룹화한다
3. WHEN Issue_Priority를 계산한다 THEN Issue_Detector SHALL 조회수, 댓글수, 언급 빈도를 가중 합산한다
4. WHEN Hot_Issue를 판별한다 THEN Issue_Detector SHALL Issue_Priority 상위 10%를 Hot_Issue로 분류한다
5. WHEN 이슈 목록을 표시한다 THEN Game_Analytics_Dashboard SHALL Issue_Priority 순으로 정렬하여 표시한다
6. WHEN Hot_Issue가 탐지된다 THEN Game_Analytics_Dashboard SHALL 시각적으로 강조하여 표시한다

### Requirement 4: 트렌드 분석

**User Story:** As a 게임 운영자, I want to 이슈와 감성의 시간별 변화 추이를 확인하고 싶다, so that 특정 업데이트나 이벤트 후의 반응 변화를 파악할 수 있다.

#### Acceptance Criteria

1. WHEN 트렌드를 분석한다 THEN Game_Analytics_Dashboard SHALL 일별/주별 Sentiment_Score 평균 추이를 계산한다
2. WHEN 트렌드를 시각화한다 THEN Game_Analytics_Dashboard SHALL 시계열 차트로 Trend_Indicator를 표시한다
3. WHEN 특정 기간을 선택한다 THEN Game_Analytics_Dashboard SHALL 해당 기간의 데이터만 필터링하여 분석한다
4. WHEN 이슈별 트렌드를 분석한다 THEN Game_Analytics_Dashboard SHALL 각 Keyword_Cluster의 언급 빈도 변화를 추적한다

### Requirement 5: 대시보드 UI 개선

**User Story:** As a 게임 운영자, I want to 직관적인 대시보드 인터페이스를 사용하고 싶다, so that 복잡한 분석 결과를 쉽게 이해하고 활용할 수 있다.

#### Acceptance Criteria

1. WHEN 대시보드 메인 페이지에 접속한다 THEN Game_Analytics_Dashboard SHALL 게임별 요약 카드를 표시한다
2. WHEN 게임 상세 페이지에 접속한다 THEN Game_Analytics_Dashboard SHALL 감성 분포, 이슈 목록, 트렌드 차트를 한 화면에 표시한다
3. WHEN Hot_Issue가 존재한다 THEN Game_Analytics_Dashboard SHALL 상단에 알림 배너로 표시한다
4. WHEN 게시글 목록을 표시한다 THEN Game_Analytics_Dashboard SHALL 조회수, 댓글수, 감성 점수로 정렬 옵션을 제공한다
5. WHEN 필터를 적용한다 THEN Game_Analytics_Dashboard SHALL 기간, 사이트, 감성, 이슈 유형으로 필터링을 지원한다

### Requirement 6: QuickSight 연동 데이터 내보내기

**User Story:** As a 데이터 분석가, I want to AWS QuickSight에서 분석 데이터를 활용하고 싶다, so that 고급 시각화 및 리포트를 생성할 수 있다.

#### Acceptance Criteria

1. WHEN 데이터를 내보낸다 THEN Game_Analytics_Dashboard SHALL 게임별로 별도 디렉토리에 CSV 파일을 생성한다
2. WHEN QuickSight_Export를 수행한다 THEN Game_Analytics_Dashboard SHALL posts.csv, comments.csv, sentiment.csv, issues.csv 파일을 생성한다
3. WHEN CSV 파일을 생성한다 THEN Game_Analytics_Dashboard SHALL QuickSight 호환 형식(UTF-8, 표준 날짜 형식)을 사용한다
4. WHEN 게임별 경로를 구성한다 THEN Game_Analytics_Dashboard SHALL `quicksight_data/{game_name}/` 형식의 디렉토리 구조를 사용한다

### Requirement 7: 버그/오류 관련 이슈 자동 분류

**User Story:** As a 게임 개발자, I want to 버그나 오류 관련 게시글을 자동으로 분류하고 싶다, so that 기술적 문제를 빠르게 파악하고 수정할 수 있다.

#### Acceptance Criteria

1. WHEN 게시글을 분석한다 THEN Issue_Detector SHALL 버그/오류 관련 키워드를 탐지한다
2. WHEN 버그 관련 게시글을 분류한다 THEN Issue_Detector SHALL "버그", "오류", "에러", "렉", "튕김", "접속불가" 등의 키워드를 기준으로 분류한다
3. WHEN 버그 이슈를 표시한다 THEN Game_Analytics_Dashboard SHALL 별도의 "버그 리포트" 섹션에 표시한다
4. WHEN 버그 이슈의 심각도를 판단한다 THEN Issue_Detector SHALL 언급 빈도와 부정적 감성 강도를 기반으로 심각도를 계산한다

### Requirement 8: 실시간 알림 기능

**User Story:** As a 게임 운영자, I want to 긴급 이슈 발생 시 알림을 받고 싶다, so that 신속하게 대응할 수 있다.

#### Acceptance Criteria

1. WHEN Hot_Issue가 새로 탐지된다 THEN Game_Analytics_Dashboard SHALL 대시보드 상단에 알림을 표시한다
2. WHEN 부정적 감성 급증이 탐지된다 THEN Game_Analytics_Dashboard SHALL 경고 알림을 표시한다
3. WHEN 알림을 표시한다 THEN Game_Analytics_Dashboard SHALL 이슈 요약과 관련 게시글 링크를 포함한다
4. IF 24시간 내 동일 이슈에 대한 게시글이 10개 이상 발생한다 THEN Game_Analytics_Dashboard SHALL 긴급 알림으로 분류한다

### Requirement 9: 대시보드 크롤링 관리

**User Story:** As a 게임 운영자, I want to 대시보드에서 직접 크롤링을 시작하고 관리하고 싶다, so that 별도의 스크립트 실행 없이 데이터를 수집하고 갱신할 수 있다.

#### Acceptance Criteria

1. WHEN 새 게임을 등록한다 THEN Game_Analytics_Dashboard SHALL 게임명, 키워드, 대상 사이트를 입력받아 GameProfile을 생성한다
2. WHEN 크롤링 시작 버튼을 클릭한다 THEN Game_Analytics_Dashboard SHALL 해당 게임의 크롤링을 백그라운드에서 실행한다
3. WHEN 크롤링이 진행 중이다 THEN Game_Analytics_Dashboard SHALL 진행 상태(검색 중/크롤링 중/완료)를 표시한다
4. WHEN 크롤링이 완료된다 THEN Game_Analytics_Dashboard SHALL 결과 요약(수집 게시글 수, 성공률, 소요시간)을 표시한다
5. WHEN 데이터 갱신 버튼을 클릭한다 THEN Game_Analytics_Dashboard SHALL 기존 게임의 최신 데이터를 재크롤링한다
6. WHEN 등록된 게임 목록을 조회한다 THEN Game_Analytics_Dashboard SHALL 각 게임의 마지막 크롤링 시간과 데이터 수를 표시한다
7. WHEN 게임 프로필을 수정한다 THEN Game_Analytics_Dashboard SHALL 키워드, 대상 사이트를 변경할 수 있다
8. WHEN 게임을 삭제한다 THEN Game_Analytics_Dashboard SHALL 해당 게임의 프로필과 크롤링 데이터를 삭제한다

