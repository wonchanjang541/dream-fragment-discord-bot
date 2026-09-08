import os
import io
import random
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
# 저장 경로: Railway에서 DATA_DIR=/data + Volume(/data) 설정 시
# 재배포/재시작 후에도 기록이 유지됩니다.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "dream_enhance.db"
BASE_IMAGE = BASE_DIR / "dream_base.png"

SUCCESS_RATE = 0.35
MAX_TENTHS = 101          # 10.1%
MESO_PER_SUCCESS = 120_000_000


def percent_font(size=30):
    # Railway에 한글 폰트가 없어도 퍼센트 숫자는 항상 크게 보이도록
    # Pillow 기본 폰트를 지정 크기로 사용합니다. (숫자/기호 전용)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


PERCENT_FONT = percent_font(31)


def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dream_users (
                user_id INTEGER PRIMARY KEY,
                boss_tenths INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                successes INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def get_state(user_id: int):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO dream_users(user_id) VALUES(?)", (user_id,)
        )
        row = conn.execute(
            "SELECT boss_tenths, attempts, successes, failures FROM dream_users WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return {
        "boss_tenths": row[0],
        "attempts": row[1],
        "successes": row[2],
        "failures": row[3],
    }


def reset_state(user_id: int):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO dream_users(user_id) VALUES(?)", (user_id,)
        )
        conn.execute(
            "UPDATE dream_users SET boss_tenths=0, attempts=0, successes=0, failures=0 WHERE user_id=?",
            (user_id,),
        )


def try_enhance(user_id: int):
    state = get_state(user_id)
    if state["boss_tenths"] >= MAX_TENTHS:
        return state, None

    success = random.random() < SUCCESS_RATE
    with db() as conn:
        if success:
            conn.execute(
                """
                UPDATE dream_users
                SET attempts=attempts+1,
                    successes=successes+1,
                    boss_tenths=MIN(?, boss_tenths+1)
                WHERE user_id=?
                """,
                (MAX_TENTHS, user_id),
            )
        else:
            conn.execute(
                "UPDATE dream_users SET attempts=attempts+1, failures=failures+1 WHERE user_id=?",
                (user_id,),
            )
    return get_state(user_id), success


def pct(tenths: int):
    return f"{tenths / 10:.1f}%"


def render_image(state):
    if not BASE_IMAGE.exists():
        raise FileNotFoundError(f"dream_base.png을 찾을 수 없습니다: {BASE_IMAGE}")

    img = Image.open(BASE_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 원본의 "보스 데미지" 한글 글자는 그대로 살리고,
    # 뒤의 퍼센트 수치만 크게 다시 그립니다.
    # 이렇게 하면 Railway에 한글 폰트가 없어도 글자가 깨지지 않습니다.
    draw.rectangle((377, 150, 620, 194), fill=(72, 72, 70, 255))

    cur = state["boss_tenths"]
    nxt = min(MAX_TENTHS, cur + 1)
    if cur >= MAX_TENTHS:
        line = f"{pct(cur)} MAX"
    else:
        line = f"{pct(cur)} > {pct(nxt)}"

    # 성공 확률 / 실패(유지) 글씨 높이와 비슷하게 크게 표시
    draw.text(
        (382, 153),
        line,
        font=PERCENT_FONT,
        fill=(245, 245, 245, 255),
        stroke_width=1,
        stroke_fill=(70, 70, 70, 255),
    )

    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out


def make_embed(user, state, result=None):
    meso = state["successes"] * MESO_PER_SUCCESS
    cur = state["boss_tenths"]

    if cur >= MAX_TENTHS:
        title = "🎉 꿈조 뜨안 강화 완료!"
        desc = f"{user.mention} **보스 데미지 10.1% 달성!**"
    elif result is True:
        title = "✅ 강화 성공!"
        desc = f"{user.mention} **{pct(cur - 1)} → {pct(cur)}**\n💰 **+1.2억 메소!**"
    elif result is False:
        title = "💥 강화 실패 (유지)"
        desc = f"{user.mention} 보스 데미지 **{pct(cur)} 유지**"
    else:
        title = "🧩 꿈조 뜨안 시뮬레이션"
        desc = f"{user.mention}의 강화 현황"

    embed = discord.Embed(title=title, description=desc, color=0x3498DB)
    embed.add_field(
        name="📊 기록",
        value=(
            f"시도 **{state['attempts']}회**  |  성공 **{state['successes']}회**\n"
            f"날린 꿈조 **{state['failures']}개**\n"
            f"누적 메소 **{meso:,} 메소**"
        ),
        inline=False,
    )
    embed.add_field(
        name="강화 정보",
        value=(
            "성공 확률 **35%** · 성공 시 **보스 데미지 +0.1%** · 실패 시 **유지**\n"
            "성공 1회당 **1.2억 메소** · 최대 **10.1%**"
        ),
        inline=False,
    )
    embed.set_image(url="attachment://dream_enhance.png")
    return embed


class DreamView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=900)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "이 강화창은 만든 사람만 사용할 수 있어요. `/꿈조뜨안`으로 본인 강화창을 열어주세요.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="꿈조 강화", style=discord.ButtonStyle.success, emoji="🧩")
    async def enhance_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 3초 안에 먼저 응답 처리 -> Discord의 '애플리케이션이 응답하지 않았어요' 방지
        await interaction.response.defer()
        try:
            state, result = try_enhance(interaction.user.id)
            if result is None:
                button.disabled = True

            file = discord.File(render_image(state), filename="dream_enhance.png")
            await interaction.edit_original_response(
                embed=make_embed(interaction.user, state, result),
                attachments=[file],
                view=self,
            )
        except Exception as e:
            print("강화 버튼 오류:", repr(e))
            await interaction.followup.send(
                f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
                ephemeral=True,
            )

    @discord.ui.button(label="초기화", style=discord.ButtonStyle.danger, emoji="🔄")
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            reset_state(interaction.user.id)
            state = get_state(interaction.user.id)
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label == "꿈조 강화":
                    child.disabled = False

            file = discord.File(render_image(state), filename="dream_enhance.png")
            await interaction.edit_original_response(
                embed=make_embed(interaction.user, state),
                attachments=[file],
                view=self,
            )
        except Exception as e:
            print("초기화 버튼 오류:", repr(e))
            await interaction.followup.send(
                f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
                ephemeral=True,
            )


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        init_db()
        await self.tree.sync()
        print("슬래시 명령어 동기화 완료")
        print(f"강화 기록 DB 경로: {DB_PATH}")


bot = Bot()


@bot.event
async def on_ready():
    print(f"로그인 완료: {bot.user} ({bot.user.id})")


@bot.tree.command(name="꿈조뜨안", description="꿈의 조각 뜨안 강화 시뮬레이션을 엽니다.")
async def dream(interaction: discord.Interaction):
    # 이미지 처리 전에 즉시 defer해서 응답 시간 초과 방지
    await interaction.response.defer()
    try:
        state = get_state(interaction.user.id)
        view = DreamView(interaction.user.id)

        if state["boss_tenths"] >= MAX_TENTHS:
            for child in view.children:
                if isinstance(child, discord.ui.Button) and child.label == "꿈조 강화":
                    child.disabled = True

        file = discord.File(render_image(state), filename="dream_enhance.png")
        await interaction.edit_original_response(
            embed=make_embed(interaction.user, state), attachments=[file], view=view
        )
    except Exception as e:
        print("/꿈조뜨안 오류:", repr(e))
        await interaction.followup.send(
            f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
            ephemeral=True,
        )


@bot.tree.command(name="꿈조뜨안보기", description="저장된 내 꿈조 뜨안 강화 기록을 봅니다.")
async def dream_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        state = get_state(interaction.user.id)
        file = discord.File(render_image(state), filename="dream_enhance.png")
        embed = make_embed(interaction.user, state)
        embed.title = "👀 내 꿈조 뜨안 기록"
        embed.description = f"{interaction.user.mention}의 **자동 저장된 현재 기록**입니다."
        await interaction.edit_original_response(embed=embed, attachments=[file])
    except Exception as e:
        print("/꿈조뜨안보기 오류:", repr(e))
        await interaction.followup.send(
            f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
            ephemeral=True,
        )


@bot.tree.command(name="꿈조뜨안랭킹", description="꿈조 뜨안 강화 랭킹 TOP 10을 봅니다.")
async def dream_ranking(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        with db() as conn:
            rows = conn.execute(
                """
                SELECT user_id, boss_tenths, attempts, successes, failures
                FROM dream_users
                ORDER BY boss_tenths DESC, successes DESC, attempts ASC
                LIMIT 10
                """
            ).fetchall()

        if not rows:
            await interaction.edit_original_response(content="아직 랭킹 기록이 없습니다.")
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (user_id, boss_tenths, attempts, successes, failures) in enumerate(rows, start=1):
            mark = medals[i-1] if i <= 3 else f"**{i}위**"
            meso = successes * MESO_PER_SUCCESS
            lines.append(
                f"{mark} <@{user_id}> — **보뎀 {pct(boss_tenths)}**\n"
                f"└ 시도 {attempts}회 · 성공 {successes}회 · 날린 꿈조 {failures}개 · 누적 메소 {meso:,}"
            )

        embed = discord.Embed(
            title="🏆 꿈조 뜨안 랭킹 TOP 10",
            description="\n\n".join(lines),
            color=0xF1C40F,
        )
        embed.set_footer(text="보스 데미지 높은 순 → 성공 횟수 높은 순 → 시도 횟수 적은 순")
        await interaction.edit_original_response(embed=embed)
    except Exception as e:
        print("/꿈조뜨안랭킹 오류:", repr(e))
        await interaction.followup.send(
            f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
            ephemeral=True,
        )


if not TOKEN:
    raise RuntimeError("Railway Variables에 DISCORD_TOKEN 또는 DISCORD_BOT_TOKEN을 등록해주세요.")

bot.run(TOKEN)
