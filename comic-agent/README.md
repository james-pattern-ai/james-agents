# Comic Agent: Automated Comic Book Cataloger

## 1. Project Overview

The Comic Agent is a Python-based, agentic application designed to automate the process of cataloging a personal comic book collection. It can process comic book images to identify, grade, and value them, and it can also answer natural language questions about the inventory.

The ultimate goal is to create a comprehensive, digitized inventory that is persisted in a Zoho inventory management system, with the agent acting as the intelligent interface to this system.

### Core Features:
-   **Image Analysis**: Uses Google's Vertex AI (with a placeholder for the Gemma model) to extract details like series title, issue number, and publisher from comic book cover images.
-   **Automated Grading**: Applies a rule-based system to estimate a comic's grade (e.g., 9.2, 8.0) based on detected defects.
-   **Pricing and Valuation**: Integrates with external APIs (Comic Vine, GoCollect, eBay) to fetch fair market value (FMV) and calculate a conservative valuation.
-   **Conversational Querying**: Can answer natural language questions about the comic inventory (e.g., "What is my most valuable comic?").
-   **Zoho Inventory Integration**: Persists the final, authoritative comic records into a Zoho inventory system via a dedicated MCP (Mode-Controller-Proxy) Server.
-   **Local Caching**: Uses a local SQLite database as a transitional datastore or cache to stage data before it is persisted to Zoho, preventing data loss and duplicate processing.

---

## 2. Agentic Workflow Architecture

The system is designed around a **single, unified Comic Agent** that handles both cataloging and querying. This agent interacts with external services and the final system of record (Zoho) through a series of tools and a dedicated MCP server.

The local SQLite database serves as a **transitional cache or staging area**, not the final source of truth.

```mermaid
graph TD;
    subgraph User Interaction
        A[Image or Question]
    end

    subgraph Comic Agent Core
        B{Agent "Brain" (Reason-Act Loop)};
    end
    
    subgraph Agent Tools
        C[Vision Tool];
        D[Pricing Tool];
        E[Database Tool];
        F[Zoho Tool];
    end

    subgraph Data & Services
        G(SQLite Cache);
        H(Zoho MCP Server);
        I[External APIs GCS, Vertex AI, GoCollect, etc.];
        J[Zoho Inventory];
    end
    
    A --> B;
    B --> C;
    B --> D;
    B --> E;
    B --> F;
    
    C --> I;
    D --> I;
    E --> G;
    F --> H;
    H --> J;
```
### How it Works:
1.  **Goal**: The agent is given a high-level goal, such as "catalog this image" or "how many Batman comics do I have?".
2.  **Reasoning Loop**: The agent analyzes its goal and its current state, then selects the appropriate tool to move closer to completion.
3.  **Tool Use**:
    - For **cataloging**, it uses the Vision, Pricing, and Database tools to process the comic and stage it in the local SQLite cache.
    - For **querying**, it uses the Database Tool to retrieve information from the cache.
    - For **final persistence**, it uses the Zoho Tool to communicate with the Zoho MCP Server, which then updates the authoritative inventory in Zoho.

---

## 3. Key Components & File Structure

This project is organized into several key files that support the agentic workflow:

-   **`run_agent.py`** (to be created, formerly `run_workflow.py`): The main entry point that initializes the agent and gives it a high-level goal.
-   **`agent.py`** (to be created): The core of the application, containing the `ComicBookAgent` and its reasoning loop.
-   **`tools/`** (to be created): A new directory that will contain the agent's tools. For example:
    -   `vision_tools.py`: Wrappers for the Vertex AI vision model.
    -   `pricing_tools.py`: Wrappers for the GoCollect and eBay APIs.
    -   `zoho_tools.py`: Functions for communicating with the Zoho MCP server.
-   **`models.py`**: Defines the database schema for the local cache using SQLAlchemy.
-   **`comics.db`**: The local SQLite database file used for caching.
-   **`api_key_guide.md`**: Instructions on how to obtain and configure the necessary API keys.
-   **`sample_comics/`**: A directory containing sample comic book images for testing.
-   **`zoho_mcp/`** (to be created): A directory that will house the Zoho MCP server as a separate application.

---

## 4. Setup and Installation

Follow these steps to set up your local environment and run the Comic Agent.

### Step 1: Install Dependencies

This project uses Python 3. Install the required libraries using pip:

```bash
pip install -r requirements.txt
```

### Step 2: Configure API Keys

The application requires API keys for several external services.

1.  **Obtain API Keys**: Follow the instructions in the **[api_key_guide.md](api_key_guide.md)** to get the necessary keys.
2.  **Create a `.env` file**: In the root directory of the project, create a file named `.env`.
3.  **Add Keys to `.env`**: Populate the `.env` file with your keys as shown in the guide.

---

## 5. How to Run

Once the setup is complete, you can run the main agent script from the root directory:

```bash
python3 run_agent.py
```

The script will:
1.  Initialize the database cache.
2.  Take a user goal as input (e.g., process a directory of images).
3.  Initialize the agent and run its main loop.
4.  Log the agent's progress to the console.