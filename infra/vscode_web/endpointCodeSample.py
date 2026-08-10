from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint="<%= endpoint %>")

# Get the OpenAI client for conversations and responses
openai = project.get_openai_client()

# Create a conversation with the user message
conversation = openai.conversations.create(
    items=[
        {
            "type": "message",
            "role": "user",
            "content": "<%= userMessage %>",
        }
    ],
)
print(f"Created conversation, ID: {conversation.id}")

# Send a response using the agent reference
response = openai.responses.create(
    input="<%= userMessage %>",
    conversation=conversation.id,
    extra_body={
        "agent_reference": {
            "name": "<%= agentId %>",
            "type": "agent_reference",
        }
    },
)

# Print the response output
for item in response.output:
    if item.type == "message":
        for block in item.content:
            if hasattr(block, "text"):
                print(f"assistant: {block.text}")
