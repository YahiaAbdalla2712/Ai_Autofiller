#example to test

json_payload = {
    "type":"object",
    "properties":{
        "client_name":{
            "type":"string",
            "description":"Name of the client that made the transaction or the transaction is made under his/her/its name"
        },
        "amount":{
            "type":"number",
            "description":"the amount of money in the transaction"
        },
        "currency":{
            "type":"string",
            "description":"transaction currency"
        },
        "due_in_days":{
            "type":"integer",
            "description":"number of days until transaction is due"
        }
    },
    "required":[
        "client_name",
        "amount",
        "currency",
        "due_in_days"
    ]
}