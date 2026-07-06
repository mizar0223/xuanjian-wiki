"""
玄鉴仙族 Wiki 管理工具
常用操作: 登录、查询页面、删除页面、统计信息
"""
import requests, json, sys, urllib3

from common.config import AppConfig, require_wiki_password

urllib3.disable_warnings()

CONFIG = AppConfig()
WIKI_API = CONFIG.wiki_api
WIKI_USER = CONFIG.wiki_user
WIKI_URL = CONFIG.wiki_url or 'http://9433.com.cn/wiki/'

class WikiAdmin:
    def __init__(self):
        self.s = requests.Session()
        self.csrf = None
    
    def login(self):
        password = require_wiki_password(CONFIG)
        r1 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        }, verify=False)
        lt = r1.json()["query"]["tokens"]["logintoken"]
        r2 = self.s.post(WIKI_API, data={
            "action": "clientlogin", "format": "json",
            "username": WIKI_USER, "password": password,
            "logintoken": lt,
            "loginreturnurl": WIKI_URL.rstrip('/') + '/首页'
        }, verify=False)
        if r2.json()["clientlogin"]["status"] != "PASS":
            raise Exception(f"Login failed: {r2.json()}")
        r3 = self.s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "format": "json"
        }, verify=False)
        self.csrf = r3.json()["query"]["tokens"]["csrftoken"]
        print(f"✅ Logged in as {WIKI_USER}")
    
    def stats(self):
        """打印 wiki 统计信息"""
        r = self.s.get(WIKI_API, params={
            "action": "query", "meta": "siteinfo", "siprop": "statistics", "format": "json"
        }, verify=False)
        s = r.json()["query"]["statistics"]
        print(f"📊 Pages: {s['pages']} | Articles: {s['articles']} | Edits: {s['edits']} | Users: {s['users']}")
    
    def list_pages(self, limit=20, prefix=""):
        """列出页面"""
        params = {
            "action": "query", "list": "allpages", "aplimit": str(limit),
            "format": "json"
        }
        if prefix:
            params["apprefix"] = prefix
        r = self.s.get(WIKI_API, params=params, verify=False)
        pages = r.json()["query"]["allpages"]
        for p in pages:
            print(f"  {p['pageid']:>4}: {p['title']}")
        return pages
    
    def search(self, query, limit=10):
        """全文搜索"""
        r = self.s.get(WIKI_API, params={
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": str(limit), "format": "json"
        }, verify=False)
        results = r.json()["query"]["search"]
        for sr in results:
            print(f"  {sr['title']} (size:{sr['size']})")
        return results
    
    def get_page(self, title):
        """获取页面内容"""
        r = self.s.get(WIKI_API, params={
            "action": "query", "prop": "revisions", "rvprop": "content",
            "titles": title, "format": "json"
        }, verify=False)
        pages = r.json()["query"]["pages"]
        page = list(pages.values())[0]
        if "revisions" in page:
            return page["revisions"][0]["*"]
        return None
    
    def delete_page(self, title, reason="管理员操作"):
        """删除页面"""
        if not self.csrf:
            self.login()
        r = self.s.post(WIKI_API, data={
            "action": "delete", "format": "json",
            "title": title, "reason": reason, "token": self.csrf
        }, verify=False)
        return r.json()
    
    def categories(self):
        """列出所有分类"""
        r = self.s.get(WIKI_API, params={
            "action": "query", "list": "allcategories", "aclimit": "50", "format": "json"
        }, verify=False)
        cats = r.json()["query"]["allcategories"]
        for c in cats:
            print(f"  [[Category:{c['*']}]]")
        return cats

def main():
    admin = WikiAdmin()
    if len(sys.argv) < 2:
        print("Usage: wiki_admin.py <command> [args]")
        print("Commands: stats, list, search <query>, get <title>, delete <title>, categories")
        return
    
    cmd = sys.argv[1]
    if cmd == "stats":
        admin.stats()
    elif cmd == "list":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        admin.list_pages(prefix=prefix)
    elif cmd == "search":
        admin.search(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "get":
        content = admin.get_page(sys.argv[2])
        print(content if content else "Page not found")
    elif cmd == "delete":
        admin.login()
        result = admin.delete_page(sys.argv[2])
        print(result)
    elif cmd == "categories":
        admin.categories()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
