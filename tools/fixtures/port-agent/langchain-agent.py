"""Example LangChain agent definition, the shape a human might hand-port."""
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage

system_message = SystemMessage(
    content="You are a helpful research assistant that cites its sources."
)

llm = ChatOpenAI(model="gpt-4", temperature=0)

agent_executor = initialize_agent(
    tools=[search_tool, calculator_tool],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    agent_kwargs={"system_message": system_message},
    verbose=True,
)
