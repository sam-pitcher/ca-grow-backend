# ca-grow-backend/main.py

from fastapi import FastAPI, Request, HTTPException
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