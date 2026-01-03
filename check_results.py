import json

# JavaScript 크롤러 결과
with open('data/mh_reviews_1months.json', encoding='utf-8') as f:
    dc_data = json.load(f)
    print(f"=== DC인사이드 크롤링 결과 ===")
    print(f"총 {len(dc_data)}개 레코드")
    if dc_data:
        print(f"샘플 제목: {dc_data[0]['title']}")
        print(f"샘플 URL: {dc_data[0]['url']}")

print()

# Python 크롤러 결과
with open('data/simple_crawl_results.json', encoding='utf-8') as f:
    ddg_data = json.load(f)
    print(f"=== DuckDuckGo 검색 결과 ===")
    print(f"총 {len(ddg_data)}개 레코드")
    if ddg_data:
        print(f"샘플 제목: {ddg_data[0]['title']}")
        print(f"샘플 URL: {ddg_data[0]['url']}")
