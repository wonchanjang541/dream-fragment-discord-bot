# 꿈조 뜨안 시뮬레이터 v9

## 명령어
- `/꿈조뜨안` : 저장된 현재 기록에서 계속 강화
- `/꿈조뜨안보기` : 내 저장 기록만 확인
- `/꿈조뜨안랭킹` : TOP 10 랭킹

## 자동 저장
강화를 누를 때마다 SQLite DB에 즉시 저장됩니다. `/꿈조뜨안`을 다시 입력해도 0%로 초기화되지 않고 저장된 상태에서 이어집니다.
초기화는 강화창의 `초기화` 버튼을 직접 누른 경우에만 됩니다.

## Railway에서 재배포 후에도 기록 유지하기 (중요)
Railway 기본 디스크는 배포 때 초기화될 수 있으므로 **Volume**을 한 번 연결해야 합니다.

1. Railway 서비스 → Settings 또는 Volumes → **Add Volume**
2. Mount Path를 `/data` 로 설정
3. Variables에 `DATA_DIR` = `/data` 추가
4. 기존 토큰 변수 `DISCORD_BOT_TOKEN` 또는 `DISCORD_TOKEN`은 그대로 유지
5. Redeploy

이후 DB는 `/data/dream_enhance.db`에 저장되어 재배포/재시작 후에도 기록이 유지됩니다.

## GitHub 적용
압축을 풀고 `bot.py`, `dream_base.png`, `requirements.txt`, `Procfile`, `README.md`를 저장소 루트에 덮어쓴 뒤 Commit하면 됩니다.
