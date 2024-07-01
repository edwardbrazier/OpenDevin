import json
from typing import Optional

from opendevin.controller.agent import Agent
from opendevin.controller.state.state import State
from opendevin.core.logger import opendevin_logger as logger
from opendevin.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    LoadCodebasesAction,
    MessageAction,
)
from opendevin.events.event import EventSource
from opendevin.llm.llm import LLM


class OmniscientChatbot(Agent):
    VERSION = '0.1'
    """
    The Omniscient Chatbot is an agent which answers questions about the codebase. Its distinctive capability is that it can pass a whole codebase to the AI model.
    """

    system_message: str = '(no system message)\n'
    in_context_example: str = '(no in-context example)\n'

    def __init__(self, llm: LLM) -> None:
        """
        Initializes a new instance of the class.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        """

        # TODO: Configure this to take the LLM parameters from the config file.
        api_key: str = llm.api_key  # type: ignore
        model: str = 'gpt-3.5-turbo'

        custom_llm = LLM(api_key=api_key, model=model)

        super().__init__(custom_llm)
        self.reset()

    def reset(self) -> None:
        """
        Resets the agent's state.
        """
        super().reset()

    def step(self, state: State) -> Action:
        """
        Performs one step using this agent.
        The step consists of loading a codebase and answering the question about it.

        Requires:
        - The input field of the state parameter must include an entry called 'task' containing
        string data in this form. (example)
        {
            "codebase_locations": ["./opendevin"],
            "file_extensions": ["py", "md"],
            "question": "How does the instruction get from the delegating agent to the Omniscient Chatbot?"
        }

        Parameters:
        - state (State): used to get the conversation history

        Returns:
        - AgentFinishAction() - End the interaction without providing any new information
        - MessageAction(content) - Response to a question
        """

        # First of all, we need to know whether this the delegator agent
        # has only just now delegated to this agent, or whether
        # this agent produced the last action.
        if len(state.history) == 0 or isinstance(
            state.history[-1][0], AgentDelegateAction
        ):
            # Get the instructions from the delegating agent.
            json_query: Optional[str] = state.inputs['task']  # type: ignore

            print(f'OmniscientChatbot.step(): json_query: \n{json_query}')
            print(f'Type of json_query: {type(json_query)}')

            if json_query is None:
                logger.error('OmniscientChatbot.step(): No query provided')
                return AgentFinishAction(outputs={'content': 'No query provided'})

            locations: Optional[list[str]]
            extensions: Optional[list[str]]
            question: Optional[str]

            # Parse the JSON query
            try:
                if isinstance(json_query, str):
                    query = json.loads(json_query)  # type: ignore
                else:
                    query = json_query  # type: ignore

                locations = query.get('codebase_locations')  # type: ignore
                extensions = query.get('file_extensions')  # type: ignore
                question = query.get('question')  # type: ignore
            except json.JSONDecodeError:
                logger.error('OmniscientChatbot.step(): Invalid JSON query')
                return AgentFinishAction(outputs={'content': 'Invalid JSON query'})

            assert locations is not None
            assert extensions is not None
            assert question is not None

            # extensions = ['py']
            # locations = ['OpenDevin/agenthub/omniscient_chatbot']
            return LoadCodebasesAction(paths=locations, extensions=extensions)

        if len(state.history) > 0:
            last_action, last_observation = state.history[-1]

            if (
                isinstance(last_action, MessageAction)
                and last_action.source == EventSource.AGENT
            ):
                # This agent has already sent its result back..
                # It only produces one message at a time, so it's finished.
                return AgentFinishAction(outputs={'content': last_action.content})

            if isinstance(last_action, LoadCodebasesAction):
                codebase_contents: str = last_observation.content

                # This agent has just received the codebase data.
                # It needs to send it to the LLM.
                messages: list[dict[str, str]] = [
                    {'role': 'system', 'content': self.system_message},
                    {'role': 'user', 'content': self.in_context_example},
                ]

                # Dummy message for testing
                messages += [
                    {
                        'role': 'user',
                        'content': 'Here is a codebase. Read it carefully.\n'
                        + codebase_contents
                        + '\n\n'
                        + 'Summarise.',
                    }
                ]

                response = self.llm.do_completion(  # type: ignore
                    messages=messages,
                    stop=[],
                    temperature=0.0,
                )
                state.num_of_chars += sum(
                    len(message['content']) for message in messages
                ) + len(response.choices[0].message.content)  # type: ignore

                # Get the string from the response
                if response.choices == []:  # type: ignore
                    return AgentFinishAction()

                response_string: str = response.choices[0].message.content  # type: ignore
                answer: str = response_string

                return MessageAction(answer)

            logger.error(f'Unrecognised action type: {type(last_action)}')
            return AgentFinishAction()

        logger.error("History empty in OmniscientChatbot's step method")
        return AgentFinishAction()

    def search_memory(self, query: str) -> list[str]:
        raise NotImplementedError('Implement this abstract method')
