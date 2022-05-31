import boto3
from datetime import datetime
import logging
import requests
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

response = requests.get(f"{os.getenv('SIGNAL_API_HOST')}/v1/receive/{os.getenv('SIGNAL_PHONE_NUMBER')}")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.getenv('TABLE_NAME'))
table.load()

with table.batch_writer() as writer:
    for msg in response.json():
        envelope = msg['envelope']

        logger.info(f"Writing message from {envelope['sourceNumber']}")

        writer.put_item(Item={
            'timestamp': envelope['dataMessage']['timestamp'],
            'fromNumber': envelope['sourceNumber'],
            'fromName': envelope['sourceName'],
            'message':  envelope['dataMessage']['message']
        })

logger.info('Done')