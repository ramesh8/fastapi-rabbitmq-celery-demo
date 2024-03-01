import json
from pprint import pprint

outputstr = """
```json
{
    "invoice_number": "9210046318",
    "invoice_date": "12/29/2022",
    "invoice_amount": "1,073.11",
    "vendor_name": "HD Supply Facilities Maintenance, Ltd.",
    "vendor_address": "PO Box 509058",
    "vendor_city": "San Diego",
    "vendor_zipcode": "CA 92150-9058",
    "line_items": [
        {
            "stock_number": "327625",
            "description": "175w Clear Metal Halide Bulb Med Base",
            "gl_account": "6",
            "ordered": "6",
            "shipped": "6",
            "unit_price": "57.64",
            "unit_extension": "345.84"
        },
        {
            "stock_number": "34584",
            "description": "Sunbeam Best Value Auto Off Iron Wht 8500",
            "gl_account": "6",
            "ordered": "6",
            "shipped": "6",
            "unit_price": "26.53",
            "unit_extension": "159.18"
        },
        {
            "stock_number": "180195",
            "description": "Hb WII Mnt Hr Dry Wht W/ NI 8500",
            "gl_account": "4",
            "ordered": "4",
            "shipped": "4",
            "unit_price": "41.17",
            "unit_extension": "164.68"
        },
        {
            "stock_number": "311508",
            "description": "7w Twin Cfl Bulb 4100k G23 Bs 10/Pkg",
            "gl_account": "3",
            "ordered": "3",
            "shipped": "3",
            "unit_price": "36.41",
            "unit_extension": "109.23"
        },
        {
            "stock_number": "327031",
            "description": "G16-1/2 Blb Phl 60W Cand Base Clr 12/Pkg",
            "gl_account": "2",
            "ordered": "2",
            "shipped": "2",
            "unit_price": "65.23",
            "unit_extension": "130.46"
        },
        {
            "stock_number": "733752",
            "description": "Gymwipes PRO Cleaning Wipes Refill Roll",
            "gl_account": "1",
            "ordered": "1",
            "shipped": "1",
            "unit_price": "31.50",
            "unit_extension": "31.50"
        },
        {
            "stock_number": "118803",
            "description": "1200 MI Gojo Plum Foam Soap Refill 2/Cs",
            "gl_account": "1",
            "ordered": "1",
            "shipped": "1",
            "unit_price": "59.10",
            "unit_extension": "59.10"
        }
    ]
}
```
"""

outputjson = outputstr.replace("```json", "").replace("```", "")

output = json.loads(outputjson)

pprint(output)
