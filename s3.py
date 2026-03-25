import time
import requests
import mimetypes
from requests import HTTPError
from urllib.error import URLError

def create_bucket(s3_client, ec2_instance_id):
    """
    Creates a publicly-accessible general purpose S3 bucket and returns a dictionary representation of
    the bucket attributes.

    Function:
    - Names the bucket using the argument EC2 instance ID as follows, joe-omahony-[ec2_instance_id]
    - Creates the bucket with object lock disabled.
    - Changing object ownership to BucketOwnerPreferred was required as the default BucketOwnerEnforced prevented assigning the public-read ACL.
    - Waits until the bucket exists, then removes the public access block.
    - A dictionary representing the bucket attributes is returned.

    **StackOverflow reference:**
    "How to upload to AWS S3 with Object Tagging" |
    https://stackoverflow.com/questions/55592349/how-to-upload-to-aws-s3-with-object-tagging |
    I couldn't figure out how to add tags, tried the previous way using a dictionary, then the put_object_tagging()
    way, but these both raised ParamValidationError for an Invalid type for parameter Tagging.
    A search resulted in this post, which solved my issue with "Use & as a delimiter between tag values
    like "Key1=Value1"&"Key2=Value2..."

    Boto3 documentation for s3_client.create_bucket():
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/create_bucket.html

    Boto3 documentation for S3.Client.get_waiter(waiter_name):
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_waiter.html

    Boto3 documentation for S3 waiters:
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3.html#waiters

    Boto3 documentation for S3 BucketExists waiter:
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/waiter/BucketExists.html

    Boto3 documentation for s3_client.delete_public_access_block(**kwargs):
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/delete_public_access_block.html

    Boto3 documentation for s3_client.put_public_access_block(**kwargs):
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_bucket_acl.html

    Boto3 documentation for s3_client.put_bucket_acl():
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_bucket_acl.html

    :param s3_client: S3 Client Handle
    :param ec2_instance_id: EC2 Instance ID used to form the bucket name
    :return: bucket dictionary representation
    """
    bucket_name = 'joe-omahony-' + ec2_instance_id

    bucket = s3_client.create_bucket(
        # ACL='public-read' (InvalidBucketAclWithObjectOwnership)
        # Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
        # ACL='public-read', NEED TO CREATE BUCKET FIRST
        Bucket=bucket_name,
        CreateBucketConfiguration={
            # 'LocationConstraint': 'us-east-1', (InvalidLocationConstraint) / EC2 Handles are given region
            'Tags': [
                {'Key': 'CreatedBy', 'Value': 'JoeOMahony'},
                {'Key': 'Module', 'Value': 'AutomatedCloudServices'},
                {'Key': 'Assignment', 'Value': 'Assignment01'}
            ],
        },
        ObjectLockEnabledForBucket=False, # Check later
        ObjectOwnership = 'BucketOwnerPreferred',
    )

    # could use s3 resource handle instead of below, but will stick with this to match ec2
    waiter = s3_client.get_waiter('bucket_exists') # needed to avoid error with delete_public_access_block()
    waiter.wait(
        Bucket = bucket_name,
    )

    s3_client.delete_public_access_block(
        Bucket=bucket_name,
    )

    # https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_bucket_acl.html
    s3_client.put_bucket_acl(
        ACL='public-read',
        Bucket=bucket_name,
    )

    bucket.update({'BucketName': bucket_name})  # bucket Dict only contains ARN/Location, need to add bucket_name

    return bucket

def get_image_object(obj_url_input):
    """
    Retrieves and returns an image from the argument URL or the default image.

    **Use of HTTP User-Agent header:**

    - Sets HTTP User-Agent header (from my machine) as all requests were denied without it (HTTP Error 403: Forbidden).
    - Requests were implemented from urllib instead of the standard urlopen() because of this eventual need to set headers.
    - Please see my reference on this below.

    Reference for the Wikimedia Foundation document explaining the need to use a user agent, and also how to implement:
    https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy

    Default image used:
    https://upload.wikimedia.org/wikipedia/commons/b/bd/Waterford_Institute_of_Technology%2C_2021-06-01%2C_06.jpg

    Python documentation for the urllib.request module:
    https://docs.python.org/3/library/urllib.request.html#module-urllib.request

    :param obj_url_input: Image URL to be fetched or 'NONE' for the default image
    :return: Binary representation of the argument or default image for an S3 object
    """
    # https://docs.python.org/3/library/urllib.request.html#module-urllib.request
    # urllib.request.urlopen(url, data=None, [timeout, ]*, context=None)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0'}
    fallback_obj_url_input = 'https://upload.wikimedia.org/wikipedia/commons/b/bd/Waterford_Institute_of_Technology%2C_2021-06-01%2C_06.jpg'
    timeout = 30 # "By default, requests do not time out unless a timeout value is set explicitly." [seconds]
    try:
        if obj_url_input == 'NONE': # keyword for no URL to provide, use known good
            obj_url_input = 'https://upload.wikimedia.org/wikipedia/commons/b/bd/Waterford_Institute_of_Technology%2C_2021-06-01%2C_06.jpg'

        # https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
        image = requests.get(obj_url_input, timeout=timeout, headers=headers).content

    except URLError: # Raises URLError on protocol errors.
        image = requests.get(fallback_obj_url_input, timeout=timeout, headers=headers).content
        # image = 'http://www.setu.ie/imager/ctas/35068/Cork-Road-Campus-Waterford-3_a1dcb81403a2f417e019929f519bbb18.jpg?width=360'

    except HTTPError: # Thrown if no user agent or site denied - urllib.error.HTTPError: HTTP Error 403: Forbidden
        image = requests.get(fallback_obj_url_input, timeout=timeout, headers=headers).content

    except Exception:
        image = requests.get(fallback_obj_url_input, timeout=timeout, headers=headers).content

    return image

def guess_mime_type(obj_url_input):
    """
    Uses MIME guesser to guess the argument URL's MIME type for S3 object display in index.html document.

    Python documentation for the MIME type guesser module's guess_type function:
    https://docs.python.org/3/library/mimetypes.html#mimetypes.guess_type

    :param obj_url_input: Image URL to be fetched or 'NONE' for the default image
    :return: Guessed MIME type or 'image/jpg' (type of default image)
    """
    # (type, encoding) = mimetypes.guess_type(obj_url_input)
    # return (type, encoding)
    # Invalid type for parameter ContentEncoding, value: None, type: <class 'NoneType'>, valid types: <class 'str'>
    (mime_type, encoding) = mimetypes.guess_type(obj_url_input)

    # The default image is image/jpg, so this is used as the fallback
    if mime_type is None:
        mime_type = 'image/jpg' # type is None if the type can't be guessed (no or unknown suffix)

    try:
        if not str(mime_type).startswith('image/'):
            mime_type = 'image/jpg'
    except Exception:
        mime_type = 'image/jpg'

    return mime_type

def put_object(s3_client, bucket_name, ec2_instance_id, image, mime_type):
    """
    Function which puts an image object into an S3 bucket (arguments).

    AWS documentation on naming S3 objects:
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html

    Boto3 documentation on S3.Client.put_object(**kwargs):
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html

    Boto3 documentating for upload files (showed me MIME types needed + binary read with open):
    https://docs.aws.amazon.com/boto3/latest/guide/s3-uploading-files.html

    :param mime_type: MIME type of the image
    :param s3_client: S3 client handle
    :param bucket_name: S3 bucket to add the object to
    :param image: Binary image representation
    :param ec2_instance_id: EC2 instance ID used in naming the object
    :return: Created S3 object dictionary representation
    """
    # Since S3 bucket name also uses 'joe-omahony-' + ec2_instance_id, I could reactor this
    # TypeError: can only concatenate str (not "int") to str -> forgot not using f-string
    object_name = 'joe-omahony-' + ec2_instance_id + '-' + 'obj-' + str(time.time_ns()) # max length for obj names is 1024

    s3_client.put_object(
        ACL='public-read',
        Body=image,
        Bucket=bucket_name,
        Key=object_name,
        # REFERENCE: Full StackOverflow reference in create_bucket() function at the top
        Tagging='CreatedBy=JoeOMahony&Module=AutomatedCloudServices&Assignment=AutomatedCloudServices',
        ContentType=mime_type, # MIME type required here for local file upload
    )

    # Adding as I need the key
    obj_details = {
        'BucketName': bucket_name,
        'ObjKey': object_name,
    }

    return obj_details


def list_all_buckets(s3_client):
    """
    Returns a list of dictionary representations of all S3 buckets.

    Boto3 documentation for s3_client.list_buckets() function:
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/list_buckets.html

    :param s3_client: S3 client handle
    :return: List of dictionary bucket representations
    """
    # Response Syntax {'Buckets': [{'Name': 'string',
    response = s3_client.list_buckets()
    return response['Buckets']

def delete_objects(s3_client, bucket_name):
    """
    Deletes all objects in the argument bucket.

    Boto3 documentation for s3_client.delete_objects() function:
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/delete_object.html

    :param s3_client: S3 client handle
    :param bucket_name: S3 bucket name to delete all objects from
    :return: True if all objects were successfully deleted, error thrown otherwise
    """
    bucket_objects = s3_client.list_objects(
        Bucket=bucket_name,
    )

    # 'Contents': [
    #         {
    #             'ETag': '"70ee1738b6b21e2c8a43f3a5ab0eee71"',
    #             'Key': 'example1.jpg', ...
    for bucket_object in bucket_objects['Contents']:
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=bucket_object['Key'],
        )
    return True # come back to verify later


def delete_bucket(s3_client, bucket_name):
    """
    Deletes the argument bucket after deleting all objects within.

    :param s3_client: S3 client handle
    :param bucket_name: S3 bucket name to be deleted, including all objects within
    :return: True if all objects and the bucket were deleted, False if not.
    """
    delete_all_objects = delete_objects(s3_client, bucket_name)

    if delete_all_objects:
        s3_client.delete_bucket( # returns None
            Bucket = bucket_name,
        )

        all_buckets = list_all_buckets(s3_client)
        #   'Buckets': [
        #         {
        #             'Name': 'string', ...
        for bucket in all_buckets: # list
            if bucket['Name'] == bucket_name:
                return False

        return True

    return False