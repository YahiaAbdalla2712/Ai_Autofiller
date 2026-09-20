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

#to validate the value of the field if this field has definit choices
def validate_enum_values(data: dict, schema: dict) -> dict:
    properties = schema.get("properties", {})
    validation_messages = []

    for field, value in data.items():

        if field not in properties:
            continue

        field_schema = properties[field]
        allowed_values = field_schema.get("enum")

        if not allowed_values or value is None:
            continue

        if value not in allowed_values:
            validation_messages.append(
                {
                    "field": field,
                    "value": value,
                    "message":(
                        f"'{value}' is not a valid value for {field}."
                        f"Allowed values are: {', '.join(allowed_values)}"
                    )
                }
            )
            data[field] = None

    return data, validation_messages       


#to validate the value of the field if it is in range between min and max or not
def validate_numeric_ranges(data: dict, schema: dict) -> dict:
    properties = schema.get("properties",{})
    validation_messages = []

    for field, value in data.items():

        if field not in properties:
            continue

        field_schema = properties[field]
        field_type = field_schema.get("type")

        if field_type not in ("number", "integer"):
            continue

        if value is None:
            continue

        #convert strings into numbers (integers or float)
        if isinstance(value, str):
            try:
                if field_type == "integer":
                    value = int(value)
                else:
                    value = float(value)

                data[field] = value

            except ValueError:
                validation_messages.append(
                    {
                        "field": field,
                        "value": value,
                        "message":(
                            f"'{value}' is not a valid {field_type}"
                            f"value for '{field}'."
                        )
                    }
                )

                data[field] = None
                continue            

        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")

        if minimum is not None and value < minimum:
            validation_messages.append(
                {
                    "field": field,
                    "value": value,
                    "message":(
                        f"The value if '{field}' must be at least "
                        f"{minimum}. You provided {value}."
                    )
                }
            )

            data[field] = None
            continue

        if maximum is not None and value > maximum:
            validation_messages.append(
                {
                    "field": field,
                    "value": value,
                    "message":(
                        f"The value if '{field}' must be at most "
                        f"{maximum}. You provided {value}."
                    )
                }
            )
            data[field] = None
            continue

    return data, validation_messages

def run_intent_parser(user_input:str,current_data:dict,schema:dict,history:list[dict] = None):
    history = history or []
    validation_messages = []

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

        IMPORTANT FIELD VALIDATION RULE:

        If the user explicitly mentions a field in their message, you MUST include that
        field in your output, even if the value is invalid.

        If the value does not satisfy the field's schema constraints, return null.

        For example, if:

        employment_type:
        enum = ["full-time", "part-time", "contract"]

        and the user says:

        "my employment type is freelancing"

        you MUST return:

        {{
            "employment_type": null
        }}

        Do NOT omit the field.

        If the user does not mention a field at all, you may omit that field from
        the current extraction.

        This distinction is important:

        - Field not mentioned -> omit the field
        - Field mentioned with valid value -> return the value
        - Field mentioned with invalid value -> return null

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

    data, enum_messages = validate_enum_values(data, schema)
    validation_messages += enum_messages

    data, numeric_messages = validate_numeric_ranges(data, schema)
    validation_messages += numeric_messages
    
    updated_data = {
        **current_data,
        **data
    }

    missing = get_missing_fields(updated_data,schema)

    business_rule_flags = evaluate_business_rules(updated_data, business_rules_context)

    return {
        "data": updated_data,
        "missing_fields": missing,
        "complete": len(missing) == 0,
        "validation_messages": validation_messages,
        "business_rule_flags": business_rule_flags
    }


if __name__ == "__main__":
    run_intent_parser()