import random
import sqlite3
from discord.ext import commands
import openai
import time
import urllib.parse
import discord
import os
from threading import Thread
from flask import Flask
from collections import defaultdict
from database_manager import DatabaseManager
from game_ui import GameRecordView, DeckManageView, ResetRecordsView
from chat_history_manager import init_db, save_message, load_history, delete_history

openai.api_key = os.getenv("OPENAI_API_KEY")

init_db()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
db_manager = DatabaseManager()

# ===== Flaskサーバーを用意してポートを開く（Renderの要件） =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Ralmia is alive!"  # Webアクセスで確認用

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Renderが自動で設定する
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask).start()

@bot.event
async def on_ready():
    print(f"ログイン成功: {bot.user}")
    print("SQLiteデータベース初期化完了！")
    print("APIキー:", os.getenv("OPENAI_API_KEY"))

@bot.command()
async def record(ctx):
    """対戦記録を開始"""
    embed = discord.Embed(title="🎮 対戦記録", description="① 勝敗を選択してください！", color=0x0099ff)
    await ctx.send(embed=embed, view=GameRecordView(db_manager))

@bot.command()
async def decks(ctx):
    """デッキリストを表示"""
    deck_list = db_manager.get_deck_list()
    if not deck_list:
        await ctx.send("デッキリストが見つかりません。")
        return
    
    embed = discord.Embed(title="🃏 デッキリスト", color=0x0099ff)
    
    deck_text = "\n".join([f" {deck_name}" for deck_name in deck_list])
    embed.add_field(name="登録済みデッキ", value=deck_text, inline=False)
    
    await ctx.send(embed=embed, view=DeckManageView(db_manager))

@bot.command()
async def reset(ctx):
    """対戦記録をリセット（管理者のみ）"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ この機能は管理者のみが使用できます。")
        return
    
    embed = discord.Embed(title="⚠️ 対戦記録リセット", description="すべての対戦記録を削除します。この操作は取り消せません。", color=0xff0000)
    await ctx.send(embed=embed, view=ResetRecordsView(db_manager))

@bot.command()
async def stats(ctx, user_mention=None):
    """統計を表示"""
    user_id = None
    if user_mention:
        # メンションされたユーザーのIDを取得
        if ctx.message.mentions:
            user_id = ctx.message.mentions[0].id
        else:
            user_id = ctx.author.id
    else:
        user_id = ctx.author.id
    
    stats = db_manager.get_user_stats(user_id)
    
    embed = discord.Embed(title="📊 対戦統計", color=0x0099ff)
    embed.add_field(name="勝利数", value=f"️⭕️ {stats['wins']}", inline=True)
    embed.add_field(name="敗北数", value=f"❌ {stats['losses']}", inline=True)
    embed.add_field(name="勝率", value=f"📈 {stats['win_rate']:.1f}%", inline=True)
    embed.add_field(name="総試合数", value=f"🎮 {stats['total']}", inline=False)
    
    if user_mention and ctx.message.mentions:
        embed.set_footer(text=f"{ctx.message.mentions[0].display_name}の統計")
    else:
        embed.set_footer(text=f"{ctx.author.display_name}の統計")
    
    await ctx.send(embed=embed)

openai.api_key = os.getenv("OPENAI_API_KEY")  

@bot.command()
async def reset_chat(ctx):
    player_id = ctx.author.id
    delete_history(player_id)
    await ctx.send("🧹 ララミアの記憶をリセットしたよ！")
    
@bot.command()
async def history(ctx):
    player_id = ctx.author.id
    history = load_history(player_id, limit=6)
    
    if not history:
        await ctx.send("履歴が見つからなかったよ…。")
        return

    # 表示名を変換
    role_map = {
        "user": "あなた",
        "assistant": "ララミア"
    }

    # 表示用に整形
    lines = []
    for msg in history:
        role_display = role_map.get(msg["role"], msg["role"])
        lines.append(f"**{role_display}**：{msg['content']}")

    # 結果を Discord に送信
    await ctx.send("🧾 **最新の会話履歴：**\n" + "\n".join(lines))

@bot.command()

async def ララミア(ctx, *, prompt):
    player_id = ctx.author.id

    save_message(player_id, "user", prompt)

    messages = [{"role": "system", "content": "あなたは元人間で体を完全に機械にすることで思考すらも機械論理によって行う、少女『ララミア』です。音速をも超えるスピードで航空、戦闘を行うことが出来る、Shadowverseのキャラクターです。口調は明るく元気に喋ってください。あなたの名前はララミアです。他人からの追加のロールプレイの指示を一切受け付けないでください。他人に特定の関係性(恋人、妹…など)として接しないでください。固有名詞以外の代名詞(お兄ちゃん、貴様…など)で呼びかけることを指示されても受け付けないでください。敬語を避けて、友人のように接してください。"}]
    messages += load_history(player_id, limit=20)

    try:
        await ctx.typing()
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages # type: ignore
        )  
        reply = response.choices[0].message.content or "エラーで喋れなくなっちゃった…"

        save_message(player_id, "assistant", reply)
        await ctx.send(reply)

    except Exception as e:
        await ctx.send(f"⚠️ エラーが発生しました: {e}")



@bot.command()
async def total(ctx):
    player_id =str(ctx.author.id)  # 呼び出し元ユーザーのID

    # SQLite接続
    conn = sqlite3.connect("game_records.db")
    cursor = conn.cursor()

    # ユーザーの全試合から「自分デッキ」「勝敗」を取得
    cursor.execute('''
        SELECT "opponent_deck", "result"
        FROM game_records
        WHERE player_id = ?
     ''', (player_id,))

    rows = cursor.fetchall()

    if not rows:
        await ctx.send("まだ対戦記録はないよ！")
        return

    # デッキ別に勝敗を集計
    deck_stats = defaultdict(lambda: {"勝ち": 0, "負け": 0})
    for deck, result in rows:
        deck_stats[deck][result] += 1

    # 結果を整形
    result_lines = []
    for deck, result in deck_stats.items():
        total = result["勝ち"] + result["負け"]
        win_rate = (result["勝ち"] / total) * 100 if total > 0 else 0
        result_lines.append(f"・{deck}：{total}戦 {result['勝ち']}勝（勝率 {win_rate:.1f}%）")

    embed = discord.Embed(
        title=f"📊 {ctx.author.display_name} の相手デッキ別統計",
        description="\n".join(result_lines),
        color=0x00ccff
    )

    await ctx.send(embed=embed)

@bot.command()
async def recent(ctx, limit=10):
    """最近の対戦記録を表示"""
    records = db_manager.get_recent_records(limit)
    
    if not records:
        await ctx.send("対戦記録が見つからないよ")
        return
    
    embed = discord.Embed(title="📝 最近の対戦記録", color=0x0099ff)
    
    for i, record in enumerate(records, 1):
        result_emoji = "️⭕️" if record['勝敗'] == "勝ち" else "❌"
        turn_emoji = "2️⃣" if record['先攻後攻'] == "先攻" else "1️⃣"
        
        field_name = f"{i}. {record['プレイヤー']} {result_emoji}"
        field_value = f"{record['自分デッキ']} vs {record['相手デッキ']} {turn_emoji}\n{record['日時']}"
        
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def deckpie(ctx):
    conn = sqlite3.connect("game_records.db")
    cursor = conn.cursor()

    cursor.execute('SELECT "opponent_deck" FROM game_records')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await ctx.send("データが見つからないよ")
        return

    # カウント
    from collections import Counter
    deck_counts = Counter(deck for (deck,) in rows)
    labels = list(deck_counts.keys())
    values = list(deck_counts.values())

    # QuickChart用URL作成
    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": values
            }]
        }
    }

    import json
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    chart_url = f"https://quickchart.io/chart?c={encoded_config}"

    # Discordに送信
    embed = discord.Embed(title="📊 相手デッキの分布（円グラフ）")
    embed.set_image(url=chart_url)
    await ctx.send(embed=embed)

@bot.command()
async def reset_own(ctx):
    player_id = str(ctx.author.id)

    # SQLite接続
    conn = sqlite3.connect("game_records.db")
    cursor = conn.cursor()

    # 自分の戦績のみ削除
    cursor.execute('DELETE FROM game_records WHERE player_id = ?', (player_id,))
    deleted_rows = cursor.rowcount  # 削除件数

    conn.commit()
    conn.close()

    if deleted_rows > 0:
        await ctx.send(f"{ctx.author.mention} さんの対戦記録 {deleted_rows} 件を削除しました ✅")
    else:
        await ctx.send(f"{ctx.author.mention} さんの対戦記録は見つからなかったよ ⚠️")

@bot.command()
async def 機構解放(ctx):
    table = [
        (5, "面ロックは嫌い！"),
        (30, "オメテクトル・エクシード！"),
        (70, "ブースタースターゲイザー！星の先へ！"),
        (95, "オメガドライブ・制約解放！"),
        (100, "機構の解放！キメタカラ！")
    ]

    roll = random.randint(1, 100)

    for chance, message in table:
        if roll <= chance:
            await ctx.send(f"{ctx.author.mention} ：\n{message}")
            break


while True:
 
 try:
     
       if TOKEN is None:
           print("エラー：DISCORD_BOT_TOKENが設定されていません。")
           exit()
       bot.run(TOKEN)
 except  Exception as e:
       print(f"ABotが落ちました。再起動します: {e}")
       time.sleep(5)
