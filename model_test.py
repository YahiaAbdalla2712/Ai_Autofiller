from ollama import chat
from structured_output_class import StOutput
SYSTEM_PROMPT = """
You are a data-entry intent parser for an enterprise factoring system.
Given a user's natural language description, extract the fields needed to fill out all REQUIRED attributes inside the schema you have been given.
The exracted attributes will be used to fill out forms.

Rules:
1- NEVER guess REQUIRED attributes.
2- NEVER fabricate REQUIRED attributes.
3- If there is an ambigous or unclear attribute ask the user about it again.
4- DO NOT invent information the user did not provide or imply.
5- Make sure all required fields are not empty.
6- NEVER delete or reset a previously extracted value unless the user explicitly changes it.
"""

messages = [{"role":"system","content":SYSTEM_PROMPT}]
while True:
    user_input = input("you")
    messages.append({
        "role":"user",
        "content":user_input
    })
    response = chat(model="llama3.1:latest",messages=messages,format = StOutput.model_json_schema())
    print("Assistant:", response.message.content)
    messages.append({
        "role":"assistant",
        "content":response.message.content
    })

