import os

import requests
from bs4 import BeautifulSoup
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
    prompt = f"""
            주어진 글에서 설명하고 있는 모든 장소명과 주소를 각각 추출하세요. 각 장소명과 주소는 다음과 같은 형식으로 구분합니다:

            - 주소가 존재하는 경우: '주소 - 장소명'
            - 주소가 존재하지 않는 경우: '장소명'
            - 추출된 정보는 쉼표(,)로 구분된 단일 문자열로 반환해야 합니다.

            예시 출력 형식:
                1) 주소가 존재할 때는:
                서울특별시 종로구 - 광화문, 제주특별자치도 서귀포시 - 천지연 폭포

                2) 주소가 존재하지 않을 때는:
                남산타워, 불국사, 경복궁
                
                3) 장소명과 주소가 모두 존재하지 않을 때는:
                장소명이 존재하지 않습니다.

            주의사항
            - 주소와 장소명은 반드시 대시 기호(-)로 구분합니다.
            - 주소 정보가 명확하지 않은 경우(예: 일부 정보만 제공된 경우), 해당 정보를 주소 없는 장소로 분류하세요.
            - 정확한 추출을 위해 각 장소가 정확히 분리되어 있는지 확인하세요.

            본문:
            {text}

            주소 - 장소명:
            """

    # 클로바 API 실행
    completion_executor = CompletionExecutor(
        host=os.getenv('API_HOST'),  # 엔드포인트
        api_key=os.getenv('API_KEY'),
        api_key_primary_val=os.getenv('API_KEY_PRIMARY_VAL'),
        request_id=os.getenv('REQUEST_ID')
    )

    try:
        # 변환된 리스트를 저장할 새 리스트
        converted_addresses = []
        result = completion_executor.execute(prompt)
        content = result.get('result', {}).get('message', {}).get('content', 'No content found')
        if content:
            place_names = [place.strip() for place in content.split(',') if place.strip()]

            # 각 주소를 변환
            for address in place_names:
                # '-'를 ','로 바꾸고 변환된 결과를 리스트에 추가
                converted_address = address.replace(' - ', ', ')
                converted_addresses.append(converted_address)
        return converted_addresses

    except KeyError as e:
        raise Exception(f"KeyError: {e} - The expected key was not found in the result.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")


# 카카오맵 API, 장소 검색
# def search_place_kakao(keyword):
#     api = Local(service_key=os.getenv('KAKAO_SERVICE_KEY'))
#     try:
#         df = api.search_keyword(keyword, dataframe=True)
#         return df
#     except requests.exceptions.RequestException as e:
#         print(f"Request error: {e}")
#         return pd.DataFrame()
#     except Exception as e:
#         raise Exception(f"An unexpected error occurred: {e}")


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


# 키워드 리스트에 불필요한 문자 및 공백 제거
def clear_keyword_list(keyword_list, temp):
    # 텍스트 정리 함수 정의
    def clean_text(text):
        # '*'를 제거하고, 쉼표 전까지 텍스트에서 *와 그 주위 텍스트 제거
        if '*' in text:
            prefix = text.split('*')[0].rstrip()  # '*' 이전 부분
            suffix = text.split(',')[-1].strip()  # 쉼표 이후 부분
            return f"{prefix}, {suffix}"  # 쉼표 이후 부분만 반환
        else:
            # 일반적인 경우에는 공백 정리
            return ', '.join([part.strip() for part in text.split(',')])

    # 장소명을 간소화하는 함수 정의 (예: 공통된 키워드 추출)
    def simplify_place_name(place_name):
        # 특정 키워드만 사용하거나 공백 제거 등 간소화 작업
        keywords = place_name.split()
        # 여기서는 임의로 첫 번째 단어를 기준으로 간소화 (사용자 필요에 따라 조정 가능)
        return keywords[0] if keywords else place_name

    # `keyword_list`와 `temp`의 요소를 정리한 리스트 생성
    cleaned_keyword_list = [clean_text(item) for item in keyword_list]
    cleaned_temp = [clean_text(item) for item in temp]

    # 기존 `cleaned_keyword_list`의 간소화된 장소명을 추출하여 중복 확인을 위한 집합 생성
    existing_places = set()
    for entry in cleaned_keyword_list:
        if ',' in entry:
            place_name = entry.split(', ')[-1]  # 쉼표 뒤의 장소명 추출
            simplified_name = simplify_place_name(place_name)
            existing_places.add(simplified_name)

    # `cleaned_temp` 리스트에서 중복되지 않는 항목 추가
    for item in cleaned_temp:
        if ',' in item:
            place_name = item.split(', ')[-1]  # 쉼표 뒤의 장소명 추출
            simplified_name = simplify_place_name(place_name)
            if simplified_name not in existing_places:
                existing_places.add(simplified_name)
                cleaned_keyword_list.append(item)

    result = []
    for cleaned in cleaned_keyword_list:
        if '*' not in cleaned:
            result.append(cleaned)

    return result


# 네이버 블로그에서 장소명 + 주소 키워드 추출
def extract_place_keywords_from_naver(soup, text):
    name_list = []
    addr_list = []

    # 블로그 본문에 지도가 첨부되어 있는 경우: strong, p 태그의 장소명, 주소 데이터 추출
    strong_tag_name_list = soup.find_all('strong', class_='se-map-title')
    if strong_tag_name_list:
        for place_name in strong_tag_name_list:
            name_list.append(place_name.get_text(strip=True))

        p_tag_addr_list = soup.find_all('p', class_='se-map-address')
        for place_addr in p_tag_addr_list:
            str_addr = place_addr.get_text(strip=True)
            addr = ' '.join(str_addr.split(' ')[:2])
            addr_list.append(addr)

        temp_keyword = [f"{addr}, {name}" for name, addr in zip(name_list, addr_list)]
        temp = extract_place_names(text)
        keyword_list = clear_keyword_list(temp_keyword, temp)

    # 블로그 본문에 지도가 첨부되어 있지 않는 경우: 클로바 API 호출하기
    else:
        temp = extract_place_names(text)
        temp_keyword = extract_place_names(temp)
        keyword_list = clear_keyword_list(temp_keyword, [])

    return keyword_list


# Naver 제목, 본문 추출 함수
def extract_content_naver(main_url):
    try:
        if 'm.blog.naver' in main_url:
            main_url = main_url.replace('m.', '')
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
        raise Exception(f"HTTP Request error: {str(e)}")
    except ValueError as e:
        raise Exception(f"ValueError: {str(e)} - Check if the iframe is correctly extracted.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")
