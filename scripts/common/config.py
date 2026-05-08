from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / 'config.yaml'


def _parse_scalar(value):
    value = value.strip()
    if not value:
        return ''
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() in {'true', 'false'}:
        return value.lower() == 'true'
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _load_simple_yaml(path):
    """解析本项目 config.yaml 当前使用的两级键值结构。"""
    data = {}
    current_section = None
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.split('#', 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(' '):
            key, _, value = line.partition(':')
            key = key.strip()
            if not key:
                continue
            if value.strip():
                data[key] = _parse_scalar(value)
                current_section = None
            else:
                data[key] = {}
                current_section = key
            continue
        if current_section and line.startswith('  ') and not line.lstrip().startswith('-'):
            key, _, value = line.strip().partition(':')
            if key:
                data[current_section][key] = _parse_scalar(value)
    return data


def load_config(path=CONFIG_PATH):
    try:
        import yaml
    except ImportError:
        return _load_simple_yaml(path)
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


class AppConfig:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = Path(config_path)
        self.project_root = PROJECT_ROOT
        self.raw = load_config(self.config_path)

    def get(self, *keys, default=None):
        value = self.raw
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

    def resolve_project_path(self, value):
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    @property
    def wiki_api(self):
        return os.getenv('WIKI_API') or self.get('wiki', 'api')

    @property
    def wiki_url(self):
        return os.getenv('WIKI_URL') or self.get('wiki', 'url', default='')

    @property
    def wiki_user(self):
        return os.getenv('WIKI_USER') or self.get('wiki', 'user', default='WikiAdmin')

    @property
    def wiki_password(self):
        return os.getenv('WIKI_PASS') or os.getenv('WIKI_PASSWORD') or self.get('wiki', 'password', default='')

    @property
    def pages_dir(self):
        return self.resolve_project_path(self.get('paths', 'pages_dir', default='pages'))

    @property
    def data_base_dir(self):
        return Path(self.get('data_sources', 'base_dir', default=str(self.project_root)))

    def data_source_path(self, key, **format_values):
        template = self.get('data_sources', key)
        if not template:
            raise KeyError(f'config.yaml 未配置 data_sources.{key}')
        relative = template.format(**format_values)
        path = Path(relative)
        if not path.is_absolute():
            path = self.data_base_dir / path
        return path

    @property
    def xianji_json_path(self):
        return self.resolve_project_path(
            self.get('paths', 'xianji_json', default='资料库 - 神通/04_参考权威/玄鉴仙族_五德位业体系_结构化.json')
        )

    @property
    def xianji_authority_path(self):
        return self.resolve_project_path(
            self.get('paths', 'xianji_authority', default='资料库 - 神通/04_参考权威/玄鉴仙族_神通仙基汇总.md')
        )


def require_wiki_password(config):
    if not config.wiki_password:
        raise RuntimeError('缺少 Wiki 密码，请通过环境变量 WIKI_PASS 或 WIKI_PASSWORD 设置')
    return config.wiki_password
