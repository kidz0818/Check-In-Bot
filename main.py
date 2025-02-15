import os
import discord
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from flask import Flask
from threading import Thread

# 加载 .env 文件
load_dotenv()

# 初始化 Flask 服务器
app = Flask('')


@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


# 启动 Flask 服务器
keep_alive()

# 初始化 Discord 机器人
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 连接 MongoDB
mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME")
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db["users"]


# 签到命令
@bot.command(name="sign")
async def sign(ctx):
    user_id = ctx.author.id
    now = datetime.now()
    today = now.date()  # 获取当前日期

    # 查询用户数据
    user_data = collection.find_one({"user_id": user_id})

    # 检查是否已签到
    if user_data:
        last_sign = user_data["last_sign"]
        last_sign_date = last_sign.date()  # 获取上次签到的日期

        # 如果上次签到日期与今天相同，说明已签到
        if last_sign_date == today:
            await ctx.send("你今天已经签到过了！")
            return

        # 检查是否连续签到（上次签到日期是否为昨天）
        if (today - last_sign_date).days == 1:
            streak_days = user_data.get("streak_days", 0) + 1
        else:
            streak_days = 1  # 重置连续签到
    else:
        streak_days = 1

    # 更新用户数据
    new_data = {
        "user_id": user_id,
        "name": ctx.author.name,
        "total_signs": (user_data["total_signs"] + 1) if user_data else 1,
        "last_sign": now,
        "coins": (user_data.get("coins", 0) + 5) if user_data else 5,
        "streak_days": streak_days
    }
    collection.update_one({"user_id": user_id}, {"$set": new_data},
                          upsert=True)

    # 签到成功消息
    embed = discord.Embed(
        title="签到成功！",
        description=f"{ctx.author.mention} 签到成功！获得5金币！\n连续签到 {streak_days} 天！",
        color=0x00ff00  # 绿色
    )
    embed.set_image(url="https://i.imgur.com/你的图片ID.gif")  # 替换为你的图片 URL
    await ctx.send(embed=embed)


# 排行榜命令（改为 !halloffame）
@bot.command(name="halloffame")
async def hall_of_fame(ctx):
    try:
        # 按签到次数排序
        top_users = collection.find().sort("total_signs", -1).limit(10)

        embed = discord.Embed(title="签到名人堂 🏆", color=0xffd700)  # 金色
        for index, user in enumerate(top_users, start=1):
            embed.add_field(
                name=f"第 {index} 名",
                value=
                f"{user['name']} - {user['total_signs']} 次签到 | 金币: {user['coins']}",
                inline=False)
        await ctx.send(embed=embed)
    except ServerSelectionTimeoutError:
        await ctx.send("无法连接到数据库，请稍后再试！")
    except Exception as e:
        await ctx.send(f"发生错误：{str(e)}")


# 读取 Token 并运行机器人
token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise ValueError("Discord Token 未找到！请检查 .env 文件或 Secrets 设置。")

bot.run(token)
