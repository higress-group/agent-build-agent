import json
from typing import Union, List
import json5

from qwen_agent.llm.schema import ContentItem
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.llm import get_chat_model

@register_tool('generate_ai_agent_code')
class GenerateAIAgentCode(BaseTool):
    description = '根据MCP Server配置、MCP Server的描述、prompt描述生成符合Qwen-Agent代码模板的AI Agent代码'
    parameters = [
        {
            'name': 'config',
            'type': 'string',
            'description': 'MCP Server配置参数（JSON格式）,如{"mcp-server1":{"url":"xxx"}}',
            'required': True
        },
        {
            'name': 'description',
            'type': 'string',
            'description': 'MCP Server的描述',
            'required': False
        },
        {
            'name': 'system',
            'type': 'string',
            'description': '该AI Agent的System prompt描述',
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            # 解析输入参数
            input_params = json5.loads(params)
            tools_str = input_params['config']
            print("===> tools_str ===<")
            print(tools_str)
            print("===> tools_str_finish ===<")
            system = input_params['system']
            tool_description = input_params['description']

            # 验证配置格式
            tools = json.loads(tools_str)

            # 生成代码模板
            code_template = f"""
            import os
            from qwen_agent.agents import Assistant
            from qwen_agent.gui import WebUI

            def init_agent_service():
                llm_cfg = {{
                    'model': 'qwen3-235b-a22b',
                    'model_type': 'qwen_dashscope',
                    'api_key': os.getenv('DASHSCOPE_API_KEY'),
                }}

                tools = [ {{
                    'mcpServers': 
                        {tools}
                }} ]

                return Assistant(
                    llm=llm_cfg,
                    function_list=tools,
                    name='Custom MCP Agent',
                    system_message='{system}',
                    description='{tool_description}'
                )

            def app_gui():
                bot = init_agent_service()
                WebUI(bot).run()

            if __name__ == '__main__':
                app_gui()
                """
            return code_template.strip()

        except Exception as e:
            return f"代码生成失败：{str(e)}"

@register_tool('list_mcp_tools')
class ListMcpTools(BaseTool):
    description = '返回所有的mcpserver的配置'
    parameters = [{
        'name': 'server_names',
        'type': 'string',
        'description': '需要选择的MCP服务器名称列表（JSON数组格式，如["time", "fetch"]）',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        with open('mcpservers.json', 'r') as f:
            config = json.load(f)
        all_servers = config.get('mcpServers', {})
        function_list = [{
            "mcpServers": all_servers
        }]

        return json.dumps(function_list, ensure_ascii=False)

@register_tool('file_writer')
class FileWriter(BaseTool):
    parameters = [
        {
            'name': 'code',
            'type': 'string',
            'description': '用户要保存到文件的python代码',
            'required': True
        },
        {
            'name': 'file_name',
            'type': 'string',
            'description': '用户要保存的文件的文件名',
            'required': True
        },
    ]
    def call(self, params: str, **kwargs) -> str:
        print("+++++++++++++ debug params ++++++++++++++++")
        print(params)
        print("+++++++++++++++++++++++++++++")
        try:
            data = json5.loads(params)
        except ValueError:
            data = json5.loads(params+'"}')
        code = data['code']
        file_name = data['file_name']
        if not code or not file_name:
            raise ValueError("Missing required parameters: 'code' and 'filename' are both required")
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(code)

        return f"代码已成功保存到当前目录的文件：{file_name}"

@register_tool('generate_ai_agent_prompt')
class GenerateAIAgentPrompt(BaseTool):
    parameters = [{
        'name': 'user_prompt',
        'type': 'string',
        'description': '用户对agent功能需求的详细描述（如："我要实现一个天气助手，需要根据位置提供天气信息"）',
        'required': True
    }]
    def call(self, params: str, **kwargs) -> dict:

        print("+++++++++++++ debug params ++++++++++++++++")
        print(params)
        print("+++++++++++++++++++++++++++++")

        try:
            data = json5.loads(params)
        except ValueError:
            data = json5.loads(params+'"}')

        user_prompt = data['user_prompt']

        # 构建提示词模板
        prompt = f"""
        请根据以下用户需求生成合适的system_message：
        用户需求："{user_prompt}"

        生成要求：
        1. 使用专业且友好的语气
        2. 明确agent的功能边界
        3. 包含必要的执行指引
        4. 保持简洁且完整，注意不能遗漏用户需求
        5. 明确说明可以并且主动使用 mcp 工具
        6. system_message中需要包含：其中所有mcp调用涉及到分页查询的大小限制均保留成5
        7. 生成的system_message不需要换行，保证一行
        8. system_message中需要包含：如果mcp工具调用失败，则跳过，使用同类型工具（比如list失败则改用search）

        请直接输出生成的system_message文本，不要添加其他解释：
        """

        llm_cfg = {
            'model': 'qwen3-235b-a22b',
            'model_server': 'dashscope',
        }
        # 调用大模型生成
        llm = get_chat_model(llm_cfg)
        messages = [{'role': 'user', 'content': f'{prompt}'}]
        response = llm.quick_chat_oai(messages)

        print("++++++++++++++++++++++++")
        for x in response:
            print(x)
            message = x["choices"][0]['message']["content"]
        print("++++++++++++++++++++++++")

        res = [{
            "description": message
        }]
        print("generate_ai_agent_prompt ===>")
        return json.dumps(res, ensure_ascii=False)

def init_agent_service():
    llm_cfg = {'model': 'qwen3-235b-a22b'}
    system = f"""
    你扮演一个ai-agent自动生成助手
    1.首先你需要根据用户输入的需求，选择必要且合适的mcp-server的名称列表
    2.然后通过list_mcp_tools生成agent所需的mcp-server的配置列表
    3.然后通过generate_ai_agent_prompt生成agent所需的system prompt
    4.然后你需要通过system prompt总结该agent的职能生成agent的简单描述description，注意description是system prompt的精简缩略，尽量减少unnecessary words
    4.再按照qwen-agent框架将前面生成的prompt、description、以及mcp-server的配置列表生成符合用户需求的ai-agent的代码
    5.如果生成的代码中mcp-server有使用env的字段，在保存到文件之前，你需要将该env字段对应的value修改为os.getenv("ENV_NAME")，ENV_NAEM为mcp-server中env字段的key，注意os.getenv()需要保留函数形式，不要将其作为字符串
    6.最终要把生成的 python 代码通过file_writer保存到当前工作目录中，同时需要确保写入文件的代码格式正确
    """
    tools = ['code_interpreter',
             'generate_ai_agent_prompt',
             'list_mcp_tools',
             'generate_ai_agent_code',
             'file_writer']
    bot = Assistant(
        llm=llm_cfg,

        name='AI-agent代码助手',
        description='自动生成AI-agent代码',
        system_message=system,
        function_list=tools,
    )

    return bot

def app_gui():
    # Define the agent
    bot = init_agent_service()
    WebUI(bot).run()

if __name__ == '__main__':
    app_gui()