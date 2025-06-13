from typing import Dict, Any, Optional, List
import json
import os
from jsonschema import Draft7Validator

class SchemaManager:
    def __init__(self):
        self.schema_file = "schemas.json"
        self.schemas = self._load_schemas()
    
    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """加载所有Schema"""
        if os.path.exists(self.schema_file):
            with open(self.schema_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._get_default_schemas()
    
    def _save_schemas(self) -> None:
        """保存所有Schema"""
        with open(self.schema_file, "w", encoding="utf-8") as f:
            json.dump(self.schemas, f, ensure_ascii=False, indent=2)
    
    def _get_default_schemas(self) -> Dict[str, Dict[str, Any]]:
        """获取默认的Schema定义"""
        return {
            "single_choice": {
                "name": "单选题",
                "description": "只有一个正确答案的选择题",
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "题目内容"},
                        "options": {
                            "type": "object",
                            "description": "选项内容，键为选项编号（A、B、C、D等），值为选项内容",
                            "patternProperties": {
                                "^[A-E]$": {"type": "string"}
                            },
                            "minProperties": 2,
                            "maxProperties": 5
                        },
                        "answer": {
                            "type": "string",
                            "description": "正确答案的选项编号",
                            "pattern": "^[A-E]$"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "解析说明（可选）"
                        }
                    },
                    "required": ["question", "options", "answer"],
                    "additionalProperties": False
                },
                "prompt_template": """请将以下单选题转换为JSON格式，要求：
1. 题目内容放在question字段
2. 选项内容放在options字段，格式为对象，键为选项编号（A、B、C、D等），值为选项内容
3. 正确答案放在answer字段，只写选项编号
4. 如果有解析，放在analysis字段（可选）

示例输入：
下列哪项是Python的内置函数？
A. print()
B. display()
C. show()
D. output()

示例输出：
{
    "question": "下列哪项是Python的内置函数？",
    "options": {
        "A": "print()",
        "B": "display()",
        "C": "show()",
        "D": "output()"
    },
    "answer": "A",
    "analysis": "print()是Python的内置函数，用于输出内容到控制台。"
}

请按照上述格式转换以下试题：
{text}"""
            },
            "multiple_choice": {
                "name": "多选题",
                "description": "有多个正确答案的选择题",
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "题目内容"},
                        "options": {
                            "type": "object",
                            "description": "选项内容，键为选项编号（A、B、C、D等），值为选项内容",
                            "patternProperties": {
                                "^[A-E]$": {"type": "string"}
                            },
                            "minProperties": 2,
                            "maxProperties": 5
                        },
                        "answer": {
                            "type": "array",
                            "description": "正确答案的选项编号列表",
                            "items": {
                                "type": "string",
                                "pattern": "^[A-E]$"
                            },
                            "minItems": 1,
                            "uniqueItems": True
                        },
                        "analysis": {
                            "type": "string",
                            "description": "解析说明（可选）"
                        }
                    },
                    "required": ["question", "options", "answer"],
                    "additionalProperties": False
                },
                "prompt_template": """请将以下多选题转换为JSON格式，要求：
1. 题目内容放在question字段
2. 选项内容放在options字段，格式为对象，键为选项编号（A、B、C、D等），值为选项内容
3. 正确答案放在answer字段，为选项编号的数组
4. 如果有解析，放在analysis字段（可选）

示例输入：
以下哪些是Python的数据类型？
A. int
B. string
C. float
D. boolean

示例输出：
{
    "question": "以下哪些是Python的数据类型？",
    "options": {
        "A": "int",
        "B": "string",
        "C": "float",
        "D": "boolean"
    },
    "answer": ["A", "C"],
    "analysis": "int和float是Python的数值类型，string应该是str，boolean应该是bool。"
}

请按照上述格式转换以下试题：
{text}"""
            },
            "true_false": {
                "name": "判断题",
                "description": "判断对错的题目",
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "题目内容"},
                        "answer": {
                            "type": "boolean",
                            "description": "正确答案，true表示对，false表示错"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "解析说明（可选）"
                        }
                    },
                    "required": ["question", "answer"],
                    "additionalProperties": False
                },
                "prompt_template": """请将以下判断题转换为JSON格式，要求：
1. 题目内容放在question字段
2. 正确答案放在answer字段，true表示对，false表示错
3. 如果有解析，放在analysis字段（可选）

示例输入：
Python是一门编译型语言。（对/错）

示例输出：
{
    "question": "Python是一门编译型语言。",
    "answer": false,
    "analysis": "Python是一门解释型语言，不需要编译成机器码就可以运行。"
}

请按照上述格式转换以下试题：
{text}"""
            }
        }
    
    def get_schema(self, schema_type: str) -> Dict[str, Any]:
        """获取指定类型的Schema"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        return self.schemas[schema_type]["schema"]
    
    def get_prompt(self, schema_type: str) -> str:
        """获取指定类型的提示词模板"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        return self.schemas[schema_type]["prompt_template"]
    
    def get_schema_name(self, schema_type: str) -> str:
        """获取Schema的显示名称"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        return self.schemas[schema_type]["name"]
    
    def get_schema_description(self, schema_type: str) -> str:
        """获取Schema的描述"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        return self.schemas[schema_type]["description"]
    
    def get_all_schema_types(self) -> List[str]:
        """获取所有可用的Schema类型"""
        return list(self.schemas.keys())
    
    def add_custom_schema(self, name: str, description: str, schema: Dict[str, Any], prompt_template: str = None) -> None:
        """添加自定义Schema"""
        if not name or not schema:
            raise ValueError("名称和Schema定义不能为空")
        
        # 验证Schema格式
        if not isinstance(schema, dict):
            raise ValueError("Schema必须是一个字典")
        
        # 验证Schema是否有效
        try:
            Draft7Validator.check_schema(schema)
        except Exception as e:
            raise ValueError(f"Schema格式无效：{str(e)}")
        
        # 如果没有提供提示词模板，使用默认模板
        if not prompt_template:
            prompt_template = f"""请将以下{description}转换为JSON格式，要求：
1. 题目内容放在question字段
2. 其他字段根据Schema定义提供
3. 如果有解析，放在analysis字段（可选）

请按照Schema定义转换以下试题：
{{text}}"""
        
        # 添加到schemas中
        self.schemas[name] = {
            "name": description,  # 用description作为显示名称
            "description": description,
            "schema": schema,
            "prompt_template": prompt_template
        }
        
        # 保存到文件
        self._save_schemas()
    
    def update_schema(self, schema_type: str, schema: Dict[str, Any]) -> None:
        """更新现有的Schema"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        
        # 验证Schema格式
        if not isinstance(schema, dict):
            raise ValueError("Schema必须是一个字典")
        
        # 更新Schema
        self.schemas[schema_type]["schema"] = schema
        
        # 保存到文件
        self._save_schemas()
    
    def delete_schema(self, schema_type: str) -> None:
        """删除指定的Schema"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        
        # 删除Schema
        del self.schemas[schema_type]
        
        # 保存到文件
        self._save_schemas()

    def create_ai_prompt(self, text: str, question_type: str) -> str:
        """创建发送给AI的提示词"""
        template = self.get_prompt(question_type)
        if not template:
            raise ValueError(f"未找到题型 {question_type} 的提示词模板")
        return template.format(text=text)

    def load_custom_schema(self, schema_str: str) -> Dict[str, Any]:
        """加载并验证自定义Schema"""
        try:
            schema = json.loads(schema_str)
            # 基本验证
            if not isinstance(schema, dict):
                raise ValueError("Schema必须是JSON对象")
            if "type" not in schema:
                raise ValueError("Schema必须包含type字段")
            if "properties" not in schema:
                raise ValueError("Schema必须包含properties字段")
            return schema
        except json.JSONDecodeError:
            raise ValueError("无效的JSON格式")
        except Exception as e:
            raise ValueError(f"Schema验证失败: {str(e)}")

    def get_schema_types(self) -> list:
        """获取所有内置的Schema类型"""
        return list(self.schemas.keys())

    def create_ai_prompt(self, text: str, schema: Dict[str, Any]) -> str:
        """创建发送给AI的提示词"""
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        
        # 根据题型添加示例
        example = ""
        if schema == self.schemas["single_choice"]:
            example = """
示例输入：
1. 以下哪个是中国的首都？
A. 上海
B. 北京
C. 广州
D. 深圳
答案：B

2. 以下哪个是中国的第一大河？
A. 黄河
B. 长江
C. 珠江
D. 淮河
答案：B

示例输出：
[
    {
        "question": "以下哪个是中国的首都？",
        "options": {
            "A": "上海",
            "B": "北京",
            "C": "广州",
            "D": "深圳"
        },
        "answer": "B",
        "analysis": "北京是中国的首都"
    },
    {
        "question": "以下哪个是中国的第一大河？",
        "options": {
            "A": "黄河",
            "B": "长江",
            "C": "珠江",
            "D": "淮河"
        },
        "answer": "B",
        "analysis": "长江是中国第一大河，黄河是第二大河"
    }
]"""
        elif schema == self.schemas["multiple_choice"]:
            example = """
示例输入：
1. 以下哪些是中国的直辖市？（多选）
A. 北京
B. 上海
C. 广州
D. 重庆
答案：A,B,D

2. 以下哪些是中国的四大发明？（多选）
A. 造纸术
B. 指南针
C. 火药
D. 印刷术
E. 丝绸
答案：A,B,C,D

示例输出：
[
    {
        "question": "以下哪些是中国的直辖市？（多选）",
        "options": {
            "A": "北京",
            "B": "上海",
            "C": "广州",
            "D": "重庆"
        },
        "answer": ["A", "B", "D"],
        "analysis": "北京、上海、重庆是中国的直辖市，广州是广东省的省会城市"
    },
    {
        "question": "以下哪些是中国的四大发明？（多选）",
        "options": {
            "A": "造纸术",
            "B": "指南针",
            "C": "火药",
            "D": "印刷术",
            "E": "丝绸"
        },
        "answer": ["A", "B", "C", "D"],
        "analysis": "中国的四大发明是造纸术、指南针、火药和印刷术"
    }
]"""
        elif schema == self.schemas["true_false"]:
            example = """
示例输入：
1. 北京是中国的首都。
答案：是

2. 上海是中国的首都。
答案：否

示例输出：
[
    {
        "question": "北京是中国的首都。",
        "answer": true,
        "analysis": "北京是中国的首都，这是正确的"
    },
    {
        "question": "上海是中国的首都。",
        "answer": false,
        "analysis": "上海不是中国的首都，北京才是中国的首都"
    }
]"""

        return f"""请将以下试题文本转换为符合指定Schema的JSON格式。

原始文本：
{text}

目标Schema：
{schema_str}

{example}

要求：
1. 严格按照Schema的格式要求输出JSON
2. 确保所有必填字段都已填写：
   - question（题目文本）
   - options（选项，如果是选择题）
   - answer（答案）
3. 选项必须按照A、B、C、D、E的顺序排列
4. 答案必须使用选项字母（如"A"或["A", "B"]）
5. 如果文本中包含多道题目，请将每道题目分别转换为独立的JSON对象，并放入数组中
6. 请确保输出的JSON格式完全符合Schema要求，不要添加或遗漏任何字段
7. 每道题目之间用空行分隔，请确保识别所有题目
8. 输出格式必须是一个JSON数组，即使只有一道题目

请直接输出JSON，不要包含任何其他说明文字。"""

    def _load_custom_schemas(self):
        """加载自定义题型"""
        if os.path.exists("custom_schemas.json"):
            try:
                with open("custom_schemas.json", "r", encoding="utf-8") as f:
                    custom_schemas = json.load(f)
                    self.schemas.update(custom_schemas)
            except Exception as e:
                print(f"加载自定义题型失败：{str(e)}")

    def _save_custom_schemas(self):
        """保存自定义题型"""
        try:
            with open("custom_schemas.json", "w", encoding="utf-8") as f:
                json.dump(self.schemas, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存自定义题型失败：{str(e)}")

    def update_prompt(self, schema_type: str, prompt_template: str) -> None:
        """更新提示词模板"""
        if schema_type not in self.schemas:
            raise ValueError(f"未找到题型：{schema_type}")
        
        self.schemas[schema_type]["prompt_template"] = prompt_template
        self._save_schemas() 