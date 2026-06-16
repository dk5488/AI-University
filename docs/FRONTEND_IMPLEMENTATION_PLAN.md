# AI University Frontend Implementation Plan

## Goal
Build a modern, responsive, and "alive" web application that serves as the interface for the AI University backend. The UI should feel like a high-end coaching platform: professional, analytical, yet encouraging.

## Tech Stack
- **Framework:** React 18+ (TypeScript)
- **Build Tool:** Vite
- **Styling:** Vanilla CSS (CSS Modules for scoping)
- **State Management:** React Context (for simple globals) + TanStack Query (for server state)
- **Icons:** Lucide React
- **Routing:** React Router 6

---

## Design Principles
1. **Focus on Content:** Use clean typography and generous whitespace to ensure source material and explanations are easy to read.
2. **Interactive Feedback:** Smooth transitions, loading skeletons, and "active" states for AI responses.
3. **UPSC Aesthetic:** Use a color palette of Deep Navy (#1a2b3c), Professional Gold (#d4af37), and Clean White (#ffffff).

---

## Milestones

### F-12: Project Foundation & Layout
- Initialize Vite project with TypeScript.
- Set up CSS reset and global variables (colors, spacing).
- Create a `Shell` component (Sidebar, Top Nav, Main Content area).
- Implement responsive breakpoints.

### F-13: Dashboard & Progress Visualization
- Build the Dashboard page (`GET /dashboard`).
- Create progress cards for topics.
- Implement a "Due Revisions" list with actionable buttons.
- Display "Available Subjects" grid.

### F-14: AI Chat Interface (Teaching Mode)
- Implement a chat UI with message bubbles (User vs. AI).
- Add support for Markdown rendering in AI messages.
- Build the "Sources" drawer/accordion to show grounded references.
- Implement "Next Actions" buttons that trigger the next step in the loop.

### F-15: Quiz & Assessment Workflow
- Create a focused "Quiz Mode" layout (distraction-free).
- Implement MCQ selection logic and timer.
- Build the "Results" screen with score, percentage, and LLM mentor feedback.
- Integrate with `RevisionService` (verify revision tasks are created on failure).

### F-16: Polish & Performance
- Add loading states (skeletons) for all async operations.
- Implement global error boundary and toast notifications for backend failures.
- Add smooth animations for chat message entry.
- Final responsive audit for mobile/tablet.

---

## Technical Patterns
- **Atomic Design:** Organize components into `atoms` (Button), `molecules` (FormField), `organisms` (ChatWindow), and `pages`.
- **Service Layer:** Use a dedicated `api/` directory for Axios/Fetch calls, keeping components focused on presentation.
- **Strict Typing:** Share types with the backend domain where possible.
