import os
import json
import pprint

import requests
from bs4 import BeautifulSoup
from PyKakao import Local
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self.host = host
        self.api_key = api_key
        self.api_key_primary_val = api_key_primary_val
        self.request_id = request_id

    def execute(self, prompt):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self.api_key,
            'X-NCP-APIGW-API-KEY': self.api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self.request_id,
            'Content-Type': 'application/json; charset=utf-8'
        }

        data = {
            'messages': [{"role": "system", "content": ""}, {"role": "user", "content": prompt}],
            'topP': 0.8,
            'topK': 0,
            'maxTokens': 256,
            'temperature': 0.5,
            'repeatPenalty': 5.0,
            'stopBefore': [],
            'includeAiFilters': True,
            'seed': 0
        }

        try:
            response = requests.post(f'{self.host}/testapp/v1/chat-completions/HCX-003', headers=headers, json=data)
            response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"HTTP Request error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")


# 장소(본문)추출 함수
def extract_place_names(text):
    # 프롬프트 설정
    if type(text) == str:
        prompt = f"""
        주어진 글에서 설명하고 있는 구체적인 장소명만을 출력해주세요.
    
        본문:
        {text}
    
        장소명:
        """
    else:
        prompt = f"""
        주어진 리스트에서 대한민국 행정구역 시/군/구/읍/면/리에 해당하는 것들을 제외한 특정 구체적인 장소명만을 출력해주세요.
    
        본문:
        {text}
    
        장소명:
        """

    # 클로바 API 실행
    completion_executor = CompletionExecutor(
        host=os.getenv('API_HOST'),  # 엔드포인트
        api_key=os.getenv('API_KEY'),
        api_key_primary_val=os.getenv('API_KEY_PRIMARY_VAL'),
        request_id=os.getenv('REQUEST_ID')
    )

    try:
        place_names = []
        result = completion_executor.execute(prompt)
        content = result.get('result', {}).get('message', {}).get('content', 'No content found')
        if content:
            if content.startswith('장소명:'):
                content = content.replace('장소명:', '')
            place_names = [place.strip() for place in content.replace('-', '').replace('\n', ',').split(',') if place.strip()]
        return place_names

    except KeyError as e:
        raise Exception(f"KeyError: {e} - The expected key was not found in the result.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")


# URL 유효성 검사
def is_valid_url(url):
    try:
        response = requests.head(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"URL validation error: {e}")
        return False


# 카카오맵 API, 장소 검색
def search_place_kakao(keyword):
    api = Local(service_key=os.getenv('KAKAO_SERVICE_KEY'))
    try:
        df = api.search_keyword(keyword, dataframe=True)
        return df
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return pd.DataFrame()
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")


# Instagram 본문 추출 함수
def extract_content_instagram(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tag = soup.find('meta', {'property': 'og:description'})
        if meta_tag:
            content = meta_tag['content']
            return content
        else:
            return 'Content not found'
    except requests.RequestException as e:
        raise Exception(f"HTTP Request error: {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")


def extract_place_keywords_from_naver(soup, text):
    name_list = []
    addr_list = []
    keyword_list = []

    # 블로그 본문에 지도가 첨부되어 있는 경우: strong, p 태그의 장소명, 주소 데이터 추출
    strong_tag_name_list = soup.find_all('strong', class_='se-map-title')
    if strong_tag_name_list:
        for place_name in strong_tag_name_list:
            name_list.append(place_name.get_text(strip=True))

        p_tag_addr_list = soup.find_all('p', class_='se-map-address')
        for place_addr in p_tag_addr_list:
            addr_list.append(place_addr.get_text(strip=True))

        keyword_list = [f"{addr}, {name}" for name, addr in zip(name_list, addr_list)]

    # 블로그 본문에 지도가 첨부되어 있지 않는 경우: 클로바 API 호출하기
    else:
        temp = extract_place_names(text)
        keyword_list = extract_place_names(temp)

    print(keyword_list)

    return keyword_list


# Naver 제목, 본문 추출 함수
def extract_content_naver(main_url):
    try:
        # 첫 번째 요청: 메인 페이지에서 iframe URL 추출
        response = requests.get(main_url, verify=False)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # iframe URL 추출
        iframe = soup.find('iframe', id='mainFrame')
        if iframe:
            iframe_src = iframe['src']
            if iframe_src.startswith('http'):
                iframe_url = iframe_src
            else:
                iframe_url = 'https://blog.naver.com' + iframe_src
        else:
            raise ValueError("Iframe not found")

        # 두 번째 요청: iframe의 실제 콘텐츠 가져오기
        response = requests.get(iframe_url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # 제목 텍스트 추출
        title_div = soup.find('div', class_='se-module se-module-text se-title-text')
        title_text = title_div.get_text(strip=True) if title_div else 'Title not found'

        # 본문 텍스트 추출
        content_div = soup.find('div', class_='se-main-container')
        content_text = content_div.get_text(strip=True) if content_div else 'Content not found'

        # 블로그 본문에서 장소명+주소 키워드 리스트 추출
        keyword_list = extract_place_keywords_from_naver(soup, content_text)

        return title_text, content_text, keyword_list

    except requests.RequestException as e:
        raise Exception(f"HTTP Request error: {e}")
    except ValueError as e:
        raise Exception(f"ValueError: {e} - Check if the iframe is correctly extracted.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")


# def crawl_and_extract_places(places):
#     try:
#         # 복합적으로 추출된 장소명 분리
#         separated_places = places.split(', ')
#
#         return separated_places
#     except Exception as e:
#         raise Exception(f"An error occurred while extracting places: {e}")
