import os
import asyncio
import telebot
import google.generativeai as genai
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip

# -------------------------------------------------------------
# 1-2 BOSQICHDA OLINGAN KALITLARNI SHU YERGA QO'YASIZ:
BOT_TOKEN = "9039167659:AAFe_NXWej0XdVTRnRtnImbK6AoZ7hcPfDw"
GEMINI_KEY = "AQ.Ab8RN6JXZfT1xXjfY0wdQlyzehSJK0Ret_VaAL9RySPLDmVqnA"
# -------------------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)

# Agent ko'rsatmasi va yangi imlo nazorati
SYSTEM_PROMPT = """
Siz professional video-kontent yaratuvchi AI agentsiz.
Foydalanuvchi bergan ssenariyni 20-40 soniyalik video uchun 5 soniyalik bo'laklarga (scenes) bo'ling.

MUHIM QO'IDA:
Barcha matn va subtitrlar O'ZBEK TILINING YANGI TAHRIRDAGI LOTIN ALIFBOSI va imlo qoidalariga qat'iy amal qilishi shart!
(O‘, o‘, G‘, g‘ belgilari to'g'ri yozilishi, tutuq belgisi (') to'g'ri qo'llanilishi shart).

Javobni faqat va faqat ushbu JSON formatida qaytaring:
{
  "full_text_uz": "Yangi imlodagi to'liq ovozli matn",
  "scenes": [
    {"prompt_en": "Detailed prompt for AI image generation in English", "sub_uz": "Birinchi kadr subtitri"},
    {"prompt_en": "Detailed prompt for second scene in English", "sub_uz": "Ikkinchi kadr subtitri"}
  ]
}
"""

async def generate_audio(text_uz: str, output_path: str):
    """Microsoft Edge TTS orqali bepul o'zbekcha ovoz yozish"""
    communicate = edge_tts.Communicate(text_uz, "uz-UZ-MadinaNeural")
    await communicate.save(output_path)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Salom! Menga video ssenariysini yuboring. Men yangi tahrirdagi o'zbek alifbosida 20-40 soniyalik video montaj qilib beraman.")

@bot.message_handler(func=lambda message: True)
def process_video_request(message):
    status_msg = bot.reply_to(message, "⏳ Ssenariy tahlil qilinmoqda va yangi imloga o'tkazilmoqda...")
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(f"Ssenariy: {message.text}")
        data = eval(response.text)
        
        bot.edit_message_text("🎙️ O'zbekcha ovoz va vizual kadrlar yaratilmoqda...", message.chat.id, status_msg.message_id)
        
        audio_file = f"voice_{message.chat.id}.mp3"
        asyncio.run(generate_audio(data["full_text_uz"], audio_file))
        audio_clip = AudioFileClip(audio_file)
        
        clips = []
        scene_duration = audio_clip.duration / len(data["scenes"])
        
        for scene in data["scenes"]:
            prompt_clean = scene["prompt_en"].replace(" ", "%20")
            img_url = f"https://image.pollinations.ai/prompt/{prompt_clean}?width=1080&height=1920&nologo=true"
            
            img_clip = ImageClip(img_url).set_duration(scene_duration)
            
            txt_clip = TextClip(
                scene["sub_uz"], 
                fontsize=36, 
                color='white', 
                bg_color='black',
                font='Arial',
                size=(900, None),
                method='caption'
            ).set_duration(scene_duration).set_position(('center', 'bottom'))
            
            clips.append(CompositeVideoClip([img_clip, txt_clip]))
        
        bot.edit_message_text("🎬 Video montaj qilinmoqda...", message.chat.id, status_msg.message_id)
        
        output_video = f"video_{message.chat.id}.mp4"
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
        final_video.write_videofile(output_video, fps=24, codec="libx264")
        
        with open(output_video, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=f"✅ Videongiz tayyor!\n\nMatn (Yangi imlo):\n{data['full_text_uz']}")
        
        audio_clip.close()
        final_video.close()
        os.remove(audio_file)
        os.remove(output_video)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Xatolik yuz berdi: {str(e)}")

bot.polling()
