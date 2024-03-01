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
from utils.ocr_utils import OCRUtils
from utils.constants import BillProcessStatus
from utils.extraction_utils import ExtractionUtils
from utils.email_client_utils import EmailClientUtils
from utils.s3_utils import S3Utils
from subscriptions import Subscriptions
from extractor.extract import extract_from_openai

# from logs.init_logging import init_logging


class FileJob:
    # findex, fileid, fname, self.resid, #fcontent is too large... put it in temp db
    def __init__(self, findex, fileid, fname, fcontentid, resid, email_table_id):
        # init_logging()
        load_dotenv()
        self.mainpath = os.getenv("walk")
        self.billspath = os.getenv("billspath")
        self.extraction_url = os.getenv("extraction_url")
        self.conversion_url = os.getenv("conversion_url")
        self.findex = findex
        self.fileid = fileid
        self.fname = fname
        self.resid = resid
        self.email_table_id = email_table_id
        self.client = self.property = self.s3key = self.file_table_id = None

        mongo = MongoClient("mongodb://mongodbserver:27017/")
        self.db = mongo["asyncdemo"]
        self.resources = self.db["mq_resources"]
        self.files = self.db["mq_files"]
        self.filecontents = self.db["mq_filecontents"]
        self.filestages = self.db["mq_filestages"]
        self.openai_ents = self.db["openai_ents"]

        self.emailobj = self.get_resource()
        self.s3_utils = S3Utils()
        self.ec_utils = EmailClientUtils()
        self.subs = Subscriptions()
        self.ext_utils = ExtractionUtils()
        self.ocr_utils = OCRUtils()

        # self.attid = attid
        # self.attachment = self.subs.get_attachment(self.resid, self.attid)
        # self.fcontent = self.attachment["content"]
        self.fcontentid = fcontentid
        self.fcontent = self.get_fcontent(fcontentid)
        self.stages = [
            {
                "name": "SA",
                "description": "Save Attachment",
                "time_min": 10,
                "time_max": 30,
                "order": 2,
                "func": self.sa_func,
            },
            {
                "name": "Conv",
                "description": "Conversion",
                "time_min": 0,
                "time_max": 10,
                "order": 3,
                "func": self.conv_func,
            },
            {
                "name": "Ext",
                "description": "Extraction",
                "time_min": 10,
                "time_max": 50,
                "order": 4,
                "func": self.ext_func,
            },
            {
                "name": "GBO",
                "description": "Generate Bill Object",
                "time_min": 5,
                "time_max": 10,
                "order": 5,
                "func": self.gbo_func,
            },
        ]

        self.temp_ents = self.ext_res = {
            "ismulti": False,
            "all_ents": {
                "vendor_name": [],
                "vendor_address1": [],
                "invoice_number": [],
                "invoice_date_label": [],
                "invoice_date": [],
                "invoice_amount_label": [],
                "line_item_description": [],
                "line_item_amount": [],
            },
            "page_ents": [],
            "text": [],
            "validation_fails": 1,
            "tech": [],
            "meta": None,
            "s3_key": "",
        }

    def get_fcontent(self, fcid):
        if self.fileid != None:
            fc = self.filecontents.find_one({"_id": ObjectId(fcid)}, {"filecontent": 1})
            if fc != None:
                return fc["filecontent"]
        return None

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

    def save_attachment_to_s3(self):
        received_datetime = self.emailobj["receivedDateTime"]
        formatted_datetime = datetime.datetime.strptime(
            received_datetime, "%Y-%m-%dT%H:%M:%SZ"
        )
        received_timestamp = datetime.datetime.strftime(
            formatted_datetime, "%Y%m%d%H%M%S%f"
        )
        print("self.fname", self.fname)
        fname_noext, ext = os.path.splitext(self.fname)
        print("extension", ext)
        generated_fname = (
            received_timestamp + "-" + fname_noext + "_" + str(self.findex + 1) + ext
        )
        print(generated_fname)
        emailaddress = self.emailobj["sender"]["emailAddress"]["address"]
        target_folder = self.create_path(emailaddress)
        self.s3key = (
            os.path.join(target_folder, generated_fname)
            .replace("\\", "/")
            .replace(" ", "_")
        )
        # print(self.s3key)
        if self.fcontent == None:
            print("fcontent is None")
            return False
        bytes = io.BytesIO(base64.b64decode(self.fcontent))
        # todo: check if s3 upload is success or not
        print(f"upload_to_s3_object :: s3key= {self.s3key} ext= {ext}")
        res = self.s3_utils.upload_to_s3_object(self.s3key, bytes, ext)
        # upload_to_s3_content(self.s3key, bytes)
        print(f"upload to s3 :: res= {res}")
        if self.ec_utils.get_attchment(self.s3key) == None:
            self.file_table_id = self.save_file_table_object(self.s3key)
        return True

    def sa_func(self, stage):
        start_time = time.time()
        print("saving att to s3")
        self.s3key = None
        res = self.save_attachment_to_s3()

        timestamp = datetime.datetime.utcnow()
        end_time = time.time()
        filestage = {
            "fileid": self.fileid,
            "stage": stage,
            "result": None if res == False else self.s3key,
            "timestamp": timestamp,
            "time_taken": end_time - start_time,
        }
        self.filestages.insert_one(filestage)
        return self.s3key

    def convert_attachment(self):
        _, ext = os.path.splitext(self.fname)
        result = "NA"
        if ext.lower() != ".pdf":

            params = {"s3_key": self.s3key, "html": False}  #!important html=False
            result = {"url": self.conversion_url, "request": params}
            response = None
            try:
                response = requests.post(self.conversion_url, json=params)
                print("conversion response", response)
                if response != None:
                    result["response"] = json.loads(response.text)
                    self.s3key = result["response"]["converted_s3_key"]
                    print(f"converted s3key={self.s3key}")
                else:
                    result["response"] = None
            except Exception as ex:
                print(ex)
                result["exception"] = str(ex)
                if response != None:
                    result["response"] = response.text

        return result

    def conv_func(self, stage):
        start_time = time.time()
        print("convert att to pdf")

        result = self.convert_attachment()

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

    def extract_attachment(self):
        try:
            ocr_text = self.ocr_utils.get_ocr_text(self.s3key)
            self.ext_res = extract_from_openai(ocr_text)
            result = {"extraction_result": self.ext_res}
            res = self.openai_ents.insert_one(result)
            self.bill_status = BillProcessStatus.TO_BE_APPROVED
            return res.inserted_id
        except Exception as ex:
            print(f"Exception at extract_attachment ex={ex} s3key={self.s3key}")
            self.bill_status = BillProcessStatus.EXTRACTION_FAILED
            return str(ex)

    def ext_func(self, stage):
        start_time = time.time()
        result = "UnExtracted"
        print(f"extracting attachment ...")

        result = self.extract_attachment()

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

    def generate_bill_object(self):
        result = {"bill_table_id": None, "invoice_table_id": None}
        if self.ext_res == None:
            return "FAILED"

        # property_details = self.meta["property_details"]
        # vendor_details = self.meta["vendor_details"]
        # client_details = self.meta["client"]
        fromAddress = self.ext_utils.getfromAddress(self.email_table_id)
        if "invoices" in self.ext_res:
            # multiple invoices
            for invoice in self.ext_res["invoices"]:

                # parse extraction result
                inumber = invoice.get("invoice_number")
                idate = invoice.get("invoice_date")
                iamount = invoice.get("invoice_amount")
                vname = invoice.get("vendor_name")
                vdetails = {
                    "address": invoice.get("vendor_address"),
                    "city": invoice.get("vendor_city"),
                    "zip": invoice.get("vendor_zipcode"),
                }
                line_items = invoice.get("line_items")

                bill_object = {
                    "file_table_id": self.file_table_id,
                    "email_table_id": self.email_table_id,
                    "from_Address": fromAddress,
                    "bill_status": self.bill_status,
                    "s3_key": self.s3key,
                    "unique_id": 0,
                    "client": self.client,
                    "property": self.property,
                    "corporation_name": None,  # property_details["corporationName"],
                    "timestamp": datetime.datetime.now(),
                    "ents": invoice,
                    "invoice_number": inumber,
                    "invoice_amount": iamount,
                    "invoice_date": idate,
                    "vendor_name": vname,
                    "vendor_details": vdetails,
                    "line_items": line_items,
                    "corporation_id": None,  # property_details["corporationID"],
                    "valid_vendorName": None,  # vendor_details["name"],
                    "client_uuid": None,  # client_details["userID"],
                }
                # if "id" in vendor_details:
                #     bill_object["vendorID"] = vendor_details["id"]
                result["bill_table_id"] = self.ext_utils.update_billobj(bill_object)
                invoice["bill_id"] = result["bill_table_id"]
                invoice["timestamp"] = datetime.datetime.now()
                result["invoice_table_id"] = self.ext_utils.update_invoiceobj(invoice)

        return len(self.ext_res)

    def gbo_func(self, stage):
        start_time = time.time()
        print("generate bill object")

        result = self.generate_bill_object()

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


# decoupling services @filejob
# conversion as seperate service @filejob
# unzip @emailjob
# gbo @filejob
