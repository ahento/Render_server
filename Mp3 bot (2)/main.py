import os
import yt_dlp as youtube_dl
import instaloader
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Logging konfiguratsiyasi
logging.basicConfig(level=logging.INFO)

# YouTube API kalitini o'rnating
YOUTUBE_API_KEY = 'AIzaSyDlTWDGgl_oUvkLAF1rLqNGkxgWVQGreqM'
# Telegram bot tokenini o'rnating
TELEGRAM_TOKEN = '7664488334:AAFpSrUwTCKJCO-iejIRkBAkS1pS2rSzqsw'

# YouTube API ni ishga tushirish
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
L = instaloader.Instaloader()

# Foydalanuvchi holatlari
USER_STATE = {}

# Holatlar
WAITING_FOR_CHOICE = 'waiting_for_choice'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Salom! MP3 yoki video yuklab olish uchun YouTube yoki Instagram URL yuboring.')

def search_youtube(query: str):
    request = youtube.search().list(q=query, part='id,snippet', maxResults=1)
    response = request.execute()
    return response['items']

def download_audio(url: str) -> str:
    options = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', None)
        return f"{title}.mp3"

def download_video(url: str) -> str:
    options = {
        'format': 'mp4',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': False,
    }
    with youtube_dl.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', None)
        return f"{title}.mp4"

def download_instagram_video(url: str) -> str:
    post = instaloader.Post.from_shortcode(L.context, url.split('/')[-2])
    video_url = post.video_url
    filename = f"{post.owner_username}_{post.shortcode}.mp4"
    L.download_post(post, target=filename)
    return filename

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text

    logging.info(f'User input: {user_input}')  # Logger

    if user_id in USER_STATE and USER_STATE[user_id] == WAITING_FOR_CHOICE:
        await handle_choice(update, context)
    else:
        if "youtube.com/watch?v=" in user_input or "youtu.be/" in user_input:
            url = user_input
            await update.message.reply_text("Sizga qo'shiq kerakmi yoki video?")  # Tanlov so'rash
            context.user_data['url'] = url
            USER_STATE[user_id] = WAITING_FOR_CHOICE
        elif "instagram.com" in user_input:
            url = user_input
            await update.message.reply_text("Instagram videoni yuklaymizmi yoki MP3ga o'giramizmi?")  # Tanlov so'rash
            context.user_data['url'] = url
            USER_STATE[user_id] = WAITING_FOR_CHOICE
        else:
            videos = search_youtube(user_input)
            logging.info(f'Search results: {videos}')  # Logger

            if videos:
                video_id = videos[0]['id']['videoId']
                url = f'https://www.youtube.com/watch?v={video_id}'
                await update.message.reply_text("Sizga qo'shiq kerakmi yoki video?")  # Tanlov so'rash
                context.user_data['url'] = url
                USER_STATE[user_id] = WAITING_FOR_CHOICE
            else:
                await update.message.reply_text('Hech narsa topilmadi.')

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    choice = update.message.text.lower().strip()  # Kiritilgan tanlovni pastki registrga o'tkazish
    url = context.user_data.get('url')

    logging.info(f'User choice: {choice}, URL: {url}')  # Logger

    if url:
        if choice == 'qo\'shiq' and "youtube" in url:
            try:
                mp3_file = download_audio(url)
                with open(mp3_file, 'rb') as audio:
                    await update.message.reply_audio(audio)
                os.remove(mp3_file)  # Yuklangan faylni o'chirish
            except Exception as e:
                await update.message.reply_text(f'Xato: {e}')
        elif choice == 'video' and "youtube" in url:
            try:
                mp4_file = download_video(url)
                with open(mp4_file, 'rb') as video:
                    await update.message.reply_video(video)
                os.remove(mp4_file)  # Yuklangan faylni o'chirish
            except Exception as e:
                await update.message.reply_text(f'Xato: {e}')
        elif choice == 'video' and "instagram" in url:
            try:
                video_file = download_instagram_video(url)
                with open(video_file, 'rb') as video:
                    await update.message.reply_video(video)
                os.remove(video_file)  # Yuklangan faylni o'chirish
            except Exception as e:
                await update.message.reply_text(f'Xato: {e}')
        else:
            await update.message.reply_text("Iltimos, faqat 'qo'shiq' yoki 'video' deb javob bering.")
            return

        # Tanlovdan so'ng foydalanuvchi holatini tozalash
        USER_STATE.pop(user_id, None)
    else:
        await update.message.reply_text("Avval YouTube yoki Instagram URL ni yuboring.")

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
 