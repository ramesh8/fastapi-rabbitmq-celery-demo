import io
import logging
import os
import pathlib
from dotenv import load_dotenv
from utils.db_config import DBConfig
import boto3
from pdf2image import convert_from_bytes


class OCRUtils:
    def __init__(self):
        load_dotenv()
        self.s3client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("boto3_aws_access_key_id"),
            aws_secret_access_key=os.getenv("boto3_aws_secret_access_key"),
            region_name=os.getenv("boto3_region_name"),
        )
        self.S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
        self.textract_client = boto3.client(
            "textract",
            aws_access_key_id=os.getenv("boto3_aws_access_key_id"),
            aws_secret_access_key=os.getenv("boto3_aws_secret_access_key"),
            region_name=os.getenv("boto3_region_name"),
        )
        logging.getLogger("boto3").setLevel(logging.CRITICAL)
        logging.getLogger("botocore").setLevel(logging.CRITICAL)
        logging.getLogger("s3transfer").setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    def get_text_from_textract_res(self, res):
        if "Blocks" in res:
            alltext = []
            for block in res["Blocks"]:
                if block["BlockType"] == "LINE":
                    alltext.append(block["Text"])
            return alltext

    def get_ocr_text(self, s3_key):
        # pdf format is only supported in async operations as of today (Feb 28 2024)
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/textract/client/detect_document_text.html
        # response = self.textract_client.detect_document_text(
        #     Document={"S3Object": {"Bucket": self.S3_BUCKET_NAME, "Name": s3key}}
        # )
        data = io.BytesIO()
        self.s3client.download_fileobj(
            Bucket=self.S3_BUCKET_NAME, Key=s3_key, Fileobj=data
        )
        data.seek(0)
        ext = pathlib.Path(s3_key).suffix
        if ext.lower() != ".pdf":  # not in extractor.supportedExts:
            print(f"File format not supported")
            return None
        images = convert_from_bytes(data.read())
        alltext = []
        for image in images:
            imgbytes = io.BytesIO()
            image.save(imgbytes, format="jpeg", subsampling=0, quality=90)
            imgbytes = imgbytes.getvalue()
            imgsize = len(imgbytes) / pow(10, 6)
            # print(imgsize)
            # check if imgsize is greater than 10MB
            if imgsize >= 10:
                imgbytes = io.BytesIO()
                image.save(imgbytes, format="jpeg", subsampling=0, quality=50)
            textract_res = self.textract_client.detect_document_text(
                Document={"Bytes": imgbytes}
            )
            textract_text = self.get_text_from_textract_res(textract_res)
            alltext.append(" ".join(textract_text))

        return "\n\n".join(alltext)


# if __name__ == "__main__":
#     ocrutils = OCRUtils()
#     s3key = "NimbleIO/ramesh/bills/pending/20240228171236000000-20230117182443857000-HD-Supply_1.pdf"
#     res = ocrutils.get_ocr_text(s3key)
#     print(res)
