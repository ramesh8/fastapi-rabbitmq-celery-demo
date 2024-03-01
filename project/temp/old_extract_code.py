# def extract_attachment_old(self):
#     #! set default model on extraction api...
#     params = {"s3_key": self.s3key, "model": "s25kT3", "meta": False}
#     result = {"url": self.extraction_url, "params": params}
#     response = None
#     self.bill_status = BillProcessStatus.TO_BE_APPROVED
#     try:
#         response = requests.post(self.extraction_url, json=params)
#         print("extraction response", response)
#         if response != None:
#             # extracted =
#             result["response"] = json.loads(response.text)
#             self.ext_res = result["response"]
#         else:
#             result["response"] = None
#     except Exception as ex:
#         print(ex)
#         result["exception"] = str(ex)
#         self.ext_res = self.temp_ents  # its not neccessary, i think...
#         if response != None:
#             result["response"] = response.text
#         self.bill_status = BillProcessStatus.EXTRACTION_FAILED

#     #! Adjusting ents and meta
#     self.meta = {}
#     if "meta" in self.ext_res and self.ext_res["meta"] != None:
#         if (
#             "client" in self.ext_res["meta"]
#             and self.ext_res["meta"]["client"] != None
#         ):
#             self.meta["client"] = self.ext_res["meta"]["client"]
#         else:
#             cl = self.ext_utils.fetch_client(self.client)
#             self.meta["client"] = (
#                 cl
#                 if cl != None
#                 else {"userID": "", "url": "", "token": "", "name": self.client}
#             )
#         if (
#             "property" in self.ext_res["meta"]
#             and self.ext_res["meta"]["property"] != None
#         ):
#             self.meta["property_details"] = self.ext_res["meta"]["property"]
#         else:
#             # corp = self.fetchPropertyDetails({'uuid':cl['userID'],"name":None}) if cl else self.fetchPropertyDetails({"uuid":None,'name':property})
#             corp = self.ext_utils.fetch_property({"name": self.property})
#             self.meta["property_details"] = (
#                 corp
#                 if corp
#                 else {"corporationID": "", "corporationName": self.property}
#             )
#         if (
#             "vendor" in self.ext_res["meta"]
#             and self.ext_res["meta"]["vendor"] != None
#         ):
#             self.meta["vendor_details"] = self.ext_res["meta"]["vendor"]
#         else:
#             self.meta["vendor_details"] = {"id": "", "name": ""}
#     else:
#         cl = self.ext_utils.fetch_client(self.client)
#         self.meta["client"] = (
#             cl
#             if cl != None
#             else {"userID": "", "url": "", "token": "", "name": self.client}
#         )
#         # corp = self.fetchPropertyDetails(cl['userID'],None) if cl else self.fetchPropertyDetails(None,property)
#         corp = self.ext_utils.fetch_property(self.property)
#         self.meta["property_details"] = (
#             corp
#             if corp
#             else {"corporationID": "", "corporationName": self.property}
#         )
#         self.meta["vendor_details"] = {"id": "", "name": ""}

#     return result
