from flask import Flask, request, jsonify

from utils import *

app = Flask(__name__)


@app.route('/', methods=["GET"])
def crawl():
    try:
        main_url = request.args.get("url")

        if not main_url:
            raise ValueError("URL parameter is missing.")

        if 'instagram.com' in main_url:
            content = extract_content_instagram(main_url)
            places = extract_place_names(content)
            if places:
                all_candidates = crawl_and_extract_places(places)
                response = jsonify({"content": content, "places": places, "candidates": all_candidates})
            else:
                return jsonify({"error": "본문에 장소명이 포함되어 있지 않습니다."}), 400

        elif 'blog.naver.com' in main_url:
            title, content = extract_content_naver(main_url)
            places = extract_place_names(content)
            if places:
                all_candidates = crawl_and_extract_places(places)
                response = jsonify({"title": title, "places": places, "candidates": all_candidates})
            else:
                return jsonify({"error": "본문에 장소명이 포함되어 있지 않습니다."}), 400

        else:
            return jsonify({"error": "Invalid URL"}), 400

        response.headers.add('Content-Type', 'application/json; charset=utf-8')

        return response, 200

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
