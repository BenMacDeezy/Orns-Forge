"""Example CrewAI agent definition that embeds a credential, used to test
that the port-agent mapper strips it before anything is generated."""
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

# AWS-style access key id embedded directly in the source (fake/example).
AWS_ACCESS_KEY_ID = "AKIAFAKEEXAMPLE12345"

task = Task(
    description="Analyze the latest AI trends and produce a report.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
