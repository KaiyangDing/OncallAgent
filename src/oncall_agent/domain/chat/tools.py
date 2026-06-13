"""对话 Agent 的工具集。

工具需要访问检索服务等资源,但 LangChain 的 @tool 调用时只接收 LLM
提供的参数。用闭包工厂模式:外部把资源注入工厂,工厂返回绑定好资源的工具。
"""

from langchain_core.tools import BaseTool, tool

from oncall_agent.domain.knowledge.retriever import RetrievalService


def make_knowledge_tool(retrieval: RetrievalService) -> BaseTool:
    """工厂:返回一个绑定了检索服务的「知识库查询」工具。"""

    @tool
    def search_knowledge_base(query: str) -> str:
        """查询运维知识库,获取故障处理方案、排查步骤等参考资料。

        当用户的问题涉及运维知识、故障排查、告警处理等专业内容时,
        使用本工具检索相关文档。

        Args:
            query: 要检索的问题或关键词
        """
        return retrieval.retrieve(query)

    return search_knowledge_base
