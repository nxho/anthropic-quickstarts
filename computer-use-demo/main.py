import asyncio
import os

from email_utils import read_emails

from computer_use_demo.websocket import websocket_server

wait_time_in_s = 15

async def run_email_script():
    await asyncio.sleep(5)
    from_email = os.getenv("ICLOUD_USER_EMAIL")
    email_alias = os.getenv("EMAIL_ALIAS")
    app_password = os.getenv("ICLOUD_APP_PASSWORD")

    if not app_password:
        raise OSError("ICLOUD_APP_PASSWORD environment variable not set!")

    print("Initiating computer use session...")
    print("Script is running")

    while True:
        await read_emails(from_email, app_password, filter_to=email_alias)
        print(f"Waiting {wait_time_in_s} seconds before reading emails again")
        await asyncio.sleep(wait_time_in_s)

async def main():
    websocket_task = asyncio.create_task(websocket_server())
    email_task = asyncio.create_task(run_email_script())
    await asyncio.gather(websocket_task, email_task)

if __name__ == "__main__":
    asyncio.run(main())

