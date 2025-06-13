import requests
import json
from typing import Dict, Any, Optional
from config_manager import ConfigManager

class APIError(Exception):
    """API调用错误"""
    pass

class ModelNotSupportedError(Exception):
    """模型不支持错误"""
    pass

class APIKeyError(Exception):
    """API密钥错误"""
    pass

class APICaller:
    """API调用类"""
    
    def __init__(self):
        """初始化API调用器"""
        self.config = ConfigManager()
        self.models = {
            "deepseek": {
                "name": "DeepSeek",
                "models": {
                    "deepseek-chat": {
                        "name": "DeepSeek Chat",
                        "url": "https://api.deepseek.com/v1/chat/completions",
                        "max_tokens": 4000,
                        "description": "适用于一般对话和简单试题转换"
                    },
                    "deepseek-coder": {
                        "name": "DeepSeek Coder",
                        "url": "https://api.deepseek.com/v1/chat/completions",
                        "max_tokens": 4000,
                        "description": "专注于代码相关的试题转换"
                    }
                }
            },
            "qwen": {
                "name": "Qwen",
                "models": {
                    "qwen-turbo": {
                        "name": "Qwen Turbo",
                        "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        "max_tokens": 2000,
                        "description": "快速响应，适合简单试题"
                    },
                    "qwen-plus": {
                        "name": "Qwen Plus",
                        "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        "max_tokens": 4000,
                        "description": "平衡速度和质量，适合一般试题"
                    },
                    "qwen-max": {
                        "name": "Qwen Max",
                        "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        "max_tokens": 6000,
                        "description": "最高质量，适合复杂试题"
                    }
                }
            }
        }
    
    def _call_deepseek(self, api_key: str, prompt: str, model: str = "deepseek-chat") -> str:
        """调用DeepSeek API"""
        try:
            if model not in self.models["deepseek"]["models"]:
                raise ModelNotSupportedError(f"不支持的DeepSeek模型: {model}")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的试题转换助手，请严格按照要求转换试题格式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # 降低随机性
                "max_tokens": self.models["deepseek"]["models"][model]["max_tokens"]
            }
            
            response = requests.post(
                self.models["deepseek"]["models"][model]["url"],
                headers=headers,
                json=data,
                timeout=30  # 设置超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                raise APIKeyError("DeepSeek API密钥无效")
            else:
                raise APIError(f"DeepSeek API调用失败: {response.text}")
                
        except requests.exceptions.Timeout:
            raise APIError("DeepSeek API调用超时")
        except requests.exceptions.RequestException as e:
            raise APIError(f"DeepSeek API请求错误: {str(e)}")
        except Exception as e:
            raise APIError(f"DeepSeek API调用错误: {str(e)}")
    
    def _call_qwen(self, api_key: str, prompt: str, model: str = "qwen-turbo") -> str:
        """调用Qwen API"""
        try:
            if model not in self.models["qwen"]["models"]:
                raise ModelNotSupportedError(f"不支持的Qwen模型: {model}")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "input": {
                    "messages": [
                        {"role": "system", "content": "你是一个专业的试题转换助手，请严格按照要求转换试题格式。"},
                        {"role": "user", "content": prompt}
                    ]
                },
                "parameters": {
                    "temperature": 0.3,  # 降低随机性
                    "max_tokens": self.models["qwen"]["models"][model]["max_tokens"]
                }
            }
            
            response = requests.post(
                self.models["qwen"]["models"][model]["url"],
                headers=headers,
                json=data,
                timeout=30  # 设置超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["output"]["text"]
            elif response.status_code == 401:
                raise APIKeyError("Qwen API密钥无效")
            else:
                raise APIError(f"Qwen API调用失败: {response.text}")
                
        except requests.exceptions.Timeout:
            raise APIError("Qwen API调用超时")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Qwen API请求错误: {str(e)}")
        except Exception as e:
            raise APIError(f"Qwen API调用错误: {str(e)}")
    
    def call_api(self, model_type: str, api_key: str, prompt: str, model: Optional[str] = None) -> str:
        """调用API"""
        if model_type not in self.models:
            raise ModelNotSupportedError(f"不支持的模型类型: {model_type}")
        
        if not api_key:
            raise APIKeyError("API密钥不能为空")
        
        if model_type == "deepseek":
            model = model or "deepseek-chat"
            return self._call_deepseek(api_key, prompt, model)
        
        elif model_type == "qwen":
            model = model or "qwen-turbo"
            return self._call_qwen(api_key, prompt, model)
    
    def get_available_models(self, model_type: str) -> Dict[str, Dict[str, Any]]:
        """获取可用的模型列表"""
        if model_type not in self.models:
            raise ModelNotSupportedError(f"不支持的模型类型: {model_type}")
        return self.models[model_type]["models"]
    
    def get_model_info(self, model_type: str, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        if model_type not in self.models:
            raise ModelNotSupportedError(f"不支持的模型类型: {model_type}")
        
        if model not in self.models[model_type]["models"]:
            raise ModelNotSupportedError(f"不支持的{model_type}模型: {model}")
        
        return self.models[model_type]["models"][model]
    
    def validate_api_key(self, model_type: str, api_key: str, model: Optional[str] = None) -> bool:
        """验证API密钥"""
        try:
            test_prompt = "测试API连接"
            self.call_api(model_type, api_key, test_prompt, model)
            return True
        except Exception:
            return False 