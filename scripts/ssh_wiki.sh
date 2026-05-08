#!/bin/bash
# 快速 SSH 连接 Wiki CVM
# 端口 36000（非标准22），通过 IOA/anydev 管理
ssh -o StrictHostKeyChecking=no -p 36000 root@21.214.75.44 "$@"
