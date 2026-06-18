# n8n-nodes-orchestrator-sentiment

Custom n8n nodes for integrating with the AI Orchestrator and Sentiment Analysis backend.

## Nodes

### 1. Orchestrator
Interact with the AI Orchestrator to execute functions based on natural language commands.
- **Input**: Natural language message (e.g., "Create a quote for client X").
- **Output**: Orchestrator execution results (JSON).

### 2. Sentiment Analysis
Analyze text using the 5-Pillar Sentiment Analysis model.
- **Input**: User content (text).
- **Output**: Classification (start, stickiness, etc.), Intent, and Context.

## Installation

1.  **Local Development**:
    ```bash
    cd /path/to/n8n-nodes-custom
    npm install
    npm run build
    npm link
    ```

2.  **In your n8n directory** (usually `~/.n8n/custom` or just `~/.n8n`):
    ```bash
    npm link n8n-nodes-orchestrator-sentiment
    ```

3.  **Restart n8n**:
    ```bash
    n8n start
    ```

## Credentials

You must create a credential of type **Orchestrator API**:
- **Base URL**: The URL of your backend (e.g., `http://localhost:8000`).
- **API Token**: Your user API Token or Session Token.

## License
MIT
