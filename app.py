import gradio as gr
from openai import OpenAI
import random
from dotenv import load_dotenv
from uuid import uuid4
import csv
import pandas as pd
from supabase import create_client, Client
import os
from pydantic import BaseModel
load_dotenv()
supabase_client = create_client(os.environ.get("DB_URL"), os.environ.get("DB_PASSWORD"))
# Initialize OpenAI API
client = OpenAI()

# Character dictionary
character_dict = {}

# User dictionary
image_dict = {}

def find_all_data():
    data = supabase_client.table("Sample").select("*").execute()
    return data.data

# IDからキャラの情報を取得する関数
def get_character_info(character_id):
    char_list=reload_char()
    char = None
    for char_pred in char_list:
        if char_pred["id"] == character_id:
            char=char_pred
            break
    return char["image"], f"HP: {char['hp']} / AT: {char['at']}"

class CharacterInfo(BaseModel):
    at:int
    hp:int
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
    info=client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "以下の情報から考えられるキャラのHPとATを教えてください"},
            {"role": "user", "content": f"{description}"},
        ],
        response_format=CharacterInfo,
    )
    result=info.choices[0].message.parsed
    hp,at=result.hp,result.at
    image_url = response.data[0].url
    return id, image_url, image_url, hp, at

def battle(player_id, enemy_id):
    char_list=reload_char()
    player = None
    enemy=None
    for char_pred in char_list:
        if char_pred["id"] == player_id:
            player=char_pred
        if char_pred["id"] == enemy_id:
            enemy=char_pred
    
    # 初期HP設定
    player_hp = player["hp"]
    enemy_hp = enemy["hp"]
    player_at = player["at"]
    enemy_at = enemy["at"]
    
    log = []
    turn = 1

    while player_hp > 0 and enemy_hp > 0:
        log.append(f"【ターン {turn}】")
        random_state=random.randint(0,1)
        # 自分の攻撃
        enemy_hp -= player_at*random_state
        log.append(f"▶ {player_id} の攻撃！ {enemy_id} に {player_at} ダメージ！")
        if enemy_hp <= 0:
            log.append(f"🏆 {player_id} の勝利！")
            break
        
        # 相手の攻撃
        player_hp -= enemy_at*random_state
        log.append(f"▶ {enemy_id} の攻撃！ {player_id} に {enemy_at} ダメージ！")
        if player_hp <= 0:
            log.append(f"🏆 {enemy_id} の勝利！")
            break
        
        turn += 1

    return "\n".join(log)

def display_data():
    # `Gallery` 用に (画像URL, ID) のタプルリストを作成
    data_list = find_all_data()
    images = [(item["image"], f"AT: {item['at']}\nHP: {item['hp']}") for item in data_list]

    return images

def register_image(id, image, hp, at):
    if id is None:
        return reload_char()
    new_data = {"id": id, "image": image, "hp": hp, "at": at}
    supabase_client.table("Sample").insert(new_data).execute()
    return reload_char()

def reload_char():
    return find_all_data()

def reload_char_ids():
    char_list = reload_char()
    char_ids = [char["id"] for char in char_list]
    return char_ids 
def get_character_info_battle():
    char_list = reload_char()
    char_ids = [char["id"] for char in char_list]
    return gr.update(choices=char_ids, value=char_ids[0]),gr.update(choices=char_ids, value=char_ids[0])
# Gradio interface
with gr.Blocks() as demo:
    with gr.Tab("Register") as register_tab:
        description = gr.Textbox(label="Character Description")
        generate_btn = gr.Button("Generate Character")
        image = gr.Image()
        hp = gr.Number(label="HP")
        at = gr.Number(label="AT")
        id = gr.State("")
        image_url = gr.State("")
        generate_btn.click(fn=generate_character, inputs=description, outputs=[id, image, image_url, hp, at])

        register_button = gr.Button("Register")
        register_button.click(fn=register_image, inputs=[id, image_url, hp, at], outputs=[])

    with gr.Tab("Show") as show_tab:
        # 画像ギャラリー
        gallery = gr.Gallery(label="画像一覧")
        show_button = gr.Button("Show Character")
        show_button.click(fn=display_data, inputs=[], outputs=[gallery])
    
    with gr.Tab("Battle") as battle_tab:
        with gr.Column():
            gr.Markdown("### 🏆 自分のキャラ選択")
            player_select = gr.Dropdown(choices=reload_char_ids(), label="自分のキャラ")
            player_image = gr.Image()
            player_stats = gr.Textbox(label="ステータス", interactive=False)

        with gr.Column():
            gr.Markdown("### ⚔️ 対戦相手選択")
            enemy_select = gr.Dropdown(choices=reload_char_ids(), label="相手のキャラ")
            enemy_image = gr.Image()
            enemy_stats = gr.Textbox(label="ステータス", interactive=False)
        
        # キャラ選択時に画像とステータスを更新
        player_select.change(get_character_info, player_select, [player_image, player_stats])
        enemy_select.change(get_character_info, enemy_select, [enemy_image, enemy_stats])
        
        # バトル開始ボタン
        battle_button = gr.Button("バトル開始！")
        battle_result = gr.Textbox(label="バトルログ", interactive=False)

        # バトル処理
        battle_button.click(battle, [player_select, enemy_select], battle_result)
    battle_tab.select(get_character_info_battle, outputs=[player_select, enemy_select])

demo.launch(share=True)
