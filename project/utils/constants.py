from enum import IntEnum


class SericeProcessStatus(IntEnum):
    STARTED = 0
    CONVERSION = 1
    EXTRACTION = 2
    COMPLETED = 3


class BillProcessStatus(IntEnum):
    TO_BE_APPROVED = 0
    SUMMARY = 1
    SUBMIT = 2
    NEED_ATTENTION = -1
    FAILED_BY_USER = -2
    DUPLICATE = -3
    EXTRACTION_FAILED = -4
    MARK_AS_INACTIVE = -5
