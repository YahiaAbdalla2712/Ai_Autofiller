import os
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from structured_output_class import StOutput, REQUIRED_FIELDS
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import json 


MODEL = "qwen2.5:3b"

PLACEHOLDER_VALUES={"unknown","n/a","na","none","null","tbd","","not specified","not provided"}

def is_missing(value)->bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in PLACEHOLDER_VALUES:
        return True
    return False

def get_missing_fields(data: dict, schema: dict) -> list[str]:
    required_fields = schema.get("required",[])
    return [
        field 
        for field in required_fields
        if is_missing(data.get(field))
    ]


def build_structured_llm():
    return ChatOllama(model = MODEL, temperature = 0, format="json")
    

def run_intent_parser(user_input:str,current_data:dict,schema:dict,history:list[dict] = None):
    history = history or []

    SYSTEM_PROMPT = f"""
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
        7- Return the extracted values in the provided schema.
        8- for <person/company> referes to the name.
        9- if there is missing info ask the user about it.
        10- do not end the conversation until you have all missing info
        11- Never invent dates or any data.

        JSON schema:
        {json.dumps(schema,indent=2)}

    """
    messages = [
        SystemMessage(content = SYSTEM_PROMPT)
    ]

    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content = turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content = turn["content"]))    

    messages.append(HumanMessage(content=user_input))        

    llm = build_structured_llm()

    response = llm.invoke(messages)

    data = json.loads(response.content)

    updated_data = {
        **current_data,
        **{
            key: value 
            for key, value in data.items()
            if not is_missing(value)
        }
    }

    missing = get_missing_fields(updated_data,schema)

    return {
        "data": updated_data,
        "missing_fields": missing,
        "complete": len(missing) == 0
    }


if __name__ == "__main__":
    run_intent_parser()