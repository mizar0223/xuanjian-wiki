#!/bin/bash
# 快速 SSH 连接 Wiki 服务器（9433.com.cn 私有云）
# 默认端口 22，root 用户，使用 forAI.pem 密钥
ssh -o StrictHostKeyChecking=no -i /Users/leoshi/WorkBuddy/2026-05-15-task-13/forAI.pem root@114.132.222.8 "$@"
