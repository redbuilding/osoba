# Manual Testing Guide - Semantic Memory & Enhanced Heartbeat Systems

## Prerequisites
- Backend running: `uvicorn main:app --reload --port 8000`
- Frontend running: `npm run dev` (port 5173)
- MongoDB running
- Ollama running with `nomic-embed-text` model

---

## Part 1: Semantic Memory System Tests

### Test 1.1: Automatic Indexing
**Steps:**
1. Create a new conversation
2. Send 6+ messages back and forth with the AI
3. Wait 10 minutes (or modify interval in code for faster testing)
4. Check backend logs for "Indexing conversation" message

**Expected Result:**
- Conversation automatically indexed after 10 minutes of inactivity
- Backend logs show successful indexing
- No user action required

---

### Test 1.2: Manual Save to Memory
**Steps:**
1. Create a conversation with 5+ messages
2. Look for "💾 Save to Memory" button in chat interface
3. Click the button
4. Observe the button state change

**Expected Result:**
- Button appears after 5+ messages
- Button shows "Saving..." during operation
- Button changes to "Saved to Memory" with checkmark
- Conversation immediately indexed (check backend logs)

---

### Test 1.3: Memory Browser - Open & Search
**Steps:**
1. Press `Ctrl+Shift+M` (or `Cmd+Shift+M` on Mac)
2. Memory Browser modal opens
3. Enter search query: "Python pandas dataframe"
4. View results

**Expected Result:**
- Modal opens with search interface
- Search returns relevant conversations
- Each result shows:
  - Conversation title
  - Relevance score (e.g., "87% match")
  - Preview text snippet
  - Timestamp

---

### Test 1.4: Memory Browser - View Conversation
**Steps:**
1. Open Memory Browser (`Ctrl+Shift+M`)
2. Search for a topic
3. Click on a result to view full conversation

**Expected Result:**
- Clicking result navigates to that conversation
- Memory Browser closes
- Full conversation loads in main chat area

---

### Test 1.5: Memory Browser - Remove Conversation
**Steps:**
1. Open Memory Browser
2. Search for a conversation
3. Click "Remove" button on a result
4. Confirm removal

**Expected Result:**
- Confirmation dialog appears
- After confirmation, conversation removed from memory
- Result disappears from search results
- Conversation still exists in sidebar (not deleted, just unindexed)

---

### Test 1.6: Memory Statistics
**Steps:**
1. Go to Settings → Semantic Memory
2. View statistics section

**Expected Result:**
- Shows total indexed conversations
- Shows total chunks stored
- Shows storage usage in MB
- Shows last auto-index time

---

### Test 1.7: Manual Auto-Index Trigger
**Steps:**
1. Settings → Semantic Memory
2. Click "Trigger Auto-Index Now"
3. Wait for completion

**Expected Result:**
- Button shows "Running..." during operation
- Success message appears
- Statistics update with newly indexed conversations
- Backend logs show indexing activity

---

### Test 1.8: Clear All Memory
**Steps:**
1. Settings → Semantic Memory
2. Click "Clear All Memory"
3. Confirm in dialog
4. Check statistics

**Expected Result:**
- Confirmation dialog with warning
- After confirmation, all memory cleared
- Statistics show 0 conversations, 0 chunks
- Search returns no results
- Conversations still exist in sidebar

---

### Test 1.9: Semantic Search Context Injection
**Steps:**
1. Index several conversations about "React hooks"
2. Create a new conversation
3. Ask: "How do I use useEffect?"
4. Check if AI references previous conversations

**Expected Result:**
- AI response includes context from indexed conversations
- Response mentions "Based on previous conversations..." or similar
- More informed answer than without memory
- Backend logs show semantic search performed

---

### Test 1.10: Memory Indicator Badge
**Steps:**
1. Create a conversation with 5+ messages
2. Manually save to memory
3. Look at conversation in sidebar

**Expected Result:**
- Small badge/indicator appears on conversation
- Indicates conversation is indexed
- Badge persists across page refreshes

---

## Part 2: Enhanced Heartbeat System Tests

### Test 2.1: Basic Heartbeat Configuration
**Steps:**
1. Go to Settings → Proactive Heartbeat
2. Toggle "Enable Heartbeat" ON
3. Set interval to "30m" (for faster testing)
4. Set max insights to 5
5. Save settings

**Expected Result:**
- Settings save successfully
- Success message appears
- Heartbeat service starts running
- Backend logs show "Heartbeat service started"

---

### Test 2.2: Context Sources Configuration
**Steps:**
1. Settings → Proactive Heartbeat → Context Sources
2. Enable all 4 sources:
   - ✅ Semantic Memory
   - ✅ Git Repository
   - ✅ Project Files
   - ✅ System Health
3. Save configuration

**Expected Result:**
- All toggles turn purple (enabled state)
- Success message appears
- Next heartbeat will include all context sources

---

### Test 2.3: Manual Heartbeat Trigger
**Steps:**
1. Settings → Proactive Heartbeat
2. Ensure heartbeat is enabled
3. Click "Test Heartbeat Now"
4. Wait for completion
5. Check bell icon (🔔) in header

**Expected Result:**
- Button shows "Running..." during operation
- Success message: "Heartbeat triggered successfully"
- Bell icon shows badge with insight count
- Backend logs show context gathering and LLM call

---

### Test 2.4: View Insights in Panel
**Steps:**
1. Click bell icon (🔔) in header
2. View insights dropdown
3. Read insight details

**Expected Result:**
- Dropdown panel opens
- Shows list of insights with:
  - Title
  - Description
  - Timestamp (e.g., "2h ago")
  - "Create Task" button
  - "Dismiss" button (X)
- Badge shows unread count

---

### Test 2.5: Create Task from Insight (Manual)
**Steps:**
1. Open insights panel (🔔)
2. Click "Create Task" on an insight
3. Wait for completion
4. Open Tasks panel

**Expected Result:**
- Button shows "Creating..." during operation
- Button changes to "✓ Task Created" with green checkmark
- New task appears in Tasks panel
- Task title matches insight title
- Task description matches insight description
- Task metadata shows source: "heartbeat"

---

### Test 2.6: Auto-Create Tasks Configuration
**Steps:**
1. Settings → Proactive Heartbeat
2. Toggle "Auto-Create Tasks" ON
3. Save settings
4. Trigger manual heartbeat
5. Check Tasks panel

**Expected Result:**
- Toggle turns purple (enabled)
- Next heartbeat automatically creates tasks from insights
- Tasks appear in Tasks panel without manual action
- Insights panel still shows insights (not replaced)

---

### Test 2.7: Dismiss Insight
**Steps:**
1. Open insights panel (🔔)
2. Click X button on an insight
3. Observe panel update

**Expected Result:**
- Insight immediately disappears from list
- Badge count decreases by 1
- Dismissed insight won't reappear
- Other insights remain visible

---

### Test 2.8: Context Gathering - Memory
**Steps:**
1. Index several conversations (semantic memory)
2. Enable "Semantic Memory" context source
3. Trigger manual heartbeat
4. Check backend logs

**Expected Result:**
- Logs show "Gathering memory context"
- Logs show conversation count and storage stats
- Insight references memory usage if relevant
- Example: "You have 150 indexed conversations using 45MB"

---

### Test 2.9: Context Gathering - Git
**Steps:**
1. Ensure you're in a git repository
2. Make some uncommitted changes (edit files)
3. Enable "Git Repository" context source
4. Trigger manual heartbeat
5. Check insight

**Expected Result:**
- Logs show "Gathering git context"
- Logs show branch, uncommitted files, unpushed commits
- Insight suggests committing changes if 5+ uncommitted files
- Example: "You have 7 uncommitted files on branch 'main'"

---

### Test 2.10: Context Gathering - Project Files
**Steps:**
1. Add TODO/FIXME comments to code files
2. Enable "Project Files" context source
3. Trigger manual heartbeat
4. Check insight

**Expected Result:**
- Logs show "Gathering project context"
- Logs show TODO/FIXME counts
- Insight mentions TODO items if count is high
- Example: "You have 12 TODO comments and 3 FIXME items"

---

### Test 2.11: Context Gathering - System Health
**Steps:**
1. Enable "System Health" context source
2. Trigger manual heartbeat
3. Check insight

**Expected Result:**
- Logs show "Gathering system context"
- Logs show disk usage and service status
- Insight warns if disk usage > 90%
- Example: "Disk usage at 85%, consider cleanup"

---

### Test 2.12: HEARTBEAT.md File Creation
**Steps:**
1. Create `HEARTBEAT.md` in project root
2. Add content:
```markdown
# Heartbeat Tasks

## Memory Management
Schedule: 0 2 * * *
Enabled: true
Prompt: Review semantic memory usage
Context: memory

## Testing Reminders
Schedule: 0 9 * * 1
Enabled: true
Prompt: Check test coverage
Create_Task: true
Context: git,project
```
3. Save file
4. Go to Settings → Proactive Heartbeat

**Expected Result:**
- File status section shows "✓ HEARTBEAT.md found"
- Shows file path
- Shows "2 tasks defined"
- No validation errors

---

### Test 2.13: Sync from File
**Steps:**
1. Create HEARTBEAT.md (as above)
2. Settings → Proactive Heartbeat
3. Click "Load from File"
4. Wait for completion

**Expected Result:**
- Button shows "Syncing..." during operation
- Success message: "Synced 2 tasks from file"
- Tasks loaded into database
- Backend logs show file parsing

---

### Test 2.14: Sync to File
**Steps:**
1. Configure heartbeat tasks in UI
2. Settings → Proactive Heartbeat
3. Click "Save to File"
4. Check project root for HEARTBEAT.md

**Expected Result:**
- Button shows "Syncing..." during operation
- Success message with file path
- HEARTBEAT.md created/updated in project root
- File contains tasks in correct format

---

### Test 2.15: File Validation Errors
**Steps:**
1. Create HEARTBEAT.md with invalid content:
```markdown
## Invalid Task
Schedule: invalid_format
Enabled: true
```
2. Settings → Proactive Heartbeat
3. Check file status

**Expected Result:**
- File status shows validation errors
- Red error box lists specific issues
- "Load from File" button disabled
- Error message: "Invalid schedule format 'invalid_format'"

---

### Test 2.16: HEARTBEAT_OK Response
**Steps:**
1. Set up goals with all items completed
2. Ensure no uncommitted changes
3. Trigger manual heartbeat
4. Check insights panel

**Expected Result:**
- No new insights appear
- Backend logs show "HEARTBEAT_OK, no insights needed"
- Bell icon shows no badge
- System recognizes everything is on track

---

### Test 2.17: Daily Insight Limit
**Steps:**
1. Set max insights to 2
2. Trigger heartbeat 3 times manually
3. Check insights panel

**Expected Result:**
- First 2 heartbeats create insights
- Third heartbeat blocked
- Backend logs: "Daily insight limit reached (2/2)"
- No new insights after limit

---

### Test 2.18: Enhanced Context in Prompt
**Steps:**
1. Enable all context sources
2. Trigger manual heartbeat
3. Check backend logs for prompt content

**Expected Result:**
- Logs show "PROJECT CONTEXT:" section
- Shows memory stats (conversations, storage)
- Shows git status (branch, uncommitted files)
- Shows project stats (TODOs, recent files)
- Shows system stats (disk usage)
- All context included in LLM prompt

---

### Test 2.19: Task-Insight Linking
**Steps:**
1. Create task from insight
2. Go to Tasks panel
3. View task details/metadata

**Expected Result:**
- Task metadata shows:
  - `source: "heartbeat"`
  - `insight_id: "<insight_id>"`
- Task linked to original insight
- Can trace task back to insight

---

### Test 2.20: Heartbeat with Goals
**Steps:**
1. Settings → Goals & Priorities
2. Enter goals document:
```
SHORT-TERM:
- Complete authentication feature
- Fix payment bug

BLOCKERS:
- Waiting on design mockups
```
3. Save goals
4. Trigger heartbeat
5. Check insight

**Expected Result:**
- Insight references goals
- Suggests next steps for goals
- Identifies blockers
- Example: "Follow up on design mockups - blocking auth feature"

---

## Part 3: Integration Tests (Memory + Heartbeat)

### Test 3.1: Heartbeat Uses Semantic Memory
**Steps:**
1. Index conversations about "React performance"
2. Enable "Semantic Memory" context source
3. Set goal: "Optimize React app performance"
4. Trigger heartbeat
5. Check insight

**Expected Result:**
- Insight references indexed conversations
- Suggests reviewing previous React discussions
- More informed recommendations
- Example: "Based on your 5 conversations about React performance..."

---

### Test 3.2: Memory Search from Heartbeat Insight
**Steps:**
1. Receive insight: "Review previous API discussions"
2. Open Memory Browser (`Ctrl+Shift+M`)
3. Search for "API"
4. View relevant conversations

**Expected Result:**
- Search returns API-related conversations
- Can quickly find referenced discussions
- Seamless workflow from insight to memory

---

### Test 3.3: Full Workflow Test
**Steps:**
1. Have 10+ indexed conversations
2. Enable all context sources
3. Set meaningful goals
4. Enable auto-create tasks
5. Trigger heartbeat
6. Review insights
7. Check tasks panel
8. Search memory for context

**Expected Result:**
- Heartbeat gathers all context
- Creates relevant insights
- Auto-creates tasks
- Tasks appear in panel
- Can search memory for details
- Complete end-to-end workflow

---

## Test Execution Checklist

### Semantic Memory (10 tests)
- [ ] Test 1.1: Automatic Indexing
- [ ] Test 1.2: Manual Save to Memory
- [ ] Test 1.3: Memory Browser - Open & Search
- [ ] Test 1.4: Memory Browser - View Conversation
- [ ] Test 1.5: Memory Browser - Remove Conversation
- [ ] Test 1.6: Memory Statistics
- [ ] Test 1.7: Manual Auto-Index Trigger
- [ ] Test 1.8: Clear All Memory
- [ ] Test 1.9: Semantic Search Context Injection
- [ ] Test 1.10: Memory Indicator Badge

### Enhanced Heartbeat (20 tests)
- [ ] Test 2.1: Basic Heartbeat Configuration
- [ ] Test 2.2: Context Sources Configuration
- [ ] Test 2.3: Manual Heartbeat Trigger
- [ ] Test 2.4: View Insights in Panel
- [ ] Test 2.5: Create Task from Insight (Manual)
- [ ] Test 2.6: Auto-Create Tasks Configuration
- [ ] Test 2.7: Dismiss Insight
- [ ] Test 2.8: Context Gathering - Memory
- [ ] Test 2.9: Context Gathering - Git
- [ ] Test 2.10: Context Gathering - Project Files
- [ ] Test 2.11: Context Gathering - System Health
- [ ] Test 2.12: HEARTBEAT.md File Creation
- [ ] Test 2.13: Sync from File
- [ ] Test 2.14: Sync to File
- [ ] Test 2.15: File Validation Errors
- [ ] Test 2.16: HEARTBEAT_OK Response
- [ ] Test 2.17: Daily Insight Limit
- [ ] Test 2.18: Enhanced Context in Prompt
- [ ] Test 2.19: Task-Insight Linking
- [ ] Test 2.20: Heartbeat with Goals

### Integration (3 tests)
- [ ] Test 3.1: Heartbeat Uses Semantic Memory
- [ ] Test 3.2: Memory Search from Heartbeat Insight
- [ ] Test 3.3: Full Workflow Test

**Total: 33 Manual Tests**

---

## Notes

- Tests can be run in any order, but integration tests should be last
- Some tests require waiting (10 minutes for auto-index) - can be shortened by modifying code temporarily
- Backend logs are crucial for verifying internal behavior
- All tests should pass without errors or crashes
- UI should remain responsive throughout all operations

---

## Quick Test Commands

### Backend Logs
```bash
# Watch backend logs in real-time
cd backend && uvicorn main:app --reload --port 8000
```

### Check Ollama Model
```bash
ollama list | grep nomic-embed-text
```

### Check MongoDB
```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017/mcp_chat_db

# Check collections
show collections

# Check indexed conversations
db.conversations.find({indexed: true}).count()
```

### Check ChromaDB Storage
```bash
# Check .chroma directory size
du -sh .chroma
```

---

## Troubleshooting

### Semantic Memory Issues
- **No results in search**: Ensure conversations are indexed (check backend logs)
- **Slow indexing**: Check Ollama is running and nomic-embed-text model is available
- **Storage errors**: Check disk space and .chroma directory permissions

### Heartbeat Issues
- **No insights**: Check heartbeat is enabled and interval has passed
- **Context not gathering**: Check context sources are enabled
- **File sync errors**: Check HEARTBEAT.md syntax and file permissions

### General Issues
- **Backend errors**: Check MongoDB and Ollama are running
- **Frontend errors**: Check backend API is accessible at http://localhost:8000
- **Performance issues**: Check system resources (CPU, memory, disk)
