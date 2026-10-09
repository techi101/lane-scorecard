"""AWS SDK contracts using botocore's request validator; no network requests."""
import json
import boto3
from botocore.stub import Stubber
from mangum import Mangum

from app.storage import Store
from app.vision import suggest


def test_dynamodb_storage_roundtrip_and_conditional_insert(tmp_path, monkeypatch):
    resource = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
    table = resource.Table('lane-test')
    store = Store(tmp_path)
    store.table = table
    record = {'id':'one','score':12.5}
    data = json.dumps(record, ensure_ascii=False, allow_nan=False)
    item = {'pk':'pilot:checks','sk':'one','data':data}
    client = table.meta.client
    with Stubber(client) as stub:
        stub.add_response('put_item', {}, {'TableName':'lane-test','Item':item,'ConditionExpression':'attribute_not_exists(pk)'})
        assert store.put('pilot:checks','one',record,create=True)
        stub.add_response('get_item', {'Item':{k:{'S':v} for k,v in item.items()}}, {'TableName':'lane-test','Key':{'pk':'pilot:checks','sk':'one'},'ConsistentRead':True})
        assert store.get('pilot:checks','one') == record
        stub.add_client_error('put_item', service_error_code='ConditionalCheckFailedException', expected_params={'TableName':'lane-test','Item':item,'ConditionExpression':'attribute_not_exists(pk)'})
        assert store.put('pilot:checks','one',record,create=True) is False
        stub.add_response('delete_item', {}, {'TableName':'lane-test','Key':{'pk':'pilot:checks','sk':'one'}})
        store.delete('pilot:checks','one')
        stub.assert_no_pending_responses()


def test_bedrock_converse_request_and_response(monkeypatch):
    monkeypatch.delenv('LANE_MODEL_ID', raising=False)
    client = boto3.client('bedrock-runtime', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
    with Stubber(client) as stub:
        stub.add_response('converse', {
            'output':{'message':{'role':'assistant','content':[{'text':'{"rating":"few","reason":"A visible wrapper."}'}]}},
            'stopReason':'end_turn', 'usage':{'inputTokens':10,'outputTokens':15,'totalTokens':25}, 'metrics':{'latencyMs':5},
        })
        result = suggest(b'image-bytes-for-contract-test', 'bio', client=client)
        assert result['status'] == 'available'
        assert result['rating'] == 'few'
        stub.assert_no_pending_responses()


def test_lambda_http_api_adapter(tmp_path, monkeypatch):
    for name in ['LANE_TABLE','LANE_ADMIN_CODE','AWS_LAMBDA_FUNCTION_NAME','LANE_PHOTO_BUCKET']:
        monkeypatch.delenv(name, raising=False)
    from app.main import create_app
    adapter = Mangum(create_app(tmp_path), lifespan='off')
    event = {
        'version':'2.0', 'routeKey':'ANY /{proxy+}', 'rawPath':'/api/health', 'rawQueryString':'',
        'headers':{'host':'example.execute-api.us-east-1.amazonaws.com','x-forwarded-proto':'https'},
        'requestContext':{'accountId':'123456789012','apiId':'test','domainName':'example.execute-api.us-east-1.amazonaws.com','domainPrefix':'example','http':{'method':'GET','path':'/api/health','protocol':'HTTP/1.1','sourceIp':'127.0.0.1','userAgent':'contract-test'},'requestId':'test','routeKey':'ANY /{proxy+}','stage':'$default','time':'01/Jan/2026:00:00:00 +0000','timeEpoch':0},
        'isBase64Encoded':False,
    }
    result = adapter(event, {})
    assert result['statusCode'] == 200
    assert json.loads(result['body'])['ok'] is True
