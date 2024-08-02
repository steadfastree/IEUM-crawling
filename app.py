from flask import Flask, request, jsonify

from utils import *

app = Flask(__name__)


@app.route('/', methods=["POST"])
def crawl():
    try:
        crawling_collection = request.get_json()
        user_uuid = str(crawling_collection.get("userUuid"))
        link_type = int(crawling_collection.get("collectionType"))
        main_url = str(crawling_collection.get("link"))

        if not main_url:
            raise ValueError("URL parameter is missing.")

        if link_type == 0 and 'instagram.com' in main_url:
            content = extract_content_instagram(main_url)
            places = extract_place_names(content)
            if places:
                cleaned_keyword_list = clear_keyword_list(places, [])
                response = jsonify({
                    "userUuid": user_uuid,
                    "collectionType": link_type,
                    "link": main_url,
                    "content": content,
                    "placeKeywords": cleaned_keyword_list
                })
                response.headers.add('Content-Type', 'application/json; charset=utf-8')
                return response, 200

        elif link_type == 1 and 'blog.naver.com' in main_url:
            content, main_content, keyword_list = extract_content_naver(main_url)
            if keyword_list:
                response = jsonify({
                    "userUuid": user_uuid,
                    "collectionType": link_type,
                    "link": main_url,
                    "content": content,
                    "placeKeywords": keyword_list
                })
                response.headers.add('Content-Type', 'application/json; charset=utf-8')
                return response, 200
        else:
            return jsonify({"error": "Invalid URL"}), 400

            # payload = {
            #     "userUuid": user_uuid,
            #     "collectionType": link_type,
            #     "link": main_url,
            #     "content": content,
            #     "placeKeywords": places,
            #     "candidates": all_candidates
            # }
            #
            # # 다른 서버의 API 엔드포인트 URL 설정
            # main_server = "http://other-server/api/endpoint"  # 실제 URL로 교체
            #
            # # 다른 서버로 POST 요청 보내기
            # response = requests.post(main_server, json=payload)
            #
            # # 다른 서버에서 받은 응답을 클라이언트에 반환
            # return response.json(), response.status_code
        # else:
        #     return jsonify({"error": "본문에 장소명이 포함되어 있지 않습니다."}), 400

    except ValueError as ve:
        # URL 파라미터가 누락된 경우
        error_response = jsonify({"error": str(ve)})
        error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
        return error_response, 400  # Bad Request

    except Exception as e:
        # 기타 모든 예외 처리
        error_response = jsonify({"error": "An unexpected error occurred.", "details": str(e)})
        error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
        return error_response, 500  # Internal Server Error


if __name__ == '__main__':
    app.run(debug=True)
