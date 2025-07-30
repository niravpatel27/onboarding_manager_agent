# Onboarding Manager Agent

An autonomous agent system for automating the onboarding process of member organizations to Linux Foundation projects, built with the `agno` framework.

## Overview

This system streamlines the complex process of onboarding new member organizations to Linux Foundation projects (such as CNCF, LF networking). It orchestrates multiple specialized agents to handle different aspects of the onboarding workflow:

- **OrchestratorAgent**: Master coordinator that manages the entire onboarding workflow
- **MemberContactFetcherAgent**: Retrieves member contacts from the Member Service API
- **ProjectCommitteeAgent**: Manages project committee memberships and role assignments
- **SlackOnboardingAgent**: Handles Slack workspace invitations and channel assignments
- **EmailCommunicationAgent**: Sends committee-specific welcome emails
- **LandscapeUpdateAgent**: Updates project landscape with organization logos
- **DatabaseAgent**: Manages database operations via MCP (Model Context Protocol)

The system processes contacts in batches, includes retry logic with exponential backoff, and provides comprehensive error handling and monitoring.

## Key Features

- **Batch Processing**: Processes contacts in configurable batches for optimal performance
- **Error Resilience**: Built-in retry logic with exponential backoff for transient failures
- **Contact Classification**: Automatically categorizes contacts as primary, marketing, or technical
- **Committee Management**: Assigns contacts to appropriate committees based on their roles
- **Multi-Channel Communication**: Handles both Slack invitations and email communications
- **Landscape Integration**: Automatically creates pull requests to update project landscapes
- **Local Development**: Includes stub services for testing without external dependencies

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 14+ (for MCP SQLite server)
- `agno` framework
- SQLite (included with Python)
- Environment variables for production (see Configuration section)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd onboarding_manager_agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for MCP SQLite server)
npm install
```

### Running the Application

```bash
# Production mode (requires API credentials)
python main.py "Acme Corp" "kubernetes"

# Local development with stub services
export RUN_MODE=local
python main_agents_with_stubs.py "Acme Corp" "cncf"

# With workflow tracing for debugging
python trace_workflow.py "Tech Innovations Inc" "prometheus"
```

### Project Structure

```
onboarding_manager_agent/
├── src/                           # Modular production-ready structure
│   ├── agents/                    # Agent implementations
│   │   ├── orchestrator.py        # Master orchestrator
│   │   └── specialized/           # Specialized agents
│   │       ├── member_contact.py
│   │       ├── project_committee.py
│   │       ├── slack_onboarding.py
│   │       ├── email_communication.py
│   │       ├── landscape_update.py
│   │       └── database.py
│   ├── models/                    # Data models
│   │   ├── contact.py
│   │   ├── project.py
│   │   └── events.py
│   ├── tools/                     # External integrations
│   │   ├── api_clients/           # API client implementations
│   │   ├── mcp_client.py          # MCP client implementation
│   │   └── mcp_database.py        # MCP database abstraction
│   ├── config/                    # Configuration
│   │   └── settings.py
│   ├── utils/                     # Utilities
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   └── metrics.py
│   └── main.py                    # Entry point
├── main_agents_with_stubs.py      # Single-file implementation
├── stub_services.py               # Mock services for local testing
├── config.py                      # Simple config for stubs
├── trace_workflow.py              # Natural workflow tracing
├── example.py                     # Example showing full structure
├── package.json                   # Node.js dependencies for MCP
├── requirements.txt               # Python dependencies
└── CLAUDE.md                      # AI assistant guidelines
```

## Database Implementation (MCP)

This project uses the **Model Context Protocol (MCP)** for all database operations. MCP is a standardized protocol that enables AI assistants to interact with external tools and data sources through a consistent interface.

### MCP Architecture

```
┌─────────────────┐
│  DatabaseAgent  │
└────────┬────────┘
         │
┌────────▼────────────┐
│ OnboardingDatabase  │
│    ToolsMCP         │
└────────┬────────────┘
         │
┌────────▼────────────┐
│ MCPDatabaseOperations│
└────────┬────────────┘
         │
┌────────▼────────────┐
│    MCPClient        │
└────────┬────────────┘
         │ MCP Protocol
┌────────▼────────────┐
│ MCP SQLite Server   │
│ (External Process)  │
└─────────────────────┘
```

### MCP Setup

1. **Install dependencies:**
   ```bash
   # Install Node.js dependencies (for MCP SQLite server)
   npm install
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

2. The MCP SQLite server will be automatically spawned when the application runs.

### Benefits of MCP

- **Protocol-based communication**: Standardized interface for database operations
- **Process isolation**: Database runs in a separate process for better security
- **Tool discovery**: Can dynamically discover available database operations
- **Future-proof**: Easy to swap database backends without changing application code

## How It Works

### Workflow Steps

1. **Organization Lookup**: Fetches member organization ID from Member Service API
2. **Contact Retrieval**: Retrieves all contacts associated with the organization
3. **Project Details**: Gets project information including committee structures
4. **Contact Processing** (in batches):
   - Classifies contacts by type (primary, marketing, technical)
   - Assigns to appropriate committees
   - Sends Slack invitations with committee-specific channels
   - Sends personalized welcome emails
5. **Landscape Update**: Creates pull request to add organization logo to project landscape
6. **Completion Report**: Generates summary of all actions taken

### Contact Classification

Contacts are automatically classified based on their job titles:
- **Primary**: C-level executives (CEO, CTO, CFO) → Governing Board
- **Marketing**: Marketing/PR roles → Marketing Committee
- **Technical**: Engineering/technical roles → Technical Committee

## Local Development

### Stub Services
The repository includes comprehensive stub services that simulate all external APIs:
- **Member Service API**: Returns sample organization and contact data
- **Project Service API**: Provides project and committee information
- **Slack API**: Simulates invitation sending
- **Email Service**: Logs email sending
- **GitHub API**: Simulates pull request creation

### Sample Data
Pre-configured with realistic test data:
- **Organizations**: Acme Corp, Tech Innovations Inc, Cloud Systems Ltd
- **Projects**: CNCF, Prometheus, Envoy
- **Contacts**: Various roles including CEO, VP Marketing, CTO, Engineers
- **Committees**: Governing Board, Marketing Committee, Technical Committee

### Workflow Tracing
The `trace_workflow.py` script provides enhanced debugging output:
- Natural language descriptions of operations
- Color-coded output by operation type
- Timing information for performance analysis
- Grouped operations by workflow phase

## Configuration

### Environment Variables

For production deployment, set the following environment variables:

```bash
# API Endpoints
export MEMBER_SERVICE_API_URL="https://api.linuxfoundation.org/members"
export PROJECT_SERVICE_API_URL="https://api.linuxfoundation.org/projects"
export SLACK_API_URL="https://slack.com/api"
export EMAIL_SERVICE_URL="https://email.service.org"
export GITHUB_API_URL="https://api.github.com"

# Authentication Tokens
export MEMBER_SERVICE_API_TOKEN="your-member-service-token"
export PROJECT_SERVICE_API_TOKEN="your-project-service-token"
export SLACK_API_TOKEN="your-slack-token"
export EMAIL_SERVICE_API_KEY="your-email-api-key"
export GITHUB_TOKEN="your-github-token"

# Run Mode
export RUN_MODE=production  # or 'local' for stub services
```

### Agent Configuration

See `AgentSystemConfig` class (main.py:1150-1180) for additional settings:
- Batch size (default: 10 contacts)
- Retry attempts (default: 3)
- Retry delay (default: 2 seconds)
- Request timeout (default: 30 seconds)
- SLA thresholds for monitoring

## Architecture

### System Design

```
┌─────────────────────┐
│  OrchestratorAgent  │ ← Entry point, manages workflow
└──────────┬──────────┘
           │
    ┌──────┴──────┬────────┬────────┬────────┬────────┐
    │             │        │        │        │        │
┌───▼────┐ ┌─────▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌──▼───┐
│Member   │ │Project │ │Slack │ │Email │ │Lands.│ │ DB   │
│Contact  │ │Comm.   │ │Onb.  │ │Comm. │ │Update│ │Agent │
│Fetcher  │ │Agent   │ │Agent │ │Agent │ │Agent │ │(MCP) │
└─────────┘ └────────┘ └──────┘ └──────┘ └──────┘ └──────┘
     │           │          │        │        │        │
     └───────────┴──────────┴────────┴────────┴────────┘
                        External APIs
```

### Key Design Patterns

- **Agent Pattern**: Each agent has a single responsibility
- **Orchestrator Pattern**: Central coordinator manages workflow
- **Batch Processing**: Efficient handling of multiple contacts
- **Circuit Breaker**: Prevents cascading failures
- **Retry with Backoff**: Handles transient failures gracefully

## Testing

### Running Tests

```bash
# Run all tests (once implemented)
# python -m pytest

# Test specific scenarios
python trace_workflow.py "Acme Corp" "cncf"
python trace_workflow.py "Tech Innovations Inc" "prometheus"
```

### Testing Edge Cases

```bash
# Test with non-existent organization
python trace_workflow.py "Unknown Corp" "cncf"

# Test with organization having many contacts
python trace_workflow.py "Cloud Systems Ltd" "envoy"
```

## Monitoring and Observability

The system includes built-in monitoring capabilities:
- Operation timing and performance metrics
- Success/failure rates for each agent
- Batch processing statistics
- Error tracking and reporting

## Troubleshooting

### Common Issues

1. **API Connection Errors**: Check environment variables and network connectivity
2. **Authentication Failures**: Verify API tokens are valid and not expired
3. **Database Errors**: Ensure SQLite database has proper permissions
4. **Batch Processing Failures**: Check logs for specific contact processing errors
5. **MCP Connection Issues**: 
   - Ensure Node.js is installed (`node --version`)
   - Check that `npx` is available in PATH
   - Verify MCP SQLite server is installed (`npm list mcp-sqlite`)

### Debug Mode

Enable verbose logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

## Future Enhancements

1. **API Rate Limiting**: Implement proper rate limiting for external APIs
2. **Webhook Support**: Add webhook endpoints for real-time updates
3. **Dashboard**: Create web interface for monitoring onboarding progress
4. **Metrics Export**: Integrate with Prometheus/Grafana for monitoring
5. **Multi-tenancy**: Support multiple Linux Foundation projects simultaneously
6. **Audit Trail**: Comprehensive logging of all onboarding actions

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for all classes and methods
- Include unit tests for new features
- Update documentation as needed

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- Built with the `agno` framework for agent orchestration
- Designed for the Linux Foundation's member onboarding process
- Inspired by modern microservice architectures