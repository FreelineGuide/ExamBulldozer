import streamlit as st
import json
from typing import Dict, Any, List, Optional
from config_manager import ConfigManager
from schema_manager import SchemaManager
from json_processor import JSONProcessor
from excel_exporter import ExcelExporter
from api_caller import APICaller, APIError, ModelNotSupportedError, APIKeyError
from pages.题型管理 import QuestionTypeManager
import tiktoken
import re

# 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="试题推土机",
    page_icon="🚜",
    layout="wide"
)

# 隐藏 Streamlit 默认的多页面导航栏
hide_streamlit_style = """
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

class App:
    """试题推土机主程序"""
    
    def __init__(self):
        """初始化应用"""
        # 初始化组件
        self.config = ConfigManager()
        self.schema_manager = SchemaManager()
        self.api_caller = APICaller()
        self.json_processor = None  # 延迟初始化
        self.excel_exporter = ExcelExporter()
        self.question_type_manager = QuestionTypeManager()
        
        # 初始化会话状态
        if "api_response" not in st.session_state:
            st.session_state.api_response = None
        if "processed_data" not in st.session_state:
            st.session_state.processed_data = None
        if "current_tab" not in st.session_state:
            st.session_state.current_tab = "转换"
    
    def render_header(self):
        """渲染页面头部"""
        st.title("🚜 试题推土机")
        
        # 主导航
        st.session_state.current_tab = st.radio(
            "选择功能",
            ["✨ 试题转换", "📝 题型管理", "➕ 创建题型"],
            horizontal=True,
            label_visibility="collapsed",
            key="main_nav"
        )
    
    def render_conversion_tab(self):
        """渲染试题转换标签页"""
        st.markdown("""
        将非标准格式的选择题转换为结构化JSON数据并导出Excel。
        
        ### 支持的功能：
        - 多种题型支持（单选、多选、判断等）
        - 多个AI模型选择
        - 自定义导出格式
        - 批量处理支持
        """)
        
        # 获取设置
        model_type, model, api_key, question_type = self.render_sidebar()
        
        # 渲染主要内容区域
        self.render_main(model_type, model, api_key, question_type)
    
    def render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.header("⚙️ 设置")
            
            # 选择模型类型
            model_type = st.selectbox(
                "选择模型类型",
                ["deepseek", "qwen"],
                help="选择要使用的AI模型类型"
            )
            
            # 获取并显示可用模型
            available_models = self.api_caller.get_available_models(model_type)
            model = st.selectbox(
                "选择具体模型",
                list(available_models.keys()),
                help="选择具体的模型版本"
            )
            
            # 显示模型信息
            model_info = self.api_caller.get_model_info(model_type, model)
            st.info(f"模型说明：{model_info['description']}")
            
            # 从配置中加载已保存的API密钥
            saved_api_key = self.config.get_api_key(model_type)
            
            # API密钥输入
            api_key = st.text_input(
                "输入API密钥",
                value=saved_api_key,
                type="password",
                help="输入对应模型的API密钥，输入后会自动保存"
            )
            
            # 如果API密钥发生变化，自动保存
            if api_key != saved_api_key:
                try:
                    self.config.save_api_key(model_type, api_key)
                    if api_key:  # 只在有输入时显示提示
                        st.success("API密钥已自动保存")
                except Exception as e:
                    st.error(f"保存API密钥失败：{str(e)}")
            
            # 选择题型
            schema_types = self.schema_manager.get_all_schema_types()
            schema_names = {st: self.schema_manager.get_schema_name(st) for st in schema_types}
            selected_name = st.selectbox(
                "选择题型",
                list(schema_names.values()),
                help="选择要处理的试题类型"
            )
            # 根据中文名反查题型代码
            question_type = next(k for k, v in schema_names.items() if v == selected_name)
            
            # 验证API密钥
            if st.button("验证API密钥"):
                with st.spinner("正在验证..."):
                    if self.api_caller.validate_api_key(model_type, api_key, model):
                        st.success("API密钥验证成功！")
                    else:
                        st.error("API密钥验证失败！")
            
            return model_type, model, api_key, question_type
    
    def split_questions(self, input_text: str) -> list:
        """按空行或换行分割题目，去除空白"""
        # 支持空行或单换行分割
        questions = [q.strip() for q in re.split(r'\n\s*\n|\r\n\s*\r\n|\n|\r\n', input_text.strip()) if q.strip()]
        return questions

    def count_tokens(self, text: str, encoding: str = 'cl100k_base') -> int:
        """用tiktoken统计token数，默认兼容openai/deepseek/qwen"""
        try:
            enc = tiktoken.get_encoding(encoding)
        except Exception:
            enc = tiktoken.encoding_for_model('gpt-3.5-turbo')
        return len(enc.encode(text))

    def get_model_max_tokens(self, model_type: str) -> int:
        """根据模型类型返回最大token数"""
        if model_type == 'deepseek':
            return 16000
        elif model_type == 'qwen':
            return 8000
        else:
            return 4000  # 默认安全值

    def render_main(self, model_type: str, model: str, api_key: str, question_type: str):
        """渲染主要内容区域，增加自动分批处理"""
        st.header("📝 输入试题")
        input_text = st.text_area(
            "在此输入试题文本",
            height=200,
            help="输入要转换的试题文本，支持多个试题（可用换行或空行分隔）"
        )

        # 实时token统计与分批预估
        if input_text:
            schema = self.schema_manager.get_schema(question_type)
            prompt_template = self.schema_manager.get_prompt(question_type)
            prompt_tokens = self.count_tokens(prompt_template)
            schema_tokens = self.count_tokens(json.dumps(schema, ensure_ascii=False))
            total_tokens = prompt_tokens + schema_tokens + self.count_tokens(input_text)
            max_tokens = self.get_model_max_tokens(model_type)
            st.info(f"当前输入总token数约：{total_tokens} / {max_tokens}")
            if total_tokens > max_tokens:
                st.warning("输入内容已超出模型最大处理能力，将自动分批处理。")

        if st.button("开始处理"):
            if not input_text:
                st.warning("请输入试题文本！")
                return
            if not api_key:
                st.warning("请输入API密钥！")
                return
            schema = self.schema_manager.get_schema(question_type)
            if not schema:
                st.error("加载Schema失败！")
                return
            self.json_processor = JSONProcessor(schema)
            # 自动分批处理
            questions = self.split_questions(input_text)
            prompt_template = self.schema_manager.get_prompt(question_type)
            prompt_tokens = self.count_tokens(prompt_template)
            schema_tokens = self.count_tokens(json.dumps(schema, ensure_ascii=False))
            max_tokens = self.get_model_max_tokens(model_type)
            safety_margin = 0.15
            batch_token_limit = int(max_tokens * (1 - safety_margin)) - prompt_tokens - schema_tokens
            batches = []
            current_batch = []
            current_tokens = 0
            for q in questions:
                q_tokens = self.count_tokens(q)
                if current_tokens + q_tokens > batch_token_limit and current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                current_batch.append(q)
                current_tokens += q_tokens
            if current_batch:
                batches.append(current_batch)
            all_results = []
            for idx, batch in enumerate(batches):
                batch_text = '\n\n'.join(batch)
                prompt = prompt_template.replace('{text}', batch_text)
                with st.spinner(f"正在处理第{idx+1}/{len(batches)}批..."):
                    try:
                        api_response = self.api_caller.call_api(
                            model_type,
                            api_key,
                            prompt,
                            model
                        )
                        if not api_response:
                            st.error(f"第{idx+1}批AI返回为空")
                            continue
                        with st.expander(f"查看第{idx+1}批API响应"):
                            st.text(api_response)
                        try:
                            processed_data = self.json_processor.process_json(api_response)
                            if processed_data:
                                all_results.extend(processed_data if isinstance(processed_data, list) else [processed_data])
                                st.success(f"第{idx+1}批处理成功！")
                            else:
                                st.error(f"第{idx+1}批JSON处理失败！")
                                st.error(self.json_processor.get_formatted_errors())
                        except json.JSONDecodeError as e:
                            st.error(f"第{idx+1}批JSON解析失败：{str(e)}")
                        except Exception as e:
                            st.error(f"第{idx+1}批JSON处理过程中出现错误：{str(e)}")
                    except (APIError, ModelNotSupportedError, APIKeyError) as e:
                        st.error(f"第{idx+1}批API错误：{str(e)}")
                    except Exception as e:
                        st.error(f"第{idx+1}批处理过程中出现错误：{str(e)}")
            if all_results:
                st.session_state.processed_data = all_results
                st.success("全部批次处理完成！")
        # 显示处理结果
        if st.session_state.processed_data:
            st.header("📊 处理结果")
            with st.expander("查看JSON数据"):
                st.json(st.session_state.processed_data)
            if st.button("导出到Excel"):
                with st.spinner("正在生成Excel文件..."):
                    try:
                        excel_data, filename = self.excel_exporter.export_to_excel(
                            st.session_state.processed_data,
                            question_type
                        )
                        st.download_button(
                            label="📥 下载Excel文件",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.success("Excel文件已生成，请点击上方按钮下载！")
                    except Exception as e:
                        st.error(f"导出失败：{str(e)}")
    
    def render_create_type_tab(self):
        """渲染新建题型标签页"""
        st.title("➕ 创建新题型")
        st.markdown("""
        在这里可以快速创建全新的题型、Schema和提示词模板。
        """)
        if 'create_type_success' not in st.session_state:
            st.session_state.create_type_success = False
        if 'create_type_name' not in st.session_state:
            st.session_state.create_type_name = ''
        with st.form("create_type_form"):
            col1, col2 = st.columns(2)
            with col1:
                type_code = st.text_input(
                    "题型代码",
                    help="题型的唯一标识符，例如：'single_choice'",
                    placeholder="输入英文代码"
                )
            with col2:
                type_name = st.text_input(
                    "题型名称",
                    help="题型的显示名称，例如：'单选题'",
                    placeholder="输入中文名称"
                )
            type_desc = st.text_input(
                "题型描述",
                help="对这个题型的简要描述",
                placeholder="输入题型描述"
            )
            st.subheader("📋 Schema定义")
            schema_str = st.text_area(
                "JSON Schema",
                value="",
                height=300,
                help="输入符合JSON Schema规范的定义"
            )
            st.subheader("💭 提示词模板")
            prompt_template = st.text_area(
                "提示词模板",
                value="",
                height=300,
                help="输入提示词模板，使用{text}作为试题文本的占位符"
            )
            # 预览
            if schema_str and prompt_template:
                with st.expander("👀 预览配置", expanded=False):
                    try:
                        schema = json.loads(schema_str)
                        st.json({"schema": schema, "prompt_template": prompt_template})
                    except Exception:
                        st.warning("Schema不是有效的JSON格式")
            # 提交按钮
            created = st.form_submit_button("💾 创建题型")
            if created:
                try:
                    if not all([type_code, type_name, type_desc, schema_str, prompt_template]):
                        st.error("请填写所有必要信息")
                        return
                    schema = json.loads(schema_str)
                    self.schema_manager.add_custom_schema(
                        name=type_code,
                        description=type_name,
                        schema=schema,
                        prompt_template=prompt_template
                    )
                    st.session_state.create_type_success = True
                    st.session_state.create_type_name = type_name
                except Exception as e:
                    st.error(f"保存失败：{str(e)}")
        # 表单外部显示跳转按钮
        if st.session_state.create_type_success:
            st.success(f"题型 {st.session_state.create_type_name} 创建成功！")
            if st.button("去题型管理页查看", key="goto_manage"):
                st.session_state.current_tab = "📝 题型管理"
                st.session_state.create_type_success = False
                st.rerun()

    def run(self):
        """运行应用"""
        self.render_header()
        
        # 根据当前标签页显示不同内容
        if st.session_state.current_tab == "✨ 试题转换":
            self.render_conversion_tab()
        elif st.session_state.current_tab == "📝 题型管理":
            self.question_type_manager.render()
        elif st.session_state.current_tab == "➕ 创建题型":
            self.render_create_type_tab()

if __name__ == "__main__":
    app = App()
    app.run() 