import asyncio, json, sys
sys.path.insert(0, 'e:/Ai agent/ai-server')
from planner import ActionPlanner
from ollama_client import OllamaClient

ctx = {
    'schema_version': '1.0.0',
    'request_id': 'req-test-1',
    'drawing': {'name': 'sample.dwg', 'units': 'unitless', 'coordinate_system': 'WCS'},
    'blocks': [{'handle': '1', 'name': 'BLOCK_A', 'layer': '0', 'position': {'x': 0, 'y': 0}, 'rotation_deg': 0, 'attributes': [{'tag': 'CODE', 'value': 'A1'}]}],
    'texts': [{'handle': '2', 'value': 'TEXT_1', 'layer': '0', 'position': {'x': 1, 'y': 1}, 'height': 2.5}],
    'lines': [{'handle': '3', 'layer': '0', 'start': {'x': 0, 'y': 0}, 'end': {'x': 10, 'y': 0}}],
    'polylines': [{'handle': '4', 'layer': '0', 'closed': False, 'vertices': [{'x': 0, 'y': 0}, {'x': 5, 'y': 0}, {'x': 5, 'y': 5}]}],
}

async def main():
    planner = ActionPlanner(OllamaClient())
    result = await planner.plan(ctx, 'Identifica obiectele din desen')
    print(json.dumps(result.action_plan, indent=2))
    print('RAW=' + result.raw_response[:500])

asyncio.run(main())
