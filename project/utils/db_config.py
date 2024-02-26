import logging, io, os
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv


class DBConfig:
    def __init__(self):
        load_dotenv()
        db_url = os.getenv("db_url")
        cluster = MongoClient(db_url)
        db_name = os.getenv("db_name")
        self.db = cluster[db_name]
        self.clients_collection_name = os.getenv("CLIENTS_COLLECTION")
        self.properties_collection_name = os.getenv("PROPERTIES_COLLECTION")
        self.vendors_collection_name = os.getenv("VENDORS_COLLECTION")
        self.bills_table_collection_name = os.getenv("BILLS_TABLE_COLLECTION")
        self.file_table_collection_name = os.getenv("FILES_TABLE_COLLECTION")
        self.invoice_table_collection_name = os.getenv("INVOICE_TABLE_COLLECTION")
        self.email_table_collection_name = os.getenv("EMAIL_TABLE_COLLECTION")
        self.users_collection_name = os.getenv("USERS_COLLECTION")
        self.verified_bills_collection_name = os.getenv("VERIFIED_BILLS_COLLECTION")
        self.lifecycle_collection_name = os.getenv("LIFECYCLE_COLLECTION")
        self.renewals_collection_name = os.getenv("RENEWALS_COLLECTION")
        self.junkEmails_collection_name = os.getenv("JUNKEMAILS_COLLECTION")
        self.trackChanges_collection_name = os.getenv("TRACKCHANGES_COLLECTIONS")
        print("__init__")
