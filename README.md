# 꿈조 뜨안 시뮬레이션 (자동 저장 버전)

## 명령어
- `/꿈조뜨안` : 저장된 기록을 불러와 그대로 계속 강화
- `/꿈조뜨안랭킹` : TOP 10 랭킹
- `/꿈조뜨안보기` : 삭제됨

## 저장 방식
- 꿈조 강화 버튼을 누를 때마다 SQLite DB에 즉시 저장됩니다.
- `/꿈조뜨안`을 다시 입력해도 절대 초기화하지 않고 DB의 기존 기록을 불러옵니다.
- `초기화` 버튼을 직접 눌렀을 때만 해당 유저 기록이 0으로 초기화됩니다.

## Railway에서 기록을 재배포 후에도 유지하려면 (중요)
Railway의 기본 파일시스템은 재배포 시 사라질 수 있습니다. 반드시 Volume을 연결하세요.

1. Railway 프로젝트 > 봇 Service 선택
2. Volume 추가 후 Mount Path를 `/data` 로 설정
3. Variables에 `DATA_DIR=/data` 추가
4. 기존 `DISCORD_TOKEN` 또는 `DISCORD_BOT_TOKEN`은 그대로 유지
5. Redeploy

DB 파일은 `/data/dream_enhance.db`에 저장됩니다. Volume 없이 배포하면 재배포 때 기록이 초기화될 수 있습니다.
