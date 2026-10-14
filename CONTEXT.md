# CookToFit: domain glossary

| Term | Meaning |
|---|---|
| **Member** | An invited, activated user. Only members get AI processing (see `access_list`). |
| **Household** | A group of members who share a pantry, kitchen setup and plans. Each member has their own targets and logs. |
| **Persona** | The member's experience level (Beginner, Intermediate or Advanced). It changes questions, visible numbers and tone. |
| **Goal plan / goal phase** | A versioned long-term goal (e.g. a cut to 72 kg), split into phases with their own targets. |
| **Target set / daily target** | The macro and micro targets in force; snapshotted per day so history never changes. |
| **Meal log item** | One eaten item with grams and a **nutrient snapshot**. Corrections are new rows that supersede old ones. |
| **Product** | A branded, packaged item (GTIN or brand + name + variant + pack) with label nutrition and serving definitions. Versioned when the brand reformulates. |
| **Food** | A generic food (IFCT, INDB or USDA), e.g. "toor dal, cooked". |
| **Submission** | A label photo or URL a user sends as evidence (last resort or dispute). Accepted values go to the shared catalogue. |
| **Coach agent** | The single LLM agent that talks to members; read and plan tools only, and every write is a draft → confirm pair. |
| **Commerce agent** | A sandboxed agent that builds carts via official MCPs; it cannot place orders without a signed user confirmation. |
| **Gate** | The webhook-level allow-list check that runs before any paid work. |
| **ShareCard** | A privacy-safe PNG of stats that a member forwards to people who aren't users. |
