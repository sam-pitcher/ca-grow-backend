# ca-grow-backend/main.py
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import random
import json
import requests
import os
from dotenv import load_dotenv
load_dotenv()

import google.auth
import google.auth.transport.requests
creds, project = google.auth.default()
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)


app = FastAPI(
    title="Ca-Grow Chatbot Backend",
    description="Backend for the Ca-Grow React chatbot, handling standard and streaming responses."
)

# Configure CORS
# Adjust `allow_origins` to your React app's URL in production
# For development, you can use "*" to allow all origins, but be more specific in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Replace with your React app's actual URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def handle_chart_response(api_output_lines):
    """
    Parses the API output and extracts the chart's vegaConfig.
    """
    full_response_str = ""
    for line in api_output_lines:
        # Remove b' prefix and decode if necessary
        if isinstance(line, bytes):
            line_str = line.decode('utf-8')
        else:
            line_str = line
        full_response_str += line_str

    # Attempt to parse the full string as a single JSON array
    try:
        responses = json.loads(full_response_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Problematic string: {full_response_str}")
        return None

    for response_item in responses:
        if isinstance(response_item, dict) and \
           "systemMessage" in response_item and \
           isinstance(response_item["systemMessage"], dict) and \
           "chart" in response_item["systemMessage"] and \
           isinstance(response_item["systemMessage"]["chart"], dict) and \
           "result" in response_item["systemMessage"]["chart"] and \
           isinstance(response_item["systemMessage"]["chart"]["result"], dict) and \
           "vegaConfig" in response_item["systemMessage"]["chart"]["result"]:
            return response_item["systemMessage"]["chart"]["result"]["vegaConfig"]
            # yield response_item["systemMessage"]["chart"]["result"]["vegaConfig"]
    return None

def handle_text_response(api_output_lines):
    """
    Parses the API output and extracts the text response.
    """
    full_response_str = ""
    for line in api_output_lines:
        # Remove b' prefix and decode if necessary
        if isinstance(line, bytes):
            line_str = line.decode('utf-8')
        else:
            line_str = line
        full_response_str += line_str
    
    # Attempt to parse the full string as a single JSON array
    try:
        responses = json.loads(full_response_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Problematic string: {full_response_str}")
        return None

    for response_item in responses:
        if isinstance(response_item, dict) and \
           "systemMessage" in response_item and \
           isinstance(response_item["systemMessage"], dict) and \
           "text" in response_item["systemMessage"] and \
           isinstance(response_item["systemMessage"]["text"], dict) and \
           "parts" in response_item["systemMessage"]["text"] and \
           isinstance(response_item["systemMessage"]["text"]["parts"], list) and \
           len(response_item["systemMessage"]["text"]["parts"]) > 0:
            return response_item["systemMessage"]["text"]["parts"][0]
            # yield response_item["systemMessage"]["text"]["parts"][0]
    return None

class MessageRequest(BaseModel):
    message: str
    looker_access_token: Optional[str] = None 

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Ca-Grow Chatbot Backend!"}

@app.post("/chat")
async def chat(request_body: MessageRequest):
    gcp_oauth_token = creds.token
    print(gcp_oauth_token)

    message = request_body.message

    data_agent_id = os.environ.get("AGENT_NAME")
    lookml_model = os.environ.get("LOOKML_MODEL")
    lookml_explore = os.environ.get("LOOKML_EXPLORE")
    billing_project = os.environ.get("BILLING_PROJECT")
    looker_client_id = os.environ.get("LOOKER_CLIENT_ID")
    looker_client_secret = os.environ.get("LOOKER_CLIENT_SECRET")

    chat_url = f"https://geminidataanalytics.googleapis.com/v1alpha/projects/{billing_project}/locations/global:chat"
    looker_credentials = {
        "oauth": {
            "secret": {
                "client_id": looker_client_id,
                "client_secret": looker_client_secret,
                }
            }
        }
    
    chat_payload = {
        "parent": f"projects/{billing_project}/locations/global",
        "messages": [
            {
                "userMessage": {
                    "text": message
                    }
                }
            ],
        "data_agent_context": {
            "data_agent": f"projects/{billing_project}/locations/global/dataAgents/{data_agent_id}",
            "credentials": looker_credentials
        }
    }

    s = requests.Session()
    response_lines = []
    try:
        with s.post(url=chat_url, json=chat_payload, headers={"Authorization": f'Bearer {gcp_oauth_token}'}, stream=False) as resp:
            resp.raise_for_status()
            full_response_content = resp.text
            for line_bytes in full_response_content.encode('utf-8').splitlines():
                response_lines.append(line_bytes)

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

    chart_config = handle_chart_response(response_lines)
    text_output = handle_text_response(response_lines)

    # --- Construct the new JSON response ---
    response_payload = {
        "response": {
            "backend": "conversational_analytics", # Based on your original response
            "object": {
                "message": text_output or None, # Use the text output
                "chart": chart_config or None
                }
            }
        }
    
    return JSONResponse(content=response_payload)
    # return JSONResponse(content={"reply": text_output})

@app.post("/chat_token")
async def chat_token(
    request_body: MessageRequest,
):
    gcp_oauth_token = creds.token
    print(gcp_oauth_token)
    # gcp_oauth_token = os.environ.get("GCP_OAUTH_TOKEN_FROM_SERVICE_ACCOUNT")
    message = request_body.message
    looker_access_token = request_body.looker_access_token
    data_agent_id = os.environ.get("AGENT_NAME")
    billing_project = os.environ.get("BILLING_PROJECT")
    
    chat_url = f"https://geminidataanalytics.googleapis.com/v1alpha/projects/{billing_project}/locations/global:chat"

    looker_credentials = {
        "oauth": {
            "token": {
                "access_token": looker_access_token,
            }
        }
    }
    
    chat_payload = {
        "parent": f"projects/{billing_project}/locations/global",
        "messages": [
            {
                "userMessage": {
                    "text": message
                }
            }
        ],
        "data_agent_context": {
            "data_agent": f"projects/{billing_project}/locations/global/dataAgents/{data_agent_id}",
            "credentials": looker_credentials
        }
    }

    s = requests.Session()
    response_lines = []
    try:
        if not gcp_oauth_token:
            raise HTTPException(status_code=500, detail="GCP OAuth token not configured on backend.")

        with s.post(
            url=chat_url,
            json=chat_payload,
            headers={"Authorization": f'Bearer {gcp_oauth_token}'},
            stream=False
        ) as resp:
            resp.raise_for_status()
            full_response_content = resp.text
            for line_bytes in full_response_content.encode('utf-8').splitlines():
                response_lines.append(line_bytes)

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    chart_config = {}
    text_output = ""
    try:
        chart_config = handle_chart_response(response_lines)
        text_output = handle_text_response(response_lines)
    except Exception as e:
        print(f"Error processing Gemini response: {e}")
        text_output = f"Error processing bot response: {e}"

    response_payload = {
        "response": {
            "backend": "conversational_analytics",
            "object": {
                "message": text_output or None,
                "chart": chart_config or None
            }
        }
    }
    
    return JSONResponse(content=response_payload)

@app.post("/chat_conversation/{conversation_id}")
async def chat_with_conversation(conversation_id: str, request_body: MessageRequest):
    gcp_oauth_token = creds.token
    message = request_body.message

    data_agent_id = os.environ.get("AGENT_NAME")
    billing_project = os.environ.get("BILLING_PROJECT")
    location = os.environ.get("GCP_LOCATION", "global")
    looker_client_id = os.environ.get("LOOKER_CLIENT_ID")
    looker_client_secret = os.environ.get("LOOKER_CLIENT_SECRET")

    looker_credentials = {
        "oauth": {
            "secret": {
                "client_id": looker_client_id,
                "client_secret": looker_client_secret,
            }
        }
    }
    
    chat_url = f"https://geminidataanalytics.googleapis.com/v1alpha/projects/{billing_project}/locations/{location}:chat"

    chat_payload = {
        "parent": f"projects/{billing_project}/locations/global",
        "messages": [
            {
                "userMessage": {
                    "text": message
                }
            }
        ],
        "conversation_reference": {
            "conversation": f"projects/{billing_project}/locations/{location}/conversations/{conversation_id}",
            "data_agent_context": {
                "data_agent": f"projects/{billing_project}/locations/{location}/dataAgents/{data_agent_id}",
                "credentials": looker_credentials
            }
        }
    }

    s = requests.Session()
    response_lines = []
    try:
        with s.post(url=chat_url, json=chat_payload, headers={"Authorization": f'Bearer {gcp_oauth_token}'}, stream=False) as resp:
            resp.raise_for_status()
            full_response_content = resp.text
            for line_bytes in full_response_content.encode('utf-8').splitlines():
                response_lines.append(line_bytes)

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

    chart_config = handle_chart_response(response_lines)
    text_output = handle_text_response(response_lines)

    response_payload = {
        "response": {
            "backend": "conversational_analytics",
            "object": {
                "message": text_output or None,
                "chart": chart_config or None
            }
        }
    }
    
    return JSONResponse(content=response_payload)

@app.get("/conversations")
async def get_conversations():
    """
    Fetches a list of conversations and returns their names.
    """
    gcp_oauth_token = creds.token
    billing_project = os.environ.get("BILLING_PROJECT")
    location = os.environ.get("GCP_LOCATION", "global") # Assume 'global' if not specified

    if not billing_project:
        raise HTTPException(status_code=500, detail="BILLING_PROJECT environment variable not set.")

    conversation_url = f"https://geminidataanalytics.googleapis.com/v1alpha/projects/{billing_project}/locations/{location}/conversations"

    headers = {
        "Authorization": f"Bearer {gcp_oauth_token}",
        "Content-Type": "application/json"
    }

    try:
        conversation_response = requests.get(conversation_url, headers=headers)
        conversation_response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        response_data = conversation_response.json()
        conversations = response_data.get("conversations", [])

        conversation_names = []
        for conv in conversations:
            full_name = conv.get("name")
            if full_name:
                # Extract the last part after "conversations/"
                parts = full_name.split('/')
                if len(parts) > 1 and parts[-2] == "conversations":
                    conversation_id = parts[-1]
                    conversation_names.append({"id": full_name, "name": conversation_id}) # Store full_name as id, and just the ID as name for display
                else:
                    conversation_names.append({"id": full_name, "name": full_name}) # Fallback if format is unexpected

        return JSONResponse(content={"conversations": conversation_names})

    except requests.exceptions.RequestException as e:
        print(f"Error while fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from conversations API: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON response from conversations API: {str(e)}")

@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str): # Changed from conversation_full_id
    """
    Fetches messages for a specific conversation ID.
    The conversation_id should be the simple ID (e.g., "conversation_1").
    """
    gcp_oauth_token = creds.token
    billing_project = os.environ.get("BILLING_PROJECT")
    location = os.environ.get("GCP_LOCATION", "global")

    if not billing_project:
        raise HTTPException(status_code=500, detail="BILLING_PROJECT environment variable not set.")

    # Reconstruct the full resource path from the simple conversation_id
    conversation_full_path = f"projects/{billing_project}/locations/{location}/conversations/{conversation_id}"

    conversation_url = f"https://geminidataanalytics.googleapis.com/v1alpha/{conversation_full_path}/messages"

    headers = {
        "Authorization": f"Bearer {gcp_oauth_token}",
        "Content-Type": "application/json"
    }

    try:
        conversation_response = requests.get(conversation_url, headers=headers)
        conversation_response.raise_for_status()

        messages_data = conversation_response.json().get("messages", [])

        formatted_messages = []
        for message_entry in reversed(messages_data): # Reverse to get oldest first
            message_content = message_entry.get("message", {})
            timestamp = message_content.get("timestamp")

            if "userMessage" in message_content:
                user_text = message_content["userMessage"].get("text")
                if user_text:
                    formatted_messages.append({"sender": "user", "text": user_text, "timestamp": timestamp})
            elif "systemMessage" in message_content:
                system_msg = message_content["systemMessage"]
                if "text" in system_msg and "parts" in system_msg["text"]:
                    system_text = "".join(system_msg["text"]["parts"])
                    formatted_messages.append({"sender": "agent", "text": system_text, "timestamp": timestamp})
                # elif "chart" in system_msg:
                #     formatted_messages.append({"sender": "agent", "text": "[Chart Data - See original response for Vega spec]", "timestamp": timestamp, "type": "chart", "content": system_msg["chart"]})
                # elif "data" in system_msg:
                #      formatted_messages.append({"sender": "agent", "text": "[Data Table - See original response]", "timestamp": timestamp, "type": "data", "content": system_msg["data"]})


        return JSONResponse(content={"messages": formatted_messages})

    except requests.exceptions.RequestException as e:
        print(f"Error while fetching conversation messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from messages API: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON response from messages API: {str(e)}")