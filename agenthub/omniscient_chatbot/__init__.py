from opendevin.controller.agent import Agent

from .omniscient_chatbot import OmniscientChatbot

Agent.register('OmniscientChatbot', OmniscientChatbot)
