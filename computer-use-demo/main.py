import asyncio
import email
import imaplib
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from openai import OpenAI

from computer_use_demo.streamlit import main as streamlit_main


def askgpt(system, prompt):
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": f"{system}"}]},
            {"role": "user", "content": [{"type": "text", "text": f"{prompt}"}]},
        ],
        temperature=1,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={"type": "text"},
    )

    return response.choices[0].message.content


async def askgpt_and_start_session(prompt):
    # Execute the computer use session
    system = "You are a prompt adjuster. You make flesh out prompts for AI tools that are capable and connected to the internet so that they are more clear and direct. Your prompts come from emails from normal people. Return a more clear prompt. Make some assumptions about what reasonable people would be requesting"
    email_input = askgpt(system, prompt)

    print("Starting virtual machine with prompt")
    results = await streamlit_main(email_input)

    system = "You are a robot named easi.work. You are writing an email with a summary of your findings from the following results: "
    return askgpt(system, results)


def send_email(subject, body, to_email, from_email, email_alias, app_password):
    try:
        # set up the SMTP server
        smtp_server = "smtp.mail.me.com"
        smtp_port = 587

        # create email
        msg = MIMEMultipart()
        msg["From"] = email_alias
        msg["To"] = to_email.strip()
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        print("sending email...", to_email, subject, email_alias)

        # send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # secure the connection
            server.login(from_email, app_password)
            server.sendmail(email_alias, to_email, msg.as_string())

        print("email sent successfully")

    except Exception as e:
        print(f"error: {e}")


async def read_emails(from_email, app_password, folder="INBOX", filter_to=None):
    try:
        imap_server = "imap.mail.me.com"
        imap_port = 993

        with imaplib.IMAP4_SSL(imap_server, imap_port) as mail:
            mail.login(from_email, app_password)
            mail.select(folder)

            # apply filter for "TO" email address
            search_criteria = f'TO "{filter_to}"' if filter_to else "ALL"
            print(f"search_criteria: {search_criteria}")
            status, messages = mail.search(None, search_criteria)

            if status != "OK":
                print("Failed to search emails")
                return

            email_ids = messages[0].split()
            print(
                f"{len(email_ids)} emails found in {folder} for filter TO: {filter_to}"
            )

            for num in email_ids:
                # fetch email flags
                flag_status, flag_data = mail.fetch(num, "(FLAGS)")
                flags = flag_data[0].decode("utf-8") if flag_data[0] else ""
                is_read = "\\Seen" in flags
                busy = False

                # fetch email subject and body
                textstatus, text = mail.fetch(num, "(BODY.PEEK[TEXT])")
                subjectstatus, subject_data = mail.fetch(
                    num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])"
                )
                fromstatus, from_data = mail.fetch(
                    num, "(BODY.PEEK[HEADER.FIELDS (FROM)])"
                )

                subject = email.message_from_bytes(subject_data[0][1]).get("Subject")
                email_message = email.message_from_bytes(text[0][1])
                # get sender email
                sender = email.utils.parseaddr(from_data[0][1].decode("utf-8"))[1]
                print("sender: ", sender)
                body = (
                    email_message.get_payload(decode=True).decode("utf-8")
                    if email_message.is_multipart()
                    else email_message.get_payload()
                )

                # print read/unread status and email details
                status_text = "Read" if is_read else "Unread"
                if not is_read and not busy:
                    busy = True
                    print(f"Email ID {num.decode('utf-8')} is {status_text}")
                    print(f"Subject: {subject}")
                    print(f"Body: {body}")

                    # generate a response
                    print("Asking GPT for a response")
                    call_to_action = await askgpt_and_start_session(
                        f"Subject: {subject}\n\nBody: {body}"
                    )
                    send_email(
                        subject,
                        call_to_action,
                        sender,
                        from_email,
                        filter_to,
                        app_password,
                    )

                    # mark email as read
                    status, read_status = mail.store(num, "+FLAGS", "\\Seen")
                    if status != "OK":
                        print("Failed to mark email as read")
                    else:
                        print("Email marked as read")

                    print("-" * 50)

                else:
                    print(f"Email ID {num.decode('utf-8')} is {status_text}")
                    print(f"Subject: {subject}")
                    print("-" * 50)

    except Exception as e:
        print(f"Error: {e}")

async def main():
    from_email = os.getenv("ICLOUD_USER_EMAIL")
    email_alias = os.getenv("EMAIL_ALIAS")
    app_password = os.getenv("ICLOUD_APP_PASSWORD")

    if not app_password:
        raise OSError("ICLOUD_APP_PASSWORD environment variable not set!")

    print("Initiating computer use session...")
    print("Script is running")

    # results = load_from_storage("results")
    # print(results)
    # system = "You are taking the information provided and writing an email as a helpful AI assistant named Easi.Work"
    # print(askgpt(system, results))
    while True:
        await read_emails(from_email, app_password, filter_to=email_alias)
        time.sleep(60)

# usage example
if __name__ == "__main__":
    asyncio.run(main())
