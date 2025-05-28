from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json

RASPI_API_URL =
@csrf_exempt
def kakao_webhook(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        user_message = body.get('userRequest', {}).get('utterance', '')

        # 온도/습도 요청 처리
        if "온도" in user_message or "습도" in user_message:
            try:
                # 라즈베리파이 Flask 서버에서 센서 데이터 요청
                response = requests.get(RASPI_API_URL, timeout=5)
                response.raise_for_status()
                sensor_data = response.json()

                # 예시: 센서 데이터에 온도, 습도 키가 있다고 가정
                # 실제 센서 데이터 포맷에 맞게 수정 필요
                temperature = sensor_data.get("temperature", "알 수 없음")
                humidity = sensor_data.get("humidity", "알 수 없음")

                if "온도" in user_message:
                    reply_text = f"현재 온도는 {temperature}도입니다 🌡️"
                else:
                    reply_text = f"현재 습도는 {humidity}%입니다 💧"

            except requests.RequestException as e:
                reply_text = "센서 데이터를 가져오는 데 실패했어요. 잠시 후 다시 시도해주세요."

            return JsonResponse(make_kakao_response(reply_text))

        # 기존 메시지 처리
        if "온도" in user_message:
            return JsonResponse(make_kakao_response("현재 온도는 25도입니다 🌡️"))
        elif "습도" in user_message:
            return JsonResponse(make_kakao_response("현재 습도는 60%입니다 💧"))
        else:
            return JsonResponse(make_kakao_response("죄송해요, 이해하지 못했어요 😢"))

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def make_kakao_response(text):
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }
# 1. 로그인 버튼 클릭 시 카카오 로그인 페이지로 리다이렉트
def login_kakao(request):
    client_id = settings.KAKAO_REST_API_KEY
    redirect_uri = settings.KAKAO_REDIRECT_URI
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"response_type=code&client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}"
    )
    return redirect(kakao_auth_url)

# 2. 카카오가 redirect_uri로 보내준 인가 코드 받아서 토큰 요청
def kakao_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'No code provided'}, status=400)

    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        'grant_type': 'authorization_code',
        'client_id': settings.KAKAO_REST_API_KEY,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'code': code,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    token_response = requests.post(token_url, data=data, headers=headers)
    token_json = token_response.json()

    access_token = token_json.get('access_token')
    if not access_token:
        return JsonResponse({'error': 'Failed to get access token', 'detail': token_json}, status=400)

    # 액세스 토큰 세션에 저장
    request.session['access_token'] = access_token

    # 3. 액세스 토큰으로 사용자 정보 요청
    profile_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = requests.get(profile_url, headers=headers)
    profile_json = profile_response.json()

    # TODO: DB 저장 또는 세션 처리 작업 가능

    return JsonResponse(profile_json)

# 4. 로그인 후, 카카오톡 메시지 보내기 예시
def send_kakao_message(request):
    access_token = request.session.get("access_token")
    if not access_token:
        return JsonResponse({'error': 'Access token 없음. 먼저 로그인하세요.'}, status=401)

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": "안녕하세요! Django에서 보낸 카카오 메시지입니다 🎉",
            "link": {
                "web_url": "https://example.com",
                "mobile_web_url": "https://example.com",
            },
            "button_title": "바로 확인하기"
        })
    }

    response = requests.post(url, headers=headers, data=data)
    return JsonResponse(response.json(), status=response.status_code)
