"""Example CrewAI agent definition, the shape a human might hand-port."""
from crewai import Agent, Task, Crew

researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI and data science",
    backstory=(
        "You work at a leading tech think tank. Your expertise lies in "
        "identifying emerging trends and technologies."
    ),
    tools=[search_tool, browse_tool],
    llm="gpt-4",
    verbose=True,
)

task = Task(
    description="Analyze the latest AI trends and produce a report.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
