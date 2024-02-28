from datetime import datetime  #!careful
import os
import time
import uuid
from bson import ObjectId
from pymongo import MongoClient
import logging
from dotenv import load_dotenv
from utils.constants import BillProcessStatus
from utils.email_client_utils import EmailClientUtils
from utils.s3_utils import S3Utils
from subscriptions import Subscriptions

# from logs.init_logging import init_logging


class InvalidSenderException(Exception):
    """Sender mail id is not from accepted domain list"""

    def __init__(self, resid):
        self.resid = resid


class EmailJob:
    def __init__(self, resid, sender, subject, hasAtt):
        # init_logging()
        load_dotenv()
        self.mainpath = os.getenv("walk")
        self.billspath = os.getenv("billspath")
        self.email_id = None
        self.email_table_id = None
        self.resid = resid
        self.sender = sender
        self.subject = subject  # not used
        self.hasAttachments = hasAtt
        mongo = MongoClient("mongodb://mongodbserver:27017/")
        db = mongo["asyncdemo"]
        self.resources = db["mq_resources"]
        self.files = db["mq_files"]
        self.s3_utils = S3Utils()
        self.ec_utils = EmailClientUtils()
        self.subs = Subscriptions()

    def create_path(self, mail_address: str):
        cp = mail_address.split("@")[0].split(".")  # get client and property

        if len(cp) == 2:
            self.target_folder = os.path.join(
                self.mainpath, cp[0], cp[1], self.billspath
            )
        else:
            self.target_folder = os.path.join(self.mainpath, cp[0], self.billspath)

    def filter_mails(self, recipients):
        for recipient in recipients:
            mail_address = recipient["emailAddress"]["address"]
            if (
                "@sendhours.com" in mail_address
            ):  # fetch mail only domain with @sendhours.com
                self.create_path(mail_address)  # create path based on mail
                return mail_address
            else:
                return None

    def save_email(self):
        """save email to s3 and db"""
        # fetch mail info
        print("save email resid:", self.resid)
        email = self.resources.find_one({"_id": ObjectId(self.resid)})
        if email == None or "response" not in email:
            print(
                f"[email = {email}][resid={self.resid}] Something went wrong. Check Database..."
            )
            return

        email = email["response"]
        print("save_email", email)
        if email["isRead"] == True:
            print("mail already read!!!")
            return

        subject = email["subject"]
        body_preview = email["bodyPreview"]
        body = email.get("body", {}).get("content", "")
        from_email = email["from"]["emailAddress"]["address"]
        self.mail_id = from_email
        received_datetime = email["receivedDateTime"]
        formatted_datetime = datetime.strptime(received_datetime, "%Y-%m-%dT%H:%M:%SZ")
        received_timestamp = datetime.strftime(formatted_datetime, "%Y%m%d%H%M%S%f")
        recipients = email.get("ccRecipients", []) + email.get("toRecipients", [])
        mail_address = self.filter_mails(recipients)
        if not mail_address:
            print("Invalid Sender Exception")
            raise InvalidSenderException(self.resid)
        emails_folder = os.path.join(self.mainpath, "myemail")
        mail_fname = received_timestamp + "-Email-info.txt"

        # upload mailbody to s3
        email_content = f"""From:\n{from_email}\n\nTo:\n{mail_address}\n\nSubject:\n{subject}\n\nEmail Time:\n{received_timestamp}\n\nPlain Text Body:\n{body_preview}\n\nHTML Body:\n{body}"""
        email_s3_key = os.path.join(emails_folder, mail_fname).replace("\\", "/")
        self.s3_utils.upload_to_s3_content(email_s3_key, email_content)
        print("s3_utils.upload...")
        cp = mail_address.split("@")[0].split(".")

        client = cp[0] if len(cp) >= 1 else ""
        property = cp[1] if len(cp) > 1 else ""

        # save mail info to db
        email_object = {
            "from": from_email,
            "to": mail_address,
            "s3_key": email_s3_key,
            "reference_id": email["id"],
            "timestamp": datetime.now(),
            "client": client,
            "property": property,
            "process_status": BillProcessStatus.TO_BE_APPROVED,
            "upload_type": "email",
        }
        self.email_table_id = self.ec_utils.add_email(email_object)
        print("add_email", email_object)
        return email_object

    def get_attachments(self, resid):
        res = self.subs.get_attachments(resid)
        if res["status"] != 100:
            return None
        return res["attachments"]

    def process_mail(self):
        from worker import process_file_task

        # task 1
        # time.sleep(5)
        emailobj = self.save_email()
        self.resources.update_one(
            {"_id": ObjectId(self.resid)},
            {"$set": {"mq_status": "mail saved to s3 & db"}},
        )

        # task 2
        # fetch attachments
        # unzip attachments (optional)
        # upload attachments to s3
        # save attachments info to db
        if self.hasAttachments == False:
            print("No Attachments found ...")
            return

        attlist = self.get_attachments(emailobj["reference_id"])
        # print("attlist", attlist)

        if attlist == None:
            print("No Attachments found...")
            return

        # todo: check if att(s) is/are zip file(s), and extract in-memory
        flist = []
        # for att in attlist:
        #     fname, ext = os.path.splitext(att["name"])
        #     if ext==".rar" or ext==".zip":
        #         flist.extend(self.unzip_attachment())

        flist = attlist
        for findex, att in enumerate(flist):
            fileid = str(uuid.uuid4())
            process_file_task.delay(
                findex,
                fileid,
                att["name"],
                att["content"],
                self.resid,
                str(self.email_table_id),
            )

        # time.sleep(1)
        self.resources.update_one(
            {"_id": ObjectId(self.resid)},
            {"$set": {"mq_status": "mail attachments saved to s3 & db"}},
        )
