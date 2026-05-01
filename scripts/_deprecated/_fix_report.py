"""Restore report.py from git + add only what's needed"""
import subprocess, os

skill = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts'
rp = os.path.join(skill, 'report.py')

# Check if there's a git repo
git_dir = os.path.join(r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis', '.git')
print(f"Git dir exists: {os.path.exists(git_dir)}")

# Check current file encoding
with open(rp, 'rb') as f:
    raw = f.read(500)
print(f"First bytes (hex): {raw[:50].hex()}")
# Check for UTF-8 BOM
print(f"Has BOM: {raw[:3] == b'\\xef\\xbb\\xbf'}")
# Check for GBK marker
try:
    raw[:100].decode('gbk')
    print("File appears to be GBK encoded")
except:
    print("File appears to be UTF-8 encoded")

# Find the _section_unknown function
with open(rp, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '_section_unknown' in line or '年报PDF全文' in line or '精确盈利预测' in line:
        print(f"Line {i+1}: {line.rstrip()[:100]}")
