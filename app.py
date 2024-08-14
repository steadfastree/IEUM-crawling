from flask import Flask, request, jsonify
from utils import *
import pika
import json
from threading import Thread

app = Flask(__name__)


# @app.route('/', methods=["POST"])
# def crawl():
#     try:
#         crawling_collection = request.get_json()
#         user_uuid = str(crawling_collection.get("userUuid"))
#         link_type = int(crawling_collection.get("collectionType"))
#         main_url = str(crawling_collection.get("link"))

#         if not main_url:
#             raise ValueError("URL parameter is missing.")

#         if link_type == 0 and 'instagram.com' in main_url:
#             content = extract_content_instagram(main_url)
#             places = extract_place_names(content)
#             if places != ['장소명이 존재하지 않습니다.']:
#                 cleaned_keyword_list = clear_keyword_list(places, [])
#                 response = jsonify({
#                     "userUuid": user_uuid,
#                     "collectionType": link_type,
#                     "link": main_url,
#                     "content": content,
#                     "placeKeywords": cleaned_keyword_list
#                 })
#                 response.headers.add('Content-Type', 'application/json; charset=utf-8')
#                 return response, 200
#             else:
#                 return jsonify({"error": "Place Not Found"}), 400

#         elif link_type == 1 and 'blog.naver.com' in main_url:
#             content, main_content, keyword_list = extract_content_naver(main_url)
#             if keyword_list != ['장소명이 존재하지 않습니다.']:
#                 response = jsonify({
#                     "userUuid": user_uuid,
#                     "collectionType": link_type,
#                     "link": main_url,
#                     "content": content,
#                     "placeKeywords": keyword_list
#                 })
#                 response.headers.add('Content-Type', 'application/json; charset=utf-8')
#                 return response, 200
#             else:
#                 return jsonify({"error": "Place Not Found"}), 400
#         else:
#             return jsonify({"error": "Invalid URL"}), 400

#             # payload = {
#             #     "userUuid": user_uuid,
#             #     "collectionType": link_type,
#             #     "link": main_url,
#             #     "content": content,
#             #     "placeKeywords": places,
#             #     "candidates": all_candidates
#             # }
#             #
#             # # 다른 서버의 API 엔드포인트 URL 설정
#             # main_server = "http://other-server/api/endpoint"  # 실제 URL로 교체
#             #
#             # # 다른 서버로 POST 요청 보내기
#             # response = requests.post(main_server, json=payload)
#             #
#             # # 다른 서버에서 받은 응답을 클라이언트에 반환
#             # return response.json(), response.status_code
#         # else:
#         #     return jsonify({"error": "본문에 장소명이 포함되어 있지 않습니다."}), 400

#     except ValueError as ve:
#         # URL 파라미터가 누락된 경우
#         error_response = jsonify({"error": str(ve)})
#         error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
#         return error_response, 400  # Bad Request

#     except Exception as e:
#         # 기타 모든 예외 처리
#         error_response = jsonify({"error": "An unexpected error occurred.", "details": str(e)})
#         error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
#         return error_response, 500  # Internal Server Error

## RabbitMQ 관련 설정
credentials = pika.PlainCredentials(os.getenv('RABBITMQ_USERNAME'), os.getenv('RABBITMQ_PASSWORD'))
parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,  
    virtual_host='/',  
    credentials=credentials
)

# RabbitMQ 서버에 연결
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# 큐 선언
channel.queue_declare(queue='request_queue', durable=True, arguments={
    'x-dead-letter-exchange': 'ieum_retry',
    'x-dead-letter-routing-key': 'retry'
})

# 큐와 익스체인지 바인딩
channel.queue_bind(exchange='ieum_exchange', queue='request_queue', routing_key='request')

MAX_RETRY_COUNT = 3

def crawling_task(msg):
        crawling_collection = msg
        user_uuid = str(crawling_collection.get("userUuid"))
        link_type = int(crawling_collection.get("collectionType"))
        main_url = str(crawling_collection.get("link"))

        if not main_url:
            raise ValueError("URL parameter is missing.")

        if link_type == 0 and 'instagram.com' in main_url:
            content = extract_content_instagram(main_url)
            places = extract_place_names(content)
            if places != ['장소명이 존재하지 않습니다.']:
                cleaned_keyword_list = clear_keyword_list(places, [])
                response = {
                    "userUuid": user_uuid,
                    "collectionType": link_type,
                    "link": main_url,
                    "content": content,
                    "placeKeywords": cleaned_keyword_list
                }
                return response
            else:
                raise ValueError("Place Not Found")

        elif link_type == 1 and 'blog.naver.com' in main_url:
            content, main_content, keyword_list = extract_content_naver(main_url)
            if keyword_list != ['장소명이 존재하지 않습니다.']:
                response = {
                    "userUuid": user_uuid,
                    "collectionType": link_type,
                    "link": main_url,
                    "content": content,
                    "placeKeywords": keyword_list
                }
                return response
            else:
                raise ValueError("Place Not Found")
        else:
            raise ValueError("Invalid URL")

def publish_to_result_queue(ch, method, properties, body):
    try:
        msg = json.loads(body)
        print(f"{msg['userUuid']} 유저가 전송한 다음 링크에서 장소 키워드를 추출합니다.\n")
        print(f"링크 :  {msg['link']}\n")
        
        result = crawling_task(msg)
        print(f"추출된 장소 키워드: {result['placeKeywords']}\n")
        
        ch.basic_publish(
            exchange='ieum_exchange',
            routing_key='result',
            body=json.dumps(result)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"성공적으로 처리 완료\n")
    
    except ValueError as ve:
        # URL 파라미터가 누락된 경우
        # error_response = jsonify({"error": str(ve)})
        # error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
        # return error_response, 400  # Bad Request
        print(f"400 ValueError: {ve}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    except Exception as e:
        # 기타 모든 예외 처리
        # error_response = jsonify({"error": "An unexpected error occurred.", "details": str(e)})
        # error_response.headers.add('Content-Type', 'application/json; charset=utf-8')
        # return error_response, 500  # Internal Server Error
        print(f"500 unexpected Error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consuming():
    channel.basic_consume(queue='request_queue', on_message_callback=publish_to_result_queue)
    print("Starting to consume messages...")
    channel.start_consuming()

if __name__ == '__main__':
    consumer_thread = Thread(target=start_consuming)
    consumer_thread.daemon = True 
    consumer_thread.start()
    app.run(port = os.getenv('PORT'), debug=True)
