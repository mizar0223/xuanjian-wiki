#!/usr/bin/env python3
"""
批量上传人设图到 MediaWiki
- 来源: resources/reference/玄鉴图册/人设图/
- 目标: Wiki File: 命名空间
"""
import requests, json, os, sys, time, glob, urllib3
urllib3.disable_warnings()

WIKI_API = "http://leoshixie.devcloud.woa.com/api.php"
WIKI_USER = "WikiAdmin"
WIKI_PASS = "XuanjianAdmin2026"
IMG_DIR = "/Users/leoshi/AIBOOK/xuanjian/resources/reference/玄鉴图册/人设图"
DELAY = 1.0  # seconds between uploads (larger files need more)
MAX_RETRIES = 3
DRY_RUN = "--dry-run" in sys.argv

class WikiUploader:
    def __init__(self):
        self.s = requests.Session()
        self.csrf = None
    
    def login(self):
        r1 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        }, verify=False)
        lt = r1.json()["query"]["tokens"]["logintoken"]
        r2 = self.s.post(WIKI_API, data={
            "action": "clientlogin", "format": "json",
            "username": WIKI_USER, "password": WIKI_PASS,
            "logintoken": lt,
            "loginreturnurl": "http://leoshixie.devcloud.woa.com/wiki/"
        }, verify=False)
        if r2.json()["clientlogin"]["status"] != "PASS":
            raise Exception(f"Login failed: {r2.json()}")
        r3 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "format": "json"
        }, verify=False)
        self.csrf = r3.json()["query"]["tokens"]["csrftoken"]
        print("✅ Logged in")
    
    def upload_file(self, filepath, dest_name, description=""):
        """Upload a file to wiki. Returns (success, message)."""
        for attempt in range(MAX_RETRIES):
            try:
                with open(filepath, "rb") as f:
                    r = self.s.post(WIKI_API, data={
                        "action": "upload",
                        "format": "json",
                        "filename": dest_name,
                        "comment": "批量上传人设图",
                        "text": description,
                        "token": self.csrf,
                        "ignorewarnings": "1",
                    }, files={"file": (dest_name, f)}, verify=False, timeout=120)
                result = r.json()
                if "error" in result:
                    if result["error"].get("code") == "badtoken":
                        self._refresh_token()
                        continue
                    return False, result["error"].get("info", str(result["error"]))
                upload = result.get("upload", {})
                if upload.get("result") == "Success":
                    return True, upload.get("filename", "ok")
                if upload.get("result") == "Warning":
                    # File exists or duplicate
                    warnings = upload.get("warnings", {})
                    return False, f"Warning: {warnings}"
                return False, str(upload)
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)
                else:
                    return False, str(e)
        return False, "Max retries exceeded"
    
    def _refresh_token(self):
        r = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "format": "json"
        }, verify=False)
        self.csrf = r.json()["query"]["tokens"]["csrftoken"]

def collect_images(base_dir, recursive=False):
    """Collect image files. Default: root level only (73 named character images)."""
    images = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        images.extend(glob.glob(os.path.join(base_dir, ext)))
        if recursive:
            images.extend(glob.glob(os.path.join(base_dir, "**", ext), recursive=True))
    # Deduplicate
    images = sorted(set(images))
    return images

def make_dest_name(filepath, base_dir):
    """Generate wiki filename: 人设图_角色名.ext"""
    rel = os.path.relpath(filepath, base_dir)
    # Flatten: 子目录名作为前缀
    parts = rel.split(os.sep)
    if len(parts) > 1:
        # 子目录里的文件
        name = "_".join(parts)
    else:
        name = parts[0]
    # 确保有 "人设图_" 前缀
    if not name.startswith("人设图_"):
        name = f"人设图_{name}"
    return name

def make_description(dest_name):
    """Generate file description page."""
    char_name = dest_name.replace("人设图_", "").rsplit(".", 1)[0]
    # Remove subdirectory prefixes
    char_name = char_name.split("_")[-1] if "_" in char_name else char_name
    return f"""== {char_name} 人设图 ==
玄鉴仙族角色人设图。

[[Category:人设图]]
[[Category:角色图片]]
"""

def main():
    images = collect_images(IMG_DIR, recursive=("--recursive" in sys.argv))
    if not images:
        print("❌ No images found")
        sys.exit(1)
    
    total_size = sum(os.path.getsize(f) for f in images)
    print(f"📷 Found {len(images)} images ({total_size/1048576:.1f} MB)")
    
    if DRY_RUN:
        print("🔍 DRY RUN - first 10 files:")
        for f in images[:10]:
            dest = make_dest_name(f, IMG_DIR)
            size = os.path.getsize(f) / 1048576
            print(f"  {dest} ({size:.1f} MB)")
        print(f"  ... and {len(images)-10} more")
        return
    
    uploader = WikiUploader()
    uploader.login()
    
    success = 0
    failed = 0
    errors = []
    start_time = time.time()
    
    for i, filepath in enumerate(images, 1):
        dest_name = make_dest_name(filepath, IMG_DIR)
        desc = make_description(dest_name)
        size_mb = os.path.getsize(filepath) / 1048576
        
        ok, msg = uploader.upload_file(filepath, dest_name, desc)
        
        if ok:
            success += 1
            if i % 10 == 0 or i == len(images):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  [{i}/{len(images)}] ✅ {dest_name} ({size_mb:.1f}MB, {rate:.1f}/s)")
        else:
            failed += 1
            errors.append((dest_name, msg))
            print(f"  [{i}/{len(images)}] ❌ {dest_name}: {msg[:80]}")
        
        time.sleep(DELAY)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary:")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed:  {failed}")
    print(f"  ⏱️  Time:    {elapsed:.0f}s")
    
    if errors:
        print(f"\n❌ Failed ({len(errors)}):")
        for name, msg in errors[:20]:
            print(f"  - {name}: {msg[:80]}")

if __name__ == "__main__":
    main()
