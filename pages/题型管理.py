import streamlit as st
import json
from schema_manager import SchemaManager
from typing import Dict, Any
import jsonschema

class QuestionTypeManager:
    def __init__(self):
        self.schema_manager = SchemaManager()
        
        # 初始化会话状态
        if "selected_type" not in st.session_state:
            st.session_state.selected_type = None
        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False
        
    def render_schema_editor(self, schema_type: str = None):
        """渲染Schema编辑器"""
        current_schema = (self.schema_manager.get_schema(schema_type) 
                        if schema_type else {})
        
        schema_str = st.text_area(
            "JSON Schema",
            value=json.dumps(current_schema, ensure_ascii=False, indent=2),
            height=300,
            help="输入符合JSON Schema规范的定义",
            key=f"schema_editor_{schema_type}"
        )
        
        try:
            if schema_str:
                schema = json.loads(schema_str)
                # 验证Schema格式
                jsonschema.Draft7Validator.check_schema(schema)
                return schema
        except json.JSONDecodeError:
            st.error("JSON格式错误，请检查输入")
        except jsonschema.exceptions.SchemaError as e:
            st.error(f"Schema格式错误：{str(e)}")
        except Exception as e:
            st.error(f"发生错误：{str(e)}")
        return None

    def render_prompt_editor(self, schema_type: str = None):
        """渲染提示词编辑器"""
        current_prompt = (self.schema_manager.get_prompt(schema_type) 
                        if schema_type else "")
        
        prompt_template = st.text_area(
            "提示词模板",
            value=current_prompt,
            height=300,
            help="输入提示词模板，使用{text}作为试题文本的占位符",
            key=f"prompt_editor_{schema_type}"
        )
        
        return prompt_template

    def render_preview(self, schema: Dict[str, Any], prompt_template: str):
        """渲染预览区域"""
        if schema and prompt_template:
            with st.expander("👀 预览配置", expanded=False):
                st.json({
                    "schema": schema,
                    "prompt_template": prompt_template
                })

    def render_existing_types(self):
        """渲染现有题型列表"""
        st.sidebar.header("📚 现有题型")
        
        # 获取所有题型
        schema_types = self.schema_manager.get_all_schema_types()
        schema_names = {st: self.schema_manager.get_schema_name(st) for st in schema_types}
        
        # 创建选择器
        selected = st.sidebar.selectbox(
            "选择题型查看或编辑",
            options=list(schema_names.keys()),
            format_func=lambda x: schema_names[x],
            key="type_selector"
        )
        
        if selected:
            st.session_state.selected_type = selected
            st.sidebar.write(f"描述：{self.schema_manager.get_schema_description(selected)}")
            
            # 编辑/查看切换
            st.session_state.edit_mode = st.sidebar.toggle("✏️ 编辑模式")
            
            # 删除按钮
            if st.sidebar.button("🗑️ 删除此题型", type="secondary"):
                try:
                    self.schema_manager.delete_schema(selected)
                    st.sidebar.success(f"已删除题型：{schema_names[selected]}")
                    st.session_state.selected_type = None
                    st.session_state.edit_mode = False
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"删除失败：{str(e)}")

    def render_edit_form(self, schema_type: str = None):
        """渲染编辑表单"""
        is_new = schema_type is None
        
        with st.form("schema_form"):
            if is_new:
                st.subheader("✨ 创建新题型")
                # 基本信息
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
            else:
                st.subheader(f"✏️ 编辑题型：{self.schema_manager.get_schema_name(schema_type)}")
                type_code = schema_type
                type_name = self.schema_manager.get_schema_name(schema_type)
                type_desc = self.schema_manager.get_schema_description(schema_type)
            
            # Schema编辑器
            st.subheader("📋 Schema定义")
            schema = self.render_schema_editor(schema_type)
            
            # 提示词编辑器
            st.subheader("💭 提示词模板")
            prompt_template = self.render_prompt_editor(schema_type)
            
            # 预览
            self.render_preview(schema, prompt_template)
            
            # 提交按钮
            if is_new:
                submit_label = "💾 创建题型"
            else:
                submit_label = "💾 保存修改"
            
            if st.form_submit_button(submit_label):
                try:
                    if is_new and not all([type_code, type_name, type_desc, schema, prompt_template]):
                        st.error("请填写所有必要信息")
                        return
                    
                    if is_new:
                        # 创建新题型
                        self.schema_manager.add_custom_schema(
                            name=type_code,
                            description=type_name,
                            schema=schema,
                            prompt_template=prompt_template
                        )
                        msg = f"题型 {type_name} 创建成功！"
                    else:
                        # 更新现有题型
                        self.schema_manager.update_schema(type_code, schema)
                        self.schema_manager.update_prompt(type_code, prompt_template)
                        msg = f"题型 {type_name} 更新成功！"
                    
                    st.success(msg)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"保存失败：{str(e)}")

    def render(self):
        """渲染主页面"""
        # 渲染现有题型列表
        self.render_existing_types()
        
        # 主要内容区域
        if st.session_state.selected_type and st.session_state.edit_mode:
            # 编辑现有题型
            self.render_edit_form(st.session_state.selected_type)
        elif st.session_state.selected_type:
            # 查看现有题型
            schema_type = st.session_state.selected_type
            st.subheader(f"👀 查看题型：{self.schema_manager.get_schema_name(schema_type)}")
            
            # 显示基本信息
            st.write(f"**题型代码：** `{schema_type}`")
            st.write(f"**描述：** {self.schema_manager.get_schema_description(schema_type)}")
            
            # 显示Schema
            with st.expander("📋 Schema定义", expanded=True):
                st.json(self.schema_manager.get_schema(schema_type))
            
            # 显示提示词模板
            with st.expander("💭 提示词模板", expanded=True):
                st.text(self.schema_manager.get_prompt(schema_type))
        else:
            # 创建新题型
            self.render_edit_form() 