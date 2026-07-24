# Customer Chatbot Solution Accelerator

This solution accelerator empowers organizations to build intelligent, conversational customer service experiences by leveraging Microsoft Foundry's Agent Framework. With seamless integration of specialized AI agents and enterprise-grade data services, teams can create chatbots that answer catalog and policy questions and deliver exceptional support across industry scenarios. The solution pairs a scenario host application (ecommerce, healthcare, or banking) with an embeddable chat widget backed by an orchestrator agent that routes customer queries to specialized agents (catalog/product lookup and policy/knowledge), ensuring accurate, contextual responses grounded in scenario data. By unifying AI capabilities with scalable cloud infrastructure, organizations can deliver 24/7 customer support that understands context, maintains conversation history, and provides actionable insights to improve customer satisfaction and operational efficiency.

---

[**SOLUTION OVERVIEW**](#solution-overview)  \| [**QUICK DEPLOY**](#quick-deploy)  \| [**BUSINESS SCENARIO**](#business-scenario)  \| [**SUPPORTING DOCUMENTATION**](#supporting-documentation)

---

<img src="./documents/Images/solution-overview.png" width="48" />

## Solution overview

Leverages Microsoft Foundry's Agent Framework, Foundry IQ, and Azure Cosmos DB to create an intelligent customer chatbot with specialized agents for catalog lookup and knowledge management. Deploy one industry scenario per environment—**ecommerce**, **healthcare**, or **banking**. Each deployment includes a scenario host UI for browsing catalog content and an embedded chat widget (text and voice) that uses an orchestrator agent to route queries to specialized agents. Those agents use hybrid search across catalog and policy documents to return accurate, contextual answers.

### Solution architecture

The solution consists of:

|![image](./documents/Images/solution-architecture.png)|
|---|

**Application layout:**

| App | Role |
|---|---|
| **Scenario host** (`scenario-app`) | Industry-specific frontend and API (product grid, hospital services, or banking products) |
| **Chat service** (`chat-app`) | Chat widget UI/API, Foundry agent orchestration, and Voice Live; embedded into the host via `widget.js` |

Scenario packs under `scenarios/{ecommerce|healthcare|banking}/` supply manifests, seed data, and agent instructions. Deploy one scenario per `azd` environment with `AZURE_ENV_SCENARIO`. See the [scenario deployment guide](./documents/scenario-deployment-guide.md) for details.

### Additional resources

For detailed technical information, see the component READMEs:

[Technical Architecture](./documents/TechnicalArchitecture.md)

---

## Features

### Key features

<details open>  

<summary>Click to learn more about the key features this solution enables</summary>  

- **Intelligent agent orchestration using Microsoft Agent Framework**  
  Leverage Microsoft Foundry's Agent Framework with an orchestrator agent that uses automatic tool selection to route customer queries to specialized agents (catalog/product lookup and policy/knowledge). The orchestrator analyzes user intent and automatically invokes the appropriate specialist agent as a tool, ensuring queries are handled by the most capable agent for each task.

- **Multi-scenario deployment**  
  Choose **ecommerce** (Contoso Paints), **healthcare** (Contoso Health), or **banking** (Contoso Banking) per environment. Each scenario packs its own host UI, API surface, search indexes, seed data, and Foundry agent instructions under `scenarios/`.

- **Embeddable chat widget**  
  The chat experience ships as a standalone widget (`widget.js`) from the chat frontend and embeds into the scenario host. Customers get text chat with product/service cards where applicable, plus Voice Live for spoken conversations—without coupling the host UI to the chat stack.

- **Hybrid search capabilities**  
  Foundry IQ provides fast, accurate catalog and policy document retrieval using semantic and keyword search, enabling natural language queries across industry knowledge bases. Specialized agents access scenario-specific search indexes to retrieve relevant information.

- **Natural language interaction**  
  Microsoft Foundry's Agent Framework orchestrates multi-agent workflows using GPT-5.4-mini to deliver conversational, context-aware responses that understand customer intent. The framework maintains conversation threads and context across sessions, enabling natural, flowing conversations with specialized agents. Voice Live uses the same Foundry pipeline with scenario-aware grounding.

- **Modern scenario host experience**  
  React-based host frontend for browsing the industry catalog (paints, clinical services, or banking products) with an integrated floating chat assistant for seamless discovery and support

- **Scalable data architecture**  
  Azure Cosmos DB stores catalogs, transactions/orders, and chat history with high availability and global distribution, ensuring fast access to customer and catalog data

</details>

---

## Getting Started

<img src="./documents/Images/quick-deploy.png" width="48" />

### Quick deploy

#### How to install or deploy

Follow the quick deploy steps on the deployment guide to deploy this solution to your own Azure subscription.

[Click here to launch the deployment guide](./documents/DeploymentGuide.md)

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/customer-chatbot-solution-accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/customer-chatbot-solution-accelerator) | [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvY3VzdG9tZXItY2hhdGJvdC1zb2x1dGlvbi1hY2NlbGVyYXRvci9yZWZzL2hlYWRzL21haW4vaW5mcmEvdnNjb2RlX3dlYiIsICJpbmRleFVybCI6ICIvaW5kZXguanNvbiIsICJ2YXJpYWJsZXMiOiB7ImFnZW50SWQiOiAiIiwgImNvbm5lY3Rpb25TdHJpbmciOiAiIiwgInRocmVhZElkIjogIiIsICJ1c2VyTWVzc2FnZSI6ICIiLCAicGxheWdyb3VuZE5hbWUiOiAiIiwgImxvY2F0aW9uIjogIiIsICJzdWJzY3JpcHRpb25JZCI6ICIiLCAicmVzb3VyY2VJZCI6ICIiLCAicHJvamVjdFJlc291cmNlSWQiOiAiIiwgImVuZHBvaW50IjogIiJ9LCAiY29kZVJvdXRlIjogWyJhaS1wcm9qZWN0cy1zZGsiLCAicHl0aG9uIiwgImRlZmF1bHQtYXp1cmUtYXV0aCIsICJjb25uZWN0aW9uU3RyaW5nIl19) 
|---|---|---|

> **Note**: Some tenants may have additional security restrictions that run periodically and could impact the application (e.g., blocking public network access). If you experience issues or the application stops working, check if these restrictions are the cause. In such cases, consider deploying the WAF-supported version to ensure compliance. To configure, [Click here](./documents/DeploymentGuide.md#31-choose-deployment-type-optional).

> ⚠️ **Important: Check Azure OpenAI Quota Availability**  
> To ensure sufficient quota is available in your subscription, please follow [quota check instructions guide](./documents/QuotaCheck.md) before you deploy the solution.

> **Tip: Choose a scenario before first deploy**  
> Default is **ecommerce**. For healthcare or banking, set the scenario on a new environment first:  
> `azd env set AZURE_ENV_SCENARIO healthcare` (or `banking`), then `azd up`. See [scenario deployment guide](./documents/scenario-deployment-guide.md).

## Guidance

### Prerequisites and costs

To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups, resources, app registrations, and assign roles at the resource group level**. This should include Contributor role at the subscription level and Role Based Access Control role on the subscription and/or resource group level.

Here are some example regions where the services are available: East US, East US2, Australia East, UK South, France Central.

Check the [Azure Products by Region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/?products=all&regions=all) page and select a **region** where the following services are available.

Pricing varies by region and usage, so it isn't possible to predict exact costs for your usage. The majority of Azure resources used in this infrastructure are on usage-based pricing tiers. However, some services—such as Azure Container Registry, which has a fixed cost per registry per day, and others like Azure Cosmos DB or App Service when provisioned—may incur baseline charges regardless of actual usage.

Use the [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator) to calculate the cost of this solution in your subscription. 

Review a [sample pricing sheet](https://azure.com/e/708895d4fc4449b1826016fad8a83fe0) in the event you want to customize and scale usage.

_Note: This is not meant to outline all costs as selected SKUs, scaled use, customizations, and integrations into your own tenant can affect the total consumption of this sample solution. The sample pricing sheet is meant to give you a starting point to customize the estimate for your specific needs._

>⚠️ **Important:** To avoid unnecessary costs, remember to take down your app if it's no longer in use, either by deleting the resource group in the Portal or running `azd down`.

## Resources

| Product | Description | Tier / Expected Usage Notes | Cost |
|---|---|---|---|
| [Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry) | Used to orchestrate and build AI workflows with specialized agents for customer service. | Free Tier | [Pricing](https://azure.microsoft.com/pricing/details/ai-studio/) |
| [Azure AI Services (OpenAI)](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/overview) | Enables language understanding, chat, and realtime voice (Voice Live) using GPT models for conversational AI. | S0 Tier; pricing depends on token volume and model used (e.g., GPT-5.4-mini, gpt-realtime-mini). | [Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/) |
| [Foundry IQ](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search) | Provides hybrid search capabilities for scenario catalogs and policy documents with semantic and keyword search. | Basic Tier; pricing based on search units and data storage. | [Pricing](https://azure.microsoft.com/pricing/details/search/) |
| [Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/overview) | Hosts the scenario and chat frontend apps and FastAPI backends. | Basic or Standard plan; includes a free tier for development. | [Pricing](https://azure.microsoft.com/pricing/details/app-service/windows/) |
| [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-intro) | Stores and serves container images used by Azure App Service. | Basic Tier; fixed daily cost per registry. | [Pricing](https://azure.microsoft.com/pricing/details/container-registry/) |
| [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction) | Stores scenario catalogs, orders/transactions, and chat conversation history. | Serverless or provisioned throughput; pricing based on request units and storage. | [Pricing](https://azure.microsoft.com/pricing/details/cosmos-db/) |
| [Azure Monitor / Log Analytics](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-overview) | Collects and analyzes telemetry and logs from services and applications. | Pay-as-you-go; charges based on data ingestion volume. | [Pricing](https://azure.microsoft.com/pricing/details/monitor/) |

---

<img src="./documents/Images/business-scenario.png" width="48" />

## Business scenario

The solution provides an industry host experience with an embedded AI chat assistant, enabling customers to browse catalog content, get recommendations, and receive support through natural language (text and voice).

---

The sample data illustrates how this accelerator can be used for customer service across multiple industries. Deploy **one scenario per Azure environment**. Sample questions below are grounded in each scenario’s catalog and policy documents.

### Ecommerce — Contoso Paints *(default)*

Contoso Paints is a paint retailer looking to provide exceptional support through an intelligent chatbot. Customers previously had to navigate complex product catalogs and policy documents, or contact support for help. With the accelerator, they browse paint shades on the host site and use the embedded chat widget for color recommendations, warranties, and returns. The orchestrator routes queries to a product agent and a policy agent so answers stay grounded in the catalog and company documents.

**Try asking:**

- "I'm looking for a cool, blue-toned paint that feels calm but not gray"
- "Show me warm white paint colors"
- "What's your warranty policy?"
- "What is your return policy?"

### Healthcare — Contoso Health

Contoso Health uses the same pattern for a patient-facing hospital experience. The host UI surfaces clinical services and departments; the chat widget answers questions about services, visiting hours, billing, and patient rights—without providing medical diagnosis or emergency care advice.

**Try asking:**

- "What are visiting hours?"
- "Tell me about primary care services"
- "Do you offer radiology and imaging?"
- "What are patient rights related to billing?"

### Banking — Contoso Banking

Contoso Banking demonstrates deposit, lending, and card products with an assistant for account features, fees, and digital banking policies. The experience is informational only and must not collect or expose full account numbers, PINs, or passwords.

**Try asking:**

- "What savings options are available?"
- "Show me the credit cards you offer"
- "What's included with Everyday Checking?"
- "How do I report suspected fraud?"

⚠️ The sample data used in this repository is synthetic and generated. The data is intended for use as sample data only. Healthcare and banking scenarios are demos only—not medical devices, medical advice, or financial advice.

### Business value

<details>

  <summary>Click to learn more about what value this solution provides</summary>

  - **Intelligent customer support** 

Enable conversational AI agents that understand customer intent and provide accurate, contextual responses by routing queries to specialized agents that access catalogs and policy documents through Foundry IQ. The orchestrator agent automatically selects the appropriate specialist based on the query, reducing support ticket volume and improving customer satisfaction with 24/7 availability across text and voice.

- **Accelerated discovery**

Help customers find products, services, or account offerings faster through natural language queries and intelligent search. Enable personalized recommendations based on needs, preferences, and conversation context, increasing engagement and conversion.

- **Reusable embeddable chat**

Ship a single chat widget and backend that plug into different industry hosts. Scenario packs swap data, instructions, and branding without rebuilding the chat stack from scratch.

- **Scalable and maintainable architecture**

Deliver consistent customer experiences at scale with a separation between the industry host and the chat service. The Microsoft Foundry Agent Framework enables easy extension with new agents, scenarios, or data sources as business needs evolve.

</details>

---

<img src="./documents/Images/supporting-documentation.png" width="48" />

## Supporting documentation

### Security guidelines

This solution uses [Managed Identity](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview) for secure access to Azure resources during local development and production deployment, eliminating the need for hard-coded credentials.

To maintain strong security practices, it is recommended that GitHub repositories built on this solution enable [GitHub secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) to detect accidental secret exposure.

Additional security considerations include:

- Enabling [Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud) to monitor and secure Azure resources.
- Using [Virtual Networks](https://learn.microsoft.com/en-us/azure/app-service/networking-features) or [firewall rules](https://learn.microsoft.com/en-us/azure/app-service/app-service-ip-restrictions) to protect Azure App Service from unauthorized access.
- Implementing authentication and authorization for the frontend application using Microsoft Entra ID or other identity providers.

### Cross references

Check out similar solution accelerators

| Solution Accelerator | Description |
|---|---|
| [Agentic Applications for Unified Data Foundation](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator) | Empowers organizations to make faster, smarter decisions at scale by leveraging agentic AI solutions built on a unified data foundation with Microsoft Fabric. |
|[GPT-RAG&nbsp;Accelerator](https://github.com/Azure/gpt-rag)| Secure enterprise GPT assistant framework that uses Retrieval-Augmented Generation to ground answers on your data. It provides a ready architecture (Azure OpenAI + knowledge search) for building AI chatbots that “know” your enterprise content, with built-in security and scalability.|
|[Document&nbsp;Processing&nbsp;Accelerator](https://github.com/Azure/doc-proc-solution-accelerator/) | Modular document AI pipeline that automatically extracts, analyzes, and indexes information from unstructured documents (PDFs, images, etc.) at scale. It offers plug-and-play components for OCR, classification, summarization, and integration to search or chatbots – speeding up data ingestion with enterprise security.|

<br/> 

💡 Want to get familiar with Microsoft's AI and Data Engineering best practices? Check out our playbooks to learn more

| Playbook | Description |
|:---|:---|
| [AI&nbsp;playbook](https://learn.microsoft.com/en-us/ai/playbook/) | The Artificial Intelligence (AI) Playbook provides enterprise software engineers with solutions, capabilities, and code developed to solve real-world AI problems. |
| [Data&nbsp;playbook](https://learn.microsoft.com/en-us/data-engineering/playbook/understanding-data-playbook) | The data playbook provides enterprise software engineers with solutions which contain code developed to solve real-world problems. Everything in the playbook is developed with, and validated by, some of Microsoft's largest and most influential customers and partners. |

<br/> 

## Provide feedback

Have questions, find a bug, or want to request a feature? [Submit a new issue](https://github.com/microsoft/customer-chatbot-solution-accelerator/issues) on this repo and we'll connect.

## Responsible AI Transparency FAQ 

Please refer to [Transparency FAQ](./TRANSPARENCY_FAQ.md) for responsible AI transparency details of this solution accelerator.

## Disclaimers

To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, "Microsoft Products and Services"), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services.

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit https://aka.ms/exporting.

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer's implementation of the Online Services.

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, "HIGH-RISK USE"), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.
