import gradio as gr
from openai import OpenAI
import random
from dotenv import load_dotenv
from uuid import uuid4 
from supabase import create_client
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
def get_character_info(character_name):
    char_list=find_all_data()
    char = None
    for char_pred in char_list:
        if char_pred["name"] == character_name:
            char=char_pred
            break
    return char["image"], f"HP: {char['hp']} / AT: {char['at']}" #type: ignore

class CharacterInfo(BaseModel):
    at:int
    hp:int

def generate_character(description, character_name):
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
    return id, image_url, image_url, hp, at, character_name

def battle(player_name, enemy_name):
    char_list=find_all_data()
    player = None
    enemy=None
    for char_pred in char_list:
        if char_pred["name"] == player_name:
            player=char_pred
        if char_pred["name"] == enemy_name:
            enemy=char_pred
    
    # 初期HP設定
    player_hp = player["hp"] #type: ignore
    enemy_hp = enemy["hp"] #type: ignore
    player_at = player["at"] #type: ignore
    enemy_at = enemy["at"] #type: ignore
    
    log = []
    turn = 1

    while player_hp > 0 and enemy_hp > 0:
        log.append(f"【ターン {turn}】")
        random_state=random.randint(0,1)
        # 自分の攻撃
        enemy_hp -= player_at*random_state
        log.append(f"▶ {player_name} の攻撃！ {enemy_name} に {player_at} ダメージ！")
        if enemy_hp <= 0:
            log.append(f"🏆 {player_name} の勝利！")
            break
        
        # 相手の攻撃
        player_hp -= enemy_at*random_state
        log.append(f"▶ {enemy_name} の攻撃！ {player_name} に {enemy_at} ダメージ！")
        if player_hp <= 0:
            log.append(f"🏆 {enemy_name} の勝利！")
            break
        
        turn += 1

    return "\n".join(log)

def display_data():
    # `Gallery` 用に (画像URL, ID) のタプルリストを作成
    data_list = find_all_data()
    images = [(item["image"], f"AT: {item['at']}\nHP: {item['hp']}") for item in data_list]

    return images

def register_image(id, image, hp, at, character_name):
    if id is None:
        return find_all_data()
    new_data = {"id": id, "image": image, "hp": hp, "at": at, "name": character_name}
    supabase_client.table("Sample").insert(new_data).execute()
    return find_all_data()

def reload_char_names():
    char_list = find_all_data()
    char_ids = [char["name"] for char in char_list]
    return char_ids 


def get_character_info_battle():
    char_list = find_all_data()
    char_names = [char["name"] for char in char_list]
    return gr.update(choices=char_names, value=char_names[0]),gr.update(choices=char_names, value=char_names[0])


# Gradio interface
with gr.Blocks() as demo:
    with gr.Tab("Register") as register_tab:
        description = gr.Textbox(label="Character Description")
        character_name = gr.Textbox(label="Character Name")
        generate_btn = gr.Button("Generate Character")
        image = gr.Image()
        hp = gr.Number(label="HP")
        at = gr.Number(label="AT")
        id = gr.State("")
        image_url = gr.State("")
        generate_btn.click(fn=generate_character, inputs=[description, character_name], outputs=[id, image, image_url, hp, at, character_name])

        register_button = gr.Button("Register")
        register_button.click(fn=register_image, inputs=[id, image_url, hp, at,character_name], outputs=[])

    with gr.Tab("Show") as show_tab:
        # 画像ギャラリー
        gallery = gr.Gallery(label="画像一覧")
        show_button = gr.Button("Show Character")
        show_button.click(fn=display_data, inputs=[], outputs=[gallery])
    
    with gr.Tab("Battle") as battle_tab:
        with gr.Column():
            gr.Markdown("### 🏆 自分のキャラ選択")
            player_select = gr.Dropdown(choices=reload_char_names(), label="自分のキャラ")
            player_image = gr.Image()
            player_status = gr.Textbox(label="ステータス", interactive=False)

        with gr.Column():
            gr.Markdown("### ⚔️ 対戦相手選択")
            enemy_select = gr.Dropdown(choices=reload_char_names(), label="相手のキャラ")
            enemy_image = gr.Image()
            enemy_status = gr.Textbox(label="ステータス", interactive=False)
        
        # キャラ選択時に画像とステータスを更新
        player_select.change(get_character_info, player_select, [player_image, player_status])
        enemy_select.change(get_character_info, enemy_select, [enemy_image, enemy_status])
        
        # バトル開始ボタン
        battle_button = gr.Button("バトル開始！")
        battle_result = gr.Textbox(label="バトルログ", interactive=False)

        # バトル処理
        battle_button.click(battle, [player_select, enemy_select], battle_result)
    battle_tab.select(get_character_info_battle, outputs=[player_select, enemy_select])

demo.launch(share=True)
