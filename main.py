import asyncio
import re
import io
import time
import os
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
from PIL import Image
import pytesseract

api_id = 20443442
api_hash = '575590ee162f0056e7da056369e817eb'
session_name = 'forwarder_session'

source_channels = [
    '@was4r4',
    '@Vouchers1win_Mexico',
    '@Vouchers1win_India',
    '@offl1win_french',
    '@vouchers1win_nigeria',
    '@Vouchers1win_Turkey',
    '@Vouchers1win_Azerbaijan',
    '@official1win_br',
    '@official1win_spain',
    '@Vouchers1win_Uzbekistan',
    '@vouchers_1win_ukraine',
    '@Vouchers1win_Korea',
    '@vouchers1win_english',
    '@fartgart1',
    '@ramcha1337',
    '@voucher_win',
    -1001948817288,
    -1001516396186,
    -1001526198532,
    -1002035120390,
    -1002421228793,
    -1001660698982
]

target_channels = ['@Mortty1WIN', '@mortty1win_vip']  # Новые каналы

# Tesseract конфигурация
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
tessdata_dir = r'C:\Program Files\Tesseract-OCR\tessdata'
pytesseract.pytesseract.tesseract_cmd = tesseract_path
os.environ['TESSDATA_PREFIX'] = tessdata_dir

voucher_patterns = {
    '1w': re.compile(r'(1w-[a-z0-9\*]{3,})', re.IGNORECASE),
    'garti': re.compile(r'(garti-[a-z0-9\*]{3,})', re.IGNORECASE),
    'ls': re.compile(r'(ls-[a-z0-9\*]{3,})', re.IGNORECASE)
}

cipher_patterns = [
    re.compile(r'шифр[:\s\-]*([a-zA-Z0-9]{1,6})', re.IGNORECASE),
    re.compile(r'закрашен[оы]?[ыи]?\s*[-–—:>→]*\s*([a-zA-Z0-9]{1,6})', re.IGNORECASE),
    re.compile(r'закрашены\s*[-–—:>→]*\s*([a-zA-Z0-9]{1,6})', re.IGNORECASE),
]

sent_vouchers = set()

async def main():
    client = TelegramClient(session_name, api_id, api_hash)

    @client.on(events.NewMessage(chats=source_channels))
    async def handler(event):
        raw_text = event.raw_text or ""
        full_text = raw_text
        cipher = None
        garti_from_ocr = None
        new_codes = []

        # Поиск шифра в тексте
        for pattern in cipher_patterns:
            match = pattern.search(raw_text)
            if match:
                cipher = match.group(1).strip()
                print(f"[🔐] Найден шифр в тексте: {cipher}")
                break

        # Быстрый поиск GARTI-ваучера в тексте
        match_garti_text = re.search(r'(GARTI-[A-Z0-9]{3,})', raw_text, re.IGNORECASE)
        if match_garti_text:
            garti_from_ocr = match_garti_text.group(1).strip()
            print(f"[📝] Найден GARTI в тексте: {garti_from_ocr}")

        # OCR только если не найден GARTI в тексте
        if isinstance(event.media, MessageMediaPhoto) and not garti_from_ocr:
            try:
                image_data = await event.download_media(bytes)
                img = Image.open(io.BytesIO(image_data))
                ocr_text = pytesseract.image_to_string(img)
                print(f"[🖼️ OCR]: {ocr_text}")
                full_text += "\n" + ocr_text

                if not cipher:
                    for pattern in cipher_patterns:
                        match = pattern.search(ocr_text)
                        if match:
                            cipher = match.group(1).strip()
                            print(f"[🔐] Шифр найден через OCR: {cipher}")
                            break

                match_garti = re.search(r'(GARTI-[A-Z0-9]{3,})', ocr_text, re.IGNORECASE)
                if match_garti:
                    garti_from_ocr = match_garti.group(1).strip()
                    print(f"[📷] Найден GARTI-ваучер: {garti_from_ocr}")

            except Exception as e:
                print(f"[❌] Ошибка OCR: {e}")

        # Поиск всех типов ваучеров
        for label, pattern in voucher_patterns.items():
            matches = pattern.findall(full_text)
            for match in matches:
                code = match.strip()
                if '*' in code:
                    if cipher:
                        code = code.replace('*', cipher)
                        print(f"[✏️] Вставлен шифр: {code}")
                    else:
                        print(f"[⛔] Пропущен (нет шифра): {code}")
                        continue
                if code.lower() not in sent_vouchers:
                    sent_vouchers.add(code.lower())
                    new_codes.append(code)

        # GARTI из OCR + шифр
        if garti_from_ocr and cipher:
            full_garti = garti_from_ocr + cipher
            if full_garti.lower() not in sent_vouchers:
                sent_vouchers.add(full_garti.lower())
                new_codes.append(full_garti)
                print(f"[🧩] GARTI с OCR и шифром: {full_garti}")

        # Удаление вложенных дубликатов
        cleaned_codes = []
        for code in new_codes:
            if not any(other != code and code in other for other in new_codes):
                cleaned_codes.append(code)

        if cleaned_codes:
            msg = "\n".join(f"`{code}`" for code in cleaned_codes)
            for channel in target_channels:
                try:
                    await client.send_message(channel, msg, parse_mode='markdown')
                    print(f"[✅] Отправлено в {channel}:\n{msg}")
                except Exception as e:
                    print(f"[⚠️] Ошибка при отправке в {channel}: {e}")
        else:
            print("[ℹ️] Новых кодов не найдено.")

    print("[🚀] Бот работает... (ожидает новые сообщения)")
    await client.start()
    await client.run_until_disconnected()

# 🔁 Перезапуск при падении
while True:
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[🔥] Ошибка: {e}")
        print("⏳ Перезапуск через 5 секунд...")
        time.sleep(5)
