# Flight Agent

An AI-powered assistant to find and book flights with ease, presenting real-time options in a rich, interactive format.

**Live Demo:** `https://flight-agent-280879789566.me-central1.run.app`

---

## 🎯 About The Project

This AI agent acts as a conversational flight booking assistant. It uses **GPT-4o** to understand user requests for flight searches, including details like origin, destination, and departure date. It then utilizes the **Duffel API** to fetch live flight data and presents the top 5 results as visually appealing, interactive HTML cards, each with a direct link to initiate the booking process.

## 🛠️ Tech Stack

-   **Framework**: [Cycls](https://cycls.com/)
-   **Language**: Python
-   **APIs**:
    -   **OpenAI API (GPT-4o)**: For conversational logic and understanding user intent.
    -   **Duffel API**: For sourcing real-time flight data and offers.

## 🚀 Getting Started

To run this project locally, clone the repository, create a `.env` file with your API keys, install dependencies, and run the agent.

```bash
# 1. Clone the repository
git clone [https://github.com/your-username/flight-agent.git](https://github.com/your-username/flight-agent.git)
cd flight-agent

# 2. Create and populate your .env file with all required keys
# Example: echo "OPENAI_API_KEY=sk-..." > .env
# Required keys: CYCLS_API_KEY, OPENAI_API_KEY, DUFFEL_API_KEY
```
