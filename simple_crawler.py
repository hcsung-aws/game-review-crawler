import json
import time
from duckduckgo_search import DDGS

def simple_crawl_test():
    """간단한 DuckDuckGo 검색 테스트"""
    try:
        print("DuckDuckGo 검색 테스트 시작...")
        results = []
        
        # 몬스터헌터 관련 검색
        keywords = ["몬스터헌터", "몬헌"]
        sites = ["naver.com", "inven.co.kr", "dcinside.com"]
        
        with DDGS() as ddgs:
            for keyword in keywords:
                query = f"{keyword} 리뷰"
                print(f"검색 중: {query}")
                
                try:
                    search_results = list(ddgs.text(query, max_results=5, region='kr-kr'))
                    
                    for result in search_results:
                        results.append({
                            "url": result["href"],
                            "title": result["title"],
                            "content": result["body"],
                            "keyword": keyword
                        })
                    
                    print(f"  - {len(search_results)}개 결과 수집")
                    time.sleep(2)  # 요청 간 대기
                    
                except Exception as e:
                    print(f"  - 검색 실패: {e}")
        
        # 결과 저장
        output_file = "data/simple_crawl_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n완료! 총 {len(results)}개 결과를 {output_file}에 저장했습니다.")
        return results
        
    except Exception as e:
        print(f"에러 발생: {e}")
        return []

if __name__ == "__main__":
    simple_crawl_test()
