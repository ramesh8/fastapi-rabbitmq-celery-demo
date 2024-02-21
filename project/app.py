import asyncio
import json
from pathlib import Path
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
import os
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pika
from contextlib import asynccontextmanager
from aio_pika import connect, IncomingMessage, Message
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient
from worker import process_mail

mongo = MongoClient("mongodb://mongodbserver:27017/")
db = mongo["asyncdemo"]
mails = db["mails"]
files = db["files"]

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))
# mq_url = "amqp://rabbitmq?connection_attempts=10&retry_delay=10"
# mq_url = "amqp://rabbitmq?connection_attempts=10&retry_delay=10"
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
    print(obj)
    mails.insert_one(obj)
    await process_mail(obj)


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class MailRequest(BaseModel):
    uuid_: uuid.UUID = Field(default_factory=uuid.uuid4)
    sender: str = "ramesh"
    fcount: int = 1

    @validator("uuid_")
    def validate_uuid(cls, val):
        if val:
            return str(val)
        return val


@app.get("/", response_class=JSONResponse)
def index(request: Request):
    # return {"success": True, "message": "hello world"}
    ms = mails.find({}).sort("_id", -1)

    mslist = []
    for m in ms:
        fs = files.find({"mail_id": m["uuid_"]}).sort("_id", 1)
        if fs != None:
            m["files"] = list(fs)
            m["status"] = all(f["stage"]["name"] == "GBO" for f in m["files"])
        mslist.append(m)

    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request, "mails": mslist},
    )


@app.post("/job", response_class=JSONResponse)
async def post_job(request: Request, mail: MailRequest):
    await send_rabbitmq(mail)
    return {"message": f"Task {mail.uuid_} added"}
