from urllib.parse import urlparse
import boto3


class S3Client():

    def __init__(self):
        pass

    def download_s3_file(self, s3_url, local_path):
        o = urlparse(s3_url, allow_fragments=False)
        # ParseResult(scheme='s3', 
        #             netloc='bucket_name',
        #             path='/folder1/folder2/file1.json',
        #             params='', query='', fragment='')
        bucket = o.netloc
        key = o.path.lstrip('/')

        s3 = boto3.client('s3')
        with open(local_path, 'wb') as handle:
            s3.download_fileobj(bucket, key, handle)

