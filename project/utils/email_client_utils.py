from utils.db_config import DBConfig


class EmailClientUtils(DBConfig):
    def __init__(self):
        super().__init__()

    def add_email(self, document: dict):
        res = self.db[self.email_table_collection_name].update_one(
            {"reference_id": document["reference_id"]}, {"$set": document}, upsert=True
        )
        return res.upserted_id

    def get_email(self, refrence_id: str):
        res = self.db[self.email_table_collection_name].find_one(
            {"reference_id": refrence_id}
        )
        return res

    def save_attachment(self, document: dict):
        res = self.db[self.file_table_collection_name].insert_one(document)
        print("inserted_id", res.inserted_id)
        return res.inserted_id

    def get_attchment(self, s3key: str):
        res = self.db[self.file_table_collection_name].find_one({"s3_key": s3key})
        return res

    def find_junkEmails(self, mail: str):
        res = self.db[self.junkEmails_collection_name].find_one({"email": mail})
        return res

    def update_junkEmails(self, mail, count, prev_time, received_datetime, alert_level):
        res = self.db[self.junkEmails_collection_name].update_one(
            {"email": mail},
            {
                "$set": {
                    "count": count,
                    "prev_timestamp": prev_time,
                    "create_timestamp": received_datetime,
                    "Alert_level": alert_level,
                }
            },
        )
        return res

    def insert_junkemail(self, mail, received_datetime):
        res = self.db[self.junkEmails_collection_name].insert_one(
            {
                "email": mail,
                "count": 1,
                "create_timestamp": received_datetime,
                "Alert_level": 0,
            }
        )
        return res
