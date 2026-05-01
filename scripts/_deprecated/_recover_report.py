"""Detect exact byte pattern and fix newlines in report.py"""
import os

rp = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'

with open(rp, 'rb') as f:
    raw = f.read()

# Find all places where \n\n appears as real bytes within string literals
# These should be \\n\\n (escaped backslash-n)
problem = b'\\n\\n'
real_nl = b'\n'

# Search for the pattern around _section_multi_year_trend
idx = raw.find(b'_section_multi_year_trend')
print(f"Found _section_multi_year_trend at byte {idx}")
print(f"Context bytes: {raw[idx-100:idx+200].hex()}")
print(f"Context text: {raw[idx-100:idx+200]}")

# Find lines that have REAL \n inside return ["..."] statements
lines_bytes = raw.split(b'\n')
print(f"\nTotal lines: {len(lines_bytes)}")

problematic = []
for i, line in enumerate(lines_bytes):
    if b'return ["##' in line:
        # Check if this line contains actual newlines embedded
        if b'\\n' not in line and len(line) > 50:
            # Look for return statement with embedded newlines
            problematic.append((i+1, line))

print(f"\nProblematic lines (return with embedded newlines): {len(problematic)}")
for ln, raw_line in problematic[:10]:
    print(f"  L{ln}: {raw_line[:100]}")
