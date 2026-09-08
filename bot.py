import os, io, random, sqlite3
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv('DISCORD_TOKEN')
DB_PATH = 'dream_enhance.db'
BASE_IMAGE = 'dream_base.png'
SUCCESS_RATE = 0.35
STEP = 0.1
MAX_BOSS = 10.1
MESO_PER_SUCCESS = 120_000_000

# 숫자만 새로 그리므로 한글 폰트가 필요하지 않습니다.
def number_font(size=27):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
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
        conn.execute('''CREATE TABLE IF NOT EXISTS dream_users (
            user_id INTEGER PRIMARY KEY,
            boss_tenths INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            successes INTEGER NOT NULL DEFAULT 0,
            failures INTEGER NOT NULL DEFAULT 0
        )''')

def get_state(user_id: int):
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO dream_users(user_id) VALUES(?)', (user_id,))
        row = conn.execute('SELECT boss_tenths, attempts, successes, failures FROM dream_users WHERE user_id=?', (user_id,)).fetchone()
    return {'boss_tenths': row[0], 'attempts': row[1], 'successes': row[2], 'failures': row[3]}

def reset_state(user_id: int):
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO dream_users(user_id) VALUES(?)', (user_id,))
        conn.execute('UPDATE dream_users SET boss_tenths=0, attempts=0, successes=0, failures=0 WHERE user_id=?', (user_id,))

def try_enhance(user_id: int):
    s = get_state(user_id)
    if s['boss_tenths'] >= 101:
        return s, None
    success = random.random() < SUCCESS_RATE
    with db() as conn:
        if success:
            conn.execute('''UPDATE dream_users SET attempts=attempts+1, successes=successes+1,
                            boss_tenths=MIN(101,boss_tenths+1) WHERE user_id=?''', (user_id,))
        else:
            conn.execute('UPDATE dream_users SET attempts=attempts+1, failures=failures+1 WHERE user_id=?', (user_id,))
    return get_state(user_id), success

def pct(tenths: int):
    return f'{tenths/10:.1f}%'

def render_image(state):
    img = Image.open(BASE_IMAGE).convert('RGBA')
    # 원본의 숫자 영역만 지우고 현재 수치를 다시 그립니다.
    # 한글 '보스 데미지' 글자는 원본 그대로 유지됩니다.
    clean = img.crop((385, 203, 603, 239)).resize((218, 36))
    img.paste(clean, (385, 158))

    cur = state['boss_tenths']
    nxt = min(101, cur + 1)
    text = f'{pct(cur)} > {pct(nxt)}'
    draw = ImageDraw.Draw(img)
    # 원본 느낌에 맞춘 밝은 회백색 숫자 + 얇은 그림자
    draw.text((389, 160), text, font=FONT, fill=(25, 25, 25, 210), stroke_width=1, stroke_fill=(25,25,25,160))
    draw.text((387, 158), text, font=FONT, fill=(238, 238, 238, 255), stroke_width=1, stroke_fill=(105,105,105,255))

    out = io.BytesIO()
    img.save(out, 'PNG')
    out.seek(0)
    return out

def make_embed(user, state, result=None):
    meso = state['successes'] * MESO_PER_SUCCESS
    cur = state['boss_tenths']
    if cur >= 101:
        title = '🎉 꿈조 뜨안 강화 완료!'
        desc = f'{user.mention} **보스 데미지 10.1% 달성!**'
    elif result is True:
        title = '✅ 강화 성공!'
        desc = f'{user.mention} **{pct(cur-1)} → {pct(cur)}**\n💰 **+1.2억 메소!**'
    elif result is False:
        title = '💥 강화 실패 (유지)'
        desc = f'{user.mention} 보스 데미지 **{pct(cur)} 유지**'
    else:
        title = '🧩 꿈조 뜨안 시뮬레이션'
        desc = f'{user.mention}의 강화 현황'

    e = discord.Embed(title=title, description=desc, color=0x3498DB)
    e.add_field(name='📊 기록', value=(
        f"시도 **{state['attempts']}회**  |  성공 **{state['successes']}회**\n"
        f"날린 꿈조 **{state['failures']}개**\n"
        f"누적 메소 **{meso:,} 메소**"
    ), inline=False)
    e.add_field(name='강화 정보', value='성공 확률 **35%** · 성공 시 **보스 데미지 +0.1%** · 실패 시 **유지**\n성공 1회당 **1.2억 메소** · 최대 **10.1%**', inline=False)
    e.set_image(url='attachment://dream_enhance.png')
    return e

class DreamView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=900)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('이 강화창은 만든 사람만 사용할 수 있어요. `/꿈조강화`로 본인 강화창을 열어주세요.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='꿈조 강화', style=discord.ButtonStyle.success, emoji='🧩')
    async def enhance_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state, result = try_enhance(interaction.user.id)
        if result is None:
            button.disabled = True
        image = discord.File(render_image(state), filename='dream_enhance.png')
        await interaction.response.edit_message(embed=make_embed(interaction.user, state, result), attachments=[image], view=self)

    @discord.ui.button(label='초기화', style=discord.ButtonStyle.danger, emoji='🔄')
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        reset_state(interaction.user.id)
        state = get_state(interaction.user.id)
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == '꿈조 강화':
                child.disabled = False
        image = discord.File(render_image(state), filename='dream_enhance.png')
        await interaction.response.edit_message(embed=make_embed(interaction.user, state), attachments=[image], view=self)

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
    async def setup_hook(self):
        init_db()
        await self.tree.sync()

bot = Bot()

@bot.event
async def on_ready():
    print(f'로그인 완료: {bot.user}')

@bot.tree.command(name='꿈조강화', description='꿈의 조각 뜨안 강화 시뮬레이션을 엽니다.')
async def dream(interaction: discord.Interaction):
    state = get_state(interaction.user.id)
    view = DreamView(interaction.user.id)
    if state['boss_tenths'] >= 101:
        for child in view.children:
            if isinstance(child, discord.ui.Button) and child.label == '꿈조 강화':
                child.disabled = True
    image = discord.File(render_image(state), filename='dream_enhance.png')
    await interaction.response.send_message(embed=make_embed(interaction.user, state), file=image, view=view)

if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN 환경변수를 설정해주세요.')
bot.run(TOKEN)
