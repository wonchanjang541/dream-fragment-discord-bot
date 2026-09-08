# 꿈조 뜨안 강화 시뮬레이터

## 규칙
- 시작 보스 데미지: 0.0%
- 성공 확률: 35%
- 성공 시: +0.1%
- 실패 시: 유지
- 최대: 10.1%
- 성공 1회당: +1.2억 메소
- 기록: 시도 / 성공 / 날린 꿈조 / 누적 메소

## 명령어
`/꿈조뜨안`

## GitHub → Railway 적용
이 ZIP의 **내용물 5개를 GitHub 저장소 최상단(root)** 에 올리세요.
- bot.py
- dream_base.png
- requirements.txt
- Procfile
- README.md

Railway → Variables에 아래 변수를 등록합니다.
- `DISCORD_TOKEN 또는 DISCORD_BOT_TOKEN` = Discord Developer Portal에서 발급한 봇 토큰

GitHub에 Commit하면 Railway가 자동 재배포됩니다.

## 주의
파일들을 `dream_enhance_bot/` 같은 하위 폴더에 넣지 말고 GitHub 저장소 첫 화면에 바로 보이게 올리세요.
