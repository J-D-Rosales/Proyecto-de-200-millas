import os, json, uuid, boto3
from ._auth import validate_token

s3 = boto3.client("s3")
BUCKET = os.environ["PRODUCTS_BUCKET"]

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        token = (body.get("token") or "").strip()
        content_type = (body.get("contentType") or "image/jpeg").strip()

        auth = validate_token(token)
        if not auth:
            return _resp(403, {"error": "Token inválido"})
        tenant_id = auth["tenant_id"]

        product_id = str(uuid.uuid4())
        ext = ".png" if content_type == "image/png" else ".jpg"
        image_key = f"tenants/{tenant_id}/products/{product_id}{ext}"

        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": BUCKET, "Key": image_key, "ContentType": content_type},
            ExpiresIn=300  # 5 min
        )
        return _resp(200, {"uploadUrl": upload_url, "image_key": image_key, "product_id": product_id})
    except Exception as e:
        return _resp(500, {"error": str(e)})

def _resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json","Access-Control-Allow-Origin":"*"}, "body": json.dumps(body)}
