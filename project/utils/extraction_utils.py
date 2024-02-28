from utils.db_config import DBConfig


class ExtractionUtils(DBConfig):
    def __init__(self):
        super().__init__()

    def get_fileobj(self, file_id):
        res = self.db[self.file_table_collection_name].find_one({"_id": file_id})
        return res

    def fetch_client(self, clientname):
        res = self.db[self.clients_collection_name].find_one({"name": clientname})
        return res if res else None

    def fetch_property(self, name):
        # query = {'client_uuid':uuid} if uuid != None else {'corporationName':name}
        query = {"corporationName": name}
        res = self.db[self.properties_collection_name].find_one(query)
        return res if res else None

    def getfromAddress(self, email_id):
        res = self.db[self.email_table_collection_name].find_one({"_id": email_id})
        return res["from"] if res else ""

    def update_billobj(self, document):
        res = self.db[self.bills_table_collection_name].update_one(
            {"file_table_id": document["file_table_id"]},
            {"$set": document},
            upsert=True,
        )
        return res.upserted_id

    def update_invoiceobj(self, document):
        res = self.db[self.invoice_table_collection_name].update_one(
            {"bill_id": document["bill_id"]}, {"$set": document}, upsert=True
        )
        return res.upserted_id
