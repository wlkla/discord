import json
import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = False
intents.members = False


class GradeBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.grades_data = {}

    async def setup_hook(self):
        self.grades_data = load_grades()
        await self.tree.sync()


client = GradeBot()


class GradeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='成绩输入')

        self.subject1 = discord.ui.TextInput(label='第一科成绩', placeholder='请输入成绩', required=True)
        self.subject2 = discord.ui.TextInput(label='第二科成绩', placeholder='请输入成绩', required=True)
        self.subject3 = discord.ui.TextInput(label='第三科成绩', placeholder='请输入成绩', required=True)
        self.subject4 = discord.ui.TextInput(label='第四科成绩', placeholder='请输入成绩', required=True)
        self.subject5 = discord.ui.TextInput(label='第五科成绩', placeholder='请输入成绩', required=True)

        self.add_item(self.subject1)
        self.add_item(self.subject2)
        self.add_item(self.subject3)
        self.add_item(self.subject4)
        self.add_item(self.subject5)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        try:
            grades = [
                float(self.subject1.value),
                float(self.subject2.value),
                float(self.subject3.value),
                float(self.subject4.value),
                float(self.subject5.value)
            ]
            total = sum(grades)
            user_id = str(interaction.user.id)

            user_data = client.grades_data.get(user_id, {
                "name": interaction.user.display_name,
                "latest_total": 0,
                "best_total": 0,
                "progress": 0,
                "images": []
            })

            if user_data["best_total"] == 0:
                progress = 0
                user_data["best_total"] = total
            else:
                progress = total - user_data["best_total"]

            user_data["latest_total"] = total
            if total > user_data["best_total"]:
                user_data["best_total"] = total
            user_data["progress"] = progress

            client.grades_data[user_id] = user_data
            save_grades(client.grades_data)

            await interaction.followup.send("成绩已存储！", ephemeral=True)
        except ValueError:
            await interaction.followup.send("请输入有效的数字！", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"发生错误：{str(e)}", ephemeral=True)


class ImageModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='上传成绩图片')

        self.image_url = discord.ui.TextInput(
            label='成绩URL链接',
            placeholder='请输入图片URL链接',
            required=True
        )

        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # type: ignore
        try:
            user_id = str(interaction.user.id)

            user_data = client.grades_data.get(user_id, {
                "name": interaction.user.display_name,
                "latest_total": 0,
                "best_total": 0,
                "progress": 0,
                "latest_image": None
            })

            # 直接更新最新图片链接
            user_data["latest_image"] = self.image_url.value

            client.grades_data[user_id] = user_data
            save_grades(client.grades_data)

            await interaction.followup.send("成绩图片已更新！", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"发生错误：{str(e)}", ephemeral=True)


class GradeButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="输入成绩", style=discord.ButtonStyle.green, custom_id="grade_button")
    async def grade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GradeModal())  # type: ignore

    @discord.ui.button(label="上传图片", style=discord.ButtonStyle.blurple, custom_id="image_button")
    async def image_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImageModal())  # type: ignore


def save_grades(data):
    with open('grades.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_grades():
    try:
        with open('grades.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


@client.event
async def on_ready():
    print(f'{client.user} 已上线！')
    await client.tree.sync()


# 查看成绩命令
@client.tree.command(name="grades", description="查看所有成员的成绩排名")
async def show_grades(interaction: discord.Interaction):
    if not client.grades_data:
        await interaction.response.send_message("目前还没有任何成绩记录！", ephemeral=True)  # type: ignore
        return

    # 按最新总分排序
    sorted_grades = sorted(client.grades_data.items(), key=lambda x: x[1].get("latest_total", 0), reverse=True)

    # 创建嵌入消息列表
    embeds = []

    # 创建总排名嵌入消息
    ranking_embed = discord.Embed(
        title="成绩排名",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    ranking_text = ""
    for i, (user_id, data) in enumerate(sorted_grades, 1):
        name = data.get("name", "未知用户")
        latest_total = data.get("latest_total", 0)
        best_total = data.get("best_total", 0)
        progress = data.get("progress", 0)

        ranking_text += f"**{i}. {name}**\n"
        ranking_text += f"当前总分：{latest_total}\n"
        ranking_text += f"最佳总分：{best_total}\n"
        ranking_text += f"进步分数：{progress}\n"

        # 添加成绩图片链接（如果有）
        image_url = data.get("latest_image")
        if image_url:
            ranking_text += f"[查看成绩图片]({image_url})\n"

        ranking_text += "\n"

    ranking_embed.description = ranking_text
    embeds.append(ranking_embed)

    # 为每个有图片的用户创建图片嵌入消息
    for user_id, data in sorted_grades:
        image_url = data.get("latest_image")
        if image_url:
            img_embed = discord.Embed(title=f"{data['name']}的成绩图片", color=discord.Color.green())
            img_embed.set_image(url=image_url)
            embeds.append(img_embed)

    await interaction.response.send_message(embeds=embeds, ephemeral=True)  # type: ignore


@client.tree.command(name="progress", description="查看所有成员的进步分数排名")
async def show_progress(interaction: discord.Interaction):
    if not client.grades_data:
        await interaction.response.send_message("目前还没有任何进步记录！", ephemeral=True)  # type: ignore
        return

    # 按进步分数排序
    sorted_progress = sorted(client.grades_data.items(), key=lambda x: x[1].get("progress", 0), reverse=True)

    # 创建嵌入消息列表
    embeds = []

    # 创建总排名嵌入消息
    progress_embed = discord.Embed(
        title="进步分数排名",
        color=discord.Color.purple(),
        timestamp=discord.utils.utcnow()
    )

    progress_text = ""
    for i, (user_id, data) in enumerate(sorted_progress, 1):
        name = data.get("name", "未知用户")
        progress = data.get("progress", 0)
        latest_total = data.get("latest_total", 0)

        progress_text += f"**{i}. {name}**\n"
        progress_text += f"进步分数：{progress}\n"
        progress_text += f"当前总分：{latest_total}\n"

        # 添加成绩图片链接（如果有）
        image_url = data.get("latest_image")
        if image_url:
            progress_text += f"[查看成绩图片]({image_url})\n"

        progress_text += "\n"

    progress_embed.description = progress_text
    embeds.append(progress_embed)

    # 为每个有图片的用户创建图片嵌入消息
    for user_id, data in sorted_progress:
        image_url = data.get("latest_image")
        if image_url:
            img_embed = discord.Embed(title=f"{data['name']}的成绩图片", color=discord.Color.green())
            img_embed.set_image(url=image_url)
            embeds.append(img_embed)

    await interaction.response.send_message(embeds=embeds, ephemeral=True)  # type: ignore


@client.tree.command(name="score", description="添加成绩或上传图片")
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message("请选择要执行的操作：", view=GradeButtons(), ephemeral=True)  # type: ignore


@client.tree.command(name="pic2url", description="为您的图片生成url链接")
async def pic2url(interaction: discord.Interaction):
    await interaction.response.send_message(  # type: ignore
        content="请访问以下网站来生成图片的 URL 链接：\n[Telegraph Image URL 生成器](https://telegraph-image-6b4.pages.dev/)",
        ephemeral=True
    )


client.run('YOUR_KEY')
