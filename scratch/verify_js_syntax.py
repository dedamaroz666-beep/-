import sys

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

stack = []
pairs = {')': '(', ']': '[', '}': '{'}
in_s = False
in_d = False
in_t = False
in_c1 = False
in_c2 = False
escaped = False

i = 0
n = len(text)
errors = 0
while i < n:
    c = text[i]
    if in_c1:
        if c == '\n': in_c1 = False
    elif in_c2:
        if c == '*' and i + 1 < n and text[i+1] == '/':
            in_c2 = False
            i += 1
    elif in_s:
        if escaped: escaped = False
        elif c == '\\': escaped = True
        elif c == "'": in_s = False
    elif in_d:
        if escaped: escaped = False
        elif c == '\\': escaped = True
        elif c == '"': in_d = False
    elif in_t:
        if escaped: escaped = False
        elif c == '\\': escaped = True
        elif c == '`': in_t = False
    else:
        if c == '/' and i + 1 < n and text[i+1] == '/':
            in_c1 = True
            i += 1
        elif c == '/' and i + 1 < n and text[i+1] == '*':
            in_c2 = True
            i += 1
        elif c == "'": in_s = True
        elif c == '"': in_d = True
        elif c == '`': in_t = True
        elif c in '({[':
            stack.append((c, i))
        elif c in ')}]':
            if not stack:
                print(f"Unmatched closing {c} at {i}")
                errors += 1
            else:
                top, top_i = stack.pop()
                if top != pairs[c]:
                    print(f"Mismatched {c} at {i}, expected matching for {top} at {top_i}")
                    errors += 1
    i += 1

print(f"Balance check complete. Unclosed open brackets: {len(stack)}, errors: {errors}")
