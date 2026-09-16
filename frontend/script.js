const fieldsContainer = document.getElementById("fieldsContainer");
const emptyState = document.getElementById("emptyState");
const jsonPreview = document.getElementById("jsonPreview");

const addFieldBtn = document.getElementById("addFieldBtn");
const processBtn = document.getElementById("processBtn");

const userMessage = document.getElementById("userMessage");
const aiResponse = document.getElementById("aiResponse");

let fields = [];
let currentData = {};
let history = [];

// -----------------------------
// Add Field
// -----------------------------

addFieldBtn.addEventListener("click", () => {

    const field = {
        id: Date.now(),
        name: "",
        type: "string",
        description: "",
        options: [],
        required: true,
        value:""
    };

    fields.push(field);

    renderFields();
    updateJSON();

});


// -----------------------------
// Render Fields
// -----------------------------

function renderFields() {

    fieldsContainer.innerHTML = "";

    if (fields.length === 0) {
        emptyState.style.display = "block";
        return;
    }

    emptyState.style.display = "none";

    fields.forEach(field => {

        const fieldElement = document.createElement("div");

        fieldElement.className = "field";

        fieldElement.innerHTML = `

            <div class="field-header">

                <strong>Field</strong>

                <button
                    class="remove-btn"
                    onclick="removeField(${field.id})"
                >
                    Remove
                </button>

            </div>


            <div class="form-row">

                <div class="form-group">

                    <label>Field Name</label>

                    <input
                        type="text"
                        value="${field.name}"
                        placeholder="client_name"
                        oninput="updateField(${field.id}, 'name', this.value)"
                    >

                </div>


                <div class="form-group">

                    <label>Type</label>

                    <select
                        onchange="updateField(${field.id}, 'type', this.value)"
                    >

                        <option value="string"
                            ${field.type === "string" ? "selected" : ""}>
                            Text
                        </option>

                        <option value="number"
                            ${field.type === "number" ? "selected" : ""}>
                            Number
                        </option>

                        <option value="integer"
                            ${field.type === "integer" ? "selected" : ""}>
                            Integer
                        </option>

                        <option value="boolean"
                            ${field.type === "boolean" ? "selected" : ""}>
                            Boolean
                        </option>

                    </select>

                </div>

                <div class="options-section">
                    <label>Allowed Options</label>

                    <div id="options-${field.id}" class="options-list">
                        ${field.options.map((option, index) => `
                            <div class="option-row">
                                <input
                                    type="text"
                                    value="${option}"
                                    placeholder="Option ${index + 1}"
                                    oninput="updateOption(${field.id}, ${index}, this.value)"
                                >

                                <button
                                    type="button"
                                    class="remove-option-btn"
                                    onclick="removeOption(${field.id}, ${index})"
                                >
                                    Remove
                                </button>
                            </div>
                        `).join("")}
                    </div>

                    <button
                        type="button"
                        class="add-option-btn"
                        onclick="addOption(${field.id})"
                    >
                        + Add Option
                    </button>
                </div>

                <div class="form-group">

                    <label>Description</label>

                    <input
                        type="text"
                        value="${field.description}"
                        placeholder="Name of the client"
                        oninput="updateField(
                            ${field.id},
                            'description',
                            this.value
                        )"
                    >

                </div>

            </div>
            

            <div class="checkbox">

                <input
                    type="checkbox"
                    ${field.required ? "checked" : ""}
                    onchange="updateField(
                        ${field.id},
                        'required',
                        this.checked
                    )"
                >

                <label>Required field</label>

            </div>

        `;

        fieldsContainer.appendChild(fieldElement);

    });

}


// -----------------------------
// Update Field
// -----------------------------

function updateField(id, property, value) {

    const field = fields.find(field => field.id === id);

    if (!field) return;

    field[property] = value;

    updateJSON();
}


// -----------------------------
// Remove Field
// -----------------------------

function removeField(id) {

    fields = fields.filter(field => field.id !== id);

    renderFields();
    updateJSON();
}


// -----------------------------
// Generate JSON Schema
// -----------------------------

function generateSchema() {

    const properties = {};
    const required = [];

    fields.forEach(field => {

        if (!field.name.trim()) {
            return;
        }

    const fieldName = field.name.trim().replace(/\s+/g, "_");

    properties[fieldName] = {
        type: field.type,
        description: field.description
    };

    const validOptions = field.options
        .map(option => option.trim())
        .filter(option => option !== "");

    if (validOptions.length > 0){
        properties[fieldName].enum = validOptions;
    }    

    if (field.required) {
        required.push(fieldName);
    }

    });


    return {
        type: "object",
        properties: properties,
        required: required
    };

}


// -----------------------------
// Update JSON Preview
// -----------------------------

function updateJSON() {

    const schema = generateSchema();

    jsonPreview.textContent =
        JSON.stringify(schema, null, 2);

}


// -----------------------------
// Send Form + User Message
// -----------------------------

processBtn.addEventListener("click", async () => {
    console.log("Send Button Clicked")

    const schema = generateSchema();

    const message = userMessage.value.trim();

    console.log("Sending to AI:");
    console.log("Message:", message);
    console.log("Current Data:", currentData);
    console.log("Schema:", schema);

    if (!message) {

        alert("Please enter a message.");

        return;
    }


    aiResponse.textContent = "Processing...";


    try {

        const response = await fetch(
            "http://127.0.0.1:8000/intent",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message,
                    current_data: currentData,
                    schema: schema,
                    history
                })
            }
        );


        if (!response.ok) {

            throw new Error(
                `HTTP error: ${response.status}`
            );

        }


        const result = await response.json();

        currentData = result.data;

        fields.forEach(field => {
            if(currentData[field.name] !== undefined){
                field.value = currentData[field.name];
            }
        });

        renderFields();

        aiResponse.textContent =
            JSON.stringify(result, null, 2);


    } catch (error) {

        aiResponse.textContent =
            "Error: " + error.message;

    }

});

function addOption(fieldId) {
    const field = fields.find(field => field.id === fieldId);

    if(!field) return;

    field.options.push("");

    renderFields();
    updateJSON();
}

function updateOption(fieldId, optionIndex, value){
    const field = fields.find(field => field.id === fieldId);

    if(!field) return;

    field.options[optionIndex] = value;

    updateJSON();
}

function removeOption(fieldId, optionIndex){
    const field = fields.find(field => field.id === fieldId);

    if(!field) return;

    field.options.splice(optionIndex,1);

    renderFields();
    updateJSON();
}