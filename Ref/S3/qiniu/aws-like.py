import boto3

s3 = boto3.client(
    "s3",
    region_name="cn-east-1",  # 华东-浙江区 region id
    endpoint_url="https://s3.cn-east-1.qiniucs.com",  # 华东-浙江区 endpoint
    aws_access_key_id="<QiniuAccessKey>",
    aws_secret_access_key="<QiniuSecretKey>",
    config=boto3.session.Config(signature_version="s3v4"),
)
s3.upload_file("<path/to/upload>", "<Bucket>", "<Key>")
print("Done")
