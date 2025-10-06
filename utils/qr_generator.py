import qrcode
from PIL import Image, ImageDraw, ImageFont
import json
import os

def generate_qr_codes(bot_username: str, logo_path="logo.png"):
    os.makedirs("qr_codes", exist_ok=True)

    # Загружаем список заданий
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # Шрифт для подписи (если нет TTF — Windows шрифт по умолчанию)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    for task_id, task in tasks.items():
        link = f"https://t.me/{bot_username}?start={task_id}"

        # Создание QR-кода
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(link)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#003366", back_color="white").convert("RGB")

        qr_width, qr_height = qr_img.size

        # Создаём фон под QR, логотип и подпись
        total_height = qr_height + 220  # место под логотип + текст
        total_width = qr_width + 60
        background = Image.new("RGB", (total_width, total_height), "white")

        draw = ImageDraw.Draw(background)
        margin = 30

        # Вставляем QR-код
        qr_pos = (margin, margin)
        background.paste(qr_img, qr_pos)

        # Добавляем логотип в рамке под QR
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            logo_size = int(qr_width * 0.25)
            logo = logo.resize((logo_size, logo_size))

            logo_x = (background.width - logo_size) // 2
            logo_y = qr_height + 20

            padding = 10
            frame_width = logo_size + padding * 2
            frame_height = logo_size + padding * 2
            frame_x = logo_x - padding
            frame_y = logo_y - padding

            draw.rectangle(
                [frame_x, frame_y, frame_x + frame_width, frame_y + frame_height],
                outline="#003366",
                width=3
            )
            background.paste(logo, (logo_x, logo_y), mask=logo if logo.mode == "RGBA" else None)

        # Добавляем подпись под логотипом
        text = task['title']
        text_y = qr_height + logo_size + 50
        text_width = draw.textlength(text, font=font)
        text_x = (background.width - text_width) // 2
        draw.text((text_x, text_y), text, fill="#003366", font=font)

        # Сохраняем файл
        output_path = f"qr_codes/{task_id}.png"
        background.save(output_path)

        print(f"✅ QR с подписью создан: {output_path}")

    print("🎨 Все брендированные QR-коды успешно созданы!")
