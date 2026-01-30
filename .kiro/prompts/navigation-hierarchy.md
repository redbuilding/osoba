# Navigation Hierarchy Design System

## Core Principle
**One header per level of meaning. Never more.**

Each layer has a single responsibility and answers one specific question for the user.

## Three-Layer Header System with Visual Hierarchy

### Layer 1: Global Header (AppHeader)
**Question Answered**: "What app am I in and how do I manage my session?"

**Visual Weight**: Light
**Height**: Small  
**Typography**: Small/medium weight

**Purpose**: Application shell - always present on EVERY screen, never changes meaning

**Contains**:
- App name/logo ("Awarda")
- User session control (Sign Out)
- Optional: Organization name (future)

**Does NOT contain**:
- Page titles, section names, role names, navigation breadcrumbs

**Implementation**: Use existing `AppHeader` component on EVERY screen
**Style**: Should feel almost invisible - minimal visual weight
**Alignment**: Uses `spacing.lg` padding to match section header alignment

**Critical Rule**: EVERY screen in the app must have the AppHeader - no exceptions

---

### Layer 2: Section Header (SectionHeader)
**Question Answered**: "Where am I in the system?"

**Visual Weight**: Medium (or subdued when task header present)
**Typography**: H2/semibold (or smaller when subdued)
**Background**: Neutral (no card, no shadow)

**Purpose**: Contextual section identification - appears when user is inside a section

**Contains**:
- Section title (e.g., "Admin", "Judges", "Entries", "Results")
- Descriptive subtitle explaining the section's purpose
- Optional role badge when relevant

**Examples**:
```
Admin
Manage awards, judges, and results
[Administrator badge]

Judges  
All judges in your organization

Judges (subdued on task pages)
Manage your judging panel
```

**Implementation**: Use `SectionHeader` component with optional `isSubdued={true}`
**Style**: Should feel like a chapter title - calm and informational, not actionable

**Critical Rule**: If a page has a task header, the section header must visually step back using `isSubdued={true}`

---

### Layer 3: Task Header (TaskHeader)  
**Question Answered**: "What am I doing right now?"

**Visual Weight**: Strongest on the page
**Typography**: H1/bold (24px, bold)
**Includes**: Optional back link, subtitle

**Purpose**: Task-specific header for interior pages where user performs an action

**Contains**:
- Clear task title (e.g., "Create Judge", "Review Entry", "Edit Award")
- Short clarifying subtitle
- Back navigation when appropriate
- Nothing else

**Examples**:
```
← Back
Create Judge
Add a new judge to your awards program

← Back
Review Entry
Evaluate submission against criteria
```

**Implementation**: Use `TaskHeader` component  
**Style**: Should feel like the top of a form or document - this is where attention should land

---

## Visual Hierarchy Rules

### The Golden Rule
**If a page has a task header, the section header must visually step back.**

Never let them compete for attention.

### Screen Type Patterns

#### Dashboard/List Screens (Section Only)
```
[Global Header: Awarda | Sign Out] ← REQUIRED ON EVERY SCREEN
[Section Header: Full weight - Section Name + Description]
[Content: Cards, lists, navigation items]
```

#### Task/Form Screens (Section + Task)
```
[Global Header: Awarda | Sign Out] ← REQUIRED ON EVERY SCREEN
[Section Header: Subdued - Section Name + Description]
[Task Header: Dominant - Task Name + Description + Back]
[Content: Form, details, actions]
```

#### Pure List Screens (Section + Task with Back Navigation)
```
[Global Header: Awarda | Sign Out] ← REQUIRED ON EVERY SCREEN
[Section Header: Subdued - Section Name + Description]
[Task Header: View/List Task + Back Navigation]
[Content: List items with metadata]
```

---

## Decision Framework

When adding any header element, ask these questions:

1. **Is this where I am?** → Section Header (Layer 2)
2. **Is this what I'm doing?** → Task Header (Layer 3)  
3. **Is this always present?** → Global Header (Layer 1)

**Critical Rule**: Never let one element answer more than one question.

---

## Implementation Components

### SectionHeader Component
```jsx
// Full weight (list/dashboard pages)
<SectionHeader 
  title="Section Name"
  subtitle="Description of what this section contains"
  badge="Optional Role Badge"
/>

// Subdued weight (task pages)
<SectionHeader 
  title="Section Name"
  subtitle="Description of what this section contains"
  isSubdued={true}
/>
```

### TaskHeader Component  
```jsx
<TaskHeader
  title="Task Name"
  subtitle="What the user is doing"
  onBack={() => navigation.goBack()}
/>
```

---

## Screen-Specific Guidelines

### Admin Dashboard
- ✅ Section header at full weight
- ✅ No task header needed
- ✅ Administrator badge appropriate

### View Judges (List Page with Navigation)
- ✅ AppHeader with sign out capability
- ✅ Section header subdued (`isSubdued={true}`)
- ✅ Task header with back navigation ("View Judges")
- ✅ Count text as metadata (small, light weight)
- ✅ Proper three-layer hierarchy for navigation

### Create Judge (Task Page)  
- ✅ Section header subdued (`isSubdued={true}`)
- ✅ Task header dominant (strongest text on page)
- ✅ Back navigation in task header
- ✅ Clear visual hierarchy: Task > Section > Global

---

## Anti-Patterns to Avoid

❌ **Competing Headers**: Multiple elements trying to be "the header"
❌ **Equal Visual Weight**: Section and task headers competing for attention
❌ **Redundant Titles**: Repeating the same information in different layers
❌ **Mixed Responsibilities**: One header answering multiple questions
❌ **Missing Hierarchy**: Task headers without subdued section headers

---

## Benefits of This System

✅ **Clear Visual Hierarchy**: Task headers dominate when present
✅ **Reduced Cognitive Load**: No competing information
✅ **Consistent Navigation**: Predictable user experience  
✅ **Scalable Architecture**: Easy to add new sections/tasks
✅ **Professional Feel**: Institutional credibility
✅ **Semantic Clarity**: Each element has clear purpose and weight
✅ **Calm Interface**: Proper visual emphasis prevents competition

---

## Usage Instructions

1. **ALWAYS start with AppHeader** on every single screen - no exceptions
2. **Ensure consistent alignment** - AppHeader uses `spacing.lg` padding to match section headers
3. **Add Section Header** when user enters a distinct area of the app
4. **Use `isSubdued={true}` on section headers** when task header is present
5. **Add Task Header with back navigation** for any screen that isn't the main dashboard
6. **Make task header the strongest element** on pages where it appears
7. **Include logout functionality** - every screen must allow user to sign out
8. **Test visual hierarchy** - task should dominate, section should recede
9. **Never stack redundant information** - each layer should add unique value

**Critical Rules**:
- Every screen has AppHeader with sign out
- List/detail screens need back navigation via TaskHeader
- Alignment between AppHeader and SectionHeader must be consistent

This system ensures every screen feels intentionally designed with proper visual emphasis and reduces user confusion through clear semantic hierarchy.
