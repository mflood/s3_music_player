"""
    scraper.py

    list full s3 path of all music files in an s3 bucket
"""
import argparse
import sys
import logging

import boto3

import mylogging


# m3u - playlist

EXTENSIONS = ["mp3",
              "wav",
              "m4a",
              "m4p",
              "m4b"]


def make_s3_client(access_key=None, secret_key=None, region=None):
    """
        Build boto s3 client
    """

    kwargs = {}
    if access_key:
        args['aws_access_key'] = access_key
    if secret_key:
        args['aws_secret_access_key'] = secret_key
    if region:
        args['region'] = region

    client = boto3.client(
        's3',
        ** kwargs
    )
    return client

class S3MusicScraper():
    """
        Scans bucket for files matching EXTENSIONS
    """

    def __init__(self, s3_client):
        self._s3_client = s3_client
        self._logger = mylogging.logger()

    def list_buckets(self):
        """
            Call aws s3 ls
        """
        response = self._s3_client.list_buckets()
        buckets = []
        for bucket_info in response['Buckets']:
            bucket_name = bucket_info['Name']
            self._logger.debug("Found bucket %s", bucket_name)
            buckets.append(bucket_name)

        return buckets

    def list_bucket_objects(self, bucket_name):
        """
            generator returning list of all objects
            in the bucket that match EXTENSIONS
        """
        self._logger.info("Listing bucket %s", bucket_name)

        next_marker = ''
        batch_size = 500
        batch = 0
        while True:
            self._logger.debug("Scanning Batch %s", batch)

            response = self._s3_client.list_objects(
                Bucket=bucket_name,
                Delimiter=':##:^^:##:',
                #EncodingType='url',
                Marker=next_marker,
                MaxKeys=batch_size,
                #Prefix='string',
                #RequestPayer='requester'
            )

            for position, item in enumerate(response['Contents']):
                object_info = {
                    'position': position,
                    'batch': batch,
                    'key': item['Key'],
                    'size': item['Size'],
                    'etag': item['ETag']
                }
                yield object_info

            if 'NextMarker' in response:
                batch += 1
                next_marker = response['NextMarker']
            else:
                break

    def scrape_bucket(self, bucket_name):
        """
            generator
        """
        bucket_name = bucket_name.replace("s3://", "")
        self._logger.debug("Scraping bucket %s", bucket_name)
        found_count = 0
        total = 0
        for item in self.list_bucket_objects(bucket_name):
            total += 1
            name = item['key'].split('/')[-1].strip().lower()
            for extension in EXTENSIONS:
                if name.endswith(extension):
                    s3_complete_path = f"s3://{ bucket_name }/{ item['key'] }"
                    found_count += 1
                    yield s3_complete_path

        self._logger.info("%d of %d files scanned matched %s",
                          found_count,
                          total,
                          EXTENSIONS)


def parse_args(argv):
    """
        Build and run parser
    """

    parser = argparse.ArgumentParser(description='Scrapee S3 Bucket for music files.')
    parser.add_argument('--bucket',
                        metavar='s3://bcket',
                        type=str,
                        required=True,
                        help='s3 bucket to scrape')
    parser.add_argument('-v',
                        action='store_true',
                        dest='verbose',
                        help='verbose logging')

    args_object = parser.parse_args(argv)
    return args_object


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    if args.verbose:
        mylogging.init_logging(logging.DEBUG)
    else:
        mylogging.init_logging(logging.INFO)

    s3_client = make_s3_client()
    scraper = S3MusicScraper(s3_client)
    for s3_path in scraper.scrape_bucket(args.bucket):
        print(s3_path)

# end
