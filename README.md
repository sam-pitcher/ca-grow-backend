````markdown
# CA-Grow Chatbot Backend

This repository contains the backend for the Ca-Grow React chatbot, built with FastAPI. It handles conversational analytics, processing user messages, and returning responses that can include both text and data visualizations (charts).

-----

## Features

* **FastAPI Framework**: Provides a robust and high-performance foundation for the API.
* **CORS Configuration**: Securely handles cross-origin requests from your React frontend.
* **Google Cloud Integration**: Authenticates with Google Cloud and interacts with the Gemini for Google Cloud's Conversational Analytics API.
* **Dynamic Responses**: Parses API output to extract and return either textual messages or Vega-Lite chart configurations.
* **Environment Variable Management**: Utilizes `python-dotenv` for secure management of API keys and project settings.
* **Conversation Management**: Supports initiating new chats, continuing existing conversations using a Looker access token, or resuming past conversations via a `conversation_id`.

-----

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**
* **`pip`** (Python package installer)
* **Google Cloud SDK** (configured with your credentials and default project)
* **Access to Gemini for Google Cloud's Conversational Analytics API private preview**.

### Installation

1.  **Clone the repository (if applicable):**

    ```bash
    git clone <repository_url>
    cd ca-grow-backend
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    * On macOS and Linux:

        ```bash
        source venv/bin/activate
        ```

    * On Windows:

        ```bash
        .\venv\Scripts\activate
        ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    (If you don't have a `requirements.txt`, you'll need to create one with the following packages: `fastapi`, `uvicorn`, `python-dotenv`, `google-auth`, `requests`, `pydantic`).

### Environment Variables

Create a `.env` file in the root of your project directory and populate it with your specific configuration values.

```ini
BILLING_PROJECT="your-google-cloud-billing-project-id"
LOOKER_CLIENT_ID="your-looker-client-id"
LOOKER_CLIENT_SECRET="your-looker-client-secret"
AGENT_NAME="your-data-agent-name"
GCP_LOCATION="global" # Or your specific GCP region, e.g., us-central1
````

**Note:**

  * Replace the placeholder values with your actual Google Cloud project ID, Looker client credentials, and data agent name.
  * The `AGENT_NAME` should correspond to a **data agent you have already created** in the Conversational Analytics API.
  * The `GCP_LOCATION` defaults to `global`, but you should set it to the location where your data agent and conversations are hosted.
  * For details on creating a data agent and configuring Looker credentials, refer to the [Gemini for Google Cloud Conversational Analytics API documentation](https://www.google.com/search?q=https://cloud.google.com/gemini-for-google-cloud/docs/conversational-analytics/build-data-agent-http-python).

-----

## Running the Backend

1.  **Activate your virtual environment** (if not already active).

2.  **Start the FastAPI application:**

    ```bash
    uvicorn main:app --reload --port 8000
    ```

    This will start the server at `http://localhost:8000`. The `--reload` flag will automatically restart the server on code changes, which is useful for development.

-----

## API Endpoints

### `GET /`

  * **Description**: A simple health check endpoint.
  * **Response**:
    ```json
    {"message": "Welcome to the Ca-Grow Chatbot Backend!"}
    ```

### `POST /chat`

  * **Description**: Sends a user message to the Conversational Analytics API, initiating a new, stateless conversation. It returns the processed response, which can include text and/or a chart configuration. This endpoint uses Looker Client ID and Client Secret for authentication.
  * **Request Body**:
    ```json
    {
        "message": "Your message here"
    }
    ```
  * **Response**:
    ```json
    {
        "response": {
            "backend": "conversational_analytics",
            "object": {
                "message": "The text response from the chatbot (if any)",
                "chart": {
                    // Vega-Lite chart configuration (if a chart was generated)
                }
            }
        }
    }
    ```

### `POST /chat_token`

  * **Description**: Sends a user message to the Conversational Analytics API, initiating a new, stateless conversation. This endpoint uses a provided Looker access token for authentication, which is useful for scenarios where the frontend already possesses a valid Looker session.
  * **Request Body**:
    ```json
    {
        "message": "Your message here",
        "looker_access_token": "your_looker_oauth_access_token"
    }
    ```
  * **Response**:
    ```json
    {
        "response": {
            "backend": "conversational_analytics",
            "object": {
                "message": "The text response from the chatbot (if any)",
                "chart": {
                    // Vega-Lite chart configuration (if a chart was generated)
                }
            }
        }
    }
    ```

### `POST /chat_conversation/{conversation_id}`

  * **Description**: Sends a user message to an existing conversation identified by `conversation_id`. This allows for maintaining conversation history and context within the Conversational Analytics API.
  * **URL Parameters**:
      * `conversation_id`: The ID of the existing conversation.
  * **Request Body**:
    ```json
    {
        "message": "Your message here"
    }
    ```
  * **Response**:
    ```json
    {
        "response": {
            "backend": "conversational_analytics",
            "object": {
                "message": "The text response from the chatbot (if any)",
                "chart": {
                    // Vega-Lite chart configuration (if a chart was generated)
                }
            }
        }
    }
    ```

### `GET /conversations`

  * **Description**: Fetches a list of all existing conversations associated with the configured billing project and location.
  * **Response**:
    ```json
    {
        "conversations": [
            {
                "id": "projects/your-project/locations/global/conversations/conversation_id_1",
                "name": "conversation_id_1"
            },
            {
                "id": "projects/your-project/locations/global/conversations/conversation_id_2",
                "name": "conversation_id_2"
            }
        ]
    }
    ```

### `GET /conversations/{conversation_id}/messages`

  * **Description**: Retrieves the message history for a specific conversation.
  * **URL Parameters**:
      * `conversation_id`: The simple ID of the conversation (e.g., `conversation_id_1`).
  * **Response**:
    ```json
    {
        "messages": [
            {
                "sender": "user",
                "text": "What are my sales from last quarter?",
                "timestamp": "2024-07-18T10:00:00Z"
            },
            {
                "sender": "agent",
                "text": "Your sales for last quarter were...",
                "timestamp": "2024-07-18T10:00:05Z"
            }
        ]
    }
    ```

-----

## Project Structure

  * `main.py`: The main FastAPI application file, containing endpoint definitions, CORS configuration, and logic for interacting with the Conversational Analytics API.
  * `.env`: (Not committed to Git) Contains environment variables for API keys and project settings.
  * `requirements.txt`: Lists the Python dependencies required for the project.

-----

## Development Notes

  * **CORS**: In a production environment, it's crucial to replace `"http://localhost:3000"` in `allow_origins` with the actual domain of your React frontend for security reasons.
  * **Google Cloud Authentication**: The application uses `google.auth.default()` for authentication, which relies on the Google Cloud SDK's application default credentials. Ensure your environment is properly authenticated (e.g., by running `gcloud auth application-default login`).
  * **Error Handling**: All endpoints include basic error handling for API request failures, raising an `HTTPException` in case of issues.
  * **Response Parsing**: The `handle_chart_response` and `handle_text_response` functions are responsible for parsing the potentially complex JSON responses from the Conversational Analytics API to extract relevant information.

<!-- end list -->

```
```