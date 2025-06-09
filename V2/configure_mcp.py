#!/usr/bin/env python3
import json
import os
import sys

def main():
    if len(sys.argv) != 3:
        print("❌ Usage: configure_mcp.py <mcp_file> <review_gate_dir>")
        sys.exit(1)
    mcp_file = sys.argv[1]
    review_gate_dir = sys.argv[2]

    existing_servers = {}
    if os.path.exists(mcp_file):
        try:
            with open(mcp_file, 'r') as f:
                config = json.load(f)
            existing_servers = config.get('mcpServers', {})
            existing_servers.pop('review-gate-v2', None)
            print('✅ Found existing MCP servers, merging configurations')
        except Exception:
            print('⚠️ Existing config invalid, creating new one')
            existing_servers = {}
    else:
        print('📝 Creating new MCP configuration file')

    existing_servers['review-gate-v2'] = {
        'command': os.path.join(review_gate_dir, 'venv', 'Scripts', 'python.exe'),
        'args': [os.path.join(review_gate_dir, 'review_gate_v2_mcp.py')],
        'env': {
            'PYTHONPATH': review_gate_dir,
            'PYTHONUNBUFFERED': '1',
            'REVIEW_GATE_MODE': 'cursor_integration'
        }
    }

    config = {'mcpServers': existing_servers}

    try:
        with open(mcp_file, 'w') as f:
            json.dump(config, f, indent=2)
        print('✅ MCP configuration updated successfully')
        print(f'Total MCP servers configured: {len(existing_servers)}')
        for name in existing_servers.keys():
            print(f'  • {name}')
    except Exception as e:
        print(f'❌ Failed to write MCP configuration: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main() 