# E-Aadhar Automation Bot

A highly interactive Telegram bot that securely acts as your personal assistant for downloading your E-Aadhar card from the UIDAI portal.

## How it works
1. Send `/download` or `/start` to your Bot on Telegram.
2. It asks for your 12-digit Aadhaar number.
3. It opens an invisible Chrome browser on the cloud, visits UIDAI, and takes a picture of the Captcha.
4. It sends you the picture on Telegram.
5. You type the letters you see. It clicks "Send OTP".
6. You receive an SMS from UIDAI and type it into Telegram.
7. The Bot downloads the E-Aadhar PDF and sends it directly to you on Telegram!

---

## Setup & Cloud Deployment Guide

### Step 1: Create a Telegram Bot
1. Open Telegram and search for **BotFather** (it has a blue checkmark).
2. Send the message `/newbot` and follow the prompts.
3. BotFather will give you a **token** (it looks like `1234567890:ABCdefGHI...`). Save this! This is your `TELEGRAM_BOT_TOKEN`.

### Step 2: Push this code to GitHub
Create a Private repository on GitHub (e.g. `eaadhar-bot`) and upload all the files in this folder to it.

### Step 3: Deploy to Render.com (Free)
1. Create a free account on [Render.com](https://render.com).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub account and select your `eaadhar-bot` repository.
4. Render will automatically detect the `Dockerfile`.
5. Scroll down to **Environment Variables** and click "Add Environment Variable".
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: *(Paste the token from Step 1)*
6. Click **Create Web Service**. 
7. *Note: The first time it builds, it will take around 5-10 minutes because it has to download the Playwright browser system.*

### Step 4: Keep it Awake (UptimeRobot)
Render's free tier goes to sleep if nobody visits it for 15 minutes. To prevent your bot from falling asleep:
1. Once Render finishes building, copy the URL they give you at the top left (e.g. `https://eaadhar-bot.onrender.com`).
2. Go to [UptimeRobot.com](https://uptimerobot.com) and create a free account.
3. Click **Add New Monitor**.
   - Monitor Type: `HTTP(s)`
   - URL: *(Paste your Render URL)*
   - Interval: `14 minutes`
4. Click **Create Monitor**.

Your bot is now awake 24/7 and ready to download E-Aadhars whenever you message it!
