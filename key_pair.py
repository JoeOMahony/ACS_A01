import os
import time
from botocore.exceptions import ClientError

def create_key_pair(ec2_client):
    """
    Creates an RSA key-pair using the EC2 client handle remotely and locally.

    - Remote key name uniqueness provided through nanoseconds since Epoch, i.e., acs_a01_jomahony_{time_since_epoch}.pem}
    - Nanoseconds selected to ensure uniqueness, but also because time.time_ns() returns an int
    - Local key name is hard-coded as JOMahony_A01_RSA.pem, but existence checks before creation mitigates.
    - Local key is given 400 permissions as required when using SSH to reach EC2 instance.

    Boto3 documentation for ec2_client.create_key_pair():
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/create_key_pair.html

    Boto3 documentation for the OS library, including chmod call:
    https://docs.python.org/3/library/os.html

    :param ec2_client: EC2 client handle
    :return: dict Dictionary describing the key-pair (note KeyName)
    """
    key_name = f"acs_a01_jomahony_{time.time_ns()}" # using nanoseconds from Epoch to make each instance key unique
    try:
        response = ec2_client.create_key_pair(
            KeyName=key_name,
            KeyType='rsa',
            KeyFormat='pem',
            TagSpecifications=[
                {
                    "ResourceType": "key-pair",
                    "Tags": [
                        {"Key": "CreatedBy", "Value": "JoeOMahony"},
                        {"Key": "Module", "Value": "AutomatedCloudServices"},
                        {"Key": "Assignment", "Value": "Assignment01"}
                    ]
                }
            ]
        )
    except ClientError as client_err:
        print(f'Client error when creating remote key-pair, check your access and permissions: {client_err}')
        raise

    try:
        # DOCS: KeyMaterial (string) –
        # An unencrypted PEM encoded RSA or ED25519 private key.
        # because hard-coded, need to existence check to avoid errors
        if os.path.exists("JOMahony_A01_RSA.pem"):
            os.remove("JOMahony_A01_RSA.pem")

        with open('JOMahony_A01_RSA.pem', 'w') as file:
            file.write(response['KeyMaterial'])
    except OSError as os_err:
        raise OSError(f'Unable to write local key-pair, check file permissions: {os_err}')
    try:
        # https://docs.python.org/3/library/os.html
        # octal is used for chmod permissions
        # Key permissions need to be owner read only for EC2 connection or refused
        os.chmod('JOMahony_A01_RSA.pem', 0o400) #
    except OSError as os_err:
        raise OSError(f'Unable to change local key-pair permissions, check local file permissions: {os_err}')

    return response

def delete_remote_key_pair(ec2_client, key_name):
    """
    Deletes the remote argument key-pair.

    Boto3 EC2.Client.delete_key_pair(**kwargs) documentationL
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/delete_key_pair.html

    :param ec2_client: EC2 client handle
    :param key_name: Key name of the key-pair to be deleted
    :return: response Dictionary containing success Boolean and KeyPairId String
    """
    try:
        response = ec2_client.delete_key_pair(
            KeyName=key_name,
        )
        return response # dict Return Boolean KeyPairId String
    except ClientError as client_err:
        print(f'Unable to delete remote key-pair, please use the AWS website to delete manually. Error: {client_err}')
        # no raise, not critical
        return {'Return': False} # 'Return': True|False,

def delete_local_key_pair():
    """
    Deletes the local key-pair named JOMahony_A01_RSA.pem if it exists.

    :return: None for success
    """
    try:
        if os.path.exists("JOMahony_A01_RSA.pem"):
            return os.remove('JOMahony_A01_RSA.pem')
    except OSError as os_err:
        print(f'Unable to delete local key-pair, check file permissions and if it exists. Please delete manually. Error: {os_err}')

    return None # If it doesn't exist, return success (this doesn't run when error)