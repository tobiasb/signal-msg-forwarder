import json
import logging
import mimetypes
import os
from time import sleep

import boto3
import requests
import sentry_sdk
from requests.adapters import HTTPAdapter

if not (log_level := os.getenv("LOG_LEVEL", None)):
    log_level = logging.INFO

signal_cli_api_adapter = HTTPAdapter(max_retries=3)
signal_cli_api_session = requests.Session()
signal_cli_api_session.mount(os.getenv("SIGNAL_API_HOST"), signal_cli_api_adapter)

logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

signal_phone_numbers = os.getenv("SIGNAL_PHONE_NUMBERS").split(",")
signal_phone_numbers_to_forward = os.getenv("SIGNAL_PHONE_NUMBERS_TO_FORWARD").split(",")

s3 = boto3.resource("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME"))
table.load()

interval = os.getenv("POLL_INTERVAL")
group_name_cache = {}


sentry_sdk.init(
    os.getenv('SENTRY_URL'),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)


def get_group_name(phone_number, group_id):
    if not group_id:
        return None

    key = f"{phone_number}-{group_id}"
    if key in group_name_cache:
        return group_name_cache[key]

    try:
        logger.info(f"Fetching group name for group {group_id}")
        response = signal_cli_api_session.get(url=f"{os.getenv('SIGNAL_API_HOST')}/v1/groups/{phone_number}")

        if response.status_code != 200:
            logger.error(f"Error retrieving group name for {phone_number}/{group_id}: HTTP {response.status_code}")
            return None

        for group in response.json():
            if group["internal_id"] == group_id:
                group_name_cache[key] = group["name"]

        return group_name_cache.get(key, None)
    except Exception as ex:
        logger.error(ex, exc_info=ex)
        return None


def download_attachment(attachment_id):
    response = signal_cli_api_session.get(url=f"{os.getenv('SIGNAL_API_HOST')}/v1/attachments/{attachment_id}")
    return response.content


def download_attachments(data_message):
    results = []
    attachments = data_message.get("attachments", [])
    for attachment in attachments:
        logger.info(f'Downloading attachment {attachment["id"]}')

        attachment_data = download_attachment(attachment["id"])
        file_extension = mimetypes.guess_extension(attachment["contentType"])
        filename = f'{data_message["timestamp"]}-{attachment["id"]}{file_extension}'
        s3_location = f's3://{os.getenv("S3_BUCKET_NAME")}/{filename}'
        logger.info(f"Writing attachment to {s3_location}")
        s3_object = s3.Object(os.getenv("S3_BUCKET_NAME"), filename)
        result = s3_object.put(Body=attachment_data)

        if not (res := result.get("ResponseMetadata").get("HTTPStatusCode")) == 200:
            logger.error(f"Uploading to {s3_location} failed with HTTP {res}")

        results.append(
            {
                "content_type": attachment["contentType"],
                "size": attachment["size"],
                "location": s3_location,
            }
        )
    return results


def process_phone_number(phone_number):
    try:
        logger.info(f"Looking for messages sent to {phone_number}")
        response = signal_cli_api_session.get(url=f"{os.getenv('SIGNAL_API_HOST')}/v1/receive/{phone_number}?timeout=1")

        if response.status_code != 200:
            logger.error(f"Error retrieving messages for {phone_number}: HTTP {response.status_code}")
            return

        messages = response.json()

        if not messages:
            return

        for msg in messages:
            try:
                if not msg.get("envelope", {}).get("dataMessage", None):
                    logger.warning(f"Message did not have required data:\n{json.dumps(msg, indent=2)}")
                    continue

                envelope = msg["envelope"]
                data_message = envelope["dataMessage"]

                logger.debug(f"Message:\n{json.dumps(envelope, indent=2)}")

                if phone_number not in signal_phone_numbers_to_forward:
                    logger.info(f"Discarding message")
                    continue

                logger.info(f"Writing message from {envelope['sourceNumber']}")

                group_id = data_message.get("groupInfo", {}).get("groupId", None)
                writer.put_item(
                    Item={
                        "timestamp_utc": data_message["timestamp"],
                        "from_number": envelope["sourceNumber"],
                        "from_name": envelope["sourceName"],
                        "to_number": phone_number,
                        "message": data_message["message"],
                        "group_id": group_id,
                        "group_name": get_group_name(phone_number, group_id),
                        "attachments": download_attachments(data_message),
                    }
                )

            except Exception as ex:
                logger.error(ex, exc_info=ex)

    except Exception as ex:
        logger.error(ex, exc_info=ex)


while True:
    with table.batch_writer() as writer:
        for phone_number in signal_phone_numbers:
            process_phone_number(phone_number)

    logger.info(f"Done, sleeping for {interval}s")
    sleep(int(interval))

# Picture:

# {
#   "source": "+16047165105",
#   "sourceNumber": "+16047165105",
#   "sourceUuid": "ea1664bc-79f7-4778-91f6-bc4382a5503b",
#   "sourceName": "Tobias Boehm",
#   "sourceDevice": 1,
#   "timestamp": 1654018049054,
#   "dataMessage": {
#     "timestamp": 1654018049054,
#     "message": null,
#     "expiresInSeconds": 0,
#     "viewOnce": false,
#     "attachments": [
#       {
#         "contentType": "image/jpeg",
#         "filename": null,
#         "id": "437xHGM_HNZb1vPMDivv",
#         "size": 502104
#       }
#     ]
#   }
# }


# Gif:

# {
#   "source": "+16047165105",
#   "sourceNumber": "+16047165105",
#   "sourceUuid": "ea1664bc-79f7-4778-91f6-bc4382a5503b",
#   "sourceName": "Tobias Boehm",
#   "sourceDevice": 1,
#   "timestamp": 1654018107748,
#   "dataMessage": {
#     "timestamp": 1654018107748,
#     "message": null,
#     "expiresInSeconds": 0,
#     "viewOnce": false,
#     "attachments": [
#       {
#         "contentType": "video/mp4",
#         "filename": null,
#         "id": "MJ17quLI1ynF8oe2o9j4",
#         "size": 213534
#       }
#     ]
#   }
# }
