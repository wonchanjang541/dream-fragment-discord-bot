# 꿈조 뜨안 시뮬레이터 v4

## 명령어
`/꿈조뜨안`

## 규칙
- 시작 보스 데미지: 0.0%
- 성공 확률: 35%
- 성공 시 보스 데미지 +0.1%
- 실패 시 유지
- 성공 1회당 +1.2억 메소
- 최대 10.1%
- 기록: 시도 / 성공 / 날린 꿈조 / 누적 메소

## Railway 변수
둘 중 하나만 있어도 실행됩니다.
- `DISCORD_TOKEN`
- `DISCORD_BOT_TOKEN`

## v4 수정
- `/꿈조뜨안` 실행 시 발생하던 TypeError 수정
- Discord `edit_original_response()`에서 잘못 사용한 `file=`을 `attachments=[file]`로 수정
- 한글 폰트 우선 사용
- 안내 문구도 `/꿈조뜨안`으로 통일

## 적용
GitHub 저장소 최상단에 `bot.py`, `dream_base.png`, `requirements.txt`, `Procfile`, `README.md`를 올리고 Commit 합니다. Railway가 자동 재배포되면 완료입니다.


## v6 변경사항
- 사진 속 원본 글자 크기/굵기에 가깝게 보스 데미지 수치 표시를 조정했습니다.
- 강화할 때 이미지 안의 보스 데미지 수치가 계속 변경됩니다.
