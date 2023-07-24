import os.path
import time
import sys
from questionary import prompt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = "./gmail-auth.json"
TOKEN_PATH = "./token"

CATEGORIES = ["promotions", "forums", "updates", "social"]


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds._refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=7777)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds


def list_messages(service, query):
    messages = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=100)
        ).execute()

        if "messages" in response:
            messages.extend(response["messages"])

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return messages


def delete_message(service, message_id, max_retries=5, retry_delay=5):
    for i in range(max_retries):
        try:
            service.users().messages().trash(userId="me", id=message_id).execute()
            return
        except Exception as e:
            if isinstance(e, HttpError) and e.resp.status == 500:
                print(
                    f"Encountered server error 500. Retrying in {retry_delay} seconds... ({i+1}/{max_retries})"
                )
                time.sleep(retry_delay)
            else:
                raise e

    print(
        f"Failed to delete message {message_id} after {max_retries} attempts. Exiting."
    )


def delete_emails(category):
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

        messages = list_messages(service, f"category:{category}")

        if not messages:
            print(f"No {category} emails found.")
            return

        total_emails = len(messages)

        print(f"Found {total_emails} emails in the {category} category. Deleting...")

        batch_size = 100

        for i in range(0, total_emails, batch_size):
            batch = messages[i : i + batch_size]
            for message in batch:
                delete_message(service, message["id"])

            print(
                f"Deleted {len(batch)} emails. {total_emails - i - len(batch)} emails remaining."
            )

        print(f"All {category} emails deleted successfully.")

    except Exception as e:
        print("An error occured: ", e)


def get_category_from_prompt():
    options = [
        {
            "type": "list",
            "name": "category",
            "message": "Choose an email category from which to delete all emails: ",
            "choices": CATEGORIES,
        }
    ]

    answer = prompt(options)
    category = answer["category"]

    return category


if __name__ == "__main__":
    category = get_category_from_prompt()
    delete_emails(category)
    # print(category)

    # arg = sys.argv[1] if len(sys.argv) > 1 else None

    # if arg is None:
    #     category = get_category_from_prompt()
    #     delete_emails(category)

    # elif arg in CATEGORIES:
    #     delete_emails(arg)

    # else:
    #     print(
    #         "You must provide a valid category. One of promotions, forums, or updates. Aborted."
    #     )
