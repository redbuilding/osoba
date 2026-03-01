# Osoba Brand Standards Guide

## Overview
This document defines the visual identity and design standards for the Osoba chat application frontend. The design follows a modern dark theme with purple and blue accents, emphasizing readability and user experience.

## Color Palette

### Primary Colors
- **Brand Purple**: `#A78BFA` - Primary brand color used for logos, primary buttons, and key interactive elements
- **Brand Blue**: `#60A5FA` - Secondary brand color for accents and tool indicators
- **Brand Accent**: `#FCD34D` - Yellow-orange accent for highlights and special emphasis

### Background Colors
- **Main Background**: `#121212` - Primary application background (dark charcoal)
- **Surface Background**: `#1E1E1E` - Secondary background for cards, panels, and content containers
- **Border Gray**: `#374151` (gray-700) - Standard border color for separating elements

### Text Colors
- **Primary Text**: `#FFFFFF` - Main text color (white) for high contrast readability
- **Secondary Text**: `#D1D5DB` - Muted text for labels, descriptions, and less important content
- **Accent Text**: `#A78BFA` - Purple text for brand elements and special emphasis

### Status Colors
- **Success Green**: `#10B981` - Success states, connected indicators, positive actions
- **Alert Red**: `#EF4444` - Error states, disconnected indicators, destructive actions
- **Stat Blue**: `#3B82F6` - Interactive elements, links, informational states

### Button Gradients
- **Button Gradient From**: `#7C3AED` - Start color for primary button gradients
- **Button Gradient To**: `#8B5CF6` - End color for primary button gradients

## Typography

### Font Family
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "AppleColorEmoji", "Segoe UI Emoji", "Segoe UI Symbol";
```
- Uses system fonts for optimal performance and native feel
- Includes emoji support for cross-platform compatibility

### Font Weights
- **Regular**: 400 - Standard body text
- **Semibold**: 600 - Headings, emphasis, and important labels
- **Bold**: 700 - Strong emphasis (used sparingly)

### Text Sizes
- **Extra Small**: `text-xs` (12px) - Status indicators, metadata, secondary information
- **Small**: `text-sm` (14px) - Labels, captions, tool descriptions
- **Base**: `text-base` (16px) - Primary body text, chat messages
- **Large**: `text-lg` (18px) - Section headings
- **Extra Large**: `text-xl` (20px) - Page titles, main headings

## Layout & Spacing

### Container Structure
- **Full Height Layout**: `h-screen` - Application uses full viewport height
- **Flexbox Layout**: Primary layout uses flexbox for responsive design
- **Sidebar Width**: 320px (expanded), 64px (collapsed)
- **Header Height**: Auto-sizing with padding of 16px (`p-4`)

### Spacing Scale
- **Tight**: `space-y-2` (8px) - Between related elements
- **Normal**: `space-y-4` (16px) - Between sections
- **Loose**: `space-y-6` (24px) - Between major components

### Padding & Margins
- **Small**: `p-2` (8px) - Buttons, small containers
- **Medium**: `p-3` (12px) - Cards, message bubbles
- **Large**: `p-4` (16px) - Main containers, headers
- **Extra Large**: `p-6` (24px) - Modal dialogs, major sections

## Component Styling

### Buttons

#### Primary Button
```css
bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to 
transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-blue
```

#### Secondary Button
```css
bg-gray-700 hover:bg-gray-600 text-white rounded
```

#### Icon Button
```css
p-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple
```

### Cards & Containers

#### Surface Card
```css
bg-brand-surface-bg rounded-lg shadow border border-gray-700
```

#### Chat Message Bubble
```css
max-w-[70%] p-3 rounded-lg shadow bg-brand-surface-bg text-brand-text-primary
```

### Form Elements

#### Input Fields
```css
bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
focus:outline-none focus:ring-1 focus:ring-brand-purple rounded
```

#### Select Dropdowns
```css
bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
focus:outline-none focus:ring-1 focus:ring-brand-purple rounded
```

### Status Indicators

#### Success Indicator
```css
w-2 h-2 rounded-full bg-brand-success-green
```

#### Error Indicator
```css
w-2 h-2 rounded-full bg-brand-alert-red
```

#### Tool Indicators
- **Web Search**: Blue border-left (`border-brand-blue`)
- **Database**: Purple border-left (`border-brand-purple`)
- **HubSpot**: Orange border-left (`border-orange-500`)
- **Python**: Green border-left (`border-green-500`)

## Interactive States

### Hover Effects
- **Buttons**: Slight color darkening with 200ms transition
- **Cards**: Subtle background lightening (`hover:bg-gray-700`)
- **Links**: Color change to brand purple

### Focus States
- **Ring Style**: `focus:ring-2 focus:ring-brand-purple`
- **Outline**: `focus:outline-none` (custom ring replaces default outline)

### Loading States
- **Spinner**: Brand purple color with spin animation
- **Pulse**: `animate-pulse` for loading placeholders

## Animations & Transitions

### Standard Transitions
```css
transition-colors duration-200
transition-all duration-300 ease-in-out
```

### Custom Animations
- **Fade In**: 0.5s ease-out
- **Slide Up**: 0.5s ease-out with 20px transform
- **Spin**: Continuous rotation for loading indicators

## Accessibility

### Color Contrast
- All text meets WCAG AA standards against dark backgrounds
- Status colors provide sufficient contrast for visibility
- Focus indicators are clearly visible

### Interactive Elements
- Minimum 44px touch target size for mobile
- Clear focus indicators for keyboard navigation
- Semantic HTML structure with proper ARIA labels

## Responsive Design

### Breakpoints
- **Mobile**: Default styles (< 640px)
- **Small**: `sm:` prefix (≥ 640px)
- **Medium**: `md:` prefix (≥ 768px)
- **Large**: `lg:` prefix (≥ 1024px)

### Mobile Adaptations
- Collapsible sidebar for mobile screens
- Responsive text sizing with `sm:` variants
- Touch-friendly button sizes
- Horizontal scrolling for overflow content

## Code Blocks & Syntax

### Code Styling
```css
background-color: #1f2937;
color: #f9fafb;
font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
```

### Inline Code
```css
background-color: #f3f4f6;
padding: 0.2em 0.4em;
border-radius: 3px;
font-size: 0.9em;
```

## Scrollbars

### Custom Scrollbar Styling
```css
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: brand-surface-bg;
}
::-webkit-scrollbar-thumb {
    background: brand-purple;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: brand-button-grad-to;
}
```

## Usage Guidelines

### Do's
- Use brand purple for primary actions and brand elements
- Maintain consistent spacing using the defined scale
- Apply hover and focus states to all interactive elements
- Use semantic color coding for status indicators
- Ensure sufficient contrast for all text elements

### Don'ts
- Don't use colors outside the defined palette
- Don't mix different spacing scales within the same component
- Don't remove focus indicators for accessibility
- Don't use pure black or pure white (use brand colors instead)
- Don't apply animations longer than 500ms for UI interactions

## Implementation Notes

### Tailwind Configuration
The brand colors are defined in `tailwind.config.js` under the `brand` namespace, allowing for consistent usage across all components with classes like `bg-brand-purple` and `text-brand-text-primary`.

### CSS Custom Properties
Base styles are defined in `index.css` using Tailwind's `@layer` directive, ensuring proper cascade and specificity management.

### Component Consistency
All components follow the established patterns for spacing, colors, and interactive states to maintain visual coherence throughout the application.
