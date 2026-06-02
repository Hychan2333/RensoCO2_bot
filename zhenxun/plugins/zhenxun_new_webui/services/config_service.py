"""配置服务"""

from pathlib import Path

import yaml

from zhenxun.configs.config import Config as gConfig
from zhenxun.utils._restart_utils import request_restart

from ..exceptions import ConfigException, ValidationException
from ..models.config import (
    ConfigSaveRequest,
    EnvFileContent,
    YamlConfigContent,
)


class ConfigService:
    """配置服务"""

    @staticmethod
    def get_root_dir() -> Path:
        """获取根目录"""
        return Path().resolve()

    @staticmethod
    def _validate_env_name(name: str) -> None:
        """验证 .env 文件名称"""
        if not (name == ".env" or name.startswith(".env.")):
            raise ValidationException("只允许读取 .env 文件")

    @staticmethod
    def parse_env_file(name: str) -> EnvFileContent:
        """解析环境变量文件"""
        root_dir = ConfigService.get_root_dir()
        ConfigService._validate_env_name(name)

        validated_path = root_dir / name
        if not validated_path.name.startswith(".env"):
            raise ValidationException("只允许读取 .env 文件")

        if not validated_path.exists():
            raise ConfigException("文件不存在")

        try:
            content = validated_path.read_text(encoding="utf-8")
            return EnvFileContent(name=name, content=content)
        except Exception as e:
            raise ConfigException(f"解析环境变量文件失败：{e!s}")

    @staticmethod
    def save_env_file(request: ConfigSaveRequest) -> bool:
        """保存环境变量文件"""
        root_dir = ConfigService.get_root_dir()
        ConfigService._validate_env_name(request.name)

        validated_path = root_dir / request.name
        if not validated_path.name.startswith(".env"):
            raise ValidationException("只允许保存 .env 文件")

        try:
            validated_path.write_text(request.content, encoding="utf-8")
            return True
        except Exception as e:
            raise ConfigException(f"保存环境变量文件失败：{e!s}")

    @staticmethod
    def read_yaml() -> YamlConfigContent:
        """读取 config.yaml 配置文件"""
        root_dir = ConfigService.get_root_dir()
        validated_path = root_dir / "data" / "config.yaml"

        if not validated_path.exists():
            raise ConfigException("文件不存在")

        try:
            content = validated_path.read_text(encoding="utf-8")
            return YamlConfigContent(file_path=str(validated_path), content=content)
        except Exception as e:
            raise ConfigException(f"读取 YAML 文件失败：{e!s}")

    @staticmethod
    def save_yaml(content: str) -> bool:
        """保存 config.yaml 配置文件"""
        root_dir = ConfigService.get_root_dir()
        validated_path = root_dir / "data" / "config.yaml"

        try:
            yaml.safe_load(content)
            validated_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            raise ConfigException(f"保存 YAML 文件失败：{e!s}")

    @staticmethod
    def get_config_value(module: str, key: str) -> str | None:
        """获取配置值"""
        return gConfig.get_config(module, key)

    @staticmethod
    def set_config_value(module: str, key: str, value: str) -> bool:
        """设置配置值"""
        try:
            converted_value = ConfigService._convert_config_value(value)
            gConfig.set_config(module, key, converted_value, auto_save=True)
            return True
        except Exception:
            return False

    @staticmethod
    def batch_set_plugin_configs(module: str, configs: dict[str, str]) -> bool:
        """批量设置插件配置"""
        all_success = True
        for key, value in configs.items():
            try:
                converted_value = ConfigService._convert_config_value(value)
                gConfig.set_config(module, key, converted_value, auto_save=True)
            except Exception:
                all_success = False
        return all_success

    @staticmethod
    def _convert_config_value(value: str) -> bool | int | float | list | dict | str:
        """转换配置值为适当的类型"""
        # 布尔类型
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # 整数类型
        try:
            return int(value)
        except ValueError:
            pass

        # 浮点类型
        try:
            return float(value)
        except ValueError:
            pass

        # JSON 数组/对象
        if value.startswith("[") or value.startswith("{"):
            try:
                import json

                return json.loads(value)
            except Exception:
                pass

        return value

    @staticmethod
    async def restart_bot() -> bool:
        """重启 Bot"""
        ok, message = await request_restart("webui.config")
        if not ok:
            raise ConfigException(message)
        return True
