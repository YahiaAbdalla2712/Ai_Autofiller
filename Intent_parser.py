import os
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from structured_output_class import StOutput, REQUIRED_FIELDS
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import json 

from chunking_and_embedding import retrieve_business_rules


MODEL = "gemma3:4b"

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
    llm = ChatOllama(model = MODEL, temperature=0, format="json")
    return llm

def get_buisness_rules_context(user_input: str, current_data: dict) -> str:
    """
    Fetch buisness rules relevant to the current turn and render them as plain text context for the prompt.
    this replaces exposing retrieve_buisness_rules as a callable tool to the model.
    """
    try:
        rules = retrieve_business_rules(user_input)
    except Exception as e:
        return f"(business rules lookup failed: {e})"

    if not rules:
        return "(no relevant business rules found)"  

    if isinstance(rules,(list,tuple)):
        return "\n".join(f"- {r}" for r in rules)

    return str(rules)  


def evaluate_business_rules(data:dict,business_rules_context:str)->list[dict]:
    """
    Separate, explicit step: given the currently extracted data and the retrieved 
    business rules text, ask the model to report which rules are triggered and what 
    action they require.

    This is intentionally NOT part of the extraction call. Extraction must stay
    "only what the user said"; rule evalation is a downstream check on top of that data,
    not a source of field values. Keeping them in separate calls also mean a rule hit can
    never leak into 'data and get treated as a user-provided value.
    """

    if not data:
        return []

    EVAL_PROMPT = f"""
        Your are a business-rule compliance checker.

        Given the extracted data below and the business rules context,
        identify which rules (if any) apply to this data and what action
        each one requires. DO NOT modify or add to the data itself.

        Extreacted data:
        {json.dumps(data, indent=2)}

        Business rules:
        {business_rules_context}

        Respond with ONLY a JSON array. Each element:
        {{"rule":"<short description of the rule that applies>","action_required": "<what must happen>"}}

        If no rules apply, respond with an empty array: []

    """
    llm = ChatOllama(model=MODEL, temperature=0, format="json")
    response = llm.invoke([SystemMessage(content=EVAL_PROMPT)])

    try:
        flags = json.loads(response.content)

    except (json.JSONDecodeError,TypeError):
        return []

    if not isinstance(flags, list):
        return []

    return flags


def validate_enum_values(data: dict, schema: dict) -> dict:
    properties = schema.get("properties", {})

    for field, value in data.items():
        field_schema = properties.get(field, {})

        allowed_values = field_schema.get("enum")

        if allowed_values and value not in allowed_values:
            data[field] = None

    return data        

def run_intent_parser(user_input:str,current_data:dict,schema:dict,history:list[dict] = None):
    history = history or []

    business_rules_context = get_buisness_rules_context(user_input, current_data)

    SYSTEM_PROMPT = f"""
        You are a STRICT data-extraction system.

        your ONLY job is to extract values explicitly provided by the user.

        CRITICAL RULE:
        A field value must come from the user's message, current_data, or previous conversation history. Nothing else can be used as a value source.

        NEVER infer, assume, guess, default, or complete a field.

        This includes values that are:
        - common
        - typical
        - likely
        - standard
        - recommended
        - implied by the department
        - present in examples
        - present in buisness rules
        - present in the schema description

        If the user does not provide a value, output null for that field.

        If a field has a predefined set of allowed options in the schema, the user's input must exactly match one of those allowed options,
        If the user provides a value that is not one of the allowed options, output null for that field, Never substitute, normalize, 
        or infer a different allowed value unless it is giving the same meaning, 
        Example:
        If there is a field named employment type and you have only 3 options [full-time, part-time, contract]
        then: 
        - if user inputs full-time then the value of the field is full-time.
        - if user inputs part-time then the value of the field is part-time.
        - if user inputs contract then the value of the field is contract. 
        - if user inputs week by week the value of the field is part-time.
        - if user inputs freelancing the value of the field is null.

        Previous values:
        - If a value already exists in current_data/history, preserve it.
        - Only replace it if the user explicitly changes it.

        Business rules:
        Business rules may be used only to evaluate explicitly provided values.
        Buisness rules MUST NEVER provide values for missing fields.
        {business_rules_context}

        Required fields:
        If a required field is missing, return null for that field.
        The application will determine missing_fields.

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

    data = validate_enum_values(data, schema)
    
    updated_data = {
        **current_data,
        **{
            key: value 
            for key, value in data.items()
            if not is_missing(value)
        }
    }

    missing = get_missing_fields(updated_data,schema)

    business_rule_flags = evaluate_business_rules(updated_data, business_rules_context)

    return {
        "data": updated_data,
        "missing_fields": missing,
        "complete": len(missing) == 0,
        "business_rule_flags": business_rule_flags
    }


if __name__ == "__main__":
    run_intent_parser()