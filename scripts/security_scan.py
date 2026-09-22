#!/usr/bin/env python3
import argparse, json, re, subprocess
from pathlib import Path
TOKEN_PATTERNS=[
 ("PRIVATE_KEY",re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
 ("GITHUB_TOKEN",re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
 ("GITHUB_FINE_GRAINED",re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
 ("GOOGLE_API_KEY",re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
 ("AWS_ACCESS_KEY",re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
 ("SLACK_TOKEN",re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
 ("OAUTH_REFRESH_TOKEN",re.compile(r"\b1//[0-9A-Za-z_-]{20,}\b"))]
FORBIDDEN_OUTPUT_KEYS={"authorization","cookie","cookies","session","session_id","access_token","refresh_token","client_secret","api_key","password","private_key","credential","credentials","signed_url"}
FORBIDDEN_PATH_PARTS={".env","secrets"}
def scan_text(path,text):
    return [f"{path}:{name}" for name,rx in TOKEN_PATTERNS if rx.search(text)]
def walk_keys(v,prefix=""):
    hits=[]
    if isinstance(v,dict):
        for k,x in v.items():
            p=f"{prefix}.{k}" if prefix else str(k)
            if str(k).lower() in FORBIDDEN_OUTPUT_KEYS: hits.append(p)
            hits.extend(walk_keys(x,p))
    elif isinstance(v,list):
        for i,x in enumerate(v): hits.extend(walk_keys(x,f"{prefix}[{i}]"))
    return hits
def repository_scan():
    files=subprocess.check_output(["git","ls-files"],text=True).splitlines(); hits=[]
    for name in files:
        p=Path(name)
        if any(part.lower() in FORBIDDEN_PATH_PARTS for part in p.parts): hits.append(f"{name}:FORBIDDEN_PATH"); continue
        try: text=p.read_text(encoding="utf-8")
        except Exception: continue
        hits.extend(scan_text(name,text))
    if hits: raise SystemExit("CREDENTIAL_PATTERN_DETECTED\n"+"\n".join(hits))
    print("A_MOMENTUM_REPOSITORY_CREDENTIAL_SCAN_PASS",len(files))
def runtime_scan(root):
    root=Path(root); hits=[]
    for p in root.rglob("*"):
        if not p.is_file(): continue
        try: text=p.read_text(encoding="utf-8")
        except Exception: continue
        hits.extend(scan_text(str(p),text))
        if p.suffix.lower()==".json":
            try:
                for key in walk_keys(json.loads(text)): hits.append(f"{p}:FORBIDDEN_OUTPUT_KEY:{key}")
            except json.JSONDecodeError: hits.append(f"{p}:INVALID_JSON")
    if hits: raise SystemExit("RUNTIME_OUTPUT_SECRET_SCAN_FAIL\n"+"\n".join(hits))
    print("A_MOMENTUM_RUNTIME_OUTPUT_SECRET_SCAN_PASS",str(root))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repository",action="store_true"); ap.add_argument("--runtime-output"); a=ap.parse_args()
    if not a.repository and not a.runtime_output: raise SystemExit("choose --repository and/or --runtime-output")
    if a.repository: repository_scan()
    if a.runtime_output: runtime_scan(a.runtime_output)
if __name__=="__main__": main()
