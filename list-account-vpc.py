import boto3
import time
import webbrowser
import pprint
from boto3.session import Session

sso_url='https://XXXXXXXXXXXX.awsapps.com/start'
sso_role='network'
aws_region = 'eu-central-1'


client = boto3.client('sso-oidc')
response = client.register_client(
    clientName='my-client',
    clientType='public'
)
client_id = response['clientId']
client_secret = response['clientSecret']

# Start the device authorization
response = client.start_device_authorization(
    clientId=client_id,
    clientSecret=client_secret,
    startUrl=sso_url
)
device_code = response['deviceCode']
user_code = response['userCode']
verification_uri = response['verificationUri']

#DEBUG: pprint.pprint(response)
webbrowser.open(response['verificationUriComplete'], autoraise=True)

token = None
while not token:
    try:
        response = client.create_token(
            clientId=client_id,
            clientSecret=client_secret,
            grantType='urn:ietf:params:oauth:grant-type:device_code',
            deviceCode=device_code
        )
        token = response['accessToken']
    except client.exceptions.AuthorizationPendingException:
        print(f"Waiting for user authorization, check browser for code: {response['userCode']}")
        time.sleep(5)

#DEBUG: print(f"Access Token: {token}")
client1 = boto3.client('sso')

# List all accounts0
response = client1.list_accounts(accessToken=token, maxResults=200)
for a in response['accountList']:
    #print(f"{a['accountId']},{a['accountName']}")
    #DEBUG: pprint.pprint (account_roles['roleList'])
    try:
        role_creds = client1.get_role_credentials(roleName=sso_role, accountId=a['accountId'],accessToken=token)['roleCredentials']
        #DEBUG: pprint.pprint(role_creds)
    except Exception as e:
        print(f"{a['accountId']},{a['accountName']},ERROR,ERROR,{e}")

    ec2 = boto3.client('ec2', region_name=aws_region, aws_session_token=role_creds['sessionToken'], aws_account_id=a['accountId'], aws_access_key_id=role_creds['accessKeyId'], aws_secret_access_key=role_creds['secretAccessKey'])
    vpcs = ec2.describe_vpcs()

    for v in vpcs['Vpcs']:
        VpcName = None
        if 'Tags' in v:
            for i in v['Tags']:
                if i['Key'] == 'Name':
                    VpcName = i['Value']
        #Account ID, Account Name, VPC ID, VPC CIDR, VPC Name
        print(f"{a['accountId']},{a['accountName']},{v['VpcId']},{v['CidrBlock']},{VpcName}")

