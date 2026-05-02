## **💻 Autonomous Hybrid Scraper Development Prompt**

### **🎯 Objective**

Develop a **Production-Ready, Autonomous Web Scraper** using a **Hybrid, Two-Phase architecture** (Visual Discovery followed by Traditional Extraction). The scraper must be robust against minor website structural changes and provide a user-friendly interface for configuration and execution.

### **⚙️ Constraints & Technology Stack**

1. **Language:** Python (3.10+).  
2. **Core Libraries:** Playwright (for headless browser control and generating screenshots/HTML), BeautifulSoup (for fast extraction), Pydantic (for data modeling/validation), and a designated library for the LLM interaction (e.g., OpenAI SDK, Anthropic SDK).  
3. **LLM Requirement:** Must utilize a multimodal LLM (capable of processing both image and text inputs) for the discovery phase.  
4. **Configuration:** All targets must be defined in a structured, external configuration file (e.g., JSON or YAML).

### **📐 Architecture: Two-Phase Hybrid System**

The system must implement two distinct, sequential phases:

#### **Phase 1: Visual Discovery (LLM & Playwright)**

* **Input:** Target URL, a screenshot (PNG) of the rendered page, and the full, raw HTML content.  
* **LLM Task:** The LLM must analyze the visual page structure to identify **repeating item containers** (e.g., product cards, listings).  
* **LLM Output (Mandatory Schema):** The LLM must return a single, validated JSON object that defines the extraction schema for the target page. This schema must contain two critical elements:  
  1. item\_selector: The most generalized CSS selector for the repeating parent element (e.g., .product-card).  
  2. fields: An array of objects, where each object defines a field to extract, including:  
     * field\_name: (e.g., "title", "price", "image\_url")  
     * relative\_selector: The CSS selector relative to item\_selector (e.g., h3.name).  
     * extraction\_type: ("text", "attribute", or "href").

#### **Phase 2: Automated Extraction (BeautifulSoup)**

* **Input:** Raw HTML content and the validated JSON Schema generated in Phase 1\.  
* **Task:** Use the generated item\_selector to find all repeating elements in the HTML. Then, iterate through them and use the relative\_selector and extraction\_type to extract the required data using BeautifulSoup.  
* **Output:** A clean, validated JSON array of the extracted records.

### **✨ User/Admin/Developer Friendliness Requirements**

| Audience | Requirement | Implementation Detail |
| :---- | :---- | :---- |
| **Developer** | **Clear Abstraction** | Separate Phase 1 (LLM/Discovery) and Phase 2 (Extraction) into distinct, reusable Python modules (e.g., discovery.py, extractor.py). |
|  | **Robust Schemas** | Use Pydantic models to strictly define the input configuration and the LLM's JSON output (Schema for item\_selector and fields). |
| **Admin** | **Configurable Targets** | Allow the system to be run against a list of targets defined in a config.yaml file (URL, initial prompt instructions). |
|  | **Monitoring** | Implement comprehensive logging (status, success/failure, time taken, LLM token usage) for each run. |
| **User** | **Easy Execution** | Provide a main entry point script (main.py) that can be executed via command line arguments (e.g., python main.py \--target=amazon\_search). |
|  | **Clean Data Output** | Output the final extracted data into a clean CSV or JSON file named after the target (e.g., output\_amazon\_search\_20251207.json). |

### **🚀 Deliverables**

The final submission must include:

1. **Full, commented Python source code** implementing the Two-Phase architecture.  
2. A **Pydantic model** for the required LLM output schema.  
3. A **sample config.yaml** file defining one or more scrapable targets.  
4. A **README.md** file detailing installation, configuration, and execution instructions.

**Crucial Final Instruction for LLM:** Ensure the prompt sent to the multimodal model in Phase 1 is meticulously crafted to enforce the exact JSON output schema, preventing parsing errors in Phase 2\. The prompt must explicitly state: "Your response must be *only* the JSON object defined below, with no surrounding prose or markdown formatting."

