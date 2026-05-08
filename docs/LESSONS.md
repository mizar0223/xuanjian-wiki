# 踩坑记录 & 历史教训

## SSH 连接

### ❌ 端口 22 连接被拒
**现象**: `ssh root@21.214.75.44` → `Connection closed by 21.214.75.44 port 22`
**原因**: CVM 的 SSH 端口不是标准 22，而是 **36000**（通过 anydev/IOA 管理）
**解决**: `ssh -p 36000 root@21.214.75.44`
**教训**: anydev VM 类型环境的 SSH 端口固定为 36000，不是标准 22

### ❌ SSH 域名解析失败
**现象**: `evnIns-6h90vw7jeohg.devcloud.woa.com` 无法解析
**解决**: 直接用 IP `21.214.75.44`

---

## MediaWiki API

### ❌ `/w/api.php` 返回 301 重定向到 HTML
**现象**: 请求 `/w/api.php?action=query&format=json` 返回 MW 的 HTML 页面
**原因**: MW 的 `$wgScriptPath=""` 意味着 API 在根路径 `/api.php`，不在 `/w/api.php`
**解决**: 在 nginx 加 `location ^~ /api.php { proxy_pass http://127.0.0.1:8081/api.php; }`

### ❌ 把 `$wgScriptPath` 改成 `/w` 后 404
**现象**: 改完后 `/w/api.php` 返回 404
**原因**: Apache DocumentRoot 是 `/var/www/html/`，MW 文件在根目录，没有 `/w/` 子目录。改 ScriptPath 只影响 MW 的 URL 生成，不影响文件系统布局
**教训**: MW Docker 镜像默认 ScriptPath 为空，所有 PHP 入口在容器根目录。正确做法是保持 ScriptPath 为空，在 nginx 侧暴露需要的 `.php` 文件

### ❌ MW 1.42 Vue 前端无法用 requests 登录
**现象**: 尝试从 HTML 提取 logintoken 失败——token 是 JS 动态加载的
**解决**: 不走 HTML 表单，直接用 API 的 `clientlogin` 动作
**代码**:
```python
# Step 1: 获取 login token
r1 = s.get(API, params={"action":"query","meta":"tokens","type":"login","format":"json"})
login_token = r1.json()["query"]["tokens"]["logintoken"]

# Step 2: clientlogin
r2 = s.post(API, data={
    "action": "clientlogin", "format": "json",
    "username": "WikiAdmin", "password": "XXX",
    "logintoken": login_token,
    "loginreturnurl": "http://..."
})
# status == "PASS" 即成功

# Step 3: 获取 CSRF token 用于后续编辑
r3 = s.get(API, params={"action":"query","meta":"tokens","format":"json"})
csrf = r3.json()["query"]["tokens"]["csrftoken"]
```

---

## 数据处理

### ❌ 配偶字段截断
**现象**: "柳柔绚（孤女" 出现在 Infobox 中
**修复**: 取第一个括号/逗号前的文字作为名字

### ❌ 子嗣字段污染
**现象**: "李渊修、窦氏生）、李渊平" 混入非人名文本
**修复**: 只保留 ≤6 字符且不含"生""出""过继"和括号的名字

### ❌ 分类溢出
**现象**: 整段家谱文本出现在 `[[Category:]]` 标签中
**修复**: 限制 branch 字段为 2-3 字符匹配（如"伯脉"），字辈 ≤2 字符

### ❌ Markdown 残留
**现象**: `---` 分隔线和 `###` 标题在 wiki 页面中显示为原始文本
**修复**: `###` → `===`（wiki 三级标题），`---` → 删除

### ❌ NotebookLM 噪声
**现象**: "7维度自检"和"原文引用汇总"等自动生成内容进入页面
**修复**: 跳过包含"自检""维度""引用汇总"关键词的章节

### ❌ 身份字段混入性格
**现象**: "隐忍自保" 出现在身份字段
**修复**: 过滤长度 >4 或包含性格描述词的条目

---

## anydev 环境

### ❌ agent init 不支持 VM 类型
**现象**: `any dev env agent init -e evnIns-xxx` → "不支持的环境类型: vm"
**原因**: anydev agent 只支持 cvm（容器）类型，不支持 vm（虚拟机）
**解决**: VM 类型直接用 SSH 操作，不走 agent

---

## Nginx 配置

### 正确的 proxy_pass 写法
```nginx
# 注意: proxy_pass URL 末尾的路径必须与 location 完全对应
location ^~ /api.php {
    proxy_pass http://127.0.0.1:8081/api.php;  # ✅ 正确
}

location ^~ /wiki/ {
    proxy_pass http://127.0.0.1:8081/wiki/;    # ✅ 路径对齐
}
```

### nginx 修改后必须 test + reload
```bash
nginx -t && nginx -s reload
```

---

## 模板渲染

### ❌ `{{#if:}}` 和 `{{{参数}}}` 原样输出为乱码
**现象**: Infobox 模板显示原始 wikitext `{{#if:|[[Category:{{{族系}}}角色]]|}}`
**原因**: MW 1.42 Docker 镜像虽然自带 `ParserFunctions` 扩展，但**默认未启用**
**修复**:
```php
// LocalSettings.php
wfLoadExtension( "ParserFunctions" );
$wgPFEnableStringFunctions = true;
```
**重要**: 修改后需要 purge 所有页面缓存：
```python
# 通过 API 批量 purge
s.post(API, data={'action':'purge','titles':'Page1|Page2|...','format':'json'})
```
或用 maintenance 脚本：
```bash
docker exec mediawiki php /var/www/html/maintenance/run.php purgeParserCache --age 0
```

---

## 图片上传

### ❌ `Could not open lock file for "mwstore://local-backend/local-public/..."`
**现象**: API 上传图片全部失败，报文件锁错误
**原因**: MW 容器内 `/var/www/html/images/` 目录权限不正确，Apache 以 www-data 运行但目录属于 root
**修复**:
```bash
docker exec mediawiki chown -R www-data:www-data /var/www/html/images
docker exec mediawiki chmod -R 775 /var/www/html/images
```

### ❌ PHP upload_max_filesize 太小 (默认 2M)
**修复**: 创建 `/usr/local/etc/php/conf.d/uploads.ini`:
```ini
upload_max_filesize = 50M
post_max_size = 55M
memory_limit = 512M
```
然后 `docker restart mediawiki`

---

## SMW 扩展

### ❌ 容器重启后 503 `ERROR_SCHEMA_INVALID_KEY`
**现象**: 安装 SMW 后重启容器，所有页面返回 503 + SMW 错误页面
**原因**: SMW 需要在每次 schema 变化或首次启动后运行 setupStore
**修复**:
```bash
docker exec mediawiki php /var/www/html/extensions/SemanticMediaWiki/maintenance/setupStore.php
```
