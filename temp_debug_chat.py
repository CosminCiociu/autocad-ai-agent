import importlib.util
import sys
import json
from pathlib import Path as P
from fastapi.testclient import TestClient

ai_server_dir = str(P.cwd() / 'ai-server')
if ai_server_dir not in sys.path:
    sys.path.insert(0, ai_server_dir)

spec = importlib.util.spec_from_file_location('server_main', str(P.cwd() / 'ai-server' / 'main.py'))
server_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_main)

async def fake_plan(context_payload, user_command):
    action_plan = {
        'schema_version': '1.0.0',
        'request_id': context_payload.get('request_id', 'test-req-1'),
        'summary': 'Insert block',
        'needs_clarification': False,
        'actions': [
            {
                'id': 'a1',
                'type': 'insert_block',
                'args': {'name': 'AMP', 'position': {'x': 0, 'y': 0}},
            }
        ],
    }
    return type('PR', (), {'action_plan': action_plan, 'raw_response': json.dumps(action_plan)})()

server_main.planner.plan = fake_plan
client = TestClient(server_main.app)
ctx = {
    'schema_version': '1.0.0',
    'request_id': 'test-req-1',
    'drawing': {'name': 'test', 'units': 'unitless', 'coordinate_system': 'WCS'},
    'blocks': [],
    'texts': [],
    'lines': [],
    'polylines': [],
}
payload = {'context': ctx, 'messages': [{'role': 'user', 'content': 'insereaza un bloc'}]}
resp = client.post('/chat', json=payload)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
