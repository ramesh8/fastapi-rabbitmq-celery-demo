import base64
from datetime import datetime, timedelta
import io
import os
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
import requests


class Subscriptions:
    def __init__(self):
        # todo: review the constructor for idempotence
        load_dotenv()
        self.mail = os.getenv("mail")
        self.mainpath = os.getenv("walk")
        self.billspath = os.getenv("billspath")
        self.url = os.getenv("url")
        self.client_id = os.getenv("client_id")
        self.client_secret = os.getenv("client_secret")
        self.tenant_id = os.getenv("tenant_id")

        self.microsoft_url = "https://graph.microsoft.com/v1.0"
        self.subscriptions_endpoint = f"{self.microsoft_url}/subscriptions"

        self.subscribe_callback_endpoint = f"{self.url}/subscribed/"
        self.lifecycle_callback_endpoint = f"{self.url}/lifecycle/"
        self.junk_subscribe = f"{self.url}/subscribed_junk/"

        self.scopes = ["https://graph.microsoft.com/.default"]
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority,
        )
        self.result = self.app.acquire_token_silent(scopes=self.scopes, account=None)

    def get_headers(self, content_type: str = None):
        if not self.result:
            result = self.app.acquire_token_for_client(scopes=self.scopes)
        access_token = result["access_token"]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": content_type if content_type else "application/json",
        }
        return headers

    def subscription_api_request(self, notificationUrl, folder):
        currentTime = datetime.utcnow()
        expireTime = currentTime + timedelta(minutes=60)
        exdt = expireTime.astimezone().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        data = {
            "changeType": "created",
            "notificationUrl": notificationUrl,
            "lifecycleNotificationUrl": self.lifecycle_callback_endpoint,
            "resource": f"users/{self.mail}/mailFolders('{folder}')/messages",
            "expirationDateTime": exdt,
            # "includeResourceData":True,
        }

        response = requests.post(
            self.subscriptions_endpoint, headers=self.get_headers(), json=data
        )

        return response.json()

    def create_subscription(self):
        subs = {
            "inbox": self.subscribe_callback_endpoint,
            "junkemail": self.junk_subscribe,
        }

        final_res = []

        for folder, endpoint in subs.items():
            final_res.append(self.subscription_api_request(endpoint, folder))

        return final_res

    def get_subscriptions(self):
        response = requests.get(
            self.subscriptions_endpoint,
            headers=self.get_headers(),
        )

        if response.status_code == 200:
            return response.json()
        return None

    def delete_subs(self, subscriptionId):
        if isinstance(subscriptionId, list):
            for id in subscriptionId:
                requests.delete(
                    self.subscriptions_endpoint + "/" + id, headers=self.get_headers()
                )
        else:
            requests.delete(
                self.subscriptions_endpoint + "/" + subscriptionId,
                headers=self.get_headers(),
            )
        return None

    def get_resource(self, resid):
        resurl = f"{self.microsoft_url}/{resid}"
        response = requests.get(resurl, headers=self.get_headers())

        output = {}

        if response.status_code == 200:
            output["status"] = 100
        else:
            output["status"] = response.status_code

        output["response"] = response.json()

        return output

    def renew_subscription(self, subscriptionId):
        currentTime = datetime.utcnow()
        expireTime = currentTime + timedelta(minutes=60)
        exdt = expireTime.astimezone().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = {"expirationDateTime": exdt}
        response = requests.patch(
            self.subscriptions_endpoint + "/" + subscriptionId,
            headers=self.get_headers(),
            json=data,
        )

        if response.status_code == 200:
            return response.json()
        return None

    def get_attachments(self, resid):  # responseId
        resurl = f"{self.microsoft_url}/users/{self.mail}/messages/{resid}/attachments"
        print(resurl)
        response = requests.get(resurl, headers=self.get_headers())

        if response.status_code == 200:
            res = response.json()["value"]
            # self.save_attachments(res)
            print("get_attachments")
            # anames = [a["name"] for _, a in enumerate(res)]
            cbytes = [
                {"name": a["name"], "content": a["contentBytes"]}
                for _, a in enumerate(res)
            ]
            return {"status": 100, "attachments": cbytes}
        else:
            return {
                "status": 500,
                "message": f"Error while getting attachments",
                "response": response.json(),
            }

    # def save_attachments(self, att_response):
    #     try:
    #         os.makedirs(self.target_folder, exist_ok=True)
    #         for index, attachment in enumerate(att_response):
    #             name = attachment["name"]
    #             cbytes = attachment["contentBytes"]

    #             source_fname, ext = os.path.splitext(name)
    #             generated_fname = self.generate_name(index, name)

    #             source_file_key = os.path.join(self.target_folder, generated_fname).replace("\\","/")
    #             bytes = io.BytesIO(base64.b64decode(cbytes))
    #             res = self.aws_boto3_service.upload_to_s3_object(source_file_key, bytes,ext)
    #             if(self.ec_connector.get_attchment(source_file_key) !=None):
    #                 continue
    #             self.save_file_table_object(source_file_key)

    #             if ext == ".rar" or ext == ".zip":
    #                 os.makedirs("zip_files",exist_ok=True)
    #                 source_file=os.path.join("zip_files", generated_fname)
    #                 self.archive_files(source_file)
    #                 os.remove(source_file)

    #             # email client service in docker (50%)
    #             # todo: update db

    #             # conversion service in docker (50%)
    #             # todo: initiate asyncio task -> conversion, update db
    #             # todo: conversion -> upload to s3, update db

    #             # s3 service in docker (50%)
    #             # todo: upload to s3 -> extraction call (s3 key) -> save res to db

    #             # extraction service in docker (80%)
    #             # todo: extraction api
    #     except Exception as ex:
    #         print('exxxxxxx',ex)
