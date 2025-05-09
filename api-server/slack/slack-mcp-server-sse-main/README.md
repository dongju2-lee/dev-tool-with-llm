# Slack MCP Server with SSE Transport

A Model Context Protocol (MCP) server that provides Slack API integration using Server-Sent Events (SSE) transport. This server allows AI assistants to interact with Slack workspaces through a simple HTTP-based interface.

## Features

- **SSE Transport**: Uses Server-Sent Events (SSE) instead of stdio, enabling communication over HTTP/HTTPS
- **Slack API Integration**: Provides access to essential Slack API functionality
- **Simple Web Interface**: Includes a basic web UI and health check endpoint
- **Docker Support**: Fully containerized with Docker for easy deployment
- **TypeScript Implementation**: Built with TypeScript for type safety and better developer experience
- **Cross-Platform Compatibility**: Works with any MCP client that supports SSE transport

## Prerequisites

- Node.js 18 or higher
- Slack Bot Token with appropriate permissions
- Slack Team ID
- Docker (optional, for containerized deployment)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Your Slack Bot User OAuth Token (starts with `xoxb-`) | *Required* |
| `SLACK_TEAM_ID` | Your Slack Workspace/Team ID | *Required* |
| `PORT` | Port on which the server will run | `3000` |

## Setup Instructions

### Obtaining Slack Bot Token and Team ID

1. Create a Slack App:
   - Visit the [Slack Apps page](https://api.slack.com/apps)
   - Click "Create New App"
   - Choose "From scratch"
   - Name your app and select your workspace

2. Configure Bot Token Scopes:
   - Navigate to "OAuth & Permissions" in your app settings
   - Add these scopes:
     - `channels:history` - View messages and other content in public channels
     - `channels:read` - View basic channel information
     - `chat:write` - Send messages as the app
     - `reactions:write` - Add emoji reactions to messages
     - `users:read` - View users and their basic information

3. Install App to Workspace:
   - Click "Install to Workspace" and authorize the app
   - Save the "Bot User OAuth Token" that starts with `xoxb-`

4. Get your Team ID:
   - Open Slack in a web browser
   - Once logged in, check the URL in your browser
   - The URL will be in a format like: `https://app.slack.com/client/T01234567/...`
   - Your Team ID is the string beginning with T (e.g., `T01234567`)

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a `.env` file based on `.env.example`:
   ```
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_TEAM_ID=your-slack-team-id
   PORT=3000
   ```
4. Build the TypeScript code:
   ```bash
   npm run build
   ```
5. Start the server:
   ```bash
   npm start
   ```

For development with automatic reloading:
```bash
npm run dev
```

### Docker Deployment

#### Using Docker Compose (Recommended)

1. Create a `.env` file with your Slack credentials as shown above
2. Build and run the container:
   ```bash
   docker compose up --build
   ```

#### Using Pre-built Image

```bash
docker run -p 3000:3000 \
  -e SLACK_BOT_TOKEN=xoxb-your-slack-bot-token \
  -e SLACK_TEAM_ID=your-slack-team-id \
  ghcr.io/dvelopment/slack-mcp-server-sse:latest
```

For more detailed Docker instructions, including publishing to GitHub Container Registry, see [DOCKER.md](DOCKER.md).

## Server Endpoints

- **SSE Endpoint**: `/sse` - Connect to this endpoint to receive SSE events
- **Health Check**: `/health` - Simple health check endpoint (returns `{"status":"ok"}`)
- **Home Page**: `/` - Simple HTML page with information about the server

## Available Slack API Tools

| Tool Name | Description | Required Parameters |
|-----------|-------------|---------------------|
| `slack_list_channels` | List public channels in the workspace with pagination | None (optional: `limit`, `cursor`) |
| `slack_post_message` | Post a new message to a Slack channel | `channel_id`, `text` |
| `slack_reply_to_thread` | Reply to a specific message thread in Slack | `channel_id`, `thread_ts`, `text` |
| `slack_add_reaction` | Add a reaction emoji to a message | `channel_id`, `timestamp`, `reaction` |
| `slack_get_channel_history` | Get recent messages from a channel | `channel_id` (optional: `limit`) |
| `slack_get_thread_replies` | Get all replies in a message thread | `channel_id`, `thread_ts` |
| `slack_get_users` | Get a list of all users in the workspace | None (optional: `cursor`, `limit`) |
| `slack_get_user_profile` | Get detailed profile information for a specific user | `user_id` |

## Connecting to the Server

### Node.js Client Example

```javascript
// Replace with your server URL
const SERVER_URL = 'http://localhost:3000/sse';

// Create EventSource to connect to the SSE endpoint
const eventSource = new EventSource(SERVER_URL);

// Handle connection open
eventSource.onopen = () => {
  console.log('Connected to SSE server');
};

// Handle messages
eventSource.onmessage = (event) => {
  console.log('Received message:', event.data);
  try {
    const data = JSON.parse(event.data);
    console.log('Parsed data:', data);
  } catch (error) {
    console.log('Raw message (not JSON):', event.data);
  }
};

// Handle errors
eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};
```

See the `examples` directory for complete client examples:
- `examples/client.js` - Node.js client example
- `examples/browser-client.html` - Browser client example

### Using with Claude MCP Wrapper

To use this server with the Claude MCP wrapper:

```bash
claude_mcp_wrapper.sh -y docker run -i --rm -e SLACK_BOT_TOKEN -e SLACK_TEAM_ID mcp/slack
```

Or for an SSE-based connection:

```bash
claude_mcp_wrapper.sh -y http://localhost:3000/sse
```

## License

MIT
