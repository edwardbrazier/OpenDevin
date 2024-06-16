# VantagePoint Agent Framework

This folder implements the VantagePointAgent, which is like the CodeActAgent but has the capability to call the OmniscientChatBot for a big-picture view of the code. This enhancement allows the agent to gain a broader understanding of the codebase and make more informed decisions.

The conceptual idea is illustrated below. At each turn, the agent can:

1. **Converse**: Communicate with humans in natural language to ask for clarification, confirmation, etc.
2. **CodeAct**: Choose to perform the task by executing code
   - Execute any valid Linux `bash` command
   - Execute any valid `Python` code with [an interactive Python interpreter](https://ipython.org/). This is simulated through `bash` command, see plugin system below for more details.

![image](https://github.com/OpenDevin/OpenDevin/assets/38853559/92b622e3-72ad-4a61-8f41-8c040b6d5fb3)

## Plugin System

To make the VantagePointAgent more powerful with only access to `bash` action space, VantagePointAgent leverages OpenDevin's plugin system:
- [Jupyter plugin](https://github.com/OpenDevin/OpenDevin/tree/main/opendevin/runtime/plugins/jupyter): for IPython execution via bash command
- [SWE-agent tool plugin](https://github.com/OpenDevin/OpenDevin/tree/main/opendevin/runtime/plugins/swe_agent_commands): Powerful bash command line tools for software development tasks introduced by [swe-agent](https://github.com/princeton-nlp/swe-agent).

