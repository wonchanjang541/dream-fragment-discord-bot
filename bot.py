import os
import io
import random
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = BASE_DIR / "dream_enhance.db"
BASE_IMAGE = BASE_DIR / "dream_base.png"

SUCCESS_RATE = 0.35
MAX_TENTHS = 101          # 10.1%
MESO_PER_SUCCESS = 120_000_000


def number_font(size=27):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT = number_font(27)


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

    # 원본 이미지의 '보스 데미지 0.2% > 0.3%' 한 줄만 덮은 뒤
    # 현재 수치로 다시 작성합니다. 다른 부분은 그대로 둡니다.
    # 현재 원본 이미지(635x556) 기준 좌표.
    draw.rectangle((251, 158, 603, 193), fill=(72, 72, 70, 255))

    cur = state["boss_tenths"]
    nxt = min(MAX_TENTHS, cur + 1)
    if cur >= MAX_TENTHS:
        line = f"보스 데미지 {pct(cur)} (MAX)"
    else:
        line = f"보스 데미지 {pct(cur)} > {pct(nxt)}"

    # 그림자 + 본문
    draw.text(
        (258, 161),
        line,
        font=FONT,
        fill=(35, 35, 35, 220),
        stroke_width=1,
        stroke_fill=(35, 35, 35, 180),
    )
    draw.text(
        (256, 159),
        line,
        font=FONT,
        fill=(242, 242, 242, 255),
        stroke_width=1,
        stroke_fill=(95, 95, 95, 255),
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
                "이 강화창은 만든 사람만 사용할 수 있어요. `/꿈조강화`로 본인 강화창을 열어주세요.",
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


bot = Bot()


@bot.event
async def on_ready():
    print(f"로그인 완료: {bot.user} ({bot.user.id})")


@bot.tree.command(name="꿈조강화", description="꿈의 조각 뜨안 강화 시뮬레이션을 엽니다.")
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
            embed=make_embed(interaction.user, state), file=file, view=view
        )
    except Exception as e:
        print("/꿈조강화 오류:", repr(e))
        await interaction.followup.send(
            f"오류가 발생했습니다: `{type(e).__name__}`\nRailway Logs를 확인해주세요.",
            ephemeral=True,
        )


if not TOKEN:
    raise RuntimeError("Railway Variables에 DISCORD_TOKEN을 등록해주세요.")

bot.run(TOKEN)
