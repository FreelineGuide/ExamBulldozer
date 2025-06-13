
import streamlit as st
import json
from typing import Dict, Any, List, Optional
from config_manager import ConfigManager
from schema_manager import SchemaManager
from json_processor import JSONProcessor
from excel_exporter import ExcelExporter
from api_caller import APICaller, APIError, ModelNotSupportedError, APIKeyError
from pages.题型管理 import QuestionTypeManager

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
            ["✨ 试题转换", "📝 题型管理"],
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
    
    def render_main(self, model_type: str, model: str, api_key: str, question_type: str):
        """渲染主要内容区域"""
        # 输入区域
        st.header("📝 输入试题")
        input_text = st.text_area(
            "在此输入试题文本",
            height=200,
            help="输入要转换的试题文本，支持多个试题"
        )
        
        # 处理按钮
        if st.button("开始处理"):
            if not input_text:
                st.warning("请输入试题文本！")
                return
            
            if not api_key:
                st.warning("请输入API密钥！")
                return
            
            # 加载Schema
            schema = self.schema_manager.get_schema(question_type)
            if not schema:
                st.error("加载Schema失败！")
                return
            
            # 初始化JSON处理器
            self.json_processor = JSONProcessor(schema)
            
            # 调用API
            with st.spinner("正在处理..."):
                try:
                    # 构建提示词
                    prompt = f"""
                    请将以下试题转换为JSON格式，要求：
                    1. 严格按照Schema格式转换
                    2. 保持原有的题目顺序
                    3. 确保JSON格式正确，必须返回一个合法的JSON字符串
                    4. 不要返回任何其他内容，只返回JSON
                    
                    Schema: {json.dumps(schema, ensure_ascii=False)}
                    
                    试题文本：
                    {input_text}
                    """
                    
                    # 调用API
                    api_response = self.api_caller.call_api(
                        model_type,
                        api_key,
                        prompt,
                        model
                    )
                    
                    if not api_response:
                        st.error("API返回为空")
                        return
                    
                    # 调试信息
                    with st.expander("查看API响应"):
                        st.text(api_response)
                    
                    # 处理JSON
                    try:
                        processed_data = self.json_processor.process_json(api_response)
                        
                        if processed_data:
                            st.session_state.processed_data = processed_data
                            st.success("处理成功！")
                        else:
                            st.error("JSON处理失败！")
                            st.error(self.json_processor.get_formatted_errors())
                            
                    except json.JSONDecodeError as e:
                        st.error(f"JSON解析失败：{str(e)}")
                        st.error("API返回的不是有效的JSON格式")
                    except Exception as e:
                        st.error(f"JSON处理过程中出现错误：{str(e)}")
                        
                except (APIError, ModelNotSupportedError, APIKeyError) as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"处理过程中出现错误：{str(e)}")
        
        # 显示处理结果
        if st.session_state.processed_data:
            st.header("📊 处理结果")
            
            # 显示JSON
            with st.expander("查看JSON数据"):
                st.json(st.session_state.processed_data)
            
            # 导出Excel
            if st.button("导出到Excel"):
                with st.spinner("正在生成Excel文件..."):
                    try:
                        excel_data, filename = self.excel_exporter.export_to_excel(
                            st.session_state.processed_data,
                            question_type
                        )
                        # 提供下载按钮
                        st.download_button(
                            label="📥 下载Excel文件",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.success("Excel文件已生成，请点击上方按钮下载！")
                    except Exception as e:
                        st.error(f"导出失败：{str(e)}")
    
    def run(self):
        """运行应用"""
        self.render_header()
        
        # 根据当前标签页显示不同内容
        if st.session_state.current_tab == "✨ 试题转换":
            self.render_conversion_tab()
        else:
            self.question_type_manager.render()

if __name__ == "__main__":
    app = App()
    app.run() 