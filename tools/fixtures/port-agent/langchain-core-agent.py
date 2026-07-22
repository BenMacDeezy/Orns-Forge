"""Modern (2024+) LangChain agent using the split langchain_core /
langchain_openai packages -- the post-split import shape, distinct from the
older monolithic `langchain.agents` fixture. Uses only imports and plain
message/runnable construction so the only thing that could make this
classify correctly is the import-statement regex itself."""
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0)
greeting = HumanMessage(content="hello")
pipeline = RunnableLambda(lambda x: x) | llm
