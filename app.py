import gradio as gr
from openai import OpenAI
import random
from dotenv import load_dotenv
from uuid import uuid4
import csv
import pandas as pd
load_dotenv()

# Initialize OpenAI API
client = OpenAI()

# Character dictionary
character_dict = {}

# User dictionary
image_dict = {}

# IDからキャラの情報を取得する関数
def get_character_info(character_id):
    char = char_list[char_list["id"] == character_id].iloc[0]
    return char["image"], f"HP: {char['hp']} / AT: {char['at']}"

def generate_character(description):
    # Generate image using OpenAI
    response = client.images.generate(
        model="dall-e-3",
        prompt=description,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    id = str(uuid4())
    # Generate random HP and AT
    hp = random.randint(50, 100)
    at = random.randint(10, 50)
    image_url = response.data[0].url
    return id, image_url,image_url, hp, at

def battle(player_id, enemy_id):
    player = char_list[char_list["id"] == player_id].iloc[0]
    enemy = char_list[char_list["id"] == enemy_id].iloc[0]
    
    # 初期HP設定
    player_hp = player["hp"]
    enemy_hp = enemy["hp"]
    player_at = player["at"]
    enemy_at = enemy["at"]
    
    log = []
    turn = 1

    while player_hp > 0 and enemy_hp > 0:
        log.append(f"【ターン {turn}】")
        
        # 自分の攻撃
        enemy_hp -= player_at
        log.append(f"▶ {player_id} の攻撃！ {enemy_id} に {player_at} ダメージ！")
        if enemy_hp <= 0:
            log.append(f"🏆 {player_id} の勝利！")
            break
        
        # 相手の攻撃
        player_hp -= enemy_at
        log.append(f"▶ {enemy_id} の攻撃！ {player_id} に {enemy_at} ダメージ！")
        if player_hp <= 0:
            log.append(f"🏆 {enemy_id} の勝利！")
            break
        
        turn += 1

    return "\n".join(log)


def display_data():
    # `Gallery` 用に (画像URL, ID) のタプルリストを作成
    with open("data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data_list = [row for row in reader]  # 各行を辞書としてリスト化
    images = [(item["image"], f"AT: {item['at']}\nHP: {item["hp"]}") for item in data_list]

    return images
def register_image(id, image, hp, at):
    if id in image_dict:
        return reload_char()
    if id is None:
        return reload_char()
    new_data = {"id": id, "image": image, "hp": hp, "at": at}
    with open("data.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_data.keys())
        writer.writerow(new_data)  # 1行追記
    return reload_char()
char_list=pd.read_csv("data.csv")
def reload_char():
    char_list = pd.read_csv("data.csv")
    return char_list
# Gradio interface
with gr.Blocks() as demo:
    with gr.Tab("Register"):
        description = gr.Textbox(label="Character Description")
        generate_btn = gr.Button("Generate Character")
        image = gr.Image()
        hp = gr.Number(label="HP")
        at = gr.Number(label="AT")
        id = gr.State("")
        image_url = gr.State("")
        generate_btn.click(fn=generate_character, inputs=description, outputs=[id, image,image_url, hp, at])

        register_button = gr.Button("Register")
        register_button.click(fn=register_image, inputs=[id, image_url, hp, at], outputs=[])

    with gr.Tab("Show"):
        # 画像ギャラリー
        gallery = gr.Gallery(label="画像一覧")
        show_button = gr.Button("Show Character")
        show_button.click(fn=display_data, inputs=[], outputs=[gallery])
    
    with gr.Tab("Battle"):
        char_list=pd.read_csv("data.csv")
        with gr.Column():
            gr.Markdown("### 🏆 自分のキャラ選択")
            player_select = gr.Dropdown(choices=char_list["id"].tolist(), label="自分のキャラ")
            player_image = gr.Image()
            player_stats = gr.Textbox(label="ステータス", interactive=False)

        with gr.Column():
            gr.Markdown("### ⚔️ 対戦相手選択")
            enemy_select = gr.Dropdown(choices=char_list["id"].tolist(), label="相手のキャラ")
            enemy_image = gr.Image()
            enemy_stats = gr.Textbox(label="ステータス", interactive=False)
         # キャラ選択時に画像とステータスを更新      # バトル開始ボタン
        battle_button = gr.Button("バトル開始！")
        battle_result = gr.Textbox(label="バトルログ", interactive=False)

        # バトル処理
        battle_button.click(battle, [player_select, enemy_select], battle_result)
    player_select.change(get_character_info, player_select, [player_image, player_stats])
    enemy_select.change(get_character_info, enemy_select, [enemy_image, enemy_stats])

  
demo.launch(share=True)
