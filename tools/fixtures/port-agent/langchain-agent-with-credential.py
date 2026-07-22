"""Example LangChain agent definition that embeds a generic secret
assignment, used to test that the mapper strips it before generation."""
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage

system_message = SystemMessage(
    content="You are a helpful research assistant that cites its sources."
)

# Generic secret-shaped assignment (fake/example value).
openai_api_key = "sk-FAKEEXAMPLEabcdefghijklmnopqrstuvwxyz012345"

llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=openai_api_key)

agent_executor = initialize_agent(
    tools=[search_tool, calculator_tool],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    agent_kwargs={"system_message": system_message},
    verbose=True,
)
