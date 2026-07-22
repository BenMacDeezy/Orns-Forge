"""CrewAI imported under an alias -- a human might rename it on the way in."""
import crewai as cr

researcher = cr.Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI and data science",
    backstory="You work at a leading tech think tank.",
    tools=[search_tool],
    llm="gpt-4",
)
