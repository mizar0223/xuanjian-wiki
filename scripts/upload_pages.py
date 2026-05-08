#!/usr/bin/env python3
"""批量上传玄鉴仙族维基页面到 MediaWiki API"""
import requests, json, os, sys, time, urllib3, glob
urllib3.disable_warnings()

WIKI_API = "http://leoshixie.devcloud.woa.com/api.php"
WIKI_USER = "WikiAdmin"
WIKI_PASS = "XuanjianAdmin2026"
PAGES_DIR = "/tmp/wiki_pages"
DELAY = 0.3  # seconds between edits
MAX_RETRIES = 3
DRY_RUN = "--dry-run" in sys.argv

class WikiSession:
    def __init__(self):
        self.s = requests.Session()
        self.csrf = None
        
    def login(self):
        # Get login token
        r1 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        }, verify=False)
        login_token = r1.json()["query"]["tokens"]["logintoken"]
        
        # Login
        r2 = self.s.post(WIKI_API, data={
            "action": "clientlogin", "format": "json",
            "username": WIKI_USER, "password": WIKI_PASS,
            "logintoken": login_token,
            "loginreturnurl": "http://leoshixie.devcloud.woa.com/wiki/首页"
        }, verify=False)
        result = r2.json()
        if result.get("clientlogin", {}).get("status") != "PASS":
            raise Exception(f"Login failed: {result}")
        print(f"✅ Logged in as {result['clientlogin']['username']}")
        
        # Get CSRF token
        r3 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "format": "json"
        }, verify=False)
        self.csrf = r3.json()["query"]["tokens"]["csrftoken"]
        print(f"✅ Got CSRF token")
        
    def create_page(self, title, text, summary="批量导入"):
        """Create or edit a page. Returns (success, message)."""
        for attempt in range(MAX_RETRIES):
            try:
                r = self.s.post(WIKI_API, data={
                    "action": "edit", "format": "json",
                    "title": title,
                    "text": text,
                    "summary": summary,
                    "token": self.csrf,
                    "bot": "1",
                }, verify=False, timeout=30)
                result = r.json()
                if "error" in result:
                    # Check if it's a token expiry
                    if result["error"].get("code") == "badtoken":
                        print("  ⚠️ Token expired, refreshing...")
                        r3 = self.s.get(WIKI_API, params={
                            "action": "query", "meta": "tokens", "format": "json"
                        }, verify=False)
                        self.csrf = r3.json()["query"]["tokens"]["csrftoken"]
                        continue
                    return False, result["error"].get("info", str(result["error"]))
                edit = result.get("edit", {})
                if edit.get("result") == "Success":
                    return True, f"rev:{edit.get('newrevid','?')}"
                return False, str(edit)
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)
                else:
                    return False, str(e)
        return False, "Max retries exceeded"

def main():
    # Collect all .wiki files
    wiki_files = sorted(glob.glob(os.path.join(PAGES_DIR, "*.wiki")))
    if not wiki_files:
        print("❌ No .wiki files found in", PAGES_DIR)
        sys.exit(1)
    
    print(f"📚 Found {len(wiki_files)} wiki pages to upload")
    
    if DRY_RUN:
        print("🔍 DRY RUN - showing first 5 pages:")
        for f in wiki_files[:5]:
            title = os.path.splitext(os.path.basename(f))[0]
            size = os.path.getsize(f)
            print(f"  {title} ({size} bytes)")
        print(f"  ... and {len(wiki_files)-5} more")
        return
    
    # Login
    wiki = WikiSession()
    wiki.login()
    
    # Stats
    success = 0
    failed = 0
    skipped = 0
    errors = []
    
    start_time = time.time()
    
    for i, f in enumerate(wiki_files, 1):
        title = os.path.splitext(os.path.basename(f))[0]
        with open(f, "r", encoding="utf-8") as fh:
            text = fh.read()
        
        ok, msg = wiki.create_page(title, text, summary=f"批量导入: {title}")
        
        if ok:
            success += 1
            if i % 50 == 0 or i == len(wiki_files):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(wiki_files) - i) / rate if rate > 0 else 0
                print(f"  [{i}/{len(wiki_files)}] ✅ {title} ({rate:.1f} pages/s, ETA: {eta:.0f}s)")
        else:
            failed += 1
            errors.append((title, msg))
            print(f"  [{i}/{len(wiki_files)}] ❌ {title}: {msg[:100]}")
        
        time.sleep(DELAY)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"📊 Import Summary:")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed:  {failed}")
    print(f"  ⏱️  Time:    {elapsed:.1f}s ({success/elapsed:.1f} pages/s)")
    
    if errors:
        print(f"\n❌ Failed pages ({len(errors)}):")
        for title, msg in errors[:20]:
            print(f"  - {title}: {msg[:80]}")
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")
    
    # Save error log
    with open("/tmp/wiki_import_errors.json", "w", encoding="utf-8") as fh:
        json.dump(errors, fh, ensure_ascii=False, indent=2)
    print(f"\n📁 Error log saved to /tmp/wiki_import_errors.json")

if __name__ == "__main__":
    main()
