# 🧠 Project Knowledge Base & Troubleshooting Log

## 📝 Usage Protocol
**For the Agents:**
1.  **Before Planning:** The `Researcher` should scan this file for "Known Issues" related to the current task.
2.  **After Debugging:** If the `Critic` solves a difficult or recurring error, the `Builder` MUST append a new entry here.
3.  **Format:** Use the **Incident Template** below. Keep it concise.

---

## ⚠️ Architectural Quirks (The "Gotchas")
*Permanent rules derived from past failures. Read this first.*

- **[Example]:** We use `pnpm`, not `npm`. Never run `npm install`.
- **[Example]:** The database requires SSL connection in production but NOT in local dev.
- **[Example]:** All dates must be stored in UTC; conversion happens only at the UI layer.

---

## 📚 Incident Log (Resolved Issues)

### [INCIDENT-001] [Date: YYYY-MM-DD]
**Error Signature:**
> `Error: Hydration failed because the initial UI does not match what was rendered on the server.`

**Context:**
Occurs when using `Date.now()` or random numbers directly in React components.

**Root Cause:**
Server-side rendering (SSR) generates a different timestamp/number than the client-side hydration.

**Solution:**
Move non-deterministic logic into a `useEffect` hook or use a stable seed.
```typescript
// BAD
<div>{Math.random()}</div>

// GOOD
const [val, setVal] = useState(null);
useEffect(() => setVal(Math.random()), []);

```

---

### [INCIDENT-002] [Date: YYYY-MM-DD]

**Error Signature:**

> `PrismaClientInitializationError: Can't reach database server at localhost:5432`

**Context:**
Running integration tests in the Docker container.

**Root Cause:**
The app container tries to access `localhost` (itself) instead of the `db` service name defined in `docker-compose.yml`.

**Solution:**
Ensure `DATABASE_URL` uses the hostname `postgres` (or service name), not `localhost`, when running inside Docker.

---

## 📥 New Entry Template

*Copy and paste this block when logging a new fix.*

### [INCIDENT-###] [Date: YYYY-MM-DD]

**Error Signature:**

> `Insert error message or log snippet here`

**Context:**
*What were you trying to do?*

**Root Cause:**
*Why did it fail?*

**Solution:**
*How was it fixed?*

```

---
