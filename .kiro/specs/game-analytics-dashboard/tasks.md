# Implementation Plan: Game Analytics Dashboard

## Overview

게임별 커뮤니티 반응 분석 대시보드를 구현한다. 기존 크롤러 시스템을 확장하여 감성 분석, 이슈 탐지, 트렌드 분석 기능을 추가하고, 게임별로 분리된 대시보드와 QuickSight 연동을 지원한다.

**구현 방식**: 게임별 데이터 필터링 + 기본 대시보드를 먼저 구현하여 바로 확인 가능하게 한 후, 각 분석 기능을 순차적으로 대시보드에 추가한다.

## Tasks

- [x] 1. 데이터 모델 및 게임 프로필 관리
  - [x] 1.1 분석용 데이터 모델 구현
    - `SentimentResult`, `KeywordCluster`, `DetectedIssue`, `TrendPoint`, `TrendData`, `GameAnalysisResult` dataclass 구현
    - `crawler/models/analysis_models.py` 파일 생성
    - _Requirements: 2.1, 3.2, 4.1_

  - [x] 1.2 GameProfile 및 GameProfileManager 구현
    - `GameProfile` dataclass 구현
    - `GameProfileManager` 클래스 구현 (등록, 조회, 경로 관리)
    - `crawler/models/game_profile.py` 파일 생성
    - _Requirements: 1.1, 1.4, 1.5_

  - [x] 1.3 Property test: 게임별 데이터 경로 일관성
    - **Property 1: Game Data Path Consistency**
    - **Validates: Requirements 1.1, 1.5, 6.4**

  - [x] 1.4 Property test: GameProfile 필수 필드
    - **Property 3: GameProfile Required Fields**
    - **Validates: Requirements 1.4**

- [x] 2. Checkpoint - 데이터 모델 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. 감성 분석 모듈 구현
  - [x] 3.1 한국어 감성 사전 구축
    - 긍정/부정 키워드 사전 파일 생성
    - `crawler/analysis/lexicon/` 디렉토리에 positive.txt, negative.txt 생성
    - _Requirements: 2.5_

  - [x] 3.2 SentimentAnalyzer 클래스 구현
    - `analyze()` 메서드: 텍스트 감성 분석
    - `analyze_post()` 메서드: 게시글 전체 감성 분석
    - `analyze_comments()` 메서드: 댓글 목록 감성 분석
    - `crawler/analysis/sentiment.py` 파일 생성
    - _Requirements: 2.1, 2.2, 2.5_

  - [x] 3.3 Property test: 감성 점수 범위
    - **Property 4: Sentiment Score Range**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 3.4 Property test: 부정적 게시글 필터링
    - **Property 5: Negative Post Filtering**
    - **Validates: Requirements 2.4**

- [x] 4. 게임별 데이터 필터링 및 기본 대시보드 구현
  - [x] 4.1 DataFilter 클래스 구현
    - 게임별 데이터 필터링
    - 기간, 사이트 필터링
    - 조회수, 댓글수 정렬
    - `crawler/utils/data_filter.py` 파일 생성
    - _Requirements: 1.3, 4.3, 5.4, 5.5_

  - [x] 4.2 Property test: 게임별 데이터 필터링
    - **Property 2: Game Data Filtering**
    - **Validates: Requirements 1.3**

  - [x] 4.3 게임 목록 API 및 메인 페이지 구현
    - `GET /api/games` - 게임 목록 조회
    - 게임별 요약 카드 표시 (게임명, 총 게시글 수, 최근 업데이트)
    - `dashboard/app.py` 수정
    - `dashboard/templates/index.html` 수정
    - _Requirements: 1.2, 5.1_

  - [x] 4.4 게임 상세 페이지 기본 구조 구현
    - `GET /api/game/<game_id>/posts` - 게임별 게시글 목록
    - 게시글 목록 테이블 (제목, 작성일, 조회수, 댓글수)
    - 기본 필터 UI (기간, 사이트)
    - `dashboard/templates/game_dashboard.html` 생성
    - _Requirements: 1.3, 5.2_

- [x] 5. Checkpoint - 게임별 필터링 대시보드 확인
  - 대시보드에서 게임 목록과 게임별 게시글이 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 감성 분석 대시보드 추가
  - [x] 6.1 감성 분석 API 구현
    - `GET /api/game/<game_id>/sentiment` - 감성 분석 결과
    - 감성 분포, 평균 점수, 부정적 게시글 목록 반환
    - _Requirements: 2.3_

  - [x] 6.2 게임 상세 대시보드 - 감성 분석 섹션 추가
    - 감성 분포 차트 (긍정/부정/중립 비율)
    - 평균 감성 점수 표시
    - 부정적 게시글 하이라이트
    - `dashboard/templates/game_dashboard.html` 수정
    - _Requirements: 2.3, 5.2_

- [x] 7. Checkpoint - 감성 분석 대시보드 확인
  - 대시보드에서 감성 분석 결과가 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. 이슈 탐지 모듈 구현
  - [x] 8.1 키워드 추출기 구현
    - 형태소 분석 기반 키워드 추출
    - 불용어 필터링
    - `crawler/analysis/keyword_extractor.py` 파일 생성
    - _Requirements: 3.1_

  - [x] 8.2 IssueDetector 클래스 구현
    - `extract_keywords()` 메서드: 키워드 추출
    - `cluster_keywords()` 메서드: 유사 키워드 클러스터링
    - `detect_issues()` 메서드: 이슈 탐지 및 우선순위화
    - `calculate_priority()` 메서드: 우선순위 점수 계산
    - `detect_hot_issues()` 메서드: Hot Issue 탐지
    - `crawler/analysis/issue_detector.py` 파일 생성
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 8.3 Property test: 키워드 클러스터링 완전성
    - **Property 7: Keyword Clustering Completeness**
    - **Validates: Requirements 3.2**

  - [x] 8.4 Property test: 이슈 우선순위 단조성
    - **Property 8: Issue Priority Monotonicity**
    - **Validates: Requirements 3.3**

  - [x] 8.5 Property test: Hot Issue 상위 백분위
    - **Property 9: Hot Issue Top Percentile**
    - **Validates: Requirements 3.4**

  - [x] 8.6 Property test: 이슈 목록 정렬
    - **Property 10: Issue List Sorting**
    - **Validates: Requirements 3.5**

- [x] 9. 이슈 탐지 대시보드 추가
  - [x] 9.1 이슈 분석 API 구현
    - `GET /api/game/<game_id>/issues` - 이슈 목록
    - `GET /api/game/<game_id>/issues/hot` - Hot Issue 목록
    - _Requirements: 3.5, 3.6_

  - [x] 9.2 게임 상세 대시보드 - 이슈 섹션 추가
    - 이슈 목록 테이블 (우선순위 순)
    - Hot Issue 강조 표시
    - `dashboard/templates/game_dashboard.html` 수정
    - _Requirements: 3.5, 3.6, 5.2_

  - [x] 9.3 Hot Issue 알림 배너 구현
    - 상단 알림 배너 컴포넌트
    - 이슈 요약 및 관련 게시글 링크
    - _Requirements: 5.3, 8.1, 8.3_

- [x] 10. Checkpoint - 이슈 탐지 대시보드 확인
  - 대시보드에서 이슈 목록과 Hot Issue가 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. 버그 분류 모듈 및 대시보드 구현
  - [x] 11.1 버그 키워드 탐지 기능 구현
    - `classify_bug()` 메서드: 버그/오류 관련 게시글 분류
    - `calculate_severity()` 메서드: 버그 심각도 계산
    - IssueDetector 클래스에 추가
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 11.2 Property test: 버그 키워드 탐지
    - **Property 17: Bug Keyword Detection**
    - **Validates: Requirements 7.1, 7.2**

  - [x] 11.3 Property test: 버그 심각도 단조성
    - **Property 18: Bug Severity Monotonicity**
    - **Validates: Requirements 7.4**

  - [x] 11.4 버그 이슈 API 및 페이지 구현
    - `GET /api/game/<game_id>/bugs` - 버그 이슈 목록
    - 버그 이슈 목록 및 심각도 표시
    - `dashboard/templates/bug_report.html` 생성
    - _Requirements: 7.3_

- [x] 12. Checkpoint - 버그 리포트 대시보드 확인
  - 대시보드에서 버그 이슈가 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. 트렌드 분석 모듈 및 대시보드 구현
  - [x] 13.1 TrendAnalyzer 클래스 구현
    - `analyze_sentiment_trend()` 메서드: 감성 점수 시계열 분석
    - `analyze_issue_trend()` 메서드: 이슈 언급 빈도 추이
    - `detect_sentiment_spike()` 메서드: 부정적 감성 급증 탐지
    - `crawler/analysis/trend_analyzer.py` 파일 생성
    - _Requirements: 4.1, 4.3, 4.4_

  - [x] 13.2 Property test: 트렌드 계산
    - **Property 11: Sentiment Trend Calculation**
    - **Validates: Requirements 4.1**

  - [x] 13.3 Property test: 기간 필터링
    - **Property 12: Date Range Filtering**
    - **Validates: Requirements 4.3**

  - [x] 13.4 트렌드 API 및 차트 구현
    - `GET /api/game/<game_id>/sentiment/trend` - 감성 트렌드
    - `GET /api/game/<game_id>/issues/<issue_id>/trend` - 이슈별 트렌드
    - 일별/주별 감성 점수 추이 차트
    - 이슈별 언급 빈도 변화 차트
    - `dashboard/templates/game_dashboard.html` 수정
    - _Requirements: 4.1, 4.2, 5.2_

- [x] 14. Checkpoint - 트렌드 분석 대시보드 확인
  - 대시보드에서 트렌드 차트가 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. 알림 시스템 구현
  - [x] 15.1 AlertManager 클래스 구현
    - Hot Issue 알림 생성
    - 부정적 감성 급증 알림 생성
    - 긴급 알림 분류 (24시간 내 10개 이상)
    - `crawler/analysis/alert_manager.py` 파일 생성
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 15.2 Property test: 긴급 알림 분류
    - **Property 19: Urgent Alert Classification**
    - **Validates: Requirements 8.4**

  - [x] 15.3 알림 API 및 UI 구현
    - `GET /api/game/<game_id>/alerts` - 알림 목록
    - 부정적 감성 급증 경고 배너
    - _Requirements: 8.2, 8.3_

- [x] 16. Checkpoint - 알림 시스템 확인
  - 대시보드에서 알림이 정상 표시되는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. 고급 필터 및 정렬 기능 추가
  - [x] 17.1 DataFilter 확장
    - 감성, 이슈 유형 필터링 추가
    - 감성 점수 정렬 추가
    - _Requirements: 5.4, 5.5_

  - [x] 17.2 Property test: 게시글 정렬 옵션
    - **Property 13: Post Sorting Options**
    - **Validates: Requirements 5.4**

  - [x] 17.3 Property test: 다중 필터 적용
    - **Property 14: Multi-Filter Application**
    - **Validates: Requirements 5.5**

  - [x] 17.4 고급 필터 UI 구현
    - 감성, 이슈 유형 필터 추가
    - 감성 점수 정렬 옵션 추가
    - `dashboard/templates/game_dashboard.html` 수정
    - _Requirements: 5.4, 5.5_

- [x] 18. Checkpoint - 고급 필터 기능 확인
  - 대시보드에서 모든 필터와 정렬이 정상 동작하는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. QuickSight 내보내기 확장
  - [x] 19.1 GameQuickSightExporter 클래스 구현
    - 게임별 디렉토리 구조 생성
    - posts.csv, comments.csv, sentiment.csv, issues.csv 내보내기
    - `crawler/exporters/quicksight_exporter.py` 파일 생성
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 19.2 Property test: QuickSight 파일 생성
    - **Property 15: QuickSight Export Files**
    - **Validates: Requirements 6.2**

  - [x] 19.3 Property test: CSV 형식 호환성
    - **Property 16: CSV Format Compatibility**
    - **Validates: Requirements 6.3**

- [x] 20. 분석 데이터 저장소 구현
  - [x] 20.1 AnalysisDataStore 클래스 구현
    - 분석 결과 저장 및 로드
    - 게임별 최신 분석 결과 조회
    - `crawler/exporters/analysis_store.py` 파일 생성
    - _Requirements: 1.1, 6.1_

  - [x] 20.2 Unit test: 분석 데이터 저장/로드
    - 저장 후 로드 시 동일한 데이터 반환 검증
    - _Requirements: 1.1_

- [x] 21. 통합 및 기존 시스템 연동
  - [x] 21.1 GameAnalyzer 통합 클래스 구현
    - SentimentAnalyzer, IssueDetector, TrendAnalyzer 통합
    - 전체 분석 파이프라인 조율
    - `crawler/analysis/game_analyzer.py` 파일 생성
    - _Requirements: 2.1, 3.1, 4.1_

  - [x] 21.2 기존 CrawlerOrchestrator와 통합
    - 크롤링 후 자동 분석 옵션 추가
    - 게임별 데이터 저장 경로 적용
    - _Requirements: 1.1_

  - [x] 21.3 Integration test: 전체 분석 흐름
    - 크롤링 → 분석 → 저장 → 대시보드 표시 end-to-end 테스트
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

- [x] 22. Final Checkpoint - 전체 시스템 확인
  - 모든 기능이 통합되어 정상 동작하는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 23. 대시보드 크롤링 관리 기능 구현
  - [ ] 23.1 CrawlManager 클래스 구현
    - `CrawlJob` dataclass 구현 (작업 ID, 상태, 진행률, 결과)
    - `CrawlStatus` Enum 구현 (PENDING, SEARCHING, CRAWLING, ANALYZING, COMPLETED, FAILED, CANCELLED)
    - `start_crawl()` 메서드: 백그라운드 크롤링 시작
    - `get_job_status()` 메서드: 작업 상태 조회
    - `cancel_job()` 메서드: 작업 취소
    - `crawler/crawl_manager.py` 파일 생성
    - _Requirements: 9.2, 9.3, 9.4_

  - [ ] 23.2 Property test: 크롤링 작업 상태 일관성
    - **Property 21: Crawl Job Status Consistency**
    - **Validates: Requirements 9.2, 9.3**

  - [ ] 23.3 Property test: 크롤링 진행률 단조성
    - **Property 22: Crawl Progress Monotonicity**
    - **Validates: Requirements 9.3**

  - [ ] 23.4 Property test: 크롤링 결과 요약 정확성
    - **Property 23: Crawl Result Summary Accuracy**
    - **Validates: Requirements 9.4**

- [ ] 24. 게임 프로필 관리 API 구현
  - [ ] 24.1 게임 등록 API 구현
    - `POST /api/admin/games` - 새 게임 등록
    - 게임명, 키워드, 대상 사이트 입력 받아 GameProfile 생성
    - game_id 자동 생성 (kebab-case)
    - _Requirements: 9.1_

  - [ ] 24.2 Property test: 게임 프로필 생성
    - **Property 20: GameProfile Creation from Dashboard**
    - **Validates: Requirements 9.1**

  - [ ] 24.3 게임 프로필 수정/삭제 API 구현
    - `PUT /api/admin/games/<game_id>` - 프로필 수정
    - `DELETE /api/admin/games/<game_id>` - 게임 삭제
    - _Requirements: 9.7, 9.8_

  - [ ] 24.4 게임 프로필 목록 API 구현
    - `GET /api/admin/profiles` - 등록된 게임 목록
    - 마지막 크롤링 시간, 데이터 수 포함
    - _Requirements: 9.6_

- [ ] 25. 크롤링 실행 API 구현
  - [ ] 25.1 크롤링 시작 API 구현
    - `POST /api/admin/games/<game_id>/crawl` - 크롤링 시작
    - 백그라운드 실행, job_id 반환
    - _Requirements: 9.2_

  - [ ] 25.2 크롤링 상태 조회 API 구현
    - `GET /api/admin/games/<game_id>/crawl/status` - 상태 조회
    - 진행률, 현재 단계, 수집 결과 반환
    - _Requirements: 9.3, 9.4_

  - [ ] 25.3 데이터 갱신 API 구현
    - `POST /api/admin/games/<game_id>/refresh` - 재크롤링
    - 기존 데이터 유지하며 최신 데이터 추가
    - _Requirements: 9.5_

- [ ] 26. 게임 관리 대시보드 UI 구현
  - [ ] 26.1 게임 관리 페이지 구현
    - `/admin/games` - 등록된 게임 목록
    - 각 게임의 상태, 마지막 크롤링 시간, 데이터 수 표시
    - `dashboard/templates/admin_games.html` 생성
    - _Requirements: 9.6_

  - [ ] 26.2 새 게임 등록 페이지 구현
    - `/admin/games/new` - 게임 등록 폼
    - 게임명, 키워드, 대상 사이트 입력 UI
    - `dashboard/templates/admin_new_game.html` 생성
    - _Requirements: 9.1_

  - [ ] 26.3 크롤링 제어 UI 구현
    - 크롤링 시작/중지 버튼
    - 실시간 진행 상태 표시 (WebSocket 또는 polling)
    - 결과 요약 표시
    - _Requirements: 9.2, 9.3, 9.4_

  - [ ] 26.4 데이터 갱신 UI 구현
    - 데이터 갱신 버튼
    - 갱신 진행 상태 표시
    - _Requirements: 9.5_

- [ ] 27. Checkpoint - 크롤링 관리 기능 확인
  - 대시보드에서 새 게임 등록이 정상 동작하는지 확인
  - 크롤링 시작/상태 조회가 정상 동작하는지 확인
  - 데이터 갱신이 정상 동작하는지 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 28. Final Integration - 크롤링 관리 통합
  - [ ] 28.1 메인 대시보드에 관리 링크 추가
    - 헤더에 "게임 관리" 메뉴 추가
    - 게임 카드에 "크롤링" 버튼 추가
    - _Requirements: 9.2_

  - [ ] 28.2 Integration test: 크롤링 관리 전체 흐름
    - 게임 등록 → 크롤링 시작 → 상태 확인 → 완료 → 대시보드 표시 end-to-end 테스트
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 29. Final Checkpoint - 크롤링 관리 포함 전체 시스템 확인
  - 모든 기능이 통합되어 정상 동작하는지 확인
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 모든 테스트 태스크가 필수로 설정됨
- **대시보드 우선 구현**: 게임별 필터링 + 기본 대시보드를 먼저 구현하여 즉시 확인 가능
- **점진적 기능 추가**: 감성 분석 → 이슈 탐지 → 버그 분류 → 트렌드 → 알림 순으로 대시보드에 추가
- 기존 `crawler/` 모듈 구조를 확장하여 `crawler/analysis/` 디렉토리 추가
- 한국어 감성 분석은 사전 기반 방식으로 시작하고, 추후 ML 모델로 확장 가능
- QuickSight 연동은 게임별 별도 경로로 CSV 파일 생성하여 기존 연동 방식 유지
- **크롤링 관리 기능** (Task 23-29): 대시보드에서 직접 게임 등록 및 크롤링 실행 가능
  - 기존 `CrawlerOrchestrator`를 활용하여 백그라운드 크롤링 실행
  - 크롤링 진행 상태를 실시간으로 추적하고 표시
  - 게임 프로필 CRUD 및 데이터 갱신 기능 제공
