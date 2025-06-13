import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理类"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_file = "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "api_keys": {
                "deepseek": "",
                "qwen": ""
            },
            "default_model": {
                "deepseek": "deepseek-chat",
                "qwen": "qwen-turbo"
            },
            "export_path": "exports",
            "schema_path": "schemas"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有必要的字段都存在
                    return {**default_config, **config}
            except Exception as e:
                print(f"加载配置文件失败：{str(e)}")
                return default_config
        return default_config
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存配置文件失败：{str(e)}")
    
    def get_api_key(self, model_type: str) -> str:
        """获取指定模型的API密钥"""
        return self.config["api_keys"].get(model_type, "")
    
    def save_api_key(self, model_type: str, api_key: str) -> None:
        """保存API密钥"""
        if model_type not in ["deepseek", "qwen"]:
            raise ValueError("不支持的模型类型")
        
        self.config["api_keys"][model_type] = api_key
        self._save_config()
    
    def get_default_model(self, model_type: str) -> str:
        """获取指定类型的默认模型"""
        return self.config["default_model"].get(model_type, "")
    
    def set_default_model(self, model_type: str, model: str) -> None:
        """设置默认模型"""
        if model_type not in ["deepseek", "qwen"]:
            raise ValueError("不支持的模型类型")
        
        self.config["default_model"][model_type] = model
        self._save_config()
    
    def get_export_path(self) -> str:
        """获取导出文件路径"""
        path = self.config.get("export_path", "exports")
        os.makedirs(path, exist_ok=True)
        return path
    
    def set_export_path(self, path: str) -> None:
        """设置导出文件路径"""
        if not path:
            raise ValueError("导出路径不能为空")
        
        self.config["export_path"] = path
        os.makedirs(path, exist_ok=True)
        self._save_config()
    
    def get_schema_path(self) -> str:
        """获取Schema文件路径"""
        path = self.config.get("schema_path", "schemas")
        os.makedirs(path, exist_ok=True)
        return path
    
    def set_schema_path(self, path: str) -> None:
        """设置Schema文件路径"""
        if not path:
            raise ValueError("Schema路径不能为空")
        
        self.config["schema_path"] = path
        os.makedirs(path, exist_ok=True)
        self._save_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        if not isinstance(new_config, dict):
            raise ValueError("配置必须是字典类型")
        
        self.config.update(new_config)
        self._save_config()
    
    def reset_config(self) -> None:
        """重置配置为默认值"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self.config = self._load_config()
        self._save_config() 