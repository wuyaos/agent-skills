# MoviePilot V2 插件开发指南

本文档说明如何开发适用于 MoviePilot V2 的插件，并尽量以当前 `MoviePilot` 与 `MoviePilot-Frontend` 主仓库的真实实现为准，而不是停留在早期兼容阶段的概念说明。

关联阅读：

- [仓库指南](./Repository_Guide.md)
- [FAQ 索引](./FAQ.md)
- [MoviePilot 前端模块联邦开发指南](https://github.com/jxxghp/MoviePilot-Frontend/blob/v2/docs/module-federation-guide.md)

## 1. 先理解 V2 插件的运行模型

V2 插件始终运行在 `MoviePilot` 后端宿主内，当前插件仓库只提供：

- 插件源码
- 插件市场索引
- 插件图标
- 插件文档

V2 插件的 UI 则有两种模式：

- `vuetify`：插件返回 JSON 配置，由 `MoviePilot-Frontend` 负责渲染
- `vue`：插件提供联邦远程组件，由前端动态加载

因此，开发一个 V2 插件通常至少会涉及三个部分：

1. 本仓库中的插件实现与元数据
2. `MoviePilot` 中的插件宿主能力
3. `MoviePilot-Frontend` 中的渲染与加载逻辑

## 2. V2 的版本选择规则

MoviePilot 处理插件版本时，当前逻辑可以总结为：

1. 宿主先根据当前版本标识优先读取 `package.v2.json`
2. 若目标插件不在 `package.v2.json` 中，再检查 `package.json`
3. `package.json` 中只有显式声明了 `"v2": true` 的插件，才会被视为 V2 兼容插件

建议按下列方式选型：

- **V2 专用实现**：放在 `plugins.v2/<plugin_id_lower>/`，元数据写入 `package.v2.json`
- **单实现跨版本兼容**：代码继续放在 `plugins/<plugin_id_lower>/`，在 `package.json` 中声明 `"v2": true`
- **V1/V2 差异已经很大**：不要继续强行共用目录，直接拆到 `plugins.v2/`

## 3. 最小 V2 插件骨架

一个最小可运行的 V2 插件通常如下：

```text
plugins.v2/
└── myplugin/
    ├── __init__.py
    ├── requirements.txt          # 可选，只有插件有额外依赖时才需要
    └── README.md                 # 可选，插件自己的说明文档
```

`__init__.py` 示例：

```python
from typing import Any, Dict, List, Tuple

from app.plugins import _PluginBase


class MyPlugin(_PluginBase):
    plugin_name = "我的插件"
    plugin_desc = "一个最小可运行的 V2 插件示例。"
    plugin_icon = "Moviepilot_A.png"
    plugin_version = "1.0.0"
    plugin_author = "your-name"
    author_url = "https://github.com/your-name"
    plugin_config_prefix = "myplugin_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
    _message = "插件尚未初始化"

    def init_plugin(self, config: dict = None):
        config = config or {}
        self._enabled = bool(config.get("enabled"))
        self._message = config.get("message") or "Hello MoviePilot"

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "enabled", "label": "启用插件"},
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 8},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {"model": "message", "label": "展示文本"},
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ], {
            "enabled": False,
            "message": "Hello MoviePilot",
        }

    def get_page(self) -> List[dict]:
        return [
            {
                "component": "VAlert",
                "props": {"type": "info", "variant": "tonal", "text": self._message},
            }
        ]

    def stop_service(self):
        pass
```

## 4. `_PluginBase` 的核心能力

### 4.1 必选方法

- `init_plugin(self, config: dict = None)`
- `get_state(self) -> bool`
- `get_api(self) -> List[dict]`
- `get_form(self) -> Tuple[page_json, model]`
- `get_page(self) -> List[dict] | None`
- `stop_service(self)`

### 4.2 常用可选方法

- `get_command()` — 远程命令
- `get_service()` — 公共服务/定时任务
- `get_dashboard()` / `get_dashboard_meta()` — 仪表板
- `get_render_mode()` — 选择 vuetify / vue
- `get_module()` — 重载系统模块
- `get_actions()` — 工作流动作
- `get_agent_tools()` — 智能体工具
- `get_sidebar_nav()` — Vue 全页侧栏入口

### 4.3 基类辅助能力

- `get_config()` / `update_config()` — 读写插件配置
- `get_data_path()` — 插件数据目录
- `save_data()` / `get_data()` / `del_data()` — 持久化数据
- `post_message()` — 通知
- `self.chain` — 链式能力入口

## 5. 配置、数据与分身兼容

- 配置：`init_plugin` 读取，`update_config` 保存
- 数据：小数据用 `save_data/get_data`，文件用 `get_data_path()`
- 分身：不要硬编码插件 ID，优先用 `self.__class__.__name__`

## 6. V2 常见能力面

### 6.1 远程命令 `get_command()`

```python
@staticmethod
def get_command() -> List[Dict[str, Any]]:
    return [{
        "cmd": "/my_plugin_run",
        "event": EventType.PluginAction,
        "desc": "执行我的插件",
        "data": {"action": "my_plugin_run"},
    }]

@eventmanager.register(EventType.PluginAction)
def run_command(self, event: Event):
    if event.event_data.get("action") != "my_plugin_run":
        return
    # 业务逻辑
```

### 6.2 插件 API `get_api()`

路由注册到 `/api/v1/plugin/<PluginID>/<path>`。`auth` 支持 `bear`（前端）和 `apikey`（外部）。

### 6.3 公共服务 `get_service()`

```python
def get_service(self) -> List[Dict[str, Any]]:
    if not self.get_state():
        return []
    return [{
        "id": "MyPlugin.Refresh",
        "name": "我的插件定时刷新",
        "trigger": CronTrigger.from_crontab("0 */6 * * *"),
        "func": self.refresh,
        "kwargs": {},
    }]
```

### 6.4 仪表板

单仪表板实现 `get_dashboard()`；多仪表板额外实现 `get_dashboard_meta()`。

### 6.5 工作流动作 `get_actions()`

动作函数第一个参数固定为 `ActionContent`。

### 6.6 系统模块重载 `get_module()`

侵入性强，仅在需要扩展宿主链路时使用。

### 6.7 智能体工具 `get_agent_tools()`

工具类继承 `MoviePilotTool`，实现 `run()` 方法。参考 `plugins.v2/lexiannot/agenttool.py`。

## 7. 渲染模式

### 7.1 Vuetify JSON 模式（默认）

- `get_form()` 返回"页面 JSON + 默认模型"
- `get_page()` 返回页面 JSON
- `props.model` 等效于 `v-model`
- 配置页支持 `{{ ... }}` 表达式与 `onxxx` 事件

### 7.2 Vue 联邦模式

```python
def get_render_mode(self) -> Tuple[str, str]:
    return "vue", "dist/assets"
```

### 7.3 侧栏全页入口

只有 Vue 模式插件才会被主界面侧栏聚合。`section` 只接受：`start`、`discovery`、`subscribe`、`organize`、`system`。

## 8. 调试与校验

### 8.1 Python 层

```bash
python3 -m py_compile plugins.v2/myplugin/__init__.py
python3 -m compileall plugins.v2/myplugin
git diff --check
```

### 8.2 CLI 调试

```bash
moviepilot start / stop / restart / status
moviepilot logs                        # 后端日志
moviepilot logs --frontend             # 前端日志
moviepilot scheduler list              # 列出定时任务
moviepilot scheduler run <service_id>  # 手动触发
moviepilot tool list / run <tool>      # 工具调试
moviepilot config list / get / set     # 配置管理
```

### 8.3 API 调试

```bash
# 获取 Token
TOKEN=$(curl -s -X POST "http://HOST:PORT/api/v1/login/access-token" \
  -d "username=admin&password=<PWD>" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 查看已安装插件
curl -s "http://HOST:PORT/api/v1/plugin/" -H "Authorization: Bearer $TOKEN"

# 强制重装插件
curl -s "http://HOST:PORT/api/v1/plugin/install/<ClassName>?repo_url=<URL>&force=true" \
  -H "Authorization: Bearer $TOKEN"

# 查看插件日志
curl -s "http://HOST:PORT/api/v1/system/logging?logfile=plugins/<pid>.log&length=-1" \
  -H "Authorization: Bearer $TOKEN"
```

### 8.4 插件日志注意事项

- Logger 按插件目录名写文件：`{LOG_PATH}/plugins/{plugin_id}.log`
- `/system/logging` endpoint 文件不存在直接 **404**，不会自动创建
- Logger 的 RotatingFileHandler 在首次写日志时才懒创建文件
- 前端"查看日志"按钮拼接：`plugins/${plugin.id.toLowerCase()}.log`
- **最佳实践**：`init_plugin()` 中预创建日志文件避免首次 404

## 9. 发布清单

1. 插件目录在 `plugins/` 或 `plugins.v2/` 下位置正确
2. 目录名与类名小写一致
3. 元数据已写入正确的索引文件
4. 索引里的 `version` 与代码里的 `plugin_version` 一致
5. `history` 已补齐本次变更说明
6. 若使用 Release 分发，条目已声明 `"release": true`
7. Python 代码完成最小语法校验
8. 若有 Vue 远程组件，构建产物已更新

## 10. 宿主源码参考

| 问题 | 文件 |
|------|------|
| 插件加载 | `MoviePilot/app/core/plugin.py` |
| API 注册 | `MoviePilot/app/api/endpoints/plugin.py` |
| _PluginBase | `MoviePilot/app/plugins/__init__.py` |
| Vue 联邦 | `MoviePilot-Frontend/src/utils/federationLoader.ts` |
| 模块联邦指南 | `MoviePilot-Frontend/docs/module-federation-guide.md` |
| 日志 endpoint | `MoviePilot/app/api/endpoints/system.py` |
| Logger 实现 | `MoviePilot/app/log.py` |
| CLI 文档 | [MoviePilot-Wiki/cli.md](https://github.com/jxxghp/MoviePilot-Wiki/blob/main/cli.md) |
