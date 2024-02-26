import datetime
import json
import logging
from operator import itemgetter
import os
import random
import time
import uuid
from aio_pika import IncomingMessage
from pymongo import MongoClient
from celery import Celery, Task
from emailjob import EmailJob
from filejob import FileJob

# from logs.init_logging import init_logging

# init_logging()

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(
    "CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"
)
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
)

mongo = MongoClient("mongodb://mongodbserver:27017/")
db = mongo["asyncdemo"]


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
        # todo: implement max_retries
        pass


async def process_resource(obj):
    # get mongo document id from message queue
    # print(obj)
    if "id" in obj:
        mailid = obj["id"]
        sender = obj["sender"]
        subject = obj["subject"]
        hasAttachments = obj["hasAttachments"]
        print("spawing celery task now", obj)
        process_mail_task.delay(mailid, sender, subject, hasAttachments)
    else:
        print("something wrong with obj in process_resource ln 54 @ worker.py")


@celery.task(name="email_job_task", base=CallbackTask)
def process_mail_task(resid, sender, subject, hasAtt):
    emailjob = EmailJob(resid, sender, subject, hasAtt)
    print(f"created task: email_job with {resid}")
    emailjob.process_mail()


@celery.task(name="file_job_task", base=CallbackTask)
# findex, fileid, fname, self.resid
def process_file_task(findex, fileid, fname, fcontent, resid=None, email_table_id=None):
    filejob = FileJob(findex, fileid, fname, fcontent, resid, email_table_id)
    print(f"created task: file_job with {fileid} :: {resid}")
    filejob.run_stages()
