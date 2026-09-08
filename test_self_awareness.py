# -*- coding: utf-8 -*-
"""Quick test script to verify self_awareness module loading."""

import sys
import os

# Add project to path
sys.path.insert(0, 'G:/xiao6/xiao6-ui')

print("Python executable:", sys.executable)
print("Current dir:", os.getcwd())
print()

# Find self_awareness module
for p in sys.path:
    if p and os.path.exists(p):
        sa = os.path.join(p, 'self_awareness.py')
        if os.path.exists(sa):
            print(f"Found self_awareness.py at: {sa}")

print()

# Import and test
import self_awareness
print("Module loaded from:", self_awareness.__file__)

result = self_awareness.get_status()
print()
print("get_status() result:")
import json
print(json.dumps(result['capabilities'], indent=2))
