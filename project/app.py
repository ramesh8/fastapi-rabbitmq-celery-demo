import asyncio
from decimal import Decimal
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict
import uuid
from fastapi import Body, FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pymongo import MongoClient
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from aio_pika import connect, IncomingMessage, Message
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient
from logs.init_logging import init_logging
from subscriptions import Subscriptions
from worker import process_resource

init_logging()

subs = None
mongo = None
mq_db = None
subscriptionsData = None
mails = files = filestages = resources = None


BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))
# todo: use load_dotenv here instead of static assignment
mq_url = "amqp://guest:guest@rabbitmq:5672/"
EXCHANGE_NAME = "NIMBLEIO_EXCHANGE"
QUEUE_NAME = "MAIL_QUEUE"


async def mqsubscriber(loop):
    connection = await connect(url=mq_url, loop=loop)
    channel = await connection.channel()
    exchnage = await channel.declare_exchange(name=EXCHANGE_NAME, type="topic")
    queue = await channel.declare_queue(QUEUE_NAME)
    await queue.bind(exchange=exchnage, routing_key=QUEUE_NAME)
    await queue.consume(enqueue_mail, no_ack=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global subs, mongo, mq_db, mails, files, filestages, resources
    subs = Subscriptions()
    mongo = MongoClient("mongodb://mongodbserver:27017/")
    mq_db = mongo["asyncdemo"]
    mails = mq_db["mq_mails"]
    files = mq_db["mq_files"]
    filestages = mq_db["mq_filestages"]
    resources = mq_db["mq_resources"]
    loop = asyncio.get_event_loop()
    loop.create_task(mqsubscriber(loop))
    yield


async def send_rabbitmq(msg={}):
    connection = await connect(url=mq_url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(name=EXCHANGE_NAME, type="topic")
    queue = await channel.declare_queue(QUEUE_NAME)
    await queue.bind(exchange=exchange, routing_key=QUEUE_NAME)
    await exchange.publish(
        Message(json.dumps(msg.dict(), default=str).encode("utf-8")),
        routing_key=QUEUE_NAME,
    )
    await connection.close()


async def enqueue_mail(message: IncomingMessage):
    txt = message.body.decode("utf-8")
    obj = json.loads(txt)
    print("enqueue_mail", obj)
    obj["resid"] = obj["id"]
    # del obj["id"] this is still confusing
    mails.insert_one(obj)
    await process_resource(obj)


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ResourceIdMessage(BaseModel):
    id: str
    sender: str  # from
    subject: str
    hasAttachments: bool = False


class ResourceReadException(Exception):
    """Error reading resource using Graph API"""

    def __init__(self, resid: str):
        self.resid = resid


# todo use custom exceptions all over the project


@app.exception_handler(ResourceReadException)
async def resource_read_exception(request: Request, exc: ResourceReadException):
    error = {"message": f"Error Reading Resource {exec.resid}"}
    return JSONResponse(status_code=status.HTTP_417_EXPECTATION_FAILED, content=error)


def format_secs(secs):
    ssecs = str(secs).rstrip("0").rstrip(".") if "." in str(secs) else str(secs)
    return str(Decimal(ssecs)) + "s"


@app.get("/", response_class=JSONResponse)
def index(request: Request):
    ms = mails.find({}).sort("_id", -1)

    mslist = []
    for m in ms:
        flist = []
        fs = files.find({"resid": m["resid"]}).sort("_id", 1)
        for f in fs:
            fstages = filestages.find({"fileid": f["fileid"]}).sort("_id", 1)
            fstdict = {}
            for fstage in fstages:
                fstdict[fstage["stage"]["name"]] = format_secs(
                    round(fstage["time_taken"], 2)
                )
            f["filestages"] = fstdict
            flist.append(f)

        if len(flist) > 0:
            m["files"] = flist
            m["status"] = all(f["stage"]["name"] == "GBO" for f in m["files"])
        mslist.append(m)

    # print(mslist)

    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request, "mails": mslist},
    )


@app.post("/subscribed/")
async def subscribed(
    validationToken: str | None = None,
    data: Dict[Any, Any] | None = None,
):
    if validationToken != None:
        print(validationToken)
        return PlainTextResponse(validationToken, 200)

    resid = data["value"][0]["resource"]
    resource = subs.get_resource(resid)
    if resource["status"] != 100:
        print(f"failed to read mail: {resid}")
        raise ResourceReadException(resid)

    # check if email already recieved, ffs!!!

    check = resources.find_one({"response.id": resource["response"]["id"]})

    if check != None:
        # its already recieved!!!
        print(f"The mail with id {resource['response']['id']} already exists in db")
        # print(check)
        return

    result = resources.insert_one(resource)
    response = resource["response"]

    message = ResourceIdMessage(
        id=str(result.inserted_id),
        sender=response["from"]["emailAddress"]["address"],
        subject=response["subject"],
        hasAttachments=response["hasAttachments"],
    )

    print("send_rabbitmq", message)

    await send_rabbitmq(message)


@app.get("/createsubs", response_class=JSONResponse)
def createsubs():
    res = subs.create_subscription()
    return JSONResponse(res)


@app.get("/getsubs", response_class=JSONResponse)
def listsubs():
    res = subs.get_subscriptions()
    return JSONResponse(res["value"])


@app.post("/subscribed_junk/")
async def subscribed_junk(
    validationToken: str | None = None, data: Dict[Any, Any] | None = None
):
    if validationToken != None:
        return PlainTextResponse(validationToken, 200)

    # resid = data["value"][0]["resource"]
    # resource = subs.get_resource(resid)

    # res = (
    #     subs.junk_monitor(resource["response"])
    #     if resource["status"] == 100
    #     else resource
    # )

    # return JSONResponse(res, status_code=200)


@app.post("/lifecycle/")
async def lifecycle(
    validationToken: str | None = None, data: Dict[Any, Any] | None = None
):
    if validationToken != None:
        return PlainTextResponse(validationToken, 200)

    subscriptionId = data["value"][0]["subscriptionId"]
    # nimbleioapiconnector.insert_lifecycle(data)
    res = subs.renew_subscription(subscriptionId)
    # nimbleioapiconnector.renewal_sub(res)

    if "_id" in res:
        del res["_id"]
    print("lifecycle", res)
    return JSONResponse(res, status_code=200)


@app.post("/deletesubs", response_class=JSONResponse)
async def delete_subs(data=Body(...)):
    res = subs.delete_subs(data)
    return JSONResponse(res, status_code=200)
