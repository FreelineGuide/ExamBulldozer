from typing import Dict, Any, List, Optional, Union
import json
from jsonschema import validate, ValidationError, Draft7Validator

class JSONProcessor:
    """JSON处理类"""
    
    def __init__(self, schema: Dict[str, Any]):
        """初始化JSON处理器"""
        self.schema = schema
        self.errors = []
        self.validator = Draft7Validator(schema)
    
    def _validate_json(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
        """验证JSON数据是否符合Schema"""
        self.errors = []
        
        try:
            if isinstance(data, list):
                for item in data:
                    self.validator.validate(item)
            else:
                self.validator.validate(data)
            return True
        except ValidationError as e:
            self.errors.append(str(e))
            return False
        except Exception as e:
            self.errors.append(f"验证失败：{str(e)}")
            return False
    
    def _format_options(self, options: Union[List[str], Dict[str, str]]) -> Dict[str, str]:
        """格式化选项数据"""
        if isinstance(options, list):
            # 将列表转换为字典格式
            return {chr(65 + i): opt for i, opt in enumerate(options) if i < 26}
        elif isinstance(options, dict):
            # 确保键是大写字母
            return {k.upper(): v for k, v in options.items()}
        else:
            raise ValueError("选项格式不正确")
    
    def _format_answer(self, answer: Union[str, List[str], bool]) -> Union[str, List[str], bool]:
        """格式化答案数据"""
        if isinstance(answer, str):
            return answer.upper()
        elif isinstance(answer, list):
            return [a.upper() for a in answer]
        elif isinstance(answer, bool):
            return answer
        else:
            raise ValueError("答案格式不正确")
    
    def process_json(self, json_str: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """处理JSON字符串"""
        try:
            # 尝试解析JSON
            data = json.loads(json_str)
            
            # 如果是列表，处理每个项目
            if isinstance(data, list):
                processed_data = []
                for item in data:
                    processed_item = self._process_single_item(item)
                    if processed_item:
                        processed_data.append(processed_item)
                return processed_data if processed_data else None
            else:
                # 处理单个项目
                return self._process_single_item(data)
            
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON解析失败：{str(e)}")
            return None
        except Exception as e:
            self.errors.append(f"处理失败：{str(e)}")
            return None
    
    def _process_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个JSON对象"""
        try:
            # 复制数据以避免修改原始数据
            processed_item = item.copy()
            
            # 格式化选项（如果存在）
            if "options" in processed_item:
                processed_item["options"] = self._format_options(processed_item["options"])
            
            # 格式化答案
            if "answer" in processed_item:
                processed_item["answer"] = self._format_answer(processed_item["answer"])
            
            # 验证处理后的数据
            if self._validate_json(processed_item):
                return processed_item
            return None
            
        except Exception as e:
            self.errors.append(f"处理项目失败：{str(e)}")
            return None
    
    def get_errors(self) -> List[str]:
        """获取错误信息列表"""
        return self.errors
    
    def get_formatted_errors(self) -> str:
        """获取格式化的错误信息"""
        if not self.errors:
            return "没有错误"
        
        return "\n".join([
            f"错误 {i+1}: {error}"
            for i, error in enumerate(self.errors)
        ])
    
    def validate_schema(self) -> bool:
        """验证Schema本身是否有效"""
        try:
            # 验证Schema是否符合JSON Schema规范
            Draft7Validator.check_schema(self.schema)
            return True
        except Exception as e:
            self.errors.append(f"Schema无效：{str(e)}")
            return False

    def set_schema_manager(self, schema_manager):
        """设置Schema管理器"""
        self.schema_manager = schema_manager

    def _log_error(self, stage: str, error: str, data: Any = None):
        """记录错误信息"""
        error_info = {
            "stage": stage,
            "error": error,
            "data": data
        }
        self.errors.append(error_info)

    def _convert_options_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换选项格式"""
        if "options" in data and isinstance(data["options"], list):
            # 记录原始格式
            self._log_error(
                "format_conversion",
                "检测到数组格式的选项，正在转换为对象格式",
                {"original": data["options"]}
            )
            
            # 转换选项格式
            options_dict = {}
            for i, option in enumerate(data["options"]):
                key = chr(65 + i)  # 65 是 'A' 的 ASCII 码
                options_dict[key] = option
            
            # 更新数据
            data["options"] = options_dict
            
            # 记录转换结果
            self._log_error(
                "format_conversion",
                "选项格式转换完成",
                {"converted": options_dict}
            )
        
        return data

    def _validate_schema(self, data: Any) -> bool:
        """验证数据是否符合Schema"""
        try:
            validate(instance=data, schema=self.schema)
            return True
        except ValidationError as e:
            self._log_error(
                "schema_validation",
                str(e),
                {
                    "path": list(e.path),
                    "schema_path": list(e.schema_path),
                    "message": e.message,
                    "validator": e.validator,
                    "validator_value": e.validator_value
                }
            )
            return False

    def _format_error_message(self, error_info: Dict[str, Any]) -> str:
        """格式化错误信息"""
        stage = error_info["stage"]
        error = error_info["error"]
        data = error_info.get("data", {})
        
        if stage == "json_parsing":
            return f"JSON解析错误：{error}"
        elif stage == "schema_validation":
            path = " -> ".join(data.get("path", []))
            schema_path = " -> ".join(data.get("schema_path", []))
            return f"Schema验证错误：\n路径：{path}\nSchema路径：{schema_path}\n错误：{data.get('message', error)}"
        elif stage == "data_processing":
            return f"数据处理错误：{error}"
        elif stage == "format_conversion":
            if "original" in data:
                return f"格式转换：\n原始格式：{data['original']}\n{error}"
            elif "converted" in data:
                return f"格式转换：\n转换后格式：{data['converted']}\n{error}"
            return f"格式转换：{error}"
        else:
            return f"未知错误：{error}"

    def validate_json(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """验证JSON数据是否符合Schema"""
        try:
            validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            raise ValueError(f"JSON验证失败: {str(e)}")

    def process_ai_response(self, response: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理AI返回的JSON数据"""
        try:
            # 如果返回的是单个对象，转换为列表
            if isinstance(response, dict):
                if "items" in response and isinstance(response["items"], list):
                    # 处理包含items字段的响应
                    response = response["items"]
                else:
                    response = [response]
            elif not isinstance(response, list):
                raise ValueError("AI返回的数据必须是对象或数组")

            # 验证每个对象
            validated_data = []
            for item in response:
                if self.validate_json(item, schema):
                    validated_data.append(item)

            if not validated_data:
                raise ValueError("没有找到有效的试题数据")

            return validated_data
        except Exception as e:
            raise ValueError(f"处理AI响应失败: {str(e)}")

    def format_json_for_display(self, data: List[Dict[str, Any]]) -> str:
        """格式化JSON数据用于显示"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    def prepare_excel_data(self, data: List[Dict[str, Any]], question_type: str) -> List[Dict[str, Any]]:
        """准备用于Excel导出的数据"""
        excel_data = []
        for item in data:
            row = {
                "题目": item["question"]
            }

            if question_type in ["single_choice", "multiple_choice"]:
                # 添加选项
                for option in ["A", "B", "C", "D", "E"]:
                    if option in item["options"]:
                        row[f"选项{option}"] = item["options"][option]

                # 添加答案
                if question_type == "single_choice":
                    row["答案"] = item["answer"]
                else:  # multiple_choice
                    row["答案"] = ",".join(item["answer"])

            elif question_type == "true_false":
                row["答案"] = "是" if item["answer"] else "否"

            # 添加解析（如果存在）
            if "analysis" in item:
                row["解析"] = item["analysis"]

            excel_data.append(row)

        return excel_data 