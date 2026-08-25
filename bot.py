import asyncio
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from playwright.async_api import async_playwright

load_dotenv()

# Web server for Render Keep-Alive
app = Flask(__name__)
@app.route('/')
def home():
    return "E-Aadhar Bot is running and healthy!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))

# Bot Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# States for the Conversation Flow
AADHAAR, CAPTCHA, OTP = range(3)

# Global dictionary to hold browser sessions per user so they stay open while waiting for messages
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the E-Aadhar Downloader Bot! 🇮🇳\n\n"
        "To begin, please send me your 12-digit Aadhaar Number.\n\n"
        "(Type /cancel at any time to stop)"
    )
    return AADHAAR

async def receive_aadhaar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    aadhaar_num = update.message.text.strip().replace(" ", "")
    
    if len(aadhaar_num) != 12 or not aadhaar_num.isdigit():
        await update.message.reply_text("Invalid Aadhaar Number. Please enter exactly 12 digits.")
        return AADHAAR
        
    msg = await update.message.reply_text("Initializing secure browser and connecting to UIDAI... Please wait.")
    
    # Clean up any existing session for this user just in case
    await cleanup_session(user_id)
    
    # Start Playwright session for this user
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    b_context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await b_context.new_page()
    
    user_sessions[user_id] = {
        'playwright': pw,
        'browser': browser,
        'context': b_context,
        'page': page
    }
    
    try:
        await page.goto("https://myaadhaar.uidai.gov.in/genricDownloadAadhaar", timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        # Robust locator for Aadhaar input
        await page.locator("input[placeholder*='Aadhaar']").first.fill(aadhaar_num)
        
        # Take screenshot of captcha
        captcha_element = page.locator("img[alt='captcha'], img[src*='captcha']").first
        await captcha_element.wait_for(state="visible", timeout=10000)
            
        captcha_path = f"captcha_{user_id}.png"
        await captcha_element.screenshot(path=captcha_path)
        
        await update.message.reply_photo(
            photo=open(captcha_path, 'rb'), 
            caption="Please type the letters you see in this Captcha image:"
        )
        os.remove(captcha_path)
        
        return CAPTCHA
        
    except Exception as e:
        await update.message.reply_text(f"Failed to load UIDAI page. The government server might be busy. Please type /start to try again.\n\nError code: {str(e)[:100]}")
        await cleanup_session(user_id)
        return ConversationHandler.END

async def receive_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    captcha_text = update.message.text.strip()
    
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Session expired because it took too long. Please type /start to try again.")
        return ConversationHandler.END
        
    page = session['page']
    await update.message.reply_text("Submitting Captcha and requesting OTP...")
    
    try:
        # Fill captcha and click Send OTP
        await page.locator("input[placeholder*='captcha'], input[placeholder*='Captcha']").first.fill(captcha_text)
        await page.locator("button:has-text('Send OTP')").first.click()
        
        # Wait for the OTP input field to become visible, indicating success
        try:
            otp_input = page.locator("input[placeholder*='OTP']").first
            await otp_input.wait_for(state="visible", timeout=15000)
            await update.message.reply_text("✅ OTP sent successfully to your Aadhaar-registered mobile number!\n\nPlease type the OTP here:")
            return OTP
        except:
            # If OTP input doesn't appear, the captcha was likely wrong
            await update.message.reply_text("❌ Failed to send OTP. Usually this means the Captcha was typed incorrectly, or UIDAI servers are slow.\n\nPlease type /start to try again.")
            await cleanup_session(user_id)
            return ConversationHandler.END
            
    except Exception as e:
        await update.message.reply_text(f"An error occurred. Please type /start to try again.")
        await cleanup_session(user_id)
        return ConversationHandler.END

async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Session expired. Please type /start to try again.")
        return ConversationHandler.END
        
    page = session['page']
    
    await update.message.reply_text("Verifying OTP and downloading your E-Aadhar... Please wait (this can take up to 30 seconds).")
    
    try:
        await page.locator("input[placeholder*='OTP']").first.fill(otp)
        
        # Start waiting for the PDF download before clicking the download button
        async with page.expect_download(timeout=60000) as download_info:
            await page.locator("button:has-text('Verify & Download')").first.click()
            
        download = await download_info.value
        pdf_path = f"eaadhar_{user_id}.pdf"
        await download.save_as(pdf_path)
        
        await update.message.reply_document(
            document=open(pdf_path, 'rb'), 
            caption="🎉 Here is your E-Aadhar!\n\n*Password Note:* The password to open this PDF is the first 4 letters of your name in CAPITALS followed by your YYYY year of birth (e.g., RAKE1990).",
            parse_mode="Markdown"
        )
        os.remove(pdf_path)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to download E-Aadhar. The OTP might be incorrect, or the UIDAI server failed to generate the PDF.\n\nPlease type /start to try again.")
    finally:
        await cleanup_session(user_id)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Download cancelled. Type /start whenever you want to try again.")
    await cleanup_session(update.effective_user.id)
    return ConversationHandler.END

async def cleanup_session(user_id):
    """Securely closes the browser and frees memory for a specific user"""
    if user_id in user_sessions:
        try:
            await user_sessions[user_id]['browser'].close()
            await user_sessions[user_id]['playwright'].stop()
        except:
            pass
        del user_sessions[user_id]

def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is completely missing from environment variables.")
        return
        
    # 1. Start the Flask web server in a background thread so Render doesn't shut down the app
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 2. Start the Telegram Bot
    application = Application.builder().token(TOKEN).build()

    # The ConversationHandler manages the state machine flow for each unique user
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('download', start)],
        states={
            AADHAAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_aadhaar)],
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_captcha)],
            OTP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    
    print("E-Aadhar Bot is now running and polling for messages!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
