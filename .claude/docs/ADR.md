# 🏛️ Architectural Decision Records (ADR)
# STATUS: ACTIVE
# LAST UPDATED: 2024-05-20

## 📝 Usage Protocol
**For the Planner:** Consult this file *before* creating a plan to ensure architectural compliance.
**For the Builder:** Adhere to these patterns. Do not introduce competing libraries (e.g., do not use `axios` if we decided on `fetch`).

---

## 1. Fundamental Decisions (Immutable)

### [ADR-001] Package Management
* **Decision:** Use `pnpm` exclusively.
* **Rationale:** Faster installation, disk space efficiency via hard links, and strict dependency hoisting prevents "phantom dependencies."
* **Constraint:** Never run `npm install` or `yarn`. CI/CD pipelines must use `pnpm install`.

### [ADR-002] Language Strictness
* **Decision:** TypeScript in `strict` mode.
* **Rationale:** Catch errors at compile time.
* **Constraint:**
    * No `any` types allowed. Use `unknown` with narrowing if type is dynamic.
    * No `@ts-ignore` without a linked issue number in comments.

### [ADR-003] Date & Time Handling
* **Decision:** UTC everywhere on the backend.
* **Rationale:** Prevents timezone offset bugs during serialization/deserialization.
* **Constraint:**
    * **Database:** Store as `TIMESTAMP` (UTC).
    * **API:** Transmit ISO-8601 strings (`YYYY-MM-DDTHH:mm:ss.sssZ`).
    * **UI:** Convert to local time *only* at the rendering layer (React components).

---

## 2. Frontend Architecture (Next.js / React)

### [ADR-004] Server vs. Client Components
* **Decision:** Server Components by Default (RSC).
* **Rationale:** Performance (zero bundle size for server logic) and Security (secrets stay on server).
* **Constraint:** Only add `"use client"` when interactivity (`useState`, `useEffect`, event listeners) is strictly required. Move leaf interactive nodes to their own components to keep parent pages as RSCs.

### [ADR-005] Styling Strategy
* **Decision:** Tailwind CSS + Shadcn/UI (Radix Primitives).
* **Rationale:** Consistency, rapid development, and accessibility compliance.
* **Constraint:**
    * Do not use CSS Modules or `styled-components`.
    * Use `clsx` or `cn()` helper for conditional class merging.

---

## 3. Backend Architecture (Node / Database)

### [ADR-006] Database Access
* **Decision:** Prisma ORM.
* **Rationale:** Type-safe database queries synchronized with TypeScript interfaces.
* **Constraint:**
    * Do not write raw SQL queries unless strictly necessary for performance (must be documented).
    * Schema changes require a migration file (`npx prisma migrate dev`).

### [ADR-007] API Interaction
* **Decision:** Native `fetch` API.
* **Rationale:** Native support in Next.js allows for automatic request deduplication and caching controls.
* **Constraint:** Do not install `axios` or other HTTP clients.

---

## 4. Coding Conventions

### [ADR-008] Functional Paradigm
* **Decision:** Functional Composition over Object-Oriented Inheritance.
* **Rationale:** Reduces side effects and complexity in React/JS ecosystems.
* **Constraint:**
    * Prefer pure functions.
    * Avoid TypeScript `class` definitions unless required by a specific library (e.g., creating a custom Error class).

### [ADR-009] Error Handling
* **Decision:** Result Pattern (or `try/catch` at boundaries).
* **Constraint:**
    * API Routes must return structured error responses (e.g., `{ success: false, error: { code: 'NOT_FOUND', message: '...' } }`).
    * Do not throw raw strings (`throw "Error"`). Always throw `Error` objects.
