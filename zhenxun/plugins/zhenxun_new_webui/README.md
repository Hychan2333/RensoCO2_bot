# WebUI Next 后端重构实施完成报告

## 已完成的工作

### 第一阶段：基础设施搭建 ✅

1. **创建 `web_ui_next` 目录结构**
   - 统一的响应模型 (`responses.py`)
   - 自定义异常类 (`exceptions.py`)
   - 依赖注入系统 (`dependencies.py`)
   - 工具函数：
     - `formatters.py`: 格式化文件大小、时间、运行时长等
     - `path_validator.py`: 安全的路径验证
     - `security.py`: JWT token 创建和验证

2. **创建模型层 (`models/`)**
   - `common.py`: 公共模型
   - `auth.py`: 认证相关模型
   - `system.py`: 系统状态模型
   - `file.py`: 文件管理模型
   - `config.py`: 配置管理模型
   - `plugin.py`: 插件管理模型
   - `dashboard.py`: 仪表盘模型
   - `database.py`: 数据库模型

### 第二阶段：核心服务层实现 ✅

1. **`auth_service.py`**: 认证服务 - 登录、token 验证
2. **`system_service.py`**: 系统服务 - 系统状态、健康评估、Bot 状态
3. **`file_service.py`**: 文件服务 - 文件列表、读写、删除、重命名
4. **`config_service.py`**: 配置服务 - 环境变量和 YAML 解析
5. **`plugin_service.py`**: 插件服务 - 插件列表、状态切换、配置
6. **`dashboard_service.py`**: 仪表盘服务 - 概览、统计、快捷操作
7. **`main_service.py`**: 主页服务 - Bot 状态、统计、活跃群组
8. **`database_service.py`**: 数据库服务 - 表操作、SQL 执行
9. **`log_service.py`**: 日志服务 - 日志存储和订阅

### 第三阶段：路由层实现 ✅

1. **`routers/auth.py`**: 登录、token 验证、刷新
2. **`routers/system.py`**: 系统状态、健康检查、网络检查
3. **`routers/file.py`**: 文件列表、读写、删除、重命名、创建
4. **`routers/config.py`**: 环境变量和 YAML 配置读写
5. **`routers/plugin.py`**: 插件列表、搜索、过滤、状态切换
6. **`routers/dashboard.py`**: 仪表盘数据
7. **`routers/main.py`**: 主页数据、统计、活跃群组
8. **`routers/database.py`**: 表列表、表数据、SQL 执行
9. **`routers/websocket.py`**: 实时日志、实时状态推送、实时聊天消息

### 第四阶段：前端 API 客户端 ✅

1. **类型定义 (`types/api-next.types.ts`)**
   - 统一的 APIResponse 响应类型
   - 所有数据模型的 TypeScript 定义

2. **API 客户端 (`utils/api-next/`)**
   - `client.ts`: 统一的 axios 客户端和 WebSocket 基础 URL
   - `auth.ts`: 认证接口
   - `system.ts`: 系统接口
   - `dashboard.ts`: 仪表盘接口
   - `plugin.ts`: 插件接口
   - `file.ts`: 文件接口
   - `config.ts`: 配置接口
   - `database.ts`: 数据库接口
   - `main.ts`: 主页接口
   - `websocket-logs.ts`: 日志 WebSocket
   - `websocket-chat.ts`: 聊天 WebSocket

## 架构改进

### 1. 统一接口路径
- HTTP API: `/zhenxun/api/v1`
- WebSocket API: `/zhenxun/ws/v1`

### 2. 统一响应格式
```typescript
interface APIResponse<T> {
    success: boolean  // 替代 suc
    message: string   // 替代 info
    code: number      // 标准 HTTP 状态码
    data: T | null
}
```

### 3. 统一异常处理
- `APIException`: 基类
- `ValidationException`: 参数验证失败 (400)
- `AuthenticationException`: 认证失败 (401)
- `PermissionException`: 权限不足 (403)
- `NotFoundException`: 资源不存在 (404)
- `SystemException`: 系统错误 (500)
- `FileException`: 文件操作失败
- `ConfigException`: 配置操作失败

### 4. 依赖注入
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def require_auth(user: User = Depends(get_current_user)) -> User
```

### 5. 服务层抽象
- 路由层只负责参数验证和响应返回
- 业务逻辑全部移到 Service 层
- 便于单元测试

### 6. 前端逻辑迁移到后端

#### Dashboard.vue 需要修改的部分
- `checkSystemHealth()` → 后端 `/system/health` 返回健康状态
- `uptimeFormatted` → 后端直接返回 `uptime_formatted`

#### Plugin.vue 需要修改的部分
- 本地搜索过滤 → 后端提供 `search`, `status`, `type` 参数
- `filteredPlugins` → 直接使用后端返回的过滤结果
- 添加分页支持 → 后端分页，返回 `total`, `page`, `page_size`

#### Files.vue 需要修改的部分
- 路径拼接逻辑 → 后端返回 `path` 和 `parent`
- `pathHistory` → 后端返回 `path_segments` 面包屑
- `formatFileSize`, `formatTime` → 后端返回格式化好的字符串

#### Settings.vue 需要修改的部分
- `parseEnvToForm` → 后端 `/config/env/{file}` 返回结构化数据
- `formToEnv` → 后端 `/config/env/{file}` 接收结构化数据
- `parseConfigToForm` → 后端 `/config/yaml` 返回结构化数据

## 复用现有服务

| WebUI 功能 | 复用服务 | 位置 |
|-----------|---------|------|
| 系统状态监控 | 使用 psutil 直接实现 | - |
| 数据访问 | 直接使用 Tortoise 模型 | `models/` |
| 平台操作 | `PlatformUtils` | `zhenxun/utils/platform.py` |
| 日志记录 | `logger` | `zhenxun/services/log.py` |

## 使用方法

### 前端使用新 API 客户端

```typescript
import { authApi, dashboardApi, systemApi } from '@/utils/api-next'

// 登录
const response = await authApi.login({ username: 'admin', password: 'password' })
if (response.success) {
    auth.setAuthState(true)
    auth.setAuthToken(response.data.access_token)
}

// 获取仪表盘数据
const dashboard = await dashboardApi.getDashboard()
console.log(dashboard.data.overview)

// 获取系统健康状态
const health = await systemApi.getHealth()
console.log(health.data.status) // 'healthy' | 'warning' | 'error'
```

### WebSocket 连接

```typescript
import { connectLogsWebSocket, onLogMessage } from '@/utils/api-next'

// 连接日志 WebSocket
connectLogsWebSocket()

// 订阅日志消息
const unsubscribe = onLogMessage((log) => {
    console.log(`${log.timestamp}: ${log.message}`)
})

// 取消订阅
unsubscribe()
```

## 后续工作

### 前端适配 (Task 5)

1. **Dashboard.vue**
   - 使用后端返回的健康状态
   - 移除本地健康检查逻辑

2. **Plugin.vue**
   - 使用后端分页和过滤
   - 移除本地搜索过滤逻辑

3. **Files.vue**
   - 使用后端返回的面包屑导航
   - 移除本地路径拼接逻辑

4. **Settings.vue**
   - 使用后端解析的结构化配置数据
   - 移除本地解析逻辑

### 测试验证

1. 启动 Bot，验证新后端是否正常启动
2. 访问 FastAPI 文档 `/docs` 验证接口定义
3. 测试登录、系统状态、文件管理等核心功能
4. 测试 WebSocket 连接

## 注意事项

1. 旧 `web_ui` 代码保留，两套系统可同时运行
2. 新旧后端使用相同的配置项 (`web-ui` 模块)
3. 新后端 API 路径为 `/zhenxun/api/v1`，旧后端为 `/zhenxun/api`
4. 前端需要导入新的 API 客户端 `utils/api-next` 来使用新后端
