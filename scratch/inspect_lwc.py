with open('scratch/lwc.js', 'r', encoding='utf-8') as f:
    js = f.read()

import re
matches = re.findall(r'document\.createElement\(["\'](\w+)["\']\)', js)
from collections import Counter
print(Counter(matches))

# Look for styles set by lightweight charts:
for m in re.finditer(r'style\.([a-zA-Z]+)\s*=\s*["\']([^"\']+)["\']', js):
    prop, val = m.group(1), m.group(2)
    if any(k in val for k in ['white', '#fff', 'rgba', 'radius', 'border']):
        print(f'{prop} = {val}')
