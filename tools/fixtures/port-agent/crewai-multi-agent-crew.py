"""CrewAI definition with a multi-agent crew topology and a vector-store
memory dependency -- both features with no 1:1 Forge equivalent, used to
test compatibility-note generation for non-1:1 features."""
from crewai import Agent, Task, Crew
from langchain.vectorstores import Chroma

researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI and data science",
    backstory="You work at a leading tech think tank.",
    tools=[search_tool],
    llm="gpt-4",
)

writer = Agent(
    role="Content Writer",
    goal="Turn research findings into a readable report",
    backstory="You are a skilled technical writer.",
    tools=[],
    llm="gpt-4",
)

memory_store = Chroma(collection_name="research-notes")

crew = Crew(
    agents=[researcher, writer],
    tasks=[
        Task(description="Research the topic.", agent=researcher),
        Task(description="Write the report.", agent=writer),
    ],
    memory=memory_store,
)
