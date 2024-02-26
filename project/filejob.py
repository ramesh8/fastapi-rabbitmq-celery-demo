import base64
import datetime
import io
import json
import logging
import os
import random
import time
import uuid
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
import requests
from utils.email_client_utils import EmailClientUtils
from utils.s3_utils import S3Utils
from subscriptions import Subscriptions

# from logs.init_logging import init_logging


class FileJob:
    # findex, fileid, fname, self.resid
    def __init__(self, findex, fileid, fname, fcontent, resid, email_table_id):
        # init_logging()
        load_dotenv()
        self.mainpath = os.getenv("walk")
        self.billspath = os.getenv("billspath")
        self.extraction_url = os.getenv("extraction_url")
        self.findex = findex
        self.fileid = fileid
        self.fname = fname
        self.fcontent = fcontent
        self.resid = resid
        self.email_table_id = email_table_id
        self.client = self.property = self.s3key = self.file_table_id = None

        mongo = MongoClient("mongodb://mongodbserver:27017/")
        db = mongo["asyncdemo"]
        self.resources = db["mq_resources"]
        self.files = db["mq_files"]
        self.filestages = db["mq_filestages"]
        self.emailobj = self.get_resource()
        self.s3_utils = S3Utils()
        self.ec_utils = EmailClientUtils()
        self.subs = Subscriptions()

        self.stages = [
            # {
            #     "name": "SE",
            #     "description": "Save Email",
            #     "time_min": 1,
            #     "time_max": 5,
            #     "order": 1,
            # },
            {
                "name": "SA",
                "description": "Save Attachment",
                "time_min": 10,
                "time_max": 30,
                "order": 2,
                "func": self.save_attachment_to_s3,
            },
            {
                "name": "Conv",
                "description": "Conversion",
                "time_min": 0,
                "time_max": 10,
                "order": 3,
                "func": self.convert_attachment,
            },
            {
                "name": "Ext",
                "description": "Extraction",
                "time_min": 10,
                "time_max": 50,
                "order": 4,
                "func": self.extract_attachment,
            },
            {
                "name": "GBO",
                "description": "Generate Bill Object",
                "time_min": 5,
                "time_max": 10,
                "order": 5,
                "func": self.generate_bill_object,
            },
        ]

    def get_resource(self):
        if self.resid == None:
            return None
        res = self.resources.find_one({"_id": ObjectId(self.resid)})
        if res == None:
            return None
        return res["response"]

    def create_path(self, mail_address: str):
        cp = mail_address.split("@")[0].split(".")  # get client and property

        if len(cp) == 2:
            self.client, self.property = cp[0], cp[1]
            target_folder = os.path.join(self.mainpath, cp[0], cp[1], self.billspath)
        else:
            self.client, self.property = cp[0], ""
            target_folder = os.path.join(self.mainpath, cp[0], self.billspath)
        return target_folder

    def save_file_table_object(self, s3_key):
        file_obj = {
            "s3_key": s3_key,
            "email_table_id": ObjectId(self.email_table_id),
            "timestamp": datetime.datetime.utcnow(),
            "isactive": True,
            "client": self.client,
            "property": self.property,
            "process_status": 0,
        }
        file_table_id = self.ec_utils.save_attachment(file_obj)
        return file_table_id

    def save_attachment_to_s3(self, stage):
        start_time = time.time()
        print("saving att to s3")

        received_datetime = self.emailobj["receivedDateTime"]
        formatted_datetime = datetime.datetime.strptime(
            received_datetime, "%Y-%m-%dT%H:%M:%SZ"
        )
        received_timestamp = datetime.datetime.strftime(
            formatted_datetime, "%Y%m%d%H%M%S%f"
        )
        _, ext = os.path.splitext(self.fname)
        generated_fname = (
            received_timestamp + "-" + self.fname + "_" + str(self.findex + 1) + ext
        )
        emailaddress = self.emailobj["sender"]["emailAddress"]["address"]
        target_folder = self.create_path(emailaddress)
        self.s3key = os.path.join(target_folder, generated_fname).replace("\\", "/")
        bytes = io.BytesIO(base64.b64decode(self.fcontent))
        res = self.s3_utils.upload_to_s3_object(self.s3key, bytes, ext)
        # upload_to_s3_content(self.s3key, bytes)
        print("upload to s3 : ", res)
        if self.ec_utils.get_attchment(self.s3key) == None:
            self.file_table_id = self.save_file_table_object(self.s3key)

        timestamp = datetime.datetime.utcnow()
        end_time = time.time()
        filestage = {
            "fileid": self.fileid,
            "stage": stage,
            "result": self.s3key,
            "timestamp": timestamp,
            "time_taken": end_time - start_time,
        }
        self.filestages.insert_one(filestage)
        return self.s3key

    def convert_attachment(self, stage):
        start_time = time.time()
        print("convert att to pdf")
        _, ext = os.path.splitext(self.fname)
        result = "NA"
        if ext.lower() != ".pdf":
            waittime = random.randint(stage["time_min"], stage["time_max"])
            time.sleep(waittime)
            result = "converted to pdf"

        timestamp = datetime.datetime.utcnow()
        end_time = time.time()
        filestage = {
            "fileid": self.fileid,
            "stage": stage,
            "result": result,
            "timestamp": timestamp,
            "time_taken": end_time - start_time,
        }
        self.filestages.insert_one(filestage)
        return result

    def extract_attachment(self, stage):
        start_time = time.time()
        result = "UnExtracted"
        print(f"extract att from {self.extraction_url}")
        # waittime = random.randint(stage["time_min"], stage["time_max"])
        # time.sleep(waittime)
        #! ffs, set default model on extraction api...
        params = {"s3_key": self.s3key, "model": "s25kT3", "meta": False}
        try:
            response = requests.post(self.extraction_url, json=params)
            print("extraction response", response)
            if response != None:
                result = json.loads(response.text)
            else:
                result = "Failed to Extract"
        except Exception as ex:
            print(ex)
            result = "Failed to Extract"
        timestamp = datetime.datetime.utcnow()
        end_time = time.time()
        filestage = {
            "fileid": self.fileid,
            "stage": stage,
            "result": result,
            "timestamp": timestamp,
            "time_taken": end_time - start_time,
        }
        self.filestages.insert_one(filestage)
        return result

    def generate_bill_object(self, stage):
        start_time = time.time()
        print("generate bill object")
        waittime = random.randint(stage["time_min"], stage["time_max"])
        time.sleep(waittime)
        timestamp = datetime.datetime.utcnow()
        end_time = time.time()
        filestage = {
            "fileid": self.fileid,
            "stage": stage,
            "result": None,
            "timestamp": timestamp,
            "time_taken": end_time - start_time,
        }
        self.filestages.insert_one(filestage)
        return str(uuid.uuid4())

    def run_stages(self):
        # we can use message queue / celery tasks here instead of loop
        for stage in self.stages:
            # time.sleep(waittime)
            # if each function is a celery task, get task id
            stagecopy = stage.copy()
            del stagecopy["func"]
            taskid = stage.get("func")(stagecopy)
            stage["result"] = taskid

            fileobj = {
                "fileid": self.fileid,
                "findex": self.findex,
                "fname": self.fname,
                "stage": stagecopy,
                "timestamp": datetime.datetime.utcnow(),
                "resid": self.resid,
            }
            # print("FileJob::", fileobj)
            self.files.update_one(
                {"fileid": self.fileid}, {"$set": fileobj}, upsert=True
            )
            # waittime = random.randint(stage["time_min"], stage["time_max"])
            # time.sleep(waittime)
