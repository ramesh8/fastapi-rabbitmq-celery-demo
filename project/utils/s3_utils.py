import logging
import os
import boto3
import mimetypes
from dotenv import load_dotenv
import mimetypes
import openxmllib


class S3Utils:
    def __init__(self):
        load_dotenv()
        self.s3client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("boto3_aws_access_key_id"),
            aws_secret_access_key=os.getenv("boto3_aws_secret_access_key"),
            region_name=os.getenv("boto3_region_name"),
        )
        self.S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
        logging.getLogger("boto3").setLevel(logging.CRITICAL)
        logging.getLogger("botocore").setLevel(logging.CRITICAL)
        logging.getLogger("s3transfer").setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    def get_mime_type(self, file_extension):
        print("looking for mimetype : ", file_extension)
        mime_type, _ = mimetypes.guess_type(f"file{file_extension}")
        print("mime_Type", mime_type)
        return mime_type

    def upload_to_s3_content(self, s3_key, content):
        if type(content) == str:
            data = content.encode()
            res = self.s3client.put_object(
                ACL="public-read", Body=data, Bucket=self.S3_BUCKET_NAME, Key=s3_key
            )
            return res
        else:
            logging.critical("content type is not str in s3_utils ln 37")
        # elif type(content)==Bytes:

    def upload_to_s3_object(self, s3_key, file_obj, file_extension):
        try:
            file_obj.seek(0)
            content_type = self.get_mime_type(file_extension)

            self.s3client.upload_fileobj(
                Fileobj=file_obj,
                Bucket=self.S3_BUCKET_NAME,
                Key=s3_key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )
        except Exception as ex:
            print("exception due to ", ex)

    def upload_to_s3_file(self, key, file, uploadfile_bytes):
        try:
            fname, file_extension = os.path.splitext(file)

            content_type = self.get_mime_type(file_extension)
            self.s3client.upload_fileobj(
                Fileobj=uploadfile_bytes,
                Bucket=self.S3_BUCKET_NAME,
                Key=key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )

            return key
        except Exception as ex:
            print("errro in upload_to_s3_file due to ", ex)

    def get_file_obj(self, s3_key):
        print("get_file_obj", s3_key)
        doc_object = self.s3client.get_object(Bucket=self.S3_BUCKET_NAME, Key=s3_key)

        doc_content = doc_object["Body"].read()
        return doc_content
