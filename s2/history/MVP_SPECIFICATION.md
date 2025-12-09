# MVP Specification: "BizBot" - The Autonomous Business Operator

### 1. Core Objective (MVP)
The goal of the MVP is to prove the loop: **Asset Acquisition/Creation → Deployment → Maintenance**.
*   **Focus**: Digital Products (Gumroad, info-products) and simple Micro-SaaS.
*   **Constraint**: Low budget (<$500), high automation.

### 2. Architecture & Tech Stack
*   **Brain**: `Claude 3.5 Sonnet` (for reasoning/code) + `GPT-4o` (for creative content).
*   **Hands (Browser)**: `Playwright` connected to an existing Chrome profile (to bypass auth challenges).
*   **Memory**: `SQLite` database to track assets, revenue, and tasks.
*   **Payment/Money**: Stripe Connect or Gumroad API (for creating) / Manual Human Approval (for acquiring).
*   **Host**: A simple local server or VPS (e.g., DigitalOcean).

### 3. Key Capabilities (MVP Scope)

#### A. CREATE (The "Maker" Module)
Instead of building complex platforms, the MVP focuses on **Digital Assets**.
*   **Idea Generation**: Scrapes trending keywords on X.com and Reddit (r/sidehustle) to propose simple products (e.g., "Notion Template for Crypto Tracking" or "Python Bot for Instagram").
*   **Asset Generation**:
    *   *Code*: Writes the script.
    *   *Content*: Generates the PDF/E-book text using LLMs.
*   **Listing Creation**:
    *   Auto-generates a `Gumroad` or `Lemon Squeezy` product page description.
    *   Uploads the asset.
    *   **Human Check**: Pauses for you to click "Publish".

#### B. ACQUIRE (The "Scout" Module)
Buying businesses is high-risk, so the MVP is a **Research Agent**.
*   **Scouting**: Daily scan of **Flippa**, **IndieMaker**, and **Acquire.com** for listings under $500.
*   **Filtering Criteria**:
    *   Age > 6 months.
    *   Traffic verified (if visible).
    *   Tech stack: HTML/CSS/JS or simple WordPress (easy to maintain).
*   **Due Diligence Report**: Generates a daily summary: *"Found 3 potentials. Top pick: A simple CSS generator site. Traffic 500/mo. Price $300."*

#### C. MAINTAIN (The "Operator" Module)
Once a business is "owned" (in the DB), the Agent runs daily loops.
*   **Marketing Run**:
    *   Uses `x_poster.js` to post daily updates/tips related to the product niche.
    *   Replies to comments containing keywords.
*   **Uptime Monitoring**: Checks if the landing pages are up every hour.
*   **Customer Support**: Connects to the support email; drafts replies to FAQs for your approval.

### 4. The Human Control Center (Dashboard)
A simple `Streamlit` or `Next.js` dashboard for you.
1.  **Inbox**: Proposals (Create this? Buy this? Reply to this?).
2.  **Portfolio**: List of active assets and their daily views/sales.
3.  **Logs**: What the agent did today (e.g., "Posted 3 tweets, scanned 50 listings").

### 5. Implementation Plan (Week 1)
1.  **Day 1**: Build the **Scraper** for Reddit/X to find "What people want".
2.  **Day 2**: Build the **Product Generator** (takes a topic, outputs a PDF/Code ZIP).
3.  **Day 3**: Integrate `x_poster.js` into a generic **Marketing Loop**.
4.  **Day 4**: Build the **Dashboard** to view agent logs.
5.  **Day 5**: First live run—Command it to "Create a product about 'AI Automation'".

### 6. Safety Protocols
*   **Budget Hard Cap**: Agent cannot spend money. It can only *stage* transactions for you to execute.
*   **Content Shield**: All public posts must pass a "safety check" (LLM tailored to detect offensive/hallucinated content) or require human approval.
