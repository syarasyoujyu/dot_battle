import gradio as gr
from PIL import Image

def pixel_art(image, pixel_size):
    # 画像を読み込む
    img = Image.open(image)

    # ピクセルサイズを適用して画像を縮小・拡大
    img = img.resize(
        (img.size[0] // pixel_size, img.size[1] // pixel_size),
        Image.NEAREST
    )
    img = img.resize(
        (img.size[0] * pixel_size, img.size[1] * pixel_size),
        Image.NEAREST
    )

    return img

# Gradioインターフェースの設定
with gr.Blocks() as demo:
    gr.Markdown("## 画像をピクセルアート風に変換するアプリ")
    # type="file" を削除します
    image_input = gr.Image(label="画像をアップロード")  # Removed type="file"
    pixel_size_input = gr.Slider(2, 30, value=10, step=1, label="ピクセルサイズ")
    result_output = gr.Image(label="変換されたピクセルアート画像")

    convert_button = gr.Button("変換")
    convert_button.click(
        pixel_art,
        inputs=[image_input, pixel_size_input],
        outputs=[result_output]
    )

# アプリの起動
demo.launch()