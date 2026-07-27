# Tasks

- [ ] **1. Add Conversation History to Teaching Agent**
  - [ ] 1a. Update `polity_agent.py` — accept `conversation_history` param in `teach()`
  - [ ] 1b. Pass recent conversation messages to the LLM
  - [ ] 1c. Update `chat_service.py` — store conversation history per-user
  - [ ] 1d. Pass history to `polity_agent.teach()` on every call

- [ ] **2. Fix "Stuck on Concept" Problem**
  - [ ] 2a. Remove aggressive "You haven't finished X" blocking message
  - [ ] 2b. Replace with gentle context-aware status
  - [ ] 2c. Add follow-up detection in `chat_service.py` ("explain more", "I didn't understand")

- [ ] **3. Fix Routing for In-Context Questions**
  - [ ] 3a. Update `master_agent.py` system prompt for Polity-related historical questions
  - [ ] 3b. Pass current topic context to master agent
  - [ ] 3c. Change non-POLITY fallback to route to Polity when contextually appropriate

- [ ] **4. Verification**
  - [ ] 4a. Run existing tests
  - [ ] 4b. Start backend and test manually
  - [ ] 4c. Create walkthrough
