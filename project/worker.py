import datetime
import json
from operator import itemgetter
import os
import random
import time
import uuid
from aio_pika import IncomingMessage
from pymongo import MongoClient
from celery import Celery, Task


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(
    "CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"
)
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
)


class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        """
        retval – The return value of the task.
        task_id – Unique id of the executed task.
        args – Original arguments for the executed task.
        kwargs – Original keyword arguments for the executed task.
        """
        print(retval, task_id, args, kwargs, "==[V]==")
        pass

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        exc – The exception raised by the task.
        task_id – Unique id of the failed task.
        args – Original arguments for the task that failed.
        kwargs – Original keyword arguments for the task that failed.
        """
        print(exc, task_id, args, kwargs, einfo, "---[#]---")
        # max_retries
        pass


# it is called from mq callback
async def process_mail(obj):
    mailid, sender, filecount = itemgetter("uuid_", "sender", "fcount")(obj)
    print(f"processing {mailid}, {sender}, {filecount}")
    for findex in range(filecount):
        # create celery task for each file
        print(f"creating celery task for {sender} file {findex}")
        process_file.delay(mailid, sender, findex)


@celery.task(name="create_task", base=CallbackTask)
def process_file(mailid, sender, findex):
    myjob = MyJob(mailid, sender, findex)
    print(f"created task with {mailid}, {sender}, {findex}")
    myjob.run_stages()


class MyJob:
    def __init__(self, mailid, sender, findex):
        self.mailid = mailid
        self.sender = sender
        self.findex = findex
        mongo = MongoClient("mongodb://mongodbserver:27017/")
        db = mongo["asyncdemo"]
        self.mails = db["mails"]
        self.files = db["files"]
        self.stages = [
            {
                "name": "SE",
                "description": "Save Email",
                "time_min": 1,
                "time_max": 5,
                "order": 1,
            },
            {
                "name": "SA",
                "description": "Save Attachment",
                "time_min": 10,
                "time_max": 30,
                "order": 2,
            },
            {
                "name": "Conv",
                "description": "Conversion",
                "time_min": 0,
                "time_max": 10,
                "order": 3,
            },
            {
                "name": "Ext",
                "description": "Extraction",
                "time_min": 10,
                "time_max": 50,
                "order": 4,
            },
            {
                "name": "GBO",
                "description": "Generate Bill Object",
                "time_min": 5,
                "time_max": 10,
                "order": 5,
            },
        ]

    def run_stages(self):
        fileid = str(uuid.uuid4())
        # we can use message queue here instead of loop
        for stage in self.stages:
            fileobj = {
                "fileid": fileid,
                "sender": self.sender,
                "index": self.findex,
                "stage": stage,
                "timestamp": datetime.datetime.utcnow(),
                "mail_id": self.mailid,
            }
            print(fileobj)
            self.files.update_one({"fileid": fileid}, {"$set": fileobj}, upsert=True)
            waittime = random.randint(stage["time_min"], stage["time_max"])
            time.sleep(waittime)
