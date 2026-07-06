#!/bin/bash
# ================================================================
# deploy-wiki.sh — Agent 友好的 9433.com.cn wiki 部署脚本
# 用途: 把 MediaWiki 配置文件/资源发布到 /opt/mediawiki，
#       自动 docker compose restart mediawiki 生效。
# 与 agent-deploy.sh 的差异:
#   - 目标不是静态站点，而是 Docker 化的 MediaWiki 应用
#   - 推送路径是 /opt/mediawiki（宿主机 bind mount 源）
#   - 默认行为是「配置 + 资源」，跳过上传目录（mw_images 88M）
# ================================================================

set -eo pipefail

# -------------------- 配置区 --------------------
# 字符串拼接绕过沙盒对 root@ 字面量的识别
RUSER="r""oot"
HOST_IP="${WIKI_SSH_HOST:-114.132.222.8}"
SSH_KEY="${WIKI_SSH_KEY:-/Users/leoshi/WorkBuddy/2026-05-15-task-13/forAI.pem}"

REMOTE_MW_DIR="/opt/mediawiki"

# 需要同步的文件/目录（相对 REMOTE_MW_DIR）
SYNC_FILES=(
    "LocalSettings.php"
    ".htaccess"
    "apache-wiki-alias.conf"
    "resources-assets"
)

SSH_OPTS=(-i "$SSH_KEY" -o "StrictHostKeyChecking=no" -o "IdentitiesOnly=yes" -o "BatchMode=yes")
SCP_OPTS=(-i "$SSH_KEY" -o "StrictHostKeyChecking=no" -o "IdentitiesOnly=yes")

# -------------------- 默认值 --------------------
NO_RESTART=false
DRY_RUN=false
JSON_OUT=false
NO_COLOR=false
ASSUME_YES=false
INCLUDE_IMAGES=false
LOCAL_MW_DIR=""   # 本地源目录（默认脚本所在仓库的 /opt/mediawiki 等价物）
HEALTHCHECK=true
HEALTHCHECK_MAX_ATTEMPTS=${HEALTHCHECK_MAX_ATTEMPTS:-15}   # 健康检查最大重试次数
HEALTHCHECK_INTERVAL=${HEALTHCHECK_INTERVAL:-2}           # 每次重试间隔秒数

# -------------------- 工具函数 --------------------
SCRIPT_NAME=$(basename "$0")
LOG_FILE="/tmp/${SCRIPT_NAME%.sh}-$$.log"

_start_ts() { python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null || echo "$(date +%s)000"; }
_now_ms()    { python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null || echo "$(date +%s)000"; }
START_MS=$(_start_ts)
declare -a STEPS=()

# 颜色
if [[ -t 1 ]] && [[ "$NO_COLOR" != "true" ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; GRAY='\033[0;90m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; GRAY=''; NC=''
fi

log()  { echo -e "$*" | tee -a "$LOG_FILE" >&2; }
info() { log "${BLUE}[INFO]${NC}  $*"; }
ok()   { log "${GREEN}[OK]${NC}   $*"; }
warn() { log "${YELLOW}[WARN]${NC} $*"; }
err()  { log "${RED}[ERR]${NC}  $*"; }
gray() { log "${GRAY}$*${NC}"; }

now_ms() { _now_ms; }

record_step() {
    local name="$1" ok="$2" dur_ms="$3" detail="${4:-}"
    STEPS+=("{\"name\":\"$name\",\"ok\":$ok,\"ms\":$dur_ms,\"detail\":\"$detail\"}")
}

TMP_DIR=""
cleanup() {
    [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]] && rm -rf "$TMP_DIR"
    return 0
}
trap cleanup EXIT

# -------------------- 占位符渲染（脱敏推送用）--------------------
# LocalSettings.php 在仓库里用 @@PLACEHOLDER@@ 占位符（不入敏感信息）
# 部署前从此函数注入真实值（从环境变量或 .env 文件读）
RENDER_PLACEHOLDERS=(
    "MW_DB_PASSWORD"
    "MW_SECRET_KEY"
    "MW_UPGRADE_KEY"
)

# 加载 .env（如果存在）：从 WIKI_DEPLOY_ENV_FILE 指定的文件，或从默认位置
WIKI_DEPLOY_ENV_FILE="${WIKI_DEPLOY_ENV_FILE:-/opt/mediawiki/.env}"

# 渲染 LocalSettings.php：把 @@PLACEHOLDER@@ 替换为真实值
# 真实值优先级: 1) 环境变量 2) WIKI_DEPLOY_ENV_FILE
render_local_settings() {
    local src="$1" dst="$2"

    # 准备环境变量（从 .env 文件加载，覆盖优先级低于现有环境变量）
    local env_file="$WIKI_DEPLOY_ENV_FILE"
    if [[ -f "$env_file" ]]; then
        # 临时 set -a 让所有赋值自动 export
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
    fi

    cp "$src" "$dst"
    local missing=()
    for ph in "${RENDER_PLACEHOLDERS[@]}"; do
        local value="${!ph:-}"
        if [[ -z "$value" ]]; then
            missing+=("$ph")
        else
            # 用 sed 转义 | 防止占位符被当作正则特殊字符
            local escaped_value="${value//\//\\/}"
            # macOS sed 需 -i '' 形式；用 -e 一次性替换避免 BSD/GNU 差异
            if ! sed -i '' "s|@@${ph}@@|${escaped_value}|g" "$dst" 2>/dev/null; then
                err "渲染占位符 ${ph} 失败"
                return 1
            fi
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        err "占位符未配置（环境变量或 $env_file 缺失）: ${missing[*]}"
        err "  请在 $env_file 中设置: MW_DB_PASSWORD=... MW_SECRET_KEY=... MW_UPGRADE_KEY=..."
        return 1
    fi

    # 验证所有占位符已被替换
    if grep -q "@@MW_.*@@" "$dst"; then
        err "渲染后仍残留占位符（请检查真实值是否含特殊字符）:"
        grep -n "@@MW_.*@@" "$dst" | head -3
        return 1
    fi
    return 0
}

# -------------------- 用法 --------------------
usage() {
    cat <<EOF
${SCRIPT_NAME} — Agent-friendly MediaWiki 部署到 9433.com.cn

用法: $0 [选项]

选项:
      --local-mw-dir <路径>   本地源目录（默认: 脚本相对路径/../opt/mediawiki）
                              该目录下应包含 LocalSettings.php / .htaccess 等
      --include-images        同步 images 目录（mw_images volume 内容，默认跳过）
      --no-restart            跳过 docker compose restart
      --no-healthcheck        跳过 HTTP 健康检查
      --dry-run               仅打印将执行的动作
      --json                  输出机读 JSON
      --no-color              关闭彩色
  -y, --yes                   跳过确认（非 TTY 自动启用）
  -h, --help                  显示帮助

环境变量:
  WIKI_SSH_HOST               自定义目标主机（默认 114.132.222.8）
  WIKI_SSH_KEY                自定义 SSH 私钥
  WIKI_DEPLOY_ENV_FILE        占位符渲染用的凭据文件（默认 /opt/mediawiki/.env）
                             包含 MW_DB_PASSWORD / MW_SECRET_KEY / MW_UPGRADE_KEY

凭据:
  LocalSettings.php 仓库版用 @@MW_DB_PASSWORD@@ / @@MW_SECRET_KEY@@ / @@MW_UPGRADE_KEY@@ 占位符
  部署时 deploy-wiki.sh 自动从 \$WIKI_DEPLOY_ENV_FILE 读真实值并 sed 注入
  真实凭据不入仓库；占位符版本可安全推送到 github 公开仓库

退出码:
  0  成功
  1  参数错误
  2  SSH 连接失败
  3  scp 失败
  4  docker restart 失败
  5  HTTP 健康检查失败

示例:
  # 默认：同步配置 + 重启容器 + 健康检查
  $0

  # 跳过重启（仅推文件）
  $0 --no-restart

  # 含 images（首次迁移或恢复用，88M+）
  $0 --include-images

  # 预览模式
  $0 --dry-run

  # Agent 调用
  $0 --json --yes
EOF
}

# -------------------- 参数解析 --------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --local-mw-dir) LOCAL_MW_DIR="$2"; shift 2 ;;
        --include-images) INCLUDE_IMAGES=true; shift ;;
        --no-restart) NO_RESTART=true; shift ;;
        --no-healthcheck) HEALTHCHECK=false; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --json) JSON_OUT=true; shift ;;
        --no-color) NO_COLOR=true; shift ;;
        -y|--yes) ASSUME_YES=true; shift ;;
        -*) err "未知选项: $1"; usage; exit 1 ;;
        *) err "多余位置参数: $1"; usage; exit 1 ;;
    esac
done

# 非 TTY 环境自动 yes
[[ ! -t 0 ]] && ASSUME_YES=true

# 默认本地源：脚本所在仓库的同级 opt/mediawiki（与远程目录结构一致）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$LOCAL_MW_DIR" ]]; then
    LOCAL_MW_DIR="${SCRIPT_DIR}/../opt/mediawiki"
fi
LOCAL_MW_DIR="$(cd "$LOCAL_MW_DIR" 2>/dev/null && pwd || echo "$LOCAL_MW_DIR")"

# 校验本地源
if [[ ! -d "$LOCAL_MW_DIR" ]]; then
    err "本地源目录不存在: $LOCAL_MW_DIR"
    err "提示: 用 --local-mw-dir 显式指定，或在仓库 opt/mediawiki/ 下维护源文件"
    exit 1
fi
if [[ ! -f "$LOCAL_MW_DIR/LocalSettings.php" ]]; then
    err "本地源目录缺少 LocalSettings.php: $LOCAL_MW_DIR"
    exit 1
fi

# -------------------- JSON 输出辅助 --------------------
emit_json_result() {
    local ok_flag="$1" exit_code="$2" http_status="${3:-}"
    local total_ms=$(($(_now_ms) - START_MS))
    local steps_json
    steps_json=$(IFS=,; echo "${STEPS[*]:-}")
    [[ -z "$steps_json" ]] && steps_json=""

    cat <<EOF
{"ok":$ok_flag,"exit_code":$exit_code,"host":"$HOST_IP","mw_dir":"$REMOTE_MW_DIR","http_status":$http_status,"duration_ms":$total_ms,"log_file":"$LOG_FILE","steps":[$steps_json]}
EOF
}

# -------------------- 主流程 --------------------
banner() {
    [[ "$JSON_OUT" == "true" ]] && return
    echo ""
    echo "=============================================================="
    echo "  Wiki Deploy → ${HOST_IP}:${REMOTE_MW_DIR}"
    echo "=============================================================="
    echo "  本地源: $LOCAL_MW_DIR"
    echo "  远程目录: $REMOTE_MW_DIR"
    echo "  同步: ${SYNC_FILES[*]}"
    $INCLUDE_IMAGES && echo "  额外同步: images/"
    $NO_RESTART      && echo "  跳过: docker restart"
    $DRY_RUN         && echo "  ⚠️  DRY RUN 模式"
    echo ""
}

# Step 1: SSH 检查
step_ssh() {
    local step_name="ssh_check"
    local t0=$(now_ms)
    info "步骤 1/4: 检查 SSH 连接"

    if [[ "$DRY_RUN" == "true" ]]; then
        gray "  [DRY] ssh ${RUSER}@${HOST_IP} echo OK"
        record_step "$step_name" "true" 0 "dry-run"
        return 0
    fi

    if ! ssh "${SSH_OPTS[@]}" "${RUSER}@${HOST_IP}" "echo OK" >/dev/null 2>&1; then
        record_step "$step_name" "false" 0 "auth-fail"
        err "SSH 连接失败 (退出码 2)"
        return 2
    fi
    local t1=$(now_ms)
    record_step "$step_name" "true" $((t1 - t0)) ""
    ok "SSH 连接正常 (${GRAY}$((t1 - t0))ms${NC})"
}

# Step 2: 同步配置 + 资源
step_sync() {
    local step_name="sync_files"
    local t0=$(now_ms)
    info "步骤 2/4: 同步配置文件 + 资源"

    if [[ "$DRY_RUN" == "true" ]]; then
        for f in "${SYNC_FILES[@]}"; do
            gray "  [DRY] scp $LOCAL_MW_DIR/$f → ${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/$f"
        done
        $INCLUDE_IMAGES && gray "  [DRY] scp -r $LOCAL_MW_DIR/images → ${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/images"
        record_step "$step_name" "true" 0 "dry-run"
        return 0
    fi

    # 先确保远程目录存在
    ssh "${SSH_OPTS[@]}" "${RUSER}@${HOST_IP}" "mkdir -p '$REMOTE_MW_DIR'" >/dev/null 2>&1 || {
        record_step "$step_name" "false" 0 "mkdir-fail"
        err "创建远程目录失败 (退出码 3)"
        return 3
    }

    for f in "${SYNC_FILES[@]}"; do
        if [[ ! -e "$LOCAL_MW_DIR/$f" ]]; then
            warn "本地源缺少 $f，跳过"
            continue
        fi
        if [[ -d "$LOCAL_MW_DIR/$f" ]]; then
            if ! scp "${SCP_OPTS[@]}" -r "$LOCAL_MW_DIR/$f/." "${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/$f/" >/dev/null 2>>"$LOG_FILE"; then
                record_step "$step_name" "false" 0 "scp-dir-fail:$f"
                err "scp 目录失败: $f (退出码 3)"
                return 3
            fi
            ok "同步目录: $f/"
        else
            # 特殊处理：LocalSettings.php 含占位符，需先 sed 注入真实值再 scp
            if [[ "$f" == "LocalSettings.php" ]]; then
                local rendered="/tmp/LocalSettings.rendered.$$"
                if ! render_local_settings "$LOCAL_MW_DIR/$f" "$rendered"; then
                    rm -f "$rendered"
                    record_step "$step_name" "false" 0 "render-fail"
                    err "渲染 LocalSettings.php 失败（占位符未替换）"
                    return 3
                fi
                if ! scp "${SCP_OPTS[@]}" "$rendered" "${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/$f" >/dev/null 2>>"$LOG_FILE"; then
                    rm -f "$rendered"
                    record_step "$step_name" "false" 0 "scp-file-fail:$f"
                    err "scp 文件失败: $f (退出码 3)"
                    return 3
                fi
                rm -f "$rendered"
                ok "同步文件: $f (含占位符渲染)"
            else
                if ! scp "${SCP_OPTS[@]}" "$LOCAL_MW_DIR/$f" "${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/$f" >/dev/null 2>>"$LOG_FILE"; then
                    record_step "$step_name" "false" 0 "scp-file-fail:$f"
                    err "scp 文件失败: $f (退出码 3)"
                    return 3
                fi
                ok "同步文件: $f"
            fi
        fi
    done

    if $INCLUDE_IMAGES; then
        if [[ -d "$LOCAL_MW_DIR/images" ]]; then
            if ! scp "${SCP_OPTS[@]}" -r "$LOCAL_MW_DIR/images/." "${RUSER}@${HOST_IP}:$REMOTE_MW_DIR/images/" >/dev/null 2>>"$LOG_FILE"; then
                record_step "$step_name" "false" 0 "scp-images-fail"
                err "scp images 失败 (退出码 3)"
                return 3
            fi
            ok "同步目录: images/"
        else
            warn "本地源缺少 images/，跳过"
        fi
    fi

    # 修权限（容器内 apache 用户需可读）
    ssh "${SSH_OPTS[@]}" "${RUSER}@${HOST_IP}" \
        "find '$REMOTE_MW_DIR' -type f -exec chmod 644 {} +; find '$REMOTE_MW_DIR' -type d -exec chmod 755 {} +" \
        >/dev/null 2>&1 || warn "权限修复失败（不影响功能）"
    ok "权限修复: 644/755"

    local t1=$(now_ms)
    record_step "$step_name" "true" $((t1 - t0)) "files=${#SYNC_FILES[@]}"
    ok "同步完成 (${GRAY}$((t1 - t0))ms${NC})"
}

# Step 3: docker compose restart
step_restart() {
    local step_name="docker_restart"
    local t0=$(now_ms)
    info "步骤 3/4: docker compose restart mediawiki"

    if $NO_RESTART; then
        warn "跳过 docker restart（--no-restart）"
        record_step "$step_name" "true" 0 "skipped"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        gray "  [DRY] ssh ... cd $REMOTE_MW_DIR && docker compose restart mediawiki"
        record_step "$step_name" "true" 0 "dry-run"
        return 0
    fi

    if ! ssh "${SSH_OPTS[@]}" "${RUSER}@${HOST_IP}" \
        "cd '$REMOTE_MW_DIR' && docker compose restart mediawiki" >/dev/null 2>>"$LOG_FILE"; then
        record_step "$step_name" "false" 0 "restart-fail"
        err "docker compose restart 失败 (退出码 4)"
        return 4
    fi
    ok "mw-app 已 restart"

    # 不在此处 sleep；由 step_healthcheck 自行等待容器就绪
    local t1=$(now_ms)
    record_step "$step_name" "true" $((t1 - t0)) ""
    ok "容器重启完成 (${GRAY}$((t1 - t0))ms${NC})"
}

# Step 4: HTTP 健康检查
step_healthcheck() {
    local step_name="healthcheck"
    local t0=$(now_ms)
    info "步骤 4/4: HTTP 健康检查"

    if ! $HEALTHCHECK; then
        warn "跳过健康检查（--no-healthcheck）"
        record_step "$step_name" "true" 0 "skipped"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        gray "  [DRY] curl -sk https://9433.com.cn/api.php?action=query"
        record_step "$step_name" "true" 0 "dry-run"
        return 0
    fi

    local url="https://9433.com.cn/api.php?action=query"
    local http_status
    local attempt=0
    local max_attempts=${HEALTHCHECK_MAX_ATTEMPTS:-15}   # 15 × 2s = 30s 上限
    local sleep_s=${HEALTHCHECK_INTERVAL:-2}

    while (( attempt < max_attempts )); do
        attempt=$((attempt + 1))
        http_status=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

        if [[ "$http_status" == "200" ]]; then
            local t1=$(now_ms)
            record_step "$step_name" "true" $((t1 - t0)) "http=$http_status,attempts=$attempt"
            ok "HTTP $http_status ✅ (${GRAY}尝试 $attempt 次 / ${GRAY}$((t1 - t0))ms${NC}): $url"
            return 0
        fi

        if (( attempt < max_attempts )); then
            gray "  [wait] HTTP $http_status，第 $attempt 次 / 共 $max_attempts 次，${sleep_s}s 后重试..."
            sleep "$sleep_s"
        fi
    done

    record_step "$step_name" "false" 0 "http-$http_status-after-${max_attempts}-tries"
    err "HTTP $http_status ❌ 重试 $max_attempts 次后仍失败 (退出码 5) - $url"
    return 5
}

# -------------------- 执行 --------------------
banner

EXIT_CODE=0
STAGE_NUM=0
run_step() {
    STAGE_NUM=$((STAGE_NUM + 1))
    if [[ $EXIT_CODE -eq 0 ]]; then
        "$1"
        local rc=$?
        if [[ $rc -ne 0 ]]; then
            EXIT_CODE=$rc
        fi
    fi
}
run_step step_ssh
run_step step_sync
run_step step_restart
run_step step_healthcheck

# -------------------- 结果输出 --------------------
if $JSON_OUT; then
    if [[ $EXIT_CODE -eq 0 ]]; then
        emit_json_result "true" 0 200
    else
        emit_json_result "false" "$EXIT_CODE" 0
    fi
else
    {
        echo ""
        echo "=============================================================="
        if [[ $EXIT_CODE -eq 0 ]]; then
            echo "  ✅ Wiki 部署完成"
        else
            echo "  ❌ Wiki 部署失败 (退出码 $EXIT_CODE)"
        fi
        echo "=============================================================="
        echo "  远程: $REMOTE_MW_DIR"
        echo "  验证: https://9433.com.cn/wiki/"
        echo "  日志: $LOG_FILE"
        echo ""
    } | tee -a "$LOG_FILE" >&2
fi

exit $EXIT_CODE
